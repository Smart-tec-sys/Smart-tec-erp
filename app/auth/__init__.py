"""Contratos e serviços de autenticação desacoplados do provedor de identidade."""

from .models import (
    AuthenticatedTenantContext,
    AuthenticationState,
    UserContext,
)
from .service import (
    ExternalIdentity,
    list_identity_company_ids,
    resolve_identity_tenant,
)

__all__ = [
    "AuthenticatedTenantContext",
    "AuthenticationState",
    "UserContext",
    "ExternalIdentity",
    "resolve_identity_tenant",
    "list_identity_company_ids",
]