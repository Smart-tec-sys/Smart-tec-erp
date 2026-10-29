"""Contagem e verificacao de vagas de usuarios por empresa (4D.2).

Modulo isolado: nao importa modelos nem o modulo de banco do ERP, nao cria nem
reativa vinculos, nao faz commit e nao esta ligado a nenhuma rota. O limite
contratual nunca e presumido: vem de um resolvedor injetado e, se nao estiver
comprovado, a decisao e ``LIMITE_DESCONHECIDO``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text

# Dialetos sem bloqueio de linha (testes locais); os demais exigem FOR UPDATE.
_DIALETOS_SEM_TRAVA = frozenset({"sqlite"})

_SQL_EMPRESA = "SELECT id, status FROM empresas WHERE id = :empresa_id"

# Uma linha por usuario e empresa: (empresa_id, usuario_id) e unico, entao o
# papel (OWNER, ADMIN ou USUARIO) nao duplica a contagem. A equipe da
# plataforma nao esta em empresa_usuarios e portanto nao entra.
_SQL_CONTAGEM = text(
    "SELECT COUNT(*) FROM empresa_usuarios eu "
    "JOIN usuarios u ON u.id = eu.usuario_id "
    "WHERE eu.empresa_id = :empresa_id AND eu.ativo = :ativo AND u.status = 'ATIVO'"
)

LimiteResolvedor = Callable[[object, int], "int | None"]


class SituacaoVaga(str, Enum):
    VAGA_DISPONIVEL = "VAGA_DISPONIVEL"
    LIMITE_ATINGIDO = "LIMITE_ATINGIDO"
    LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"
    LIMITE_DESCONHECIDO = "LIMITE_DESCONHECIDO"
    EMPRESA_INDISPONIVEL = "EMPRESA_INDISPONIVEL"


@dataclass(frozen=True)
class DecisaoVaga:
    situacao: SituacaoVaga
    usuarios_ativos: int | None = None
    limite: int | None = None

    @property
    def permite_expansao(self) -> bool:
        """Somente com vaga comprovada; desconhecido nunca autoriza."""
        return self.situacao is SituacaoVaga.VAGA_DISPONIVEL


def _id_positivo(valor) -> bool:
    return type(valor) is int and valor > 0


def _limite_valido(valor) -> bool:
    return type(valor) is int and valor >= 0


def _dialeto(sessao) -> str:
    return sessao.get_bind().dialect.name


def contar_usuarios_ativos(sessao, empresa_id: int) -> int:
    """Usuarios ATIVOS com vinculo ativo na empresa; somente leitura."""
    if not _id_positivo(empresa_id):
        raise ValueError("empresa_id invalido")
    return int(sessao.execute(_SQL_CONTAGEM, {"empresa_id": empresa_id, "ativo": True}).scalar_one())


def verificar_vaga(
    sessao,
    empresa_id: int,
    *,
    resolver_limite: LimiteResolvedor,
) -> DecisaoVaga:
    """Decide se a empresa pode ocupar mais uma vaga.

    Trava a linha da empresa (FOR UPDATE) na transacao recebida antes de
    contar e decidir. Nao faz commit nem rollback: o chamador controla a
    transacao e mantem a trava ate concluir a expansao.
    """
    if not _id_positivo(empresa_id) or not callable(resolver_limite):
        return DecisaoVaga(SituacaoVaga.EMPRESA_INDISPONIVEL)

    sql = _SQL_EMPRESA if _dialeto(sessao) in _DIALETOS_SEM_TRAVA else _SQL_EMPRESA + " FOR UPDATE"
    empresa = sessao.execute(text(sql), {"empresa_id": empresa_id}).first()
    if empresa is None or empresa[1] != "ATIVA":
        return DecisaoVaga(SituacaoVaga.EMPRESA_INDISPONIVEL)

    ativos = contar_usuarios_ativos(sessao, empresa_id)

    try:
        limite = resolver_limite(sessao, empresa_id)
    except Exception:
        limite = None
    if not _limite_valido(limite):
        return DecisaoVaga(SituacaoVaga.LIMITE_DESCONHECIDO, ativos, None)

    if ativos > limite:
        situacao = SituacaoVaga.LIMITE_EXCEDIDO
    elif ativos == limite:
        situacao = SituacaoVaga.LIMITE_ATINGIDO
    else:
        situacao = SituacaoVaga.VAGA_DISPONIVEL
    return DecisaoVaga(situacao, ativos, limite)