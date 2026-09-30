from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.admin.service import (
    PlatformMemberContext,
    resolve_platform_member,
)
from app.auth.dependencies import get_verified_external_identity
from app.auth.service import ExternalIdentity
from app.database import get_db


def get_current_platform_member(
    identity: Annotated[
        ExternalIdentity,
        Depends(get_verified_external_identity),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> PlatformMemberContext:

    try:
        return resolve_platform_member(
            db,
            identity=identity,
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="acesso administrativo não autorizado",
        ) from exc

    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="contexto administrativo inválido",
        ) from exc


def require_platform_permission(
    permission: str,
) -> Callable:

    permission = permission.strip().upper()

    if not permission:
        raise ValueError("permissão administrativa obrigatória")

    def dependency(
        member: Annotated[
            PlatformMemberContext,
            Depends(get_current_platform_member),
        ],
    ) -> PlatformMemberContext:

        if not member.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permissão administrativa insuficiente",
            )

        return member

    return dependency