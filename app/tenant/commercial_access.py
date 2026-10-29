"""Observacao do acesso comercial (preparacao, desligada por padrao).

Modos:
* ``off`` (padrao): nenhuma leitura, nenhuma avaliacao, nenhum log.
* ``observe``: avalia somente empresas piloto e registra a decisao tecnica.
  Nunca bloqueia, nunca escreve e nunca propaga excecao.
* ``enforce``: reservado. Nesta etapa nao existe caminho que ative bloqueio;
  o valor e tratado como ``off``.

Este modulo nao le ambiente, configuracao global nem banco por conta propria. A
configuracao vem de valores internos ja resolvidos pelo chamador, a empresa
vem exclusivamente do ``TenantContext`` autenticado e a sessao vem de uma
fabrica interna. Ausencia de evidencia nunca vira autorizacao.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
import logging

from . import commercial_evidence as evidencia
from . import commercial_policy as politica
from .context import TenantContext, TenantOrigin

logger = logging.getLogger("smarttec.commercial_access")

TIMEOUT_PADRAO_S = 2.0
TIMEOUT_MIN_S = 0.05
TIMEOUT_MAX_S = 10.0
MAX_EMPRESAS_PILOTO = 50


class ModoComercial(str, Enum):
    OFF = "off"
    OBSERVE = "observe"
    ENFORCE = "enforce"


class SituacaoObservacao(str, Enum):
    NAO_OBSERVADO_MODO = "NAO_OBSERVADO_MODO"
    NAO_OBSERVADO_NAO_PILOTO = "NAO_OBSERVADO_NAO_PILOTO"
    CONTEXTO_INVALIDO = "CONTEXTO_INVALIDO"
    EVIDENCIA_TEMPORAL_INSUFICIENTE = "EVIDENCIA_TEMPORAL_INSUFICIENTE"
    FALHA_LEITURA = "FALHA_LEITURA"
    TIMEOUT_LEITURA = "TIMEOUT_LEITURA"
    FALHA_POLITICA = "FALHA_POLITICA"
    AVALIADO = "AVALIADO"


_TEMPORAIS = {
    evidencia.MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE,
    evidencia.MotivoLeitura.DATA_AMBIGUA_OU_INVALIDA,
}


@dataclass(frozen=True)
class ConfiguracaoObservacao:
    """Somente configuracao interna; o padrao e sempre ``off``."""
    modo: ModoComercial = ModoComercial.OFF
    empresas_piloto: frozenset[int] = frozenset()
    convencao: evidencia.ConvencaoTemporal = field(default_factory=evidencia.ConvencaoTemporal)
    timeout_leitura_s: float = TIMEOUT_PADRAO_S
    segredo_identificador: bytes | None = field(default=None, repr=False)
    erros: tuple[str, ...] = ()
    enforce_solicitado: bool = False


@dataclass(frozen=True)
class ResultadoObservacao:
    observado: bool
    situacao: SituacaoObservacao
    decisao: politica.DecisaoAcesso | None = None
    limitacoes: tuple[str, ...] = ()

    @property
    def bloqueia(self) -> bool:
        """Constante: observar nunca bloqueia."""
        return False


def _desligada(erros=(), enforce=False):
    return ConfiguracaoObservacao(erros=tuple(erros), enforce_solicitado=enforce)


def _id_positivo(valor):
    return type(valor) is int and valor > 0


def _empresas(valor):
    if valor is None:
        return frozenset()
    if type(valor) is str:
        partes = [parte.strip() for parte in valor.split(",") if parte.strip()]
        if not all(parte.isascii() and parte.isdigit() for parte in partes):
            raise ValueError("empresas_piloto")
        itens = [int(parte) for parte in partes]
    elif type(valor) in (list, tuple, set, frozenset):
        itens = list(valor)
    else:
        raise ValueError("empresas_piloto")
    if len(itens) > MAX_EMPRESAS_PILOTO or not all(_id_positivo(i) for i in itens):
        raise ValueError("empresas_piloto")
    return frozenset(itens)

def carregar_configuracao(
    modo=None,
    empresas_piloto=None,
    *,
    convencao: evidencia.ConvencaoTemporal | None = None,
    timeout_leitura_s=TIMEOUT_PADRAO_S,
    segredo_identificador: bytes | None = None,
) -> ConfiguracaoObservacao:
    """Valida valores brutos. Qualquer erro resulta em ``off`` (nunca em bloqueio).

    ``enforce`` e valor reservado: e registrado como solicitado, mas continua
    ``off`` ate haver homologacao e autorizacao explicita (nao implementadas).
    """
    texto = modo.strip().lower() if type(modo) is str else None
    if modo is None or texto == "off":
        return _desligada()
    if texto == "enforce":
        return _desligada(("ENFORCE_INDISPONIVEL",), enforce=True)
    if texto != "observe":
        return _desligada(("MODO_INVALIDO",))
    try:
        piloto = _empresas(empresas_piloto)
    except ValueError:
        return _desligada(("EMPRESAS_PILOTO_INVALIDAS",))
    if (type(timeout_leitura_s) not in (int, float) or timeout_leitura_s != timeout_leitura_s
            or not TIMEOUT_MIN_S <= timeout_leitura_s <= TIMEOUT_MAX_S):
        return _desligada(("TIMEOUT_INVALIDO",))
    if convencao is None:
        convencao = evidencia.ConvencaoTemporal()
    elif type(convencao) is not evidencia.ConvencaoTemporal:
        return _desligada(("CONVENCAO_INVALIDA",))
    if segredo_identificador is not None and (
            type(segredo_identificador) is not bytes or len(segredo_identificador) < 16):
        return _desligada(("SEGREDO_INVALIDO",))
    return ConfiguracaoObservacao(
        modo=ModoComercial.OBSERVE,
        empresas_piloto=piloto,
        convencao=convencao,
        timeout_leitura_s=float(timeout_leitura_s),
        segredo_identificador=segredo_identificador,
    )


def _identificador(config, empresa_id):
    """HMAC truncado; sem segredo configurado nao se registra identificador."""
    if config.segredo_identificador is None:
        return "-"
    mac = hmac.new(config.segredo_identificador, str(empresa_id).encode(), hashlib.sha256)
    return mac.hexdigest()[:16]


def _registrar(config, empresa_id, modulo_id, resultado):
    # Somente campos controlados: nunca excecoes, SQL, valores ou nomes.
    try:
        decisao = resultado.decisao
        logger.info(
            "commercial_observe situacao=%s permitido=%s motivo=%s limitacoes=%s empresa=%s modulo=%s",
            resultado.situacao.value,
            "-" if decisao is None else str(decisao.permitido).lower(),
            "-" if decisao is None else decisao.motivo.value,
            ",".join(resultado.limitacoes) or "-",
            _identificador(config, empresa_id),
            modulo_id if _id_positivo(modulo_id) else "-",
        )
    except Exception:
        pass


def _ler(sessao_factory, tenant, agora, convencao, leitor):
    sessao = sessao_factory()
    try:
        return leitor(sessao, tenant, agora=agora, convencao=convencao)
    finally:
        for operacao in ("rollback", "close"):
            try:
                getattr(sessao, operacao)()
            except Exception:
                pass


def _agora_utc():
    return datetime.now(timezone.utc)


def observar_acesso(
    config: ConfiguracaoObservacao,
    tenant: TenantContext,
    modulo_id: int,
    *,
    sessao_factory: Callable[[], object],
    relogio: Callable[[], datetime] = _agora_utc,
    leitor=evidencia.ler_evidencias_comerciais,
    avaliador=politica.avaliar_acesso_comercial,
) -> ResultadoObservacao:
    """Avalia e registra; o chamador deve ignorar o retorno para autorizar.

    Nunca levanta excecao, nunca escreve e nunca bloqueia. A empresa vem do
    ``TenantContext`` autenticado, nunca de parametro do cliente. Uma unica
    leitura de evidencias por avaliacao, em sessao propria e com tempo limite.
    """
    if type(config) is not ConfiguracaoObservacao or config.modo is not ModoComercial.OBSERVE:
        return ResultadoObservacao(False, SituacaoObservacao.NAO_OBSERVADO_MODO)
    try:
        return _observar(config, tenant, modulo_id, sessao_factory, relogio, leitor, avaliador)
    except Exception:
        resultado = ResultadoObservacao(True, SituacaoObservacao.FALHA_POLITICA)
        _registrar(config, getattr(tenant, "empresa_id", None), modulo_id, resultado)
        return resultado


def _observar(config, tenant, modulo_id, sessao_factory, relogio, leitor, avaliador):
    if (type(tenant) is not TenantContext or tenant.origem is not TenantOrigin.AUTHENTICATION
            or not _id_positivo(tenant.empresa_id) or not _id_positivo(tenant.user_id)
            or not _id_positivo(modulo_id) or not callable(sessao_factory)):
        resultado = ResultadoObservacao(False, SituacaoObservacao.CONTEXTO_INVALIDO)
        _registrar(config, None, None, resultado)
        return resultado
    if tenant.empresa_id not in config.empresas_piloto:
        return ResultadoObservacao(False, SituacaoObservacao.NAO_OBSERVADO_NAO_PILOTO)
    empresa_id = tenant.empresa_id

    if config.convencao.fuso_comercial is None:
        resultado = ResultadoObservacao(
            True, SituacaoObservacao.EVIDENCIA_TEMPORAL_INSUFICIENTE,
            limitacoes=(evidencia.MotivoLeitura.CONVENCAO_TEMPORAL_AUSENTE.value,),
        )
        _registrar(config, empresa_id, modulo_id, resultado)
        return resultado

    agora = relogio()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="commercial-observe")
    try:
        futuro = executor.submit(_ler, sessao_factory, tenant, agora, config.convencao, leitor)
        try:
            leitura = futuro.result(timeout=config.timeout_leitura_s)
        except _Timeout:
            futuro.cancel()
            resultado = ResultadoObservacao(True, SituacaoObservacao.TIMEOUT_LEITURA)
            _registrar(config, empresa_id, modulo_id, resultado)
            return resultado
        except Exception:
            resultado = ResultadoObservacao(True, SituacaoObservacao.FALHA_LEITURA)
            _registrar(config, empresa_id, modulo_id, resultado)
            return resultado
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    try:
        limitacoes = tuple(sorted(m.value for m in leitura.limitacoes))
        temporal = any(m in _TEMPORAIS for m in leitura.limitacoes)
        decisao = avaliador(politica.ConsultaAcesso(empresa_id, modulo_id, agora), leitura.evidencias)
        if type(decisao) is not politica.DecisaoAcesso:
            raise TypeError
    except Exception:
        resultado = ResultadoObservacao(True, SituacaoObservacao.FALHA_POLITICA)
        _registrar(config, empresa_id, modulo_id, resultado)
        return resultado
    situacao = (SituacaoObservacao.EVIDENCIA_TEMPORAL_INSUFICIENTE if temporal
                else SituacaoObservacao.AVALIADO)
    resultado = ResultadoObservacao(True, situacao, decisao, limitacoes)
    _registrar(config, empresa_id, modulo_id, resultado)
    return resultado
