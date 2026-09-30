from sqlalchemy.orm import Session

from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB


VALID_ROLES = {"OWNER", "ADMIN", "USUARIO"}


def link_user_to_company(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
    papel: str,
) -> EmpresaUsuarioDB:
    """
    Cria vínculo entre usuário existente e empresa existente.

    Não cria usuário.
    Não cria empresa.
    Não escolhe tenant automaticamente.
    """

    role = (papel or "").strip().upper()

    if role not in VALID_ROLES:
        raise ValueError("papel inválido")

    usuario = (
        db.query(UsuarioDB)
        .filter(UsuarioDB.id == usuario_id)
        .one_or_none()
    )

    if usuario is None:
        raise ValueError("usuário não encontrado")

    if usuario.status != "ATIVO":
        raise ValueError("usuário inativo")

    empresa = (
        db.query(EmpresaDB)
        .filter(EmpresaDB.id == empresa_id)
        .one_or_none()
    )

    if empresa is None:
        raise ValueError("empresa não encontrada")

    if empresa.status != "ATIVA":
        raise ValueError("empresa inativa")

    existente = (
        db.query(EmpresaUsuarioDB)
        .filter(
            EmpresaUsuarioDB.usuario_id == usuario_id,
            EmpresaUsuarioDB.empresa_id == empresa_id,
        )
        .one_or_none()
    )

    if existente is not None:
        raise ValueError("usuário já possui vínculo com esta empresa")

    vinculo = EmpresaUsuarioDB(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        papel=role,
        ativo=True,
    )

    db.add(vinculo)

    return vinculo


def deactivate_user_company_link(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
) -> EmpresaUsuarioDB:
    vinculo = (
        db.query(EmpresaUsuarioDB)
        .filter(
            EmpresaUsuarioDB.usuario_id == usuario_id,
            EmpresaUsuarioDB.empresa_id == empresa_id,
        )
        .one_or_none()
    )

    if vinculo is None:
        raise ValueError("vínculo não encontrado")

    vinculo.ativo = False

    return vinculo


def get_user_company_links(
    db: Session,
    *,
    usuario_id: int,
) -> list[EmpresaUsuarioDB]:
    return (
        db.query(EmpresaUsuarioDB)
        .filter(EmpresaUsuarioDB.usuario_id == usuario_id)
        .order_by(EmpresaUsuarioDB.empresa_id)
        .all()
    )