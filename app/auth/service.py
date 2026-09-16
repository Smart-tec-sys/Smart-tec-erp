from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.auth.models import AuthenticatedTenantContext
from app.auth.tenant_resolver import (
    list_authorized_company_ids,
    resolve_authenticated_tenant,
)


@dataclass(frozen=True)
class ExternalIdentity:
    """
    Identidade já validada por um provedor externo.

    Este objeto NÃO valida token e NÃO representa login.
    No futuro será preenchido somente depois da validação
    criptográfica pelo provedor de identidade.
    """

    provider: str
    subject: str


def resolve_identity_tenant(
    db: Session,
    *,
    identity: ExternalIdentity,
    empresa_id: int,
) -> AuthenticatedTenantContext:
    """
    Resolve uma identidade externa já autenticada para um tenant autorizado.

    Não aceita fallback DEV.
    Não escolhe empresa automaticamente.
    """

    if not isinstance(identity, ExternalIdentity):
        raise TypeError("identidade externa inválida")

    return resolve_authenticated_tenant(
        db,
        provider=identity.provider,
        provider_subject=identity.subject,
        empresa_id=empresa_id,
    )


def list_identity_company_ids(
    db: Session,
    *,
    identity: ExternalIdentity,
) -> list[int]:
    """
    Lista somente empresas ativas às quais a identidade possui vínculo ativo.
    """

    if not isinstance(identity, ExternalIdentity):
        raise TypeError("identidade externa inválida")

    return list_authorized_company_ids(
        db,
        provider=identity.provider,
        provider_subject=identity.subject,
    )