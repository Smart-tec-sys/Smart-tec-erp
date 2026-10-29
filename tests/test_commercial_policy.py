"""Testes isolados da politica: executar somente este arquivo com python -I -B.

Usa biblioteca padrao, dados ficticios, importacao direta do arquivo puro e
bloqueios de rede/ERP/framework/banco. Nenhuma importacao de app.main/database,
carregamento de .env, DDL ou instalacao de pacote.
"""
import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import http.client
import importlib.abc
import importlib.util
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch
import urllib.request

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "app" / "tenant" / "commercial_policy.py"
NETWORK_ATTEMPTS = []


def forbid_network(*args, **kwargs):
    NETWORK_ATTEMPTS.append(True)
    raise AssertionError("Rede proibida nos testes da politica")


for target in (
    "socket.create_connection", "socket.getaddrinfo",
    "socket.socket.connect", "socket.socket.connect_ex",
    "socket.socket.bind", "socket.socket.sendto",
    "urllib.request.urlopen", "urllib.request.OpenerDirector.open",
    "http.client.HTTPConnection.connect", "http.client.HTTPSConnection.connect",
):
    guard = patch(target, side_effect=forbid_network)
    guard.start()
    unittest.addModuleCleanup(guard.stop)


class BlockExternalImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".", 1)[0]
        if root in {"app", "fastapi", "sqlalchemy", "psycopg", "psycopg2",
                    "asyncpg", "requests", "httpx", "dotenv"}:
            raise AssertionError("Dependencia externa proibida")


import_guard = BlockExternalImports()
sys.meta_path.insert(0, import_guard)
unittest.addModuleCleanup(sys.meta_path.remove, import_guard)
spec = importlib.util.spec_from_file_location("smarttec_pure_commercial_policy", POLICY_PATH)
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
unittest.addModuleCleanup(sys.modules.pop, spec.name, None)
spec.loader.exec_module(p)

UTC = timezone.utc
START = datetime(2026, 10, 1, 3, tzinfo=UTC)
END = datetime(2026, 11, 1, 3, tzinfo=UTC)
NOW = datetime(2026, 10, 17, 15, tzinfo=UTC)
PAID_AT = START - timedelta(days=1)
WINDOW = p.Periodo(START, END)
QUERY = p.ConsultaAcesso(empresa_id=7, modulo_id=11, agora=NOW)


def paid_cycle(identifier=501, window=WINDOW):
    confirmation = p.ConfirmacaoPagamento(
        auditoria_id=identifier + 1000, empresa_id=7, assinatura_id=40,
        cobranca_id=identifier, periodo=window, confirmado_em=PAID_AT,
    )
    return p.CicloCobranca(
        id=identifier, empresa_id=7, assinatura_id=40, tipo=p.TipoCobranca.ASSINATURA,
        estado=p.EstadoPagamento.PAGO, periodo=window, pago_em=PAID_AT,
        confirmacao=confirmation,
    )


def paid_evidence():
    return p.EvidenciasComerciais(
        assinaturas_candidatas=(p.Assinatura(40, 7, p.EstadoAssinatura.ATIVA, 3),),
        ciclos=(paid_cycle(),),
        concessoes=(p.ConcessaoModulo(
            61, 7, 40, 11, p.OrigemConcessao.PLANO, p.EstadoConcessao.ATIVO,
            WINDOW, plano_id=3, incluido_no_plano=True,
        ),),
        completas=True,
    )


def change_subscription(evidence, **values):
    return replace(evidence, assinaturas_candidatas=(replace(evidence.assinaturas_candidatas[0], **values),))


def change_cycle(evidence, **values):
    return replace(evidence, ciclos=(replace(evidence.ciclos[0], **values),))


def change_grant(evidence, **values):
    return replace(evidence, concessoes=(replace(evidence.concessoes[0], **values),))


def trial_evidence():
    evidence = change_subscription(paid_evidence(), estado=p.EstadoAssinatura.TRIAL, periodo_trial=WINDOW)
    return change_grant(replace(evidence, ciclos=()), origem=p.OrigemConcessao.TRIAL, incluido_no_plano=False)


