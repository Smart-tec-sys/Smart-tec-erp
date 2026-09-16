"""Adaptador futuro de sessão sem importar Streamlit."""

from collections.abc import Mapping
from typing import Any

from .context import LEGACY_UNSCOPED, TenantContext, TenantOrigin


TENANT_SESSION_KEY = "tenant_empresa_id"
TENANT_USER_SESSION_KEY = "tenant_user_id"
TENANT_SLUG_SESSION_KEY = "tenant_slug"


def get_tenant_from_session(session: Mapping[str, Any]) -> TenantContext:
    empresa_id = session.get(TENANT_SESSION_KEY)
    if empresa_id is None:
        return LEGACY_UNSCOPED
    return TenantContext(
        empresa_id=int(empresa_id),
        user_id=session.get(TENANT_USER_SESSION_KEY),
        origem=TenantOrigin.SESSION,
    )


def tenant_cache_key(context: TenantContext, namespace: str, *parts: object) -> tuple:
    """Gera chave segura para caches novos, recusando o modo sem escopo."""
    empresa_id = context.empresa_id
    if empresa_id is None:
        raise ValueError("cache tenant-aware exige empresa_id")
    return ("tenant", empresa_id, namespace, *parts)


def tenant_session_key(context: TenantContext, key: str) -> str:
    """Cria namespace de sessão comercial estável e isolado por empresa."""
    if context.empresa_id is None:
        raise ValueError("sessão tenant-aware exige empresa_id")
    clean_key = str(key or "").strip()
    if not clean_key:
        raise ValueError("chave de sessão é obrigatória")
    return f"tenant:{context.empresa_id}:{clean_key}"


def initialize_development_tenant_session(session: dict[str, Any]) -> TenantContext:
    """Inicializa uma única identidade DEV; não consulta nem escolhe empresa."""
    from .dependencies import DEV_TENANT_ID, DEV_TENANT_SLUG

    session.setdefault(TENANT_SESSION_KEY, DEV_TENANT_ID)
    session.setdefault(TENANT_SLUG_SESSION_KEY, DEV_TENANT_SLUG)
    return get_tenant_from_session(session)
