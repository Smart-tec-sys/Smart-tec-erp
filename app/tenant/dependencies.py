import os

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.service import resolve_identity_tenant
from app.auth.supabase_jwt import (
    SupabaseAuthConfigurationError,
    SupabaseTokenError,
    extract_bearer_token,
    verify_supabase_access_token,
)
from app.database import get_db

from .context import LEGACY_UNSCOPED, TenantContext, TenantOrigin


DEV_TENANT_ID = 1
DEV_TENANT_SLUG = "smart-tec-persianas"

AUTH_MODE_DEV = "dev"
AUTH_MODE_AUTHENTICATED = "authenticated"


def get_auth_mode() -> str:
    mode = os.getenv("SMARTTEC_AUTH_MODE", AUTH_MODE_DEV).strip().lower()

    if mode not in {AUTH_MODE_DEV, AUTH_MODE_AUTHENTICATED}:
        raise RuntimeError(
            "SMARTTEC_AUTH_MODE inválido. Use 'dev' ou 'authenticated'."
        )

    return mode


def get_development_tenant() -> TenantContext:
    """Resolve a Smart-tec somente em ambiente local explicitamente reconhecido."""
    environment = os.getenv("SMARTTEC_ENV", "development").strip().lower()

    if environment not in {"dev", "development", "local"}:
        return LEGACY_UNSCOPED

    return TenantContext(
        empresa_id=DEV_TENANT_ID,
        origem=TenantOrigin.SESSION,
    )


def get_current_tenant(
    x_empresa_id: Annotated[int | None, Header(alias="X-Empresa-ID")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Resolve o tenant atual.

    Modo DEV:
    - preserva o comportamento local existente;
    - aceita header explícito somente quando habilitado para testes.

    Modo AUTHENTICATED:
    - não aceita fallback DEV;
    - não aceita X-Empresa-ID arbitrário;
    - a resolução definitiva será feita pela identidade autenticada.
    """

    auth_mode = get_auth_mode()

    allow_test_header = (
        os.getenv("SMARTTEC_ALLOW_TEST_TENANT_HEADER") == "1"
    )

    if auth_mode == AUTH_MODE_DEV and allow_test_header and x_empresa_id is not None:
        return TenantContext(
            empresa_id=x_empresa_id,
            user_id=x_user_id,
            origem=TenantOrigin.EXPLICIT_TEST,
        )

    if auth_mode == AUTH_MODE_DEV:
        return get_development_tenant()

    if x_empresa_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="empresa ativa não informada",
        )

    try:
        token = extract_bearer_token(authorization)
        identity = verify_supabase_access_token(token).identity
        return resolve_identity_tenant(
            db,
            identity=identity,
            empresa_id=x_empresa_id,
        ).tenant
    except SupabaseAuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="autenticação não configurada",
        ) from exc
    except SupabaseTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token de autenticação inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso à empresa não autorizado",
        ) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contexto de empresa inválido",
        ) from exc