def cancelled_evidence(mode=p.ModalidadeCancelamento.FIM_VIGENCIA, **changes):
    cancel = p.Cancelamento(mode, 3001, 7, 40, NOW - timedelta(days=1), END)
    cancel = replace(cancel, **changes)
    return change_subscription(paid_evidence(), estado=p.EstadoAssinatura.CANCELADA, cancelamento=cancel)


def extra_grant(origin=p.OrigemConcessao.CORTESIA):
    proof = p.ConfirmacaoConcessao(4001, 7, 40, 62, 22, origin, WINDOW, PAID_AT)
    return p.ConcessaoModulo(
        62, 7, 40, 22, origin, p.EstadoConcessao.ATIVO, WINDOW, confirmacao=proof,
    )


class CommercialPolicyTests(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(NETWORK_ATTEMPTS, [])
        self.assertFalse(any(name == "app" or name.startswith("app.") for name in sys.modules))

    def assert_decision(self, evidence, reason, query=QUERY):
        result = p.avaliar_acesso_comercial(query, evidence)
        self.assertIs(type(result), p.DecisaoAcesso)
        self.assertIs(result.motivo, reason)
        self.assertIs(result.permitido, reason in (p.MotivoAcesso.PAGO_PERMITIDO, p.MotivoAcesso.TRIAL_PERMITIDO))
        return result

    def test_valid_paid_subscription(self):
        self.assert_decision(paid_evidence(), p.MotivoAcesso.PAGO_PERMITIDO)

    def test_all_contract_states_with_paid_evidence(self):
        expected = {
            p.EstadoAssinatura.ATIVA: p.MotivoAcesso.PAGO_PERMITIDO,
            p.EstadoAssinatura.PROXIMA_VENCIMENTO: p.MotivoAcesso.PAGO_PERMITIDO,
            p.EstadoAssinatura.PENDENTE: p.MotivoAcesso.ASSINATURA_PENDENTE,
            p.EstadoAssinatura.SUSPENSA: p.MotivoAcesso.ASSINATURA_SUSPENSA,
            p.EstadoAssinatura.VENCIDA: p.MotivoAcesso.ASSINATURA_VENCIDA,
            p.EstadoAssinatura.TRIAL_EXPIRADO: p.MotivoAcesso.COBERTURA_ENCERRADA,
            p.EstadoAssinatura.CANCELADA: p.MotivoAcesso.CANCELAMENTO_AMBIGUO,
            p.EstadoAssinatura.TRIAL: p.MotivoAcesso.TRIAL_INVALIDO,
        }
        self.assertEqual(set(expected), set(p.EstadoAssinatura))
        for state, reason in expected.items():
            with self.subTest(state=state):
                self.assert_decision(change_subscription(paid_evidence(), estado=state), reason)

    def test_paid_period_exact_boundaries(self):
        cases = (
            (START - timedelta(microseconds=1), p.MotivoAcesso.COBERTURA_FUTURA),
            (START, p.MotivoAcesso.PAGO_PERMITIDO),
            (END - timedelta(microseconds=1), p.MotivoAcesso.PAGO_PERMITIDO),
            (END, p.MotivoAcesso.COBERTURA_ENCERRADA),
            (END + timedelta(microseconds=1), p.MotivoAcesso.COBERTURA_ENCERRADA),
        )
        for now, reason in cases:
            with self.subTest(now=now):
                self.assert_decision(paid_evidence(), reason, replace(QUERY, agora=now))

    def test_payment_without_admin_confirmation(self):
        self.assert_decision(change_cycle(paid_evidence(), confirmacao=None),
                             p.MotivoAcesso.CONFIRMACAO_ADMINISTRATIVA_AUSENTE)

    def test_paid_status_without_payment_date(self):
        self.assert_decision(change_cycle(paid_evidence(), pago_em=None),
                             p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_confirmation_without_payment(self):
        self.assert_decision(change_cycle(paid_evidence(), estado=p.EstadoPagamento.PENDENTE, pago_em=None),
                             p.MotivoAcesso.CONFIRMACAO_INCONSISTENTE)

    def test_unpaid_refunded_cancelled_states_never_prove_payment(self):
        for state in p.EstadoPagamento:
            if state is p.EstadoPagamento.PAGO:
                continue
            with self.subTest(state=state):
                evidence = change_cycle(paid_evidence(), estado=state, pago_em=None, confirmacao=None)
                self.assert_decision(evidence, p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_future_payment_or_confirmation(self):
        future = NOW + timedelta(seconds=1)
        evidence = paid_evidence()
        for changed in (
            change_cycle(evidence, pago_em=future),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, confirmado_em=future)),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, confirmado_em=PAID_AT - timedelta(seconds=1))),
        ):
            with self.subTest(evidence=changed):
                self.assertFalse(p.avaliar_acesso_comercial(QUERY, changed).permitido)

    def test_payment_of_other_type_is_not_subscription_proof(self):
        self.assert_decision(change_cycle(paid_evidence(), tipo=p.TipoCobranca.MODULO_AVULSO),
                             p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_no_payment_even_if_contract_active(self):
        self.assert_decision(replace(paid_evidence(), ciclos=()), p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_valid_trial(self):
        self.assert_decision(trial_evidence(), p.MotivoAcesso.TRIAL_PERMITIDO)

    def test_trial_boundaries_and_missing_window(self):
        self.assert_decision(change_subscription(trial_evidence(), periodo_trial=None), p.MotivoAcesso.TRIAL_INVALIDO)
        for now, reason in (
            (START - timedelta(microseconds=1), p.MotivoAcesso.COBERTURA_FUTURA),
            (START, p.MotivoAcesso.TRIAL_PERMITIDO),
            (END - timedelta(microseconds=1), p.MotivoAcesso.TRIAL_PERMITIDO),
            (END, p.MotivoAcesso.COBERTURA_ENCERRADA),
        ):
            with self.subTest(now=now):
                self.assert_decision(trial_evidence(), reason, replace(QUERY, agora=now))

    def test_trial_requires_explicit_module(self):
        self.assert_decision(replace(trial_evidence(), concessoes=()), p.MotivoAcesso.MODULO_NAO_CONTRATADO)
        self.assert_decision(change_grant(trial_evidence(), origem=p.OrigemConcessao.PLANO, incluido_no_plano=True),
                             p.MotivoAcesso.CONCESSAO_NAO_COMPROVADA)

    def test_explicit_trial_grant_without_plan_is_not_general_access(self):
        evidence = change_subscription(trial_evidence(), plano_id=None)
        evidence = change_grant(evidence, plano_id=None)
        self.assert_decision(evidence, p.MotivoAcesso.TRIAL_PERMITIDO)
        self.assert_decision(evidence, p.MotivoAcesso.MODULO_NAO_CONTRATADO, replace(QUERY, modulo_id=999))

    def test_unknown_or_missing_module(self):
        self.assert_decision(paid_evidence(), p.MotivoAcesso.MODULO_NAO_CONTRATADO, replace(QUERY, modulo_id=999))
        self.assert_decision(replace(paid_evidence(), concessoes=()), p.MotivoAcesso.MODULO_NAO_CONTRATADO)

    def test_grant_requires_correct_plan_and_inclusion(self):
        for values in ({"plano_id": 999}, {"plano_id": None}, {"incluido_no_plano": False},
                       {"origem": p.OrigemConcessao.TRIAL}):
            with self.subTest(values=values):
                self.assert_decision(change_grant(paid_evidence(), **values), p.MotivoAcesso.CONCESSAO_NAO_COMPROVADA)

    def test_inactive_or_expired_grant_never_authorizes(self):
        for state in p.EstadoConcessao:
            if state is p.EstadoConcessao.ATIVO:
                continue
            with self.subTest(state=state):
                self.assert_decision(change_grant(paid_evidence(), estado=state), p.MotivoAcesso.MODULO_NAO_CONTRATADO)
        for window in (p.Periodo(START, NOW), p.Periodo(NOW + timedelta(seconds=1), END)):
            self.assert_decision(change_grant(paid_evidence(), periodo=window), p.MotivoAcesso.MODULO_NAO_CONTRATADO)

    def test_module_block_overrides_valid_plan(self):
        self.assert_decision(replace(paid_evidence(), modulos_bloqueados=(11,)), p.MotivoAcesso.MODULO_BLOQUEADO)
        self.assert_decision(replace(paid_evidence(), modulos_bloqueados=(22,)), p.MotivoAcesso.PAGO_PERMITIDO)

    def test_foreign_company_at_each_level_never_authorizes(self):
        evidence = paid_evidence()
        for changed in (
            change_subscription(evidence, empresa_id=8),
            change_cycle(evidence, empresa_id=8),
            change_grant(evidence, empresa_id=8),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, empresa_id=8)),
        ):
            with self.subTest(evidence=changed):
                self.assert_decision(changed, p.MotivoAcesso.EMPRESA_DIVERGENTE)
        self.assert_decision(evidence, p.MotivoAcesso.EMPRESA_DIVERGENTE, replace(QUERY, empresa_id=8))

    def test_wrong_contract_and_payment_proof_links(self):
        evidence = paid_evidence()
        for changed in (
            change_cycle(evidence, assinatura_id=41),
            change_grant(evidence, assinatura_id=41),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, assinatura_id=41)),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, cobranca_id=999)),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, periodo=p.Periodo(START, NOW))),
        ):
            with self.subTest(evidence=changed):
                self.assert_decision(changed, p.MotivoAcesso.VINCULO_DIVERGENTE)

    def test_pending_renewal_preserves_current_paid_cycle(self):
        evidence = paid_evidence()
        renewal = replace(evidence.ciclos[0], id=502, estado=p.EstadoPagamento.PENDENTE,
                          periodo=p.Periodo(END, END + timedelta(days=30)), pago_em=None, confirmacao=None)
        evidence = replace(evidence, ciclos=(*evidence.ciclos, renewal))
        self.assert_decision(evidence, p.MotivoAcesso.PAGO_PERMITIDO)
        self.assert_decision(evidence, p.MotivoAcesso.COBERTURA_ENCERRADA, replace(QUERY, agora=END))

    def test_adjacent_paid_cycles_and_future_coverage(self):
        current = paid_cycle()
        future = paid_cycle(502, p.Periodo(END, END + timedelta(days=30)))
        evidence = replace(paid_evidence(), ciclos=(current, future),
                           concessoes=(replace(paid_evidence().concessoes[0], periodo=p.Periodo(START, future.periodo.fim)),))
        self.assert_decision(evidence, p.MotivoAcesso.PAGO_PERMITIDO)
        self.assert_decision(evidence, p.MotivoAcesso.PAGO_PERMITIDO, replace(QUERY, agora=END))
        self.assert_decision(replace(evidence, ciclos=(future,)), p.MotivoAcesso.COBERTURA_FUTURA)

    def test_future_cycle_does_not_bridge_unpaid_gap(self):
        evidence = paid_evidence()
        future = paid_cycle(502, p.Periodo(END + timedelta(days=3), END + timedelta(days=30)))
        self.assertFalse(p.avaliar_acesso_comercial(
            replace(QUERY, agora=END + timedelta(days=1)),
            replace(evidence, ciclos=(*evidence.ciclos, future)),
        ).permitido)

    def test_cancel_at_end_keeps_only_paid_coverage(self):
        self.assert_decision(cancelled_evidence(), p.MotivoAcesso.PAGO_PERMITIDO)
        self.assert_decision(cancelled_evidence(), p.MotivoAcesso.COBERTURA_ENCERRADA, replace(QUERY, agora=END))
        self.assert_decision(replace(cancelled_evidence(), ciclos=()), p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO)

    def test_cancellation_does_not_extend_payment(self):
        evidence = cancelled_evidence(fim_vigencia=END + timedelta(days=30))
        self.assert_decision(evidence, p.MotivoAcesso.COBERTURA_ENCERRADA, replace(QUERY, agora=END))

    def test_end_cancellation_cannot_silently_shorten_paid_coverage(self):
        evidence = cancelled_evidence(fim_vigencia=NOW + timedelta(hours=1))
        self.assert_decision(evidence, p.MotivoAcesso.CANCELAMENTO_AMBIGUO)
        self.assert_decision(evidence, p.MotivoAcesso.CANCELAMENTO_AMBIGUO,
                             replace(QUERY, agora=NOW + timedelta(hours=1)))

    def test_immediate_revocation_overrides_paid_cycle_or_trial(self):
        cancel = cancelled_evidence(p.ModalidadeCancelamento.IMEDIATO).assinaturas_candidatas[0].cancelamento
        for evidence in (paid_evidence(), trial_evidence()):
            self.assert_decision(change_subscription(evidence, cancelamento=cancel), p.MotivoAcesso.ACESSO_REVOGADO)

    def test_ambiguous_or_unproved_cancellation_is_denied(self):
        for evidence in (
            change_subscription(paid_evidence(), estado=p.EstadoAssinatura.CANCELADA),
            cancelled_evidence(p.ModalidadeCancelamento.DESCONHECIDA),
            cancelled_evidence(fim_vigencia=None),
            cancelled_evidence(confirmado_em=NOW + timedelta(seconds=1)),
            cancelled_evidence(fim_vigencia=NOW - timedelta(days=2)),
        ):
            with self.subTest(evidence=evidence):
                self.assert_decision(evidence, p.MotivoAcesso.CANCELAMENTO_AMBIGUO)

    def test_cancellation_company_and_contract_links(self):
        self.assert_decision(cancelled_evidence(empresa_id=8), p.MotivoAcesso.EMPRESA_DIVERGENTE)
        self.assert_decision(cancelled_evidence(assinatura_id=41), p.MotivoAcesso.VINCULO_DIVERGENTE)

    def test_contract_conflicts_and_absence(self):
        evidence = paid_evidence()
        self.assert_decision(replace(evidence, assinaturas_candidatas=()), p.MotivoAcesso.ASSINATURA_AUSENTE)
        self.assert_decision(replace(evidence, conflito_impeditivo=True), p.MotivoAcesso.CONTRATOS_CONFLITANTES)
        self.assert_decision(replace(evidence, assinaturas_candidatas=(
            *evidence.assinaturas_candidatas, replace(evidence.assinaturas_candidatas[0], id=41),
        )), p.MotivoAcesso.CONTRATOS_CONFLITANTES)

    def test_overlapping_duplicate_and_pending_cycle_conflicts(self):
        evidence = paid_evidence()
        for other in (
            evidence.ciclos[0],
            paid_cycle(502),
            replace(paid_cycle(502), estado=p.EstadoPagamento.PENDENTE, pago_em=None, confirmacao=None),
        ):
            with self.subTest(cycle=other):
                self.assert_decision(replace(evidence, ciclos=(*evidence.ciclos, other)),
                                     p.MotivoAcesso.CICLOS_CONFLITANTES)

    def test_cancelled_charge_does_not_erase_valid_payment(self):
        evidence = paid_evidence()
        cancelled = replace(evidence.ciclos[0], id=502, estado=p.EstadoPagamento.CANCELADO,
                            pago_em=None, confirmacao=None)
        self.assert_decision(replace(evidence, ciclos=(*evidence.ciclos, cancelled)), p.MotivoAcesso.PAGO_PERMITIDO)

    def test_extra_rights_are_restricted_to_the_explicit_module(self):
        for origin in (p.OrigemConcessao.CORTESIA, p.OrigemConcessao.AVULSO):
            with self.subTest(origin=origin):
                evidence = replace(paid_evidence(), concessoes=(extra_grant(origin),))
                self.assert_decision(evidence, p.MotivoAcesso.PAGO_PERMITIDO, replace(QUERY, modulo_id=22))
                self.assert_decision(evidence, p.MotivoAcesso.MODULO_NAO_CONTRATADO)
                self.assert_decision(evidence, p.MotivoAcesso.MODULO_NAO_CONTRATADO, replace(QUERY, modulo_id=999))

    def test_extra_right_does_not_replace_base_coverage(self):
        evidence = replace(paid_evidence(), concessoes=(extra_grant(),))
        query = replace(QUERY, modulo_id=22)
        self.assert_decision(replace(evidence, ciclos=()), p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO, query)
        self.assert_decision(change_subscription(evidence, estado=p.EstadoAssinatura.SUSPENSA),
                             p.MotivoAcesso.ASSINATURA_SUSPENSA, query)
        self.assert_decision(change_subscription(evidence, estado=p.EstadoAssinatura.PENDENTE),
                             p.MotivoAcesso.ASSINATURA_PENDENTE, query)

    def test_extra_right_requires_bound_current_admin_proof(self):
        grant = extra_grant()
        evidence = replace(paid_evidence(), concessoes=(grant,))
        query = replace(QUERY, modulo_id=22)
        for proof, reason in (
            (None, p.MotivoAcesso.CONCESSAO_NAO_COMPROVADA),
            (replace(grant.confirmacao, confirmado_em=NOW + timedelta(seconds=1)), p.MotivoAcesso.CONCESSAO_NAO_COMPROVADA),
            (replace(grant.confirmacao, empresa_id=8), p.MotivoAcesso.EMPRESA_DIVERGENTE),
            (replace(grant.confirmacao, modulo_id=11), p.MotivoAcesso.VINCULO_DIVERGENTE),
            (replace(grant.confirmacao, concessao_id=999), p.MotivoAcesso.VINCULO_DIVERGENTE),
            (replace(grant.confirmacao, assinatura_id=41), p.MotivoAcesso.VINCULO_DIVERGENTE),
            (replace(grant.confirmacao, origem=p.OrigemConcessao.AVULSO), p.MotivoAcesso.VINCULO_DIVERGENTE),
            (replace(grant.confirmacao, periodo=p.Periodo(START, NOW)), p.MotivoAcesso.VINCULO_DIVERGENTE),
        ):
            with self.subTest(proof=proof):
                self.assert_decision(replace(evidence, concessoes=(replace(grant, confirmacao=proof),)), reason, query)

    def test_duplicate_grant_ids_are_denied(self):
        evidence = paid_evidence()
        self.assert_decision(replace(evidence, concessoes=evidence.concessoes * 2),
                             p.MotivoAcesso.CONCESSAO_NAO_COMPROVADA)

    def test_missing_or_malformed_top_level_evidence(self):
        for evidence in (None, {}, "PAID", True, 1):
            with self.subTest(evidence=evidence):
                self.assert_decision(evidence, p.MotivoAcesso.DADOS_INVALIDOS)
        self.assert_decision(p.EvidenciasComerciais(), p.MotivoAcesso.EVIDENCIAS_INCOMPLETAS)
        self.assert_decision(replace(paid_evidence(), completas=False), p.MotivoAcesso.EVIDENCIAS_INCOMPLETAS)
        for query in (None, {}, "empresa", replace(QUERY, empresa_id=True), replace(QUERY, modulo_id=0)):
            self.assert_decision(paid_evidence(), p.MotivoAcesso.DADOS_INVALIDOS, query)

    def test_malformed_normalized_fields_fail_closed(self):
        evidence = paid_evidence()
        changes = (
            replace(evidence, completas=1), replace(evidence, conflito_impeditivo="false"),
            replace(evidence, assinaturas_candidatas=list(evidence.assinaturas_candidatas)),
            replace(evidence, ciclos=(None,)), replace(evidence, concessoes=({},)),
            replace(evidence, modulos_bloqueados=(True,)),
            change_subscription(evidence, estado="ATIVA"),
            change_subscription(evidence, plano_id=False),
            change_cycle(evidence, id=True), change_cycle(evidence, estado="PAGO"),
            change_cycle(evidence, periodo=p.Periodo(END, START)),
            change_cycle(evidence, periodo=p.Periodo(START, START)),
            change_cycle(evidence, confirmacao=True),
            change_cycle(evidence, pago_em="2026-10-01"),
            change_cycle(evidence, confirmacao=replace(evidence.ciclos[0].confirmacao, auditoria_id=0)),
            change_grant(evidence, incluido_no_plano=1),
            change_grant(evidence, assinatura_id=None),
            change_grant(evidence, confirmacao={}),
            change_subscription(evidence, cancelamento=True),
        )
        for changed in changes:
            with self.subTest(evidence=changed):
                self.assert_decision(changed, p.MotivoAcesso.DADOS_INVALIDOS)

    def test_utc_normalization_is_mandatory(self):
        for value in (NOW.replace(tzinfo=None), NOW.date(), NOW.isoformat(),
                      NOW.astimezone(timezone(timedelta(hours=-3)))):
            with self.subTest(value=value):
                self.assert_decision(paid_evidence(), p.MotivoAcesso.DADOS_INVALIDOS, replace(QUERY, agora=value))

    def test_decision_contains_only_safe_fixed_fields(self):
        result = self.assert_decision(paid_evidence(), p.MotivoAcesso.PAGO_PERMITIDO)
        self.assertEqual(set(vars(result)), {"permitido", "motivo"})
        for reason in p.MotivoAcesso:
            self.assertRegex(reason.value, r"^[A-Z_]+$")
        self.assertNotIn("empresa", repr(result).lower())
        self.assertNotIn("501", repr(result))

    def test_deterministic_immutable_and_input_order_independent(self):
        evidence = paid_evidence()
        renewal = replace(evidence.ciclos[0], id=502, estado=p.EstadoPagamento.PENDENTE,
                          periodo=p.Periodo(END, END + timedelta(days=30)), pago_em=None, confirmacao=None)
        evidence = replace(evidence, ciclos=(*evidence.ciclos, renewal))
        before = deepcopy(evidence)
        first = p.avaliar_acesso_comercial(QUERY, evidence)
        self.assertEqual(first, p.avaliar_acesso_comercial(QUERY, evidence))
        self.assertEqual(first, p.avaliar_acesso_comercial(QUERY, replace(evidence, ciclos=tuple(reversed(evidence.ciclos)))))
        self.assertEqual(evidence, before)
        with self.assertRaises(FrozenInstanceError):
            evidence.completas = False

    def test_audit_cannot_be_reused_for_distinct_paid_cycles(self):
        evidence = paid_evidence()
        future = paid_cycle(502, p.Periodo(END, END + timedelta(days=30)))
        future = replace(future, confirmacao=replace(
            future.confirmacao, auditoria_id=evidence.ciclos[0].confirmacao.auditoria_id,
        ))
        self.assert_decision(replace(evidence, ciclos=(*evidence.ciclos, future)),
                             p.MotivoAcesso.CONFIRMACAO_INCONSISTENTE)

    def test_audit_cannot_be_reused_for_payment_and_extra_right(self):
        evidence = paid_evidence()
        grant = extra_grant()
        grant = replace(grant, confirmacao=replace(
            grant.confirmacao, auditoria_id=evidence.ciclos[0].confirmacao.auditoria_id,
        ))
        self.assert_decision(replace(evidence, concessoes=(*evidence.concessoes, grant)),
                             p.MotivoAcesso.CONFIRMACAO_INCONSISTENTE)

    def test_paid_access_requires_plan_even_with_explicit_extra_right(self):
        evidence = change_subscription(paid_evidence(), plano_id=None)
        self.assert_decision(evidence, p.MotivoAcesso.PLANO_NAO_COMPROVADO)
        self.assert_decision(replace(evidence, concessoes=(extra_grant(),)),
                             p.MotivoAcesso.PLANO_NAO_COMPROVADO, replace(QUERY, modulo_id=22))

    def test_independent_extra_grants_do_not_require_invented_contract_link(self):
        for origin in (p.OrigemConcessao.CORTESIA, p.OrigemConcessao.AVULSO):
            with self.subTest(origin=origin):
                grant = extra_grant(origin)
                independent = replace(grant, assinatura_id=None,
                                      confirmacao=replace(grant.confirmacao, assinatura_id=None))
                evidence = replace(paid_evidence(), concessoes=(independent,))
                query = replace(QUERY, modulo_id=22)
                self.assert_decision(evidence, p.MotivoAcesso.PAGO_PERMITIDO, query)
                self.assert_decision(evidence, p.MotivoAcesso.MODULO_NAO_CONTRATADO)
                self.assert_decision(replace(evidence, ciclos=()), p.MotivoAcesso.PAGAMENTO_NAO_COMPROVADO, query)
                inconsistent = replace(independent, confirmacao=grant.confirmacao)
                self.assert_decision(replace(evidence, concessoes=(inconsistent,)),
                                     p.MotivoAcesso.VINCULO_DIVERGENTE, query)

    def test_policy_has_only_standard_library_imports_and_no_startup_actions(self):
        tree = ast.parse(POLICY_PATH.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, {"dataclasses", "datetime", "enum"})
            else:
                self.assertTrue(isinstance(node, (ast.ClassDef, ast.FunctionDef))
                                or isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
        self.assertFalse(any(isinstance(node, ast.Import) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main(verbosity=2)

