"""Regras puras para filtragem e bloqueio de acesso cruzado."""

from typing import Any

from .context import TenantContext


class TenantContextRequiredError(RuntimeError):
    pass


class TenantAccessError(PermissionError):
    pass


def require_tenant(context: TenantContext) -> int:
    """Exige empresa explícita; o modo legado não satisfaz operações isoladas."""
    if context.is_legacy_unscoped or context.empresa_id is None:
        raise TenantContextRequiredError("operação exige TenantContext com empresa")
    return context.empresa_id


def validate_resource_tenant(
    resource_empresa_id: int | None,
    current_empresa_id: int,
) -> None:
    """Bloqueia recurso sem empresa ou pertencente a outra empresa."""
    if resource_empresa_id is None or resource_empresa_id != current_empresa_id:
        raise TenantAccessError("recurso não pertence à empresa atual")


def apply_tenant_filter(query: Any, model: Any, empresa_id: int) -> Any:
    """Aplica filtro SQLAlchemy sem acoplar o helper a uma sessão concreta."""
    if empresa_id <= 0:
        raise ValueError("empresa_id deve ser positivo")
    tenant_column = getattr(model, "empresa_id", None)
    if tenant_column is None:
        raise TypeError("modelo ainda não possui coluna empresa_id")
    return query.filter(tenant_column == empresa_id)
