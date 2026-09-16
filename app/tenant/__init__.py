"""Contratos de isolamento multiempresa ainda não ligados às rotas legadas."""

from .context import LEGACY_UNSCOPED, TenantContext, TenantOrigin
from .isolation import TenantAccessError, require_tenant, validate_resource_tenant

__all__ = [
    "LEGACY_UNSCOPED",
    "TenantAccessError",
    "TenantContext",
    "TenantOrigin",
    "require_tenant",
    "validate_resource_tenant",
]
