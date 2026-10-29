"""Etapa 4C.2: somente este arquivo, python -I -B, sem rede ou banco real."""
import ast
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import http.client
import importlib.abc
import importlib.util
from pathlib import Path
import socket
import sys
from types import ModuleType
import unittest
from unittest.mock import patch
import urllib.request

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
NETWORK_ATTEMPTS = []


def no_network(*args, **kwargs):
    NETWORK_ATTEMPTS.append(True)
    raise AssertionError("Rede proibida")


for target in (
    "socket.create_connection", "socket.getaddrinfo", "socket.socket.connect",
    "socket.socket.connect_ex", "socket.socket.bind", "socket.socket.sendto",
    "urllib.request.urlopen", "urllib.request.OpenerDirector.open",
    "http.client.HTTPConnection.connect", "http.client.HTTPSConnection.connect",
):
    guard = patch(target, side_effect=no_network)
    guard.start()
    unittest.addModuleCleanup(guard.stop)


class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in {
            "app", "fastapi", "psycopg", "psycopg2", "asyncpg", "dotenv", "sqlite3",
        }:
            raise AssertionError("ERP/framework/driver proibido")


import_guard = BlockImports()
sys.meta_path.insert(0, import_guard)
unittest.addModuleCleanup(sys.meta_path.remove, import_guard)
import sqlalchemy
from sqlalchemy.dialects import postgresql

for target in ("sqlalchemy.create_engine", "sqlalchemy.engine.create_engine",
               "sqlalchemy.engine.create.create_engine"):
    guard = patch(target, side_effect=AssertionError("Banco real proibido"))
    guard.start()
    unittest.addModuleCleanup(guard.stop)

# Carrega somente os tres arquivos reais, sem executar app/__init__ ou tenant/__init__.
package = ModuleType("isolated_commercial_evidence")
package.__path__ = [str(ROOT / "app" / "tenant")]
sys.modules[package.__name__] = package
unittest.addModuleCleanup(sys.modules.pop, package.__name__, None)


