"""Ponto de integracao do observador comercial ao app FastAPI (4C.14).

Nesta fase o resultado e sempre o modo ``off``: nenhum pool, engine, thread,
consulta ou log e criado, e nenhuma rota depende do observador. ``observe`` e
``enforce`` solicitados sao registrados apenas como pedido nao habilitado. A
futura ativacao controlada devera substituir ``MODOS_HABILITADOS`` por uma
decisao explicita e autorizada.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import commercial_access as acesso
from .commercial_observer_adapter import ObservadorComercial

MODOS_HABILITADOS = frozenset({acesso.ModoComercial.OFF})


@dataclass(frozen=True)
class IntegracaoComercial:
    """Estado guardado em ``app.state``; em OFF nao possui recursos a liberar."""

    observador: ObservadorComercial
    modo_solicitado_valido: bool

    @property
    def modo(self) -> acesso.ModoComercial:
        return self.observador.config.modo

    @property
    def possui_recursos(self) -> bool:
        return False

    def encerrar(self) -> None:
        return None


def preparar_integracao_comercial(valor_modo=None) -> IntegracaoComercial:
    """Nunca levanta, nunca abre conexoes e sempre devolve o modo ``off``."""
    valido = isinstance(valor_modo, str) and valor_modo.strip().lower() in {m.value for m in acesso.ModoComercial}
    return IntegracaoComercial(
        ObservadorComercial(acesso.ConfiguracaoObservacao()), valido
    )