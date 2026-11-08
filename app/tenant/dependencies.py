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
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB

from .context import TenantContext, TenantOrigin


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


def get_development_tenant(db: Session) -> TenantContext:
    """Resolve identidade DEV somente por configuração local controlada pelo servidor."""
    environment = os.getenv("SMARTTEC_ENV", "").strip().lower()
    if environment not in {"dev", "development", "local"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="modo de desenvolvimento permitido somente em ambiente local",
        )

    usuario_configurado = os.getenv("SMARTTEC_DEV_USER_ID", "").strip()
    if not usuario_configurado:
        return TenantContext(
            empresa_id=DEV_TENANT_ID,
            origem=TenantOrigin.SESSION,
        )

    try:
        usuario_id = int(usuario_configurado)
        if usuario_id <= 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identidade de desenvolvimento inválida",
        ) from exc

    usuario = db.get(UsuarioDB, usuario_id)
    if usuario is None or str(usuario.status).upper() != "ATIVO":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identidade de desenvolvimento não está ativa",
        )

    vinculo = db.query(EmpresaUsuarioDB).filter(
        EmpresaUsuarioDB.empresa_id == DEV_TENANT_ID,
        EmpresaUsuarioDB.usuario_id == usuario_id,
        EmpresaUsuarioDB.ativo.is_(True),
    ).first()
    if vinculo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="identidade de desenvolvimento sem vínculo ativo com a empresa local",
        )

    return TenantContext(
        empresa_id=DEV_TENANT_ID,
        user_id=usuario.id,
        origem=TenantOrigin.SESSION,
    )


def get_current_tenant(
    x_empresa_id: Annotated[int | None, Header(alias="X-Empresa-ID")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Resolve o tenant atual.

    Modo DEV:
    - permite somente empresa local fixa;
    - ignora X-User-ID e deriva usuário apenas de configuração server-side e vínculo ativo.

    Modo AUTHENTICATED:
    - não aceita fallback DEV;
    - não aceita X-Empresa-ID arbitrário;
    - a resolução definitiva será feita pela identidade autenticada.
    """

    auth_mode = get_auth_mode()

    if auth_mode == AUTH_MODE_DEV:
        return get_development_tenant(db)

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
