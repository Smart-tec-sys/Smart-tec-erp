"""Portfólio por empresa em memória; nenhuma escrita no repositório SQL."""

from dataclasses import dataclass, field

from .context import TenantContext
from .isolation import require_tenant


@dataclass
class InMemoryTenantPortfolio:
    _active_by_tenant: dict[int, set[str]] = field(default_factory=dict)

    def list_active(self, context: TenantContext) -> tuple[str, ...]:
        tenant_id = require_tenant(context)
        return tuple(sorted(self._active_by_tenant.get(tenant_id, set())))

    def activate(self, context: TenantContext, technical_model: str) -> None:
        tenant_id = require_tenant(context)
        model = technical_model.strip().upper()
        if not model:
            raise ValueError("modelo técnico é obrigatório")
        self._active_by_tenant.setdefault(tenant_id, set()).add(model)

    def deactivate(self, context: TenantContext, technical_model: str) -> None:
        tenant_id = require_tenant(context)
        self._active_by_tenant.setdefault(tenant_id, set()).discard(
            technical_model.strip().upper()
        )
