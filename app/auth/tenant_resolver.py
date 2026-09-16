from sqlalchemy.orm import Session

from app.auth.models import AuthenticatedTenantContext, UserContext
from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB
from app.tenant.context import TenantContext, TenantOrigin


VALID_ROLES = {"OWNER", "ADMIN", "USUARIO"}


def resolve_authenticated_tenant(
    db: Session,
    *,
    provider: str,
    provider_subject: str,
    empresa_id: int,
) -> AuthenticatedTenantContext:
    provider = (provider or "").strip()
    provider_subject = (provider_subject or "").strip()

    if not provider:
        raise ValueError("provedor de identidade é obrigatório")

    if not provider_subject:
        raise ValueError("identidade externa é obrigatória")

    if empresa_id <= 0:
        raise ValueError("empresa_id deve ser positivo")

    usuario = (
        db.query(UsuarioDB)
        .filter(
            UsuarioDB.provedor == provider,
            UsuarioDB.provedor_subject == provider_subject,
        )
        .one_or_none()
    )

    if usuario is None:
        raise PermissionError("usuário autenticado não encontrado")

    if usuario.status != "ATIVO":
        raise PermissionError("usuário inativo")

    vinculo = (
        db.query(EmpresaUsuarioDB)
        .filter(
            EmpresaUsuarioDB.usuario_id == usuario.id,
            EmpresaUsuarioDB.empresa_id == empresa_id,
        )
        .one_or_none()
    )

    if vinculo is None:
        raise PermissionError("usuário não possui vínculo com a empresa")

    if not vinculo.ativo:
        raise PermissionError("vínculo usuário-empresa inativo")

    if vinculo.papel not in VALID_ROLES:
        raise PermissionError("papel de usuário inválido")

    empresa = (
        db.query(EmpresaDB)
        .filter(EmpresaDB.id == empresa_id)
        .one_or_none()
    )

    if empresa is None:
        raise PermissionError("empresa não encontrada")

    if empresa.status != "ATIVA":
        raise PermissionError("empresa inativa")

    user_context = UserContext(
        user_id=str(usuario.id),
        display_name=usuario.nome,
        active=True,
        system_administrator=False,
    )

    tenant_context = TenantContext(
        empresa_id=empresa.id,
        user_id=usuario.id,
        origem=TenantOrigin.AUTHENTICATION,
    )

    return AuthenticatedTenantContext(
        user=user_context,
        tenant=tenant_context,
    )


def list_authorized_company_ids(
    db: Session,
    *,
    provider: str,
    provider_subject: str,
) -> list[int]:
    usuario = (
        db.query(UsuarioDB)
        .filter(
            UsuarioDB.provedor == provider,
            UsuarioDB.provedor_subject == provider_subject,
            UsuarioDB.status == "ATIVO",
        )
        .one_or_none()
    )

    if usuario is None:
        return []

    rows = (
        db.query(EmpresaUsuarioDB.empresa_id)
        .join(EmpresaDB, EmpresaDB.id == EmpresaUsuarioDB.empresa_id)
        .filter(
            EmpresaUsuarioDB.usuario_id == usuario.id,
            EmpresaUsuarioDB.ativo.is_(True),
            EmpresaUsuarioDB.papel.in_(VALID_ROLES),
            EmpresaDB.status == "ATIVA",
        )
        .all()
    )

    return [empresa_id for (empresa_id,) in rows]