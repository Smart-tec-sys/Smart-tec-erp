"""Pool de conexoes dedicado a observacao comercial (4C.12).

Nao importa o modulo de banco do ERP, nao le ambiente e nao se ativa sozinho.
Recebe a URL de conexao ja resolvida pela aplicacao, cria o engine somente na
primeira utilizacao e nunca compartilha sessoes entre chamadas.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

LIMITE_POOL = 5
LIMITE_OVERFLOW = 2
LIMITE_ESPERA_S = 5.0
LIMITE_RECICLAGEM_S = 3600


class PoolObservacaoErro(Exception):
    """Falha controlada; a mensagem nunca contem URL nem credenciais."""


@dataclass(frozen=True)
class ConfiguracaoPool:
    tamanho: int = 2
    excesso_maximo: int = 0
    espera_conexao_s: float = 1.0
    reciclagem_s: int = 300
    verificar_conexao: bool = True
    timeout_conexao_s: int = 3

    def __post_init__(self):
        def inteiro(v):
            return isinstance(v, int) and not isinstance(v, bool)

        def numero(v):
            return isinstance(v, (int, float)) and not isinstance(v, bool)

        if not inteiro(self.tamanho) or not 1 <= self.tamanho <= LIMITE_POOL:
            raise ValueError("tamanho invalido")
        if not inteiro(self.excesso_maximo) or not 0 <= self.excesso_maximo <= LIMITE_OVERFLOW:
            raise ValueError("excesso_maximo invalido")
        if not numero(self.espera_conexao_s) or not 0.05 <= self.espera_conexao_s <= LIMITE_ESPERA_S:
            raise ValueError("espera_conexao_s invalida")
        if not inteiro(self.reciclagem_s) or not 30 <= self.reciclagem_s <= LIMITE_RECICLAGEM_S:
            raise ValueError("reciclagem_s invalida")
        if not isinstance(self.verificar_conexao, bool):
            raise ValueError("verificar_conexao invalido")
        if not inteiro(self.timeout_conexao_s) or not 1 <= self.timeout_conexao_s <= 10:
            raise ValueError("timeout_conexao_s invalido")


def _kwargs_engine(cfg: ConfiguracaoPool) -> dict[str, Any]:
    return {
        "poolclass": QueuePool,
        "pool_size": cfg.tamanho,
        "max_overflow": cfg.excesso_maximo,
        "pool_timeout": cfg.espera_conexao_s,
        "pool_recycle": cfg.reciclagem_s,
        "pool_pre_ping": cfg.verificar_conexao,
        "connect_args": {"connect_timeout": cfg.timeout_conexao_s},
        "echo": False,
        "hide_parameters": True,
    }


@dataclass
class PoolObservacao:
    """Engine proprio e preguicoso; `fechar` descarta todas as conexoes."""

    _url: Any = field(repr=False)
    configuracao: ConfiguracaoPool = field(default_factory=ConfiguracaoPool)
    _engine_factory: Callable[..., Any] = field(default=create_engine, repr=False)
    _engine: Any = field(default=None, init=False, repr=False)
    _sessionmaker: Any = field(default=None, init=False, repr=False)
    _fechado: bool = field(default=False, init=False)
    _trava: Any = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def iniciado(self) -> bool:
        return self._engine is not None

    @property
    def fechado(self) -> bool:
        return self._fechado

    def _garantir_engine(self):
        with self._trava:
            if self._fechado:
                raise PoolObservacaoErro("pool de observacao encerrado")
            if self._engine is None:
                try:
                    self._engine = self._engine_factory(self._url, **_kwargs_engine(self.configuracao))
                    self._sessionmaker = sessionmaker(
                        bind=self._engine, autocommit=False, autoflush=False, expire_on_commit=False
                    )
                except Exception:
                    self._engine = None
                    self._sessionmaker = None
                    raise PoolObservacaoErro("falha ao preparar o pool de observacao") from None
            return self._sessionmaker

    def session_factory(self) -> Session:
        """Nova sessao a cada chamada; a conexao so e obtida na primeira consulta."""
        return self._garantir_engine()()

    def fechar(self) -> None:
        with self._trava:
            self._fechado = True
            engine, self._engine, self._sessionmaker = self._engine, None, None
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                pass

    def __repr__(self) -> str:
        return f"PoolObservacao(iniciado={self.iniciado}, fechado={self._fechado})"


def criar_pool_observacao(
    url_conexao: Any,
    configuracao: ConfiguracaoPool | None = None,
    *,
    engine_factory: Callable[..., Any] | None = None,
) -> PoolObservacao:
    """Valida entradas e devolve o pool sem abrir nenhuma conexao."""
    if url_conexao is None or (isinstance(url_conexao, str) and not url_conexao.strip()):
        raise PoolObservacaoErro("url de conexao ausente")
    if configuracao is not None and not isinstance(configuracao, ConfiguracaoPool):
        raise PoolObservacaoErro("configuracao invalida")
    return PoolObservacao(
        url_conexao,
        configuracao or ConfiguracaoPool(),
        engine_factory or create_engine,
    )
