from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.service import ExternalIdentity, resolve_identity_tenant
from app.auth.supabase_jwt import (
    SupabaseAuthConfigurationError,
    SupabaseTokenError,
    extract_bearer_token,
    verify_supabase_access_token,
)
from app.database import get_db
from app.tenant.context import TenantContext


def get_verified_external_identity(
    authorization: Annotated[
        str | None,
        Header(alias="Authorization"),
    ] = None,
) -> ExternalIdentity:
    try:
        token = extract_bearer_token(authorization)
        verified = verify_supabase_access_token(token)
        return verified.identity

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


def get_authenticated_tenant(
    empresa_id: int,
    identity: Annotated[
        ExternalIdentity,
        Depends(get_verified_external_identity),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> TenantContext:
    """
    Resolve tenant somente após:
    JWT válido -> identidade externa -> vínculo ativo -> empresa ativa.

    empresa_id aqui representa a empresa que o usuário pretende acessar;
    o acesso só é concedido se existir vínculo persistido.
    """

    try:
        authenticated = resolve_identity_tenant(
            db,
            identity=identity,
            empresa_id=empresa_id,
        )

        return authenticated.tenant

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso à empresa não autorizado",
        ) from exc

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contexto de empresa inválido",
        ) from exc