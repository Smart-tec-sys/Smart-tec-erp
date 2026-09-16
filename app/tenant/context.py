"""Contexto puro da empresa atual, sem dependência de framework."""

from dataclasses import dataclass
from enum import Enum


class TenantOrigin(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    SESSION = "SESSION"
    EXPLICIT_TEST = "EXPLICIT_TEST"
    LEGACY_UNSCOPED = "LEGACY_UNSCOPED"


@dataclass(frozen=True)
class TenantContext:
    empresa_id: int | None
    user_id: int | str | None = None
    origem: TenantOrigin = TenantOrigin.AUTHENTICATION

    def __post_init__(self) -> None:
        if self.empresa_id is not None and self.empresa_id <= 0:
            raise ValueError("empresa_id deve ser positivo")
        if self.origem is TenantOrigin.LEGACY_UNSCOPED and self.empresa_id is not None:
            raise ValueError("LEGACY_UNSCOPED não pode possuir empresa_id")
        if self.origem is not TenantOrigin.LEGACY_UNSCOPED and self.empresa_id is None:
            raise ValueError("empresa_id é obrigatório fora do modo legado")

    @property
    def is_legacy_unscoped(self) -> bool:
        return self.origem is TenantOrigin.LEGACY_UNSCOPED


# Compatibilidade temporária até os dados legados serem atribuídos a uma empresa.
LEGACY_UNSCOPED = TenantContext(
    empresa_id=None,
    origem=TenantOrigin.LEGACY_UNSCOPED,
)
