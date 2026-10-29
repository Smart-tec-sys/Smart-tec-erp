"""Leitura explicita e isolada das evidencias comerciais existentes.

Nao importa banco, configuracao, autenticacao externa ou app.main. Recebe um
TenantContext ja autenticado pelo servidor e a sessao do chamador; nao aceita
empresa_id livre nem valida JWT novamente. Nao registrar este leitor em rotas.

Uma unica instrucao SELECT usa o mesmo snapshot PostgreSQL para os conjuntos.
Nao ha commits, rollback, flush, DDL, travas, cache global ou escrita. O chamador
continua dono da transacao, inclusive apos erro de consulta.

O fuso dos campos DATE e a convencao historica dos TIMESTAMP sem fuso precisam
ser comprovados/configurados pelo servidor. Nao se usa o fuso da maquina nem
o TimeZone atual da sessao como prova do passado. Sem convencao, negar prova.
Cancelamento nao tem modalidade inequivoca nos escritores atuais: nao inferir
FIM_VIGENCIA de renovacao_automatica=False, observacoes, frontend ou webhook.
Cortesias/avulsos sem fim definido nao cabem na janela finita da politica 4C.1.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
import re
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import text

from .context import TenantContext, TenantOrigin
from . import commercial_calendar as calendario
from . import commercial_policy as policy


class MotivoLeitura(str, Enum):
    CONTEXTO_NAO_AUTENTICADO = "CONTEXTO_NAO_AUTENTICADO"
    EMPRESA_INDISPONIVEL = "EMPRESA_INDISPONIVEL"
    FALHA_CONSULTA = "FALHA_CONSULTA"
    DADOS_INVALIDOS = "DADOS_INVALIDOS"
    VINCULO_DIVERGENTE = "VINCULO_DIVERGENTE"
    CONVENCAO_TEMPORAL_AUSENTE = "CONVENCAO_TEMPORAL_AUSENTE"
    DATA_AMBIGUA_OU_INVALIDA = "DATA_AMBIGUA_OU_INVALIDA"
    CONFIRMACAO_ADMINISTRATIVA_AUSENTE = "CONFIRMACAO_ADMINISTRATIVA_AUSENTE"
    CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE = "CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE"
    CANCELAMENTO_NAO_COMPROVADO = "CANCELAMENTO_NAO_COMPROVADO"
    PERIODO_NAO_COMPROVADO = "PERIODO_NAO_COMPROVADO"
    CONTRATOS_CONFLITANTES = "CONTRATOS_CONFLITANTES"
    CICLOS_CONFLITANTES = "CICLOS_CONFLITANTES"


@dataclass(frozen=True)
class ConvencaoTemporal:
    """Somente configuracao interna comprovada; nunca dados de requisicao.

    None e intencional: nao presume o fuso comercial ou o dos registros naive.
    ZoneInfo trata alteracoes historicas; um timezone fixo so serve quando
    essa for de fato a convencao comprovada. Horarios locais ambiguos falham.
    """
    fuso_comercial: ZoneInfo | timezone | None = None
    fuso_timestamps_sem_fuso: ZoneInfo | timezone | None = None


@dataclass(frozen=True)
class ResultadoLeitura:
    """Leitura completa nao significa acesso autorizado: avaliar a politica 4C.1."""
    evidencias: policy.EvidenciasComerciais
    limitacoes: tuple[MotivoLeitura, ...] = ()


class SessaoLeitura(Protocol):
    def execute(self, statement, params): ...


# Somente nomes/relacoes utilizados nos escritores administrativos atuais.
# Projecao exclui valores, nomes, e-mails, observacoes e payload financeiro bruto.
CONSULTA_EVIDENCIAS = """
WITH a AS (
    SELECT s.id,s.empresa_id,s.plano_id,s.status,s.data_inicio_trial,s.data_fim_trial,
           s.data_inicio_assinatura,s.data_vencimento,p.id AS plano_existente
    FROM assinaturas_saas s LEFT JOIN planos_saas p ON p.id=s.plano_id
    WHERE s.empresa_id=:empresa_id
), c AS (
    SELECT id,empresa_id,assinatura_id,pedido_modulo_id,tipo,status,
           ciclo_inicio,ciclo_fim,pago_em
    FROM pagamentos_saas WHERE empresa_id=:empresa_id
), g AS (
    SELECT em.id,em.empresa_id,em.assinatura_id,em.modulo_id,em.origem,em.status,
           em.data_inicio,em.data_fim,em.periodicidade,m.ativo AS modulo_ativo
    FROM empresa_modulos_saas em LEFT JOIN modulos_saas m ON m.id=em.modulo_id
    WHERE em.empresa_id=:empresa_id
), pm AS (
    SELECT plano_id,modulo_id,incluido FROM plano_modulos_saas pm
    WHERE EXISTS (SELECT 1 FROM a WHERE a.plano_id=pm.plano_id)
), pedidos AS (
    SELECT id,empresa_id,modulo_id,status FROM pedidos_modulos_saas
    WHERE empresa_id=:empresa_id
), auditorias AS (
    SELECT id,empresa_afetada_id,equipe_id,usuario_id,acao,recurso,recurso_id,criado_em,
           jsonb_build_object(
               'assinatura_id',detalhes->'assinatura_id',
               'ciclo_inicio',detalhes->'ciclo_inicio','ciclo_fim',detalhes->'ciclo_fim',
               'modulo_id',detalhes->'modulo_id','origem',detalhes->'origem',
               'periodicidade',detalhes->'periodicidade','data_fim',detalhes->'data_fim',
               'pedido_id',detalhes->'pedido_id'
           ) AS detalhes
    FROM auditoria_plataforma
    WHERE empresa_afetada_id=:empresa_id
      AND recurso IN ('assinaturas_saas','pagamentos_saas',
                      'empresa_modulos_saas','pedidos_modulos_saas')
)
SELECT e.id AS empresa_id,e.status AS empresa_status,
       (SELECT COALESCE(jsonb_agg(to_jsonb(a) ORDER BY id),'[]'::jsonb) FROM a) AS assinaturas,
       (SELECT COALESCE(jsonb_agg(to_jsonb(c) ORDER BY id),'[]'::jsonb) FROM c) AS cobrancas,
       (SELECT COALESCE(jsonb_agg(to_jsonb(g) ORDER BY id),'[]'::jsonb) FROM g) AS concessoes,
       (SELECT COALESCE(jsonb_agg(to_jsonb(pm) ORDER BY plano_id,modulo_id),'[]'::jsonb) FROM pm) AS plano_modulos,
       (SELECT COALESCE(jsonb_agg(to_jsonb(pedidos) ORDER BY id),'[]'::jsonb) FROM pedidos) AS pedidos,
       (SELECT COALESCE(jsonb_agg(to_jsonb(auditorias) ORDER BY id),'[]'::jsonb) FROM auditorias) AS auditorias
