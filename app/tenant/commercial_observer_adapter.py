"""Adaptador entre o modo de observacao comercial e a infraestrutura SQLAlchemy.

Nao importa o modulo de banco do ERP (que cria engine ao importar), nao le ambiente e
nao registra dependencias em rotas. Quem integrar injeta um ``sessionmaker``
ja existente e valores de configuracao ja resolvidos.

Seguranca:
* A empresa vem somente do ``TenantContext`` autenticado; a validacao final e
  a de ``commercial_access`` (nao ha segunda logica de autorizacao).
* Cada observacao usa sessao propria e uma unica transacao somente leitura,
  com ``statement_timeout`` e ``lock_timeout`` locais a transacao
  (``set_config(..., true)``), sem alterar configuracao global ou do banco.
* O timeout do banco e menor que a espera da thread, de modo que a consulta
  e cancelada pelo PostgreSQL e a thread nao fica presa.
* Configuracao invalida ou ausente resulta em ``off``; ``enforce`` e
  indisponivel. O retorno da observacao nunca deve ser usado para autorizar.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import text

from . import commercial_access as acesso
from . import commercial_evidence as evidencia
from .context import TenantContext

# Ordem importa: tudo vale apenas para a transacao corrente (is_local=true).
_PREPARO = (
    ("transaction_read_only", "on"),
    ("statement_timeout", None),
    ("lock_timeout", None),
    ("idle_in_transaction_session_timeout", None),
)
_SQL_PREPARO = text("SELECT set_config(:nome, :valor, true)")
FRACAO_TIMEOUT_BANCO = 0.8
TIMEOUT_BANCO_MIN_MS = 40


def timeout_banco_ms(timeout_leitura_s: float) -> int:
    """Timeout do PostgreSQL, sempre menor que a espera da thread."""
    return max(TIMEOUT_BANCO_MIN_MS, int(timeout_leitura_s * 1000 * FRACAO_TIMEOUT_BANCO))


class SessaoObservacao:
    """Sessao descartavel: prepara a transacao somente leitura antes de executar."""

    def __init__(self, sessao, timeout_ms: int):
        self._sessao = sessao
        self._timeout_ms = timeout_ms
        self._preparada = False

    def _preparar(self):
        for nome, valor in _PREPARO:
            self._sessao.execute(
                _SQL_PREPARO,
                {"nome": nome, "valor": valor if valor is not None else str(self._timeout_ms)},
            )
        self._preparada = True

    def execute(self, statement, params):
        if not self._preparada:
            self._preparar()
        return self._sessao.execute(statement, params)

    def rollback(self):
        self._sessao.rollback()

    def close(self):
        self._sessao.close()


def criar_fabrica_sessao(
    session_factory: Callable[[], object], timeout_leitura_s: float
) -> Callable[[], SessaoObservacao]:
    """Fabrica para ``observar_acesso``: nunca usa a sessao da requisicao."""
    if not callable(session_factory):
        raise TypeError("session_factory deve ser chamavel")
    timeout_ms = timeout_banco_ms(timeout_leitura_s)

    def fabrica() -> SessaoObservacao:
        return SessaoObservacao(session_factory(), timeout_ms)

    return fabrica


@dataclass(frozen=True)
class ObservadorComercial:
    config: acesso.ConfiguracaoObservacao
    _fabrica: Callable[[], SessaoObservacao] | None = None

    @property
    def ativo(self) -> bool:
        return self.config.modo is acesso.ModoComercial.OBSERVE and self._fabrica is not None

    def observar(self, tenant: TenantContext, modulo_id: int) -> acesso.ResultadoObservacao:
        """Nunca levanta e nunca bloqueia; o chamador deve ignorar o retorno."""
        try:
            if not self.ativo:
                return acesso.ResultadoObservacao(False, acesso.SituacaoObservacao.NAO_OBSERVADO_MODO)
            return acesso.observar_acesso(
                self.config, tenant, modulo_id, sessao_factory=self._fabrica
            )
        except Exception:
            return acesso.ResultadoObservacao(True, acesso.SituacaoObservacao.FALHA_POLITICA)


def criar_observador(
    modo=None,
    empresas_piloto=None,
    *,
    session_factory: Callable[[], object] | None = None,
    convencao: evidencia.ConvencaoTemporal | None = None,
    timeout_leitura_s=acesso.TIMEOUT_PADRAO_S,
    segredo_identificador: bytes | None = None,
) -> ObservadorComercial:
    """Monta o observador; qualquer problema de configuracao resulta em ``off``."""
    try:
        config = acesso.carregar_configuracao(
            modo,
            empresas_piloto,
            convencao=convencao,
            timeout_leitura_s=timeout_leitura_s,
            segredo_identificador=segredo_identificador,
        )
        if config.modo is not acesso.ModoComercial.OBSERVE:
            return ObservadorComercial(config)
        return ObservadorComercial(config, criar_fabrica_sessao(session_factory, config.timeout_leitura_s))
    except Exception:
        return ObservadorComercial(acesso.ConfiguracaoObservacao())