def load(name):
    full_name = package.__name__ + "." + name
    spec = importlib.util.spec_from_file_location(full_name, ROOT / "app" / "tenant" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    unittest.addModuleCleanup(sys.modules.pop, full_name, None)
    spec.loader.exec_module(module)
    setattr(package, name, module)
    return module


context = load("context")
p = load("commercial_policy")
r = load("commercial_evidence")

UTC = timezone.utc
COMMERCIAL = timezone(timedelta(hours=-3))  # Convencao ficticia explicita, nao prova do ERP.
CONVENTION = r.ConvencaoTemporal(fuso_comercial=COMMERCIAL)
NOW = datetime(2026, 10, 17, 15, tzinfo=UTC)
TENANT = context.TenantContext(7, user_id=201, origem=context.TenantOrigin.AUTHENTICATION)


def snapshot():
    return {
        "empresa_id": 7, "empresa_status": "ATIVA",
        "assinaturas": [{
            "id": 40, "empresa_id": 7, "plano_id": 3, "plano_existente": 3,
            "status": "ATIVA", "data_inicio_trial": None, "data_fim_trial": None,
            "data_inicio_assinatura": "2026-10-01", "data_vencimento": "2026-11-01",
        }],
        "cobrancas": [{
            "id": 501, "empresa_id": 7, "assinatura_id": 40, "pedido_modulo_id": None,
            "tipo": "ASSINATURA", "status": "PAGO",
            "ciclo_inicio": "2026-10-01", "ciclo_fim": "2026-11-01",
            "pago_em": "2026-09-30T12:00:00+00:00",
        }],
        "concessoes": [{
            "id": 61, "empresa_id": 7, "assinatura_id": 40, "modulo_id": 11,
            "origem": "PLANO", "status": "ATIVO", "data_inicio": "2026-10-01",
            "data_fim": "2026-11-01", "periodicidade": None, "modulo_ativo": True,
        }],
        "plano_modulos": [{"plano_id": 3, "modulo_id": 11, "incluido": True}],
        "pedidos": [],
        "auditorias": [{
            "id": 1501, "empresa_afetada_id": 7, "equipe_id": 101, "usuario_id": 201,
            "acao": "ASSINATURA_PAGAMENTO_CONFIRMADO", "recurso": "pagamentos_saas",
            "recurso_id": "501", "criado_em": "2026-09-30T13:00:00+00:00",
            "detalhes": {"assinatura_id": 40, "ciclo_inicio": "2026-10-01", "ciclo_fim": "2026-11-01"},
        }],
    }


def trial_snapshot(expired=False):
    result = snapshot()
    contract = result["assinaturas"][0]
    contract.update(status="TRIAL", data_inicio_trial="2026-10-01",
                    data_fim_trial="2026-10-10" if expired else "2026-11-01",
                    data_inicio_assinatura=None, data_vencimento=None)
    result["cobrancas"] = []
    result["auditorias"] = []
    result["concessoes"][0]["origem"] = "TRIAL"
    return result


def add_extra(data, origin="CORTESIA"):
    data["concessoes"].append({
        "id": 62, "empresa_id": 7, "assinatura_id": None, "modulo_id": 22,
        "origem": origin, "status": "ATIVO", "data_inicio": "2026-10-01",
        "data_fim": "2026-11-01", "periodicidade": "CORTESIA" if origin == "CORTESIA" else "MENSAL",
        "modulo_ativo": True,
    })
    details = {
        "modulo_id": 22, "origem": origin,
        "periodicidade": "CORTESIA" if origin == "CORTESIA" else "MENSAL",
        "data_fim": "2026-11-01",
    }
    if origin == "AVULSO":
        details["pedido_id"] = 81
        data["pedidos"].append({"id": 81, "empresa_id": 7, "modulo_id": 22, "status": "ATIVADO"})
        data["cobrancas"].append({
            "id": 502, "empresa_id": 7, "assinatura_id": None, "pedido_modulo_id": 81,
            "tipo": "MODULO_AVULSO", "status": "PAGO",
            "ciclo_inicio": None, "ciclo_fim": None, "pago_em": "2026-10-01T10:00:00+00:00",
        })
        data["auditorias"].append({
            "id": 1502, "empresa_afetada_id": 7, "equipe_id": 101, "usuario_id": 201,
            "acao": "PAGAMENTO_PEDIDO_CONFIRMADO", "recurso": "pagamentos_saas",
            "recurso_id": "502", "criado_em": "2026-10-01T11:00:00+00:00",
            "detalhes": {"pedido_id": 81, "modulo_id": 22},
        })
    data["auditorias"].append({
        "id": 1503, "empresa_afetada_id": 7, "equipe_id": 101, "usuario_id": 201,
        "acao": "MODULO_ATIVADO" if origin == "CORTESIA" else "MODULO_ATIVADO_POR_PEDIDO",
        "recurso": "empresa_modulos_saas", "recurso_id": "62",
        "criado_em": "2026-10-01T15:00:00+00:00", "detalhes": details,
    })
    return data


class FakeSession:
    def __init__(self, data=None, *, rows=None, error=None, result_error=False):
        self.data = deepcopy(snapshot() if data is None else data)
        self.rows = rows
        self.error = error
        self.result_error = result_error
        self.calls = []
        self.all_calls = 0

    def execute(self, statement, params):
        self.calls.append((statement, deepcopy(params)))
        if self.error is not None:
            raise self.error
        return self

    def mappings(self):
        return self

    def all(self):
        self.all_calls += 1
        if self.result_error:
            raise RuntimeError("dado-financeiro-ficticio-nao-expor")
        return deepcopy([self.data] if self.rows is None else self.rows)

    def commit(self):
        raise AssertionError("commit proibido")

    def rollback(self):
        raise AssertionError("rollback pertence ao chamador")

    def flush(self):
        raise AssertionError("flush proibido")


class CommercialEvidenceTests(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(NETWORK_ATTEMPTS, [])
        self.assertFalse(any(name == "app" or name.startswith("app.") for name in sys.modules))

    def read(self, data=None, *, tenant=TENANT, convention=CONVENTION, now=NOW, session=None):
        db = FakeSession(data) if session is None else session
        result = r.ler_evidencias_comerciais(db, tenant, agora=now, convencao=convention)
        return result, db

    def decide(self, result, module=11, now=NOW):
        return p.avaliar_acesso_comercial(p.ConsultaAcesso(7, module, now), result.evidencias)

    def assert_incomplete(self, result, reason):
        self.assertFalse(result.evidencias.completas)
        self.assertIn(reason, result.limitacoes)
        self.assertFalse(self.decide(result).permitido)

    def test_complete_payment_and_scoped_plan_module(self):
        result, db = self.read()
        self.assertEqual(result.limitacoes, ())
        self.assertTrue(result.evidencias.completas)
        self.assertEqual(self.decide(result), p.DecisaoAcesso(True, p.MotivoAcesso.PAGO_PERMITIDO))
        self.assertEqual(result.evidencias.ciclos[0].periodo.inicio, datetime(2026, 10, 1, 3, tzinfo=UTC))
        self.assertEqual(result.evidencias.ciclos[0].periodo.fim, datetime(2026, 11, 1, 3, tzinfo=UTC))
        self.assertEqual(len(db.calls), 1)

    def test_payment_without_audited_confirmation(self):
        data = snapshot()
        data["auditorias"] = []
        result, _ = self.read(data)
        self.assertIn(r.MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE, result.limitacoes)
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.CONFIRMACAO_ADMINISTRATIVA_AUSENTE)

    def test_foreign_contract_or_company_never_authorizes(self):
        for table, key in (("assinaturas", "empresa_id"), ("cobrancas", "empresa_id"),
                           ("concessoes", "empresa_id"), ("auditorias", "empresa_afetada_id")):
            with self.subTest(table=table):
                data = snapshot()
                data[table][0][key] = 8
                result, _ = self.read(data)
                self.assert_incomplete(result, r.MotivoLeitura.VINCULO_DIVERGENTE)
        data = snapshot()
        data["empresa_id"] = 8
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.VINCULO_DIVERGENTE)

    def test_payment_and_grant_of_other_contract(self):
        for table in ("cobrancas", "concessoes"):
            with self.subTest(table=table):
                data = snapshot()
                data[table][0]["assinatura_id"] = 41
                self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.VINCULO_DIVERGENTE)

    def test_audit_must_match_contract_period_resource_action_and_actor(self):
        for key, value in (("assinatura_id", 41), ("ciclo_inicio", "2026-10-02"),
                           ("ciclo_fim", "2026-12-01")):
            data = snapshot()
            data["auditorias"][0]["detalhes"][key] = value
            self.assertFalse(self.decide(self.read(data)[0]).permitido)
        for key, value in (("acao", "WEBHOOK_RECEBIDO"), ("recurso", "assinaturas_saas"),
                           ("recurso_id", "999"), ("equipe_id", None), ("usuario_id", False)):
            with self.subTest(key=key):
                data = snapshot()
                data["auditorias"][0][key] = value
                self.assertFalse(self.decide(self.read(data)[0]).permitido)

    def test_confirmation_without_payment_is_denied(self):
        data = snapshot()
        data["cobrancas"][0].update(status="PENDENTE", pago_em=None)
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)

    def test_pending_renewal_preserves_current_paid_cycle(self):
        data = snapshot()
        data["cobrancas"].append({
            **data["cobrancas"][0], "id": 502, "status": "PENDENTE", "pago_em": None,
            "ciclo_inicio": "2026-11-01", "ciclo_fim": "2026-12-01",
        })
        result, _ = self.read(data)
        self.assertTrue(self.decide(result).permitido)
        end = datetime(2026, 11, 1, 3, tzinfo=UTC)
        self.assertFalse(self.decide(result, now=end).permitido)

    def test_all_conflicting_contracts_are_retained_not_latest_only(self):
        data = snapshot()
        data["assinaturas"].append({**data["assinaturas"][0], "id": 41, "status": "PENDENTE"})
        result, _ = self.read(data)
        self.assertEqual({v.id for v in result.evidencias.assinaturas_candidatas}, {40, 41})
        self.assertIn(r.MotivoLeitura.CONTRATOS_CONFLITANTES, result.limitacoes)
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.CONTRATOS_CONFLITANTES)

    def test_conflicting_cycles_cannot_authorize(self):
        data = snapshot()
        data["cobrancas"].append({**data["cobrancas"][0], "id": 502, "status": "PENDENTE", "pago_em": None})
        result, _ = self.read(data)
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.CICLOS_CONFLITANTES)
        self.assertIn(r.MotivoLeitura.CICLOS_CONFLITANTES, result.limitacoes)

    def test_duplicate_records_or_confirmations_are_not_arbitrarily_selected(self):
        for table in ("assinaturas", "cobrancas", "concessoes", "auditorias"):
            with self.subTest(table=table):
                data = snapshot()
                data[table].append(deepcopy(data[table][0]))
                self.assertFalse(self.decide(self.read(data)[0]).permitido)
        data = snapshot()
        data["auditorias"].append({**data["auditorias"][0], "id": 1502})
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)

    def test_valid_expired_and_future_trials(self):
        self.assertEqual(self.decide(self.read(trial_snapshot())[0]).motivo, p.MotivoAcesso.TRIAL_PERMITIDO)
        self.assertEqual(self.decide(self.read(trial_snapshot(True))[0]).motivo, p.MotivoAcesso.COBERTURA_ENCERRADA)
        data = trial_snapshot()
        data["assinaturas"][0]["data_inicio_trial"] = "2026-10-20"
        self.assertEqual(self.decide(self.read(data)[0]).motivo, p.MotivoAcesso.COBERTURA_FUTURA)

    def test_suspension_of_contract_and_module(self):
        data = snapshot()
        data["assinaturas"][0]["status"] = "SUSPENSA"
        self.assertEqual(self.decide(self.read(data)[0]).motivo, p.MotivoAcesso.ASSINATURA_SUSPENSA)
        data = snapshot()
        data["concessoes"][0]["status"] = "SUSPENSO"
        result, _ = self.read(data)
        self.assertEqual(result.evidencias.modulos_bloqueados, (11,))
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.MODULO_BLOQUEADO)

    def test_cancelled_contract_is_ambiguous_even_with_unverified_claims(self):
        data = snapshot()
        data["assinaturas"][0].update(status="CANCELADA", renovacao_automatica=False,
                                     modalidade_cancelamento="FIM_VIGENCIA")
        result, _ = self.read(data)
        self.assertIn(r.MotivoLeitura.CANCELAMENTO_NAO_COMPROVADO, result.limitacoes)
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.CANCELAMENTO_AMBIGUO)
        # A politica aceita a modalidade inequivoca; o leitor nao inventa seu
        # mapeamento em tabelas/acoes que ainda nao existem nos escritores.
        signature = result.evidencias.assinaturas_candidatas[0]
        explicit = p.Cancelamento(p.ModalidadeCancelamento.FIM_VIGENCIA, 3001, 7, 40,
                                  NOW - timedelta(days=1), datetime(2026, 11, 1, 3, tzinfo=UTC))
        normalized = replace(result.evidencias, assinaturas_candidatas=(replace(signature, cancelamento=explicit),))
        self.assertTrue(p.avaliar_acesso_comercial(p.ConsultaAcesso(7, 11, NOW), normalized).permitido)

    def test_closed_cancelled_history_does_not_replace_or_conflict_with_live_contract(self):
        data = snapshot()
        data["assinaturas"].append({
            **data["assinaturas"][0], "id": 999, "status": "CANCELADA", "data_vencimento": "2026-09-01",
        })
        result, _ = self.read(data)
        self.assertEqual(tuple(v.id for v in result.evidencias.assinaturas_candidatas), (40,))
        self.assertTrue(self.decide(result).permitido)

    def test_cancelled_contract_with_future_financial_cycle_is_not_discarded(self):
        data = snapshot()
        data["assinaturas"][0].update(status="CANCELADA", data_vencimento="2026-09-01")
        result, _ = self.read(data)
        self.assert_incomplete(result, r.MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)

    def test_absent_data_and_inactive_company(self):
        self.assert_incomplete(self.read(session=FakeSession(rows=[]))[0], r.MotivoLeitura.EMPRESA_INDISPONIVEL)
        data = snapshot()
        for key in ("assinaturas", "cobrancas", "concessoes", "auditorias", "plano_modulos"):
            data[key] = []
        result, _ = self.read(data)
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.ASSINATURA_AUSENTE)
        data["empresa_status"] = "INATIVA"
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.EMPRESA_INDISPONIVEL)

    def test_query_or_result_failure_has_no_sensitive_error_or_partial_evidence(self):
        for db in (
            FakeSession(error=RuntimeError("postgresql://secret/dado-financeiro-ficticio-nao-expor")),
            FakeSession(result_error=True),
        ):
            result, _ = self.read(session=db)
            self.assert_incomplete(result, r.MotivoLeitura.FALHA_CONSULTA)
            self.assertNotIn("secret", repr(result))
            self.assertNotIn("dado-financeiro", repr(result))
            self.assertEqual(result.evidencias.ciclos, ())

    def test_naive_timestamp_is_never_assumed_utc(self):
        data = snapshot()
        data["cobrancas"][0]["pago_em"] = "2026-09-30T09:00:00"
        result, _ = self.read(data)
        self.assert_incomplete(result, r.MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE)
        convention = r.ConvencaoTemporal(COMMERCIAL, COMMERCIAL)
        result, _ = self.read(data, convention=convention)
        self.assertEqual(result.evidencias.ciclos[0].pago_em, datetime(2026, 9, 30, 12, tzinfo=UTC))
        self.assertTrue(self.decide(result).permitido)

    def test_missing_commercial_date_convention_is_not_machine_timezone(self):
        result, _ = self.read(convention=r.ConvencaoTemporal())
        self.assert_incomplete(result, r.MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE)

    def test_bad_dates_and_missing_periods_are_denied(self):
        for key, value in (("ciclo_inicio", "not-a-date"), ("ciclo_fim", "2026-09-01"),
                           ("ciclo_fim", None), ("pago_em", "sem-fuso-nem-data")):
            data = snapshot()
            data["cobrancas"][0][key] = value
            self.assertFalse(self.decide(self.read(data)[0]).permitido)
        data = snapshot()
        data["auditorias"][0]["criado_em"] = "2026-09-30T13:00:00"
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE)

    def test_exact_period_boundaries_are_preserved(self):
        result, _ = self.read()
        start = datetime(2026, 10, 1, 3, tzinfo=UTC)
        end = datetime(2026, 11, 1, 3, tzinfo=UTC)
        self.assertTrue(self.decide(result, now=start).permitido)
        self.assertFalse(self.decide(result, now=start - timedelta(microseconds=1)).permitido)
        self.assertTrue(self.decide(result, now=end - timedelta(microseconds=1)).permitido)
        self.assertFalse(self.decide(result, now=end).permitido)

    def test_missing_plan_or_module_membership_is_not_inferred_from_status(self):
        data = snapshot()
        data["assinaturas"][0]["plano_existente"] = None
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.VINCULO_DIVERGENTE)
        data = snapshot()
        data["plano_modulos"][0]["incluido"] = False
        self.assertFalse(self.decide(self.read(data)[0]).permitido)
        data = snapshot()
        data["concessoes"] = []
        self.assertFalse(self.decide(self.read(data)[0]).permitido)

    def test_audited_courtesy_is_explicit_and_not_general(self):
        result, _ = self.read(add_extra(snapshot()))
        self.assertTrue(self.decide(result, module=22).permitido)
        self.assertFalse(self.decide(result, module=999).permitido)
        grant = next(v for v in result.evidencias.concessoes if v.modulo_id == 22)
        self.assertIsNone(grant.assinatura_id)
        self.assertIsNotNone(grant.confirmacao)

    def test_paid_order_and_audited_activation_prove_only_its_module(self):
        result, _ = self.read(add_extra(snapshot(), "AVULSO"))
        self.assertTrue(self.decide(result, module=22).permitido)
        self.assertFalse(self.decide(result, module=999).permitido)
        self.assertEqual(len(result.evidencias.ciclos), 1)  # Avulso nao substitui assinatura.

    def test_extra_grants_without_proof_or_finite_period_do_not_authorize(self):
        data = add_extra(snapshot())
        data["auditorias"] = data["auditorias"][:1]
        self.assertFalse(self.decide(self.read(data)[0], module=22).permitido)
        data = add_extra(snapshot())
        data["concessoes"][-1]["data_fim"] = None
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.PERIODO_NAO_COMPROVADO)

    def test_order_payment_confirmation_and_company_must_match(self):
        for mutate in (
            lambda data: data["pedidos"][0].update(empresa_id=8),
            lambda data: data["pedidos"][0].update(modulo_id=999),
            lambda data: data["pedidos"][0].update(status="PAGO"),
            lambda data: data["cobrancas"][-1].update(status="PENDENTE"),
            lambda data: data["cobrancas"][-1].update(pedido_modulo_id=999),
            lambda data: data["auditorias"][1]["detalhes"].update(pedido_id=999),
            lambda data: data["auditorias"][1].update(acao="WEBHOOK_RECEBIDO"),
        ):
            data = add_extra(snapshot(), "AVULSO")
            mutate(data)
            self.assertFalse(self.decide(self.read(data)[0], module=22).permitido)

    def test_invalid_identity_or_configuration_executes_no_query(self):
        for tenant in (7, {"empresa_id": 7}, None,
                       context.TenantContext(7, user_id=201, origem=context.TenantOrigin.SESSION),
                       context.TenantContext(7, user_id=201, origem=context.TenantOrigin.EXPLICIT_TEST),
                       context.TenantContext(7, user_id=None)):
            result, db = self.read(tenant=tenant)
            self.assert_incomplete(result, r.MotivoLeitura.CONTEXTO_NAO_AUTENTICADO)
            self.assertEqual(db.calls, [])
        for convention, now in ((None, NOW), (r.ConvencaoTemporal("UTC"), NOW), (CONVENTION, NOW.replace(tzinfo=None))):
            result, db = self.read(convention=convention, now=now)
            self.assert_incomplete(result, r.MotivoLeitura.DADOS_INVALIDOS)
            self.assertEqual(db.calls, [])

    def test_single_bound_read_and_reusable_result_without_mutation(self):
        data = snapshot()
        before = deepcopy(data)
        db = FakeSession(data)
        result, _ = self.read(session=db)
        self.decide(result, module=11)
        self.decide(result, module=999)
        self.assertEqual(data, before)
        self.assertEqual(db.data, before)
        self.assertEqual(len(db.calls), 1)
        self.assertEqual(db.all_calls, 1)
        statement, params = db.calls[0]
        self.assertEqual(params, {"empresa_id": 7})
        compiled = statement.compile(dialect=postgresql.dialect())
        self.assertEqual(set(compiled.params), {"empresa_id"})
        sql = " ".join(str(statement).upper().split())
        self.assertTrue(sql.startswith("WITH "))
        for forbidden in ("FOR UPDATE", " LIMIT ", "INSERT INTO", "UPDATE ", "DELETE ", "CREATE ", "COMMIT", "ROLLBACK"):
            self.assertNotIn(forbidden, sql)
        self.assertGreaterEqual(sql.count("=:EMPRESA_ID"), 6)
        for sensitive in ("P.VALOR", "REFERENCIA_EXTERNA", "OBSERVACOES", "EMAIL", "FORMA_PAGAMENTO"):
            self.assertNotIn(sensitive, sql)

    def test_malformed_rows_and_boolean_ids_fail_closed(self):
        variants = []
        for table, key, value in (("assinaturas", "id", True), ("cobrancas", "id", False),
                                  ("concessoes", "modulo_id", 0), ("auditorias", "recurso_id", 501)):
            data = snapshot()
            data[table][0][key] = value
            variants.append(data)
        data = snapshot()
        del data["cobrancas"][0]["ciclo_inicio"]
        variants.append(data)
        data = snapshot()
        data["auditorias"] = "nao-e-lista"
        variants.append(data)
        for data in variants:
            self.assertFalse(self.decide(self.read(data)[0]).permitido)

    def test_contract_dates_cannot_contradict_paid_cycle_or_be_missing(self):
        for key, value in (
            ("data_inicio_assinatura", None), ("data_vencimento", None),
            ("data_inicio_assinatura", "2026-10-20"), ("data_vencimento", "2026-10-10"),
        ):
            with self.subTest(key=key, value=value):
                data = snapshot()
                data["assinaturas"][0][key] = value
                self.assertFalse(self.decide(self.read(data)[0]).permitido)

    def test_refunded_cycle_preserves_audit_history_but_never_authorizes(self):
        data = snapshot()
        data["cobrancas"][0]["status"] = "ESTORNADO"
        result, _ = self.read(data)
        self.assertTrue(result.evidencias.completas)
        self.assertIsNotNone(result.evidencias.ciclos[0].confirmacao)
        self.assertFalse(self.decide(result).permitido)

    def test_future_or_pre_payment_confirmation_is_not_proof(self):
        for instant in ("2026-12-01T00:00:00+00:00", "2026-09-29T00:00:00+00:00"):
            data = snapshot()
            data["auditorias"][0]["criado_em"] = instant
            self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
        data = snapshot()
        data["cobrancas"][0]["pago_em"] = None
        self.assertFalse(self.decide(self.read(data)[0]).permitido)

    def test_one_order_cannot_prove_two_activations(self):
        data = add_extra(snapshot(), "AVULSO")
        data["concessoes"].append({**data["concessoes"][-1], "id": 63})
        data["auditorias"].append({**data["auditorias"][-1], "id": 1504, "recurso_id": "63"})
        self.assert_incomplete(self.read(data)[0], r.MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)

    def test_missing_plan_link_cannot_be_boolean(self):
        data = snapshot()
        data["assinaturas"][0].update(plano_id=1, plano_existente=True)
        self.assertFalse(self.decide(self.read(data)[0]).permitido)

    def test_datetime_overflow_never_queries_or_exposes_exception(self):
        invalid = datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=14)))
        result, db = self.read(now=invalid)
        self.assert_incomplete(result, r.MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)
        self.assertEqual(db.calls, [])

    def test_paid_future_cycle_is_not_early_access(self):
        data = snapshot()
        data["assinaturas"][0].update(data_inicio_assinatura="2026-11-01", data_vencimento="2026-12-01")
        data["cobrancas"][0].update(ciclo_inicio="2026-11-01", ciclo_fim="2026-12-01")
        data["auditorias"][0]["detalhes"].update(ciclo_inicio="2026-11-01", ciclo_fim="2026-12-01")
        data["concessoes"][0].update(data_inicio="2026-11-01", data_fim="2026-12-01")
        result, _ = self.read(data)
        self.assertTrue(result.evidencias.completas)
        self.assertEqual(self.decide(result).motivo, p.MotivoAcesso.COBERTURA_FUTURA)

    def test_cancelled_unpaid_history_without_end_does_not_block_new_paid_contract(self):
        data = snapshot()
        data["assinaturas"].append({
            **data["assinaturas"][0], "id": 999, "status": "CANCELADA",
            "data_inicio_assinatura": None, "data_vencimento": None,
        })
        data["cobrancas"].append({
            **data["cobrancas"][0], "id": 502, "assinatura_id": 999,
            "status": "PENDENTE", "pago_em": None,
            "ciclo_inicio": "2026-11-01", "ciclo_fim": "2026-12-01",
        })
        result, _ = self.read(data)
        self.assertEqual(tuple(v.id for v in result.evidencias.assinaturas_candidatas), (40,))
        self.assertEqual(tuple(v.id for v in result.evidencias.ciclos), (501,))
        self.assertTrue(self.decide(result).permitido)

    def test_reader_has_no_application_database_or_environment_import(self):
        tree = ast.parse((ROOT / "app/tenant/commercial_evidence.py").read_text(encoding="utf-8"))
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        rendered = "\n".join(ast.unparse(node) for node in imports)
        for forbidden in ("app.database", "app.main", "fastapi", "dotenv", "settings", "psycopg"):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)