FROM empresas e WHERE e.id=:empresa_id
"""


class _Insuficiente(Exception):
    def __init__(self, motivo):
        self.motivo = motivo
        super().__init__(motivo.value)


def _falhar(motivo=MotivoLeitura.DADOS_INVALIDOS):
    raise _Insuficiente(motivo)


def _id(value):
    if type(value) is not int or value <= 0:
        _falhar()
    return value


def _opcional_id(value):
    return None if value is None else _id(value)


def _enum(enum_type, value):
    if type(value) is not str:
        _falhar()
    try:
        return enum_type(value)
    except ValueError:
        _falhar()


def _fuso(value):
    return value is None or type(value) in (ZoneInfo, timezone)


def _zona(zone):
    if zone is None:
        _falhar(MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE)
    return zone


def _data(value, convention):
    if type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        value = date.fromisoformat(value)
    if type(value) is not date:
        _falhar(MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)
    zone = _zona(convention.fuso_comercial)
    try:
        return calendario.inicio_dia_comercial_utc(value, fuso=zone, estrito=True)
    except ValueError:
        _falhar(MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)


def _instante(value, convention):
    if type(value) is str and ("T" in value or " " in value):
        value = datetime.fromisoformat(value)
    if type(value) is not datetime:
        _falhar(MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)
    if value.tzinfo is None:
        zone = _zona(convention.fuso_timestamps_sem_fuso)
        try:
            return calendario.instante_utc(value, zone, estrito=True)
        except ValueError:
            _falhar(MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)
    if type(value.tzinfo) not in (ZoneInfo, timezone):
        _falhar(MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)
    return calendario.instante_utc(value, estrito=True)


def _periodo(start, end, convention):
    if start is None or end is None:
        _falhar(MotivoLeitura.PERIODO_NAO_COMPROVADO)
    result = policy.Periodo(_data(start, convention), _data(end, convention))
    if result.inicio >= result.fim:
        _falhar(MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA)
    return result


def _conjunto(snapshot, name, empresa, company_key="empresa_id"):
    rows = snapshot[name]
    if type(rows) is not list or any(type(row) is not dict for row in rows):
        _falhar()
    if company_key is not None and any(_id(row[company_key]) != empresa for row in rows):
        _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
    ids = [_id(row["id"]) for row in rows] if name != "plano_modulos" else []
    if len(ids) != len(set(ids)):
        _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
    return rows


def _auditorias(rows, action, resource, identifier):
    # recurso_id e TEXT no ERP. Nao aceitar float, booleano, espacos ou outra ID.
    return [row for row in rows if row["acao"] == action and row["recurso"] == resource
            and type(row["recurso_id"]) is str and row["recurso_id"] == str(identifier)]


def _ator_e_instante(row, convention, now):
    _id(row["equipe_id"])
    _id(row["usuario_id"])
    instant = _instante(row["criado_em"], convention)
    if instant > now:
        _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
    if type(row["detalhes"]) is not dict:
        _falhar()
    return instant


def _prova_pagamento(cycle, rows, convention, now, limitations):
    matches = _auditorias(rows, "ASSINATURA_PAGAMENTO_CONFIRMADO", "pagamentos_saas", cycle.id)
    if not matches:
        if cycle.estado is policy.EstadoPagamento.PAGO:
            limitations.add(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE)
        return None
    if len(matches) != 1 or cycle.estado not in (policy.EstadoPagamento.PAGO, policy.EstadoPagamento.ESTORNADO):
        _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
    row, = matches
    instant = _ator_e_instante(row, convention, now)
    details = row["detalhes"]
    if (_id(details["assinatura_id"]) != cycle.assinatura_id
            or _periodo(details["ciclo_inicio"], details["ciclo_fim"], convention) != cycle.periodo
            or cycle.pago_em is None or instant < cycle.pago_em):
        _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
    return policy.ConfirmacaoPagamento(row["id"], row["empresa_afetada_id"],
                                      cycle.assinatura_id, cycle.id, cycle.periodo, instant)


def _prova_concessao(grant, raw, audits, orders, charges, convention, now, limitations, used_orders):
    courtesy = grant.origem is policy.OrigemConcessao.CORTESIA
    action = "MODULO_ATIVADO" if courtesy else "MODULO_ATIVADO_POR_PEDIDO"
    matches = _auditorias(audits, action, "empresa_modulos_saas", grant.id)
    if not matches:
        limitations.add(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE)
        return None
    if len(matches) != 1:
        _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
    audit, = matches
    activated = _ator_e_instante(audit, convention, now)
    details = audit["detalhes"]
    if (_id(details["modulo_id"]) != grant.modulo_id
            or details["origem"] != grant.origem.value
            or details["periodicidade"] != raw["periodicidade"]
            or _data(details["data_fim"], convention) != grant.periodo.fim
            or activated.astimezone(convention.fuso_comercial).date()
               != grant.periodo.inicio.astimezone(convention.fuso_comercial).date()):
        _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
    if not courtesy:
        order_id = _id(details["pedido_id"])
        if order_id in used_orders:
            _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
        used_orders.add(order_id)
        order = orders.get(order_id)
        if order is None or order["modulo_id"] != grant.modulo_id or order["status"] != "ATIVADO":
            _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
        payments = [row for row in charges if row["pedido_modulo_id"] == order_id]
        if len(payments) != 1:
            _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
        payment, = payments
        if (payment["tipo"] != "MODULO_AVULSO" or payment["status"] != "PAGO"
                or payment["assinatura_id"] is not None or payment["pago_em"] is None):
            _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
        paid = _instante(payment["pago_em"], convention)
        confirmations = _auditorias(audits, "PAGAMENTO_PEDIDO_CONFIRMADO", "pagamentos_saas", payment["id"])
        if len(confirmations) != 1:
            _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_AUSENTE)
        financial, = confirmations
        confirmed = _ator_e_instante(financial, convention, now)
        d = financial["detalhes"]
        if (_id(d["pedido_id"]) != order_id or _id(d["modulo_id"]) != grant.modulo_id
                or paid > confirmed or confirmed > activated):
            _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
    return policy.ConfirmacaoConcessao(
        audit["id"], grant.empresa_id, grant.assinatura_id, grant.id, grant.modulo_id,
        grant.origem, grant.periodo, activated,
    )


def _normalizar(snapshot, empresa, now, convention):
    if not isinstance(snapshot, Mapping) or _id(snapshot["empresa_id"]) != empresa:
        _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
    if snapshot["empresa_status"] != "ATIVA":
        _falhar(MotivoLeitura.EMPRESA_INDISPONIVEL)
    contracts = _conjunto(snapshot, "assinaturas", empresa)
    charges = _conjunto(snapshot, "cobrancas", empresa)
    grants = _conjunto(snapshot, "concessoes", empresa)
    audits = _conjunto(snapshot, "auditorias", empresa, "empresa_afetada_id")
    orders_raw = _conjunto(snapshot, "pedidos", empresa)
    memberships = _conjunto(snapshot, "plano_modulos", empresa, None)
    indexes = {row["id"]: row for row in contracts}
    orders = {row["id"]: row for row in orders_raw}
    included = {}
    for row in memberships:
        key = (_id(row["plano_id"]), _id(row["modulo_id"]))
        if type(row["incluido"]) is not bool or key in included:
            _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
        included[key] = row["incluido"]
    for order in orders_raw:
        _id(order["modulo_id"])
    for audit in audits:
        if any(type(audit[key]) is not str for key in ("acao", "recurso", "recurso_id")):
            _falhar()
    limitations = set()
    cycles = []
    for row in charges:
        _opcional_id(row["pedido_modulo_id"])
        if row["tipo"] == "MODULO_AVULSO":
            if row["pedido_modulo_id"] not in orders or row["assinatura_id"] is not None:
                _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
            continue
        if row["tipo"] != "ASSINATURA" or row["assinatura_id"] not in indexes:
            _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
        if row["pedido_modulo_id"] is not None:
            _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
        cycle = policy.CicloCobranca(
            row["id"], empresa, _id(row["assinatura_id"]), policy.TipoCobranca.ASSINATURA,
            _enum(policy.EstadoPagamento, row["status"]),
            _periodo(row["ciclo_inicio"], row["ciclo_fim"], convention),
            None if row["pago_em"] is None else _instante(row["pago_em"], convention),
        )
        proof = _prova_pagamento(cycle, audits, convention, now, limitations)
        cycles.append(policy.CicloCobranca(
            cycle.id, cycle.empresa_id, cycle.assinatura_id, cycle.tipo, cycle.estado,
            cycle.periodo, cycle.pago_em, proof,
        ))
    candidates = []
    for row in contracts:
        state = _enum(policy.EstadoAssinatura, row["status"])
        plan_id = _opcional_id(row["plano_id"])
        if plan_id is not None and (type(row["plano_existente"]) is not int or row["plano_existente"] != plan_id):
            _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
        trial = None
        if row["data_inicio_trial"] is not None or row["data_fim_trial"] is not None:
            trial = _periodo(row["data_inicio_trial"], row["data_fim_trial"], convention)
        end = None if row["data_vencimento"] is None else _data(row["data_vencimento"], convention)
        associated = [cycle for cycle in cycles if cycle.assinatura_id == row["id"]]
        paid = [cycle for cycle in associated if cycle.estado is policy.EstadoPagamento.PAGO]
        if paid:
            if row["data_inicio_assinatura"] is None or end is None:
                _falhar(MotivoLeitura.PERIODO_NAO_COMPROVADO)
            start = _data(row["data_inicio_assinatura"], convention)
            if start >= end or any(cycle.periodo.inicio < start or cycle.periodo.fim > end for cycle in paid):
                _falhar(MotivoLeitura.CONFIRMACAO_ADMINISTRATIVA_INCONSISTENTE)
        # Cancelados sem cobertura paga atual/futura nao competem com uma nova
        # contratacao comprovada. Uma renovacao apenas pendente nao e cobertura.
        if (state is policy.EstadoAssinatura.CANCELADA and (end is None or end <= now)
                and not any(cycle.estado is policy.EstadoPagamento.PAGO and cycle.periodo.fim > now
                            for cycle in associated)):
            continue
        if state is policy.EstadoAssinatura.CANCELADA:
            limitations.add(MotivoLeitura.CANCELAMENTO_NAO_COMPROVADO)
        candidates.append(policy.Assinatura(row["id"], empresa, state, plan_id, trial))
    candidate_ids = {row.id for row in candidates}
    if len(candidates) > 1:
        limitations.add(MotivoLeitura.CONTRATOS_CONFLITANTES)
    cycles = [cycle for cycle in cycles if cycle.assinatura_id in candidate_ids]
    for index, cycle in enumerate(cycles):
        for other in cycles[index + 1:]:
            if (cycle.assinatura_id == other.assinatura_id
                    and cycle.estado is not policy.EstadoPagamento.CANCELADO
                    and other.estado is not policy.EstadoPagamento.CANCELADO
                    and cycle.periodo.inicio < other.periodo.fim
                    and other.periodo.inicio < cycle.periodo.fim):
                limitations.add(MotivoLeitura.CICLOS_CONFLITANTES)
    normalized_grants = []
    used_orders = set()
    blocked = set()
    for row in grants:
        module_id = _id(row["modulo_id"])
        signature_id = _opcional_id(row["assinatura_id"])
        if signature_id is not None and signature_id not in indexes:
            _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
        if signature_id is not None and signature_id not in candidate_ids:
            continue
        origin = _enum(policy.OrigemConcessao, row["origem"])
        state = _enum(policy.EstadoConcessao, row["status"])
        if type(row["modulo_ativo"]) is not bool:
            _falhar()
        if state is policy.EstadoConcessao.SUSPENSO or row["modulo_ativo"] is False:
            blocked.add(module_id)
        if state is not policy.EstadoConcessao.ATIVO:
            continue
        if origin in (policy.OrigemConcessao.PLANO, policy.OrigemConcessao.TRIAL):
            if signature_id is None:
                _falhar(MotivoLeitura.VINCULO_DIVERGENTE)
            plan_id = indexes[signature_id]["plano_id"]
        else:
            plan_id = None
        window = _periodo(row["data_inicio"], row["data_fim"], convention)
        grant = policy.ConcessaoModulo(
            row["id"], empresa, signature_id, module_id, origin, state, window,
            plan_id, included.get((plan_id, module_id), False),
        )
        if origin in (policy.OrigemConcessao.CORTESIA, policy.OrigemConcessao.AVULSO):
            proof = _prova_concessao(grant, row, audits, orders, charges, convention, now, limitations, used_orders)
            grant = policy.ConcessaoModulo(
                grant.id, grant.empresa_id, grant.assinatura_id, grant.modulo_id, grant.origem,
                grant.estado, grant.periodo, grant.plano_id, grant.incluido_no_plano, proof,
            )
        normalized_grants.append(grant)
    result = policy.EvidenciasComerciais(
        tuple(candidates), tuple(cycles), tuple(normalized_grants), completas=True,
        modulos_bloqueados=tuple(sorted(blocked)),
    )
    return ResultadoLeitura(result, tuple(sorted(limitations, key=lambda v: v.value)))


def ler_evidencias_comerciais(
    sessao: SessaoLeitura,
    empresa_autenticada: TenantContext,
    *,
    agora: datetime,
    convencao: ConvencaoTemporal = ConvencaoTemporal(),
) -> ResultadoLeitura:
    """Leitura interna explicita. Nunca receber contexto/convencao do frontend.

    Uma consulta por chamada; reutilize o ResultadoLeitura para varios modulos.
    Ausencia/erro devolve completas=False com codigo fixo, nunca dados parciais
    apresentados como completos, detalhes da excecao, SQL ou dados financeiros.
    """
    tenant = empresa_autenticada
    if (type(tenant) is not TenantContext or tenant.origem is not TenantOrigin.AUTHENTICATION
            or type(tenant.empresa_id) is not int or tenant.empresa_id <= 0
            or type(tenant.user_id) is not int or tenant.user_id <= 0):
        return ResultadoLeitura(policy.EvidenciasComerciais(), (MotivoLeitura.CONTEXTO_NAO_AUTENTICADO,))
    if (type(convencao) is not ConvencaoTemporal
            or not _fuso(convencao.fuso_comercial) or not _fuso(convencao.fuso_timestamps_sem_fuso)
            or type(agora) is not datetime or type(agora.tzinfo) not in (ZoneInfo, timezone)):
        return ResultadoLeitura(policy.EvidenciasComerciais(), (MotivoLeitura.DADOS_INVALIDOS,))
    try:
        now = agora.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return ResultadoLeitura(policy.EvidenciasComerciais(), (MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA,))
    try:
        rows = sessao.execute(text(CONSULTA_EVIDENCIAS), {"empresa_id": tenant.empresa_id}).mappings().all()
    except Exception:
        return ResultadoLeitura(policy.EvidenciasComerciais(), (MotivoLeitura.FALHA_CONSULTA,))
    if not rows:
        return ResultadoLeitura(policy.EvidenciasComerciais(), (MotivoLeitura.EMPRESA_INDISPONIVEL,))
    try:
        if len(rows) != 1:
            _falhar()
        return _normalizar(rows[0], tenant.empresa_id, now, convencao)
    except _Insuficiente as error:
        return ResultadoLeitura(policy.EvidenciasComerciais(), (error.motivo,))
    except Exception:
        return ResultadoLeitura(policy.EvidenciasComerciais(), (MotivoLeitura.DADOS_INVALIDOS,))

