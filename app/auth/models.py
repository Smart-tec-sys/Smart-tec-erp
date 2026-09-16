"""Domínio futuro de autenticação multiempresa, sem senha ou persistência."""

from dataclasses import dataclass
from enum import Enum

from app.tenant.context import TenantContext, TenantOrigin


class AuthenticationState(str, Enum):
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    INACTIVE_USER = "INACTIVE_USER"
    INACTIVE_COMPANY = "INACTIVE_COMPANY"


@dataclass(frozen=True)
class UserContext:
    user_id: int | str
    display_name: str
    active: bool = True
    system_administrator: bool = False


@dataclass(frozen=True)
class AuthenticatedTenantContext:
    user: UserContext
    tenant: TenantContext
    state: AuthenticationState = AuthenticationState.AUTHENTICATED

    def __post_init__(self) -> None:
        if self.state is AuthenticationState.AUTHENTICATED:
            if not self.user.active:
                raise ValueError("usuário inativo não pode ter sessão autenticada")
            if self.tenant.empresa_id is None:
                raise ValueError("sessão autenticada exige empresa")
            if self.tenant.origem is TenantOrigin.LEGACY_UNSCOPED:
                raise ValueError("sessão autenticada não aceita modo legado")


def logout_context(context: AuthenticatedTenantContext) -> AuthenticationState:
    """Contrato puro de logout; não manipula cookie nem sessão externa."""
    return AuthenticationState.ANONYMOUS
