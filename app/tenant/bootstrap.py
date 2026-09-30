"""Contrato conceitual de uma empresa recém-criada e sem dados comerciais."""

from dataclasses import dataclass

from app.technical.catalog import TECHNICAL_CATALOG

from .context import TenantContext
from .isolation import require_tenant


@dataclass(frozen=True)
class EmptyTenantSnapshot:
    empresa_id: int
    produtos: tuple = ()
    fornecedores: tuple = ()
    clientes: tuple = ()
    custos: tuple = ()
    estoque: tuple = ()
    portfolio: tuple = ()
    funcoes_tecnicas_globais: tuple[str, ...] = ()


def new_tenant_empty_snapshot(context: TenantContext) -> EmptyTenantSnapshot:
    empresa_id = require_tenant(context)
    return EmptyTenantSnapshot(
        empresa_id=empresa_id,
        funcoes_tecnicas_globais=tuple(TECHNICAL_CATALOG),
    )
