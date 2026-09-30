"""Estado autenticado do frontend, sem dependência direta de Streamlit."""

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any

from app.tenant.session import (
    TENANT_SESSION_KEY,
    TENANT_SLUG_SESSION_KEY,
    TENANT_USER_SESSION_KEY,
)


AUTH_ACCESS_TOKEN_KEY = "auth_access_token"
AUTH_REFRESH_TOKEN_KEY = "auth_refresh_token"
AUTH_USER_ID_KEY = "auth_user_id"
AUTH_EMAIL_KEY = "auth_email"
AUTH_EXPIRES_AT_KEY = "auth_expires_at"
AUTH_COMPANIES_KEY = "auth_companies"
AUTH_ACTIVE_COMPANY_ID_KEY = "auth_active_company_id"

AUTH_SESSION_KEYS = (
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AUTH_USER_ID_KEY,
    AUTH_EMAIL_KEY,
    AUTH_EXPIRES_AT_KEY,
    AUTH_COMPANIES_KEY,
    AUTH_ACTIVE_COMPANY_ID_KEY,
)


@dataclass(frozen=True)
class AuthSessionData:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    user_id: str
    email: str
    expires_at: float | None = None

    def __repr__(self) -> str:
        return (
            "AuthSessionData(access_token=<redacted>, refresh_token=<redacted>, "
            f"user_id={self.user_id!r}, email={self.email!r}, "
            f"expires_at={self.expires_at!r})"
        )


def is_authenticated(session: MutableMapping[str, Any]) -> bool:
    return bool(session.get(AUTH_ACCESS_TOKEN_KEY) and session.get(AUTH_USER_ID_KEY))


def get_access_token(session: MutableMapping[str, Any]) -> str | None:
    token = session.get(AUTH_ACCESS_TOKEN_KEY)
    return str(token) if token else None


def set_authenticated_session(session: MutableMapping[str, Any], data: AuthSessionData) -> None:
    session[AUTH_ACCESS_TOKEN_KEY] = data.access_token
    session[AUTH_REFRESH_TOKEN_KEY] = data.refresh_token
    session[AUTH_USER_ID_KEY] = data.user_id
    session[AUTH_EMAIL_KEY] = data.email
    session[AUTH_EXPIRES_AT_KEY] = data.expires_at


def get_active_company_id(session: MutableMapping[str, Any]) -> int | None:
    value = session.get(AUTH_ACTIVE_COMPANY_ID_KEY)
    return int(value) if value is not None else None


def clear_commercial_tenant_state(session: MutableMapping[str, Any]) -> None:
    prefixes = ("tenant:", "cache:tenant:")
    for key in list(session):
        if isinstance(key, str) and key.startswith(prefixes):
            session.pop(key, None)


def set_active_company_id(
    session: MutableMapping[str, Any],
    empresa_id: int,
    *,
    slug: str | None = None,
) -> None:
    if empresa_id <= 0:
        raise ValueError("empresa_id deve ser positivo")
    previous = get_active_company_id(session)
    if previous is not None and previous != empresa_id:
        clear_commercial_tenant_state(session)
    session[AUTH_ACTIVE_COMPANY_ID_KEY] = empresa_id
    session[TENANT_SESSION_KEY] = empresa_id
    session[TENANT_USER_SESSION_KEY] = session.get(AUTH_USER_ID_KEY)
    if slug:
        session[TENANT_SLUG_SESSION_KEY] = slug


def clear_authenticated_session(session: MutableMapping[str, Any]) -> None:
    clear_commercial_tenant_state(session)
    for key in AUTH_SESSION_KEYS + (
        TENANT_SESSION_KEY,
        TENANT_USER_SESSION_KEY,
        TENANT_SLUG_SESSION_KEY,
    ):
        session.pop(key, None)
