from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.auth.seat_limits import DecisaoVaga, verificar_vaga
from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB


VALID_ROLES = {"OWNER", "ADMIN", "USUARIO"}

ResolvedorLimite = Callable[[Session, int], Optional[int]]


class VagaIndisponivelError(ValueError):
    def __init__(self, decisao: DecisaoVaga):
        super().__init__(f"sem vaga disponível: {decisao.situacao.value}")
        self.decisao = decisao


def _exigir_vaga(
    db: Session,
    empresa_id: int,
    resolver_limite: ResolvedorLimite,
) -> None:
    decisao = verificar_vaga(
        db,
        empresa_id,
        resolver_limite=resolver_limite,
    )

    if not decisao.permite_expansao:
        raise VagaIndisponivelError(decisao)


def link_user_to_company(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
    papel: str,
    resolver_limite: Optional[ResolvedorLimite] = None,
) -> EmpresaUsuarioDB:
    """
    Cria vínculo entre usuário existente e empresa existente.

    Não cria usuário.
    Não cria empresa.
    Não escolhe tenant automaticamente.

    Sem resolver_limite (padrão), nenhuma verificação de vagas é feita.
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

    if resolver_limite is not None:
        _exigir_vaga(db, empresa_id, resolver_limite)

    vinculo = EmpresaUsuarioDB(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        papel=role,
        ativo=True,
    )

    db.add(vinculo)

    return vinculo


def reactivate_user_company_link(
    db: Session,
    *,
    usuario_id: int,
    empresa_id: int,
    resolver_limite: Optional[ResolvedorLimite] = None,
) -> EmpresaUsuarioDB:
    """
    Reativa vínculo inativo. Não conectada a rotas.

    Vínculo já ativo é devolvido sem consumir nova vaga.
    Sem resolver_limite (padrão), nenhuma verificação de vagas é feita.
    """

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

    if vinculo.ativo:
        return vinculo

    usuario = (
        db.query(UsuarioDB)
        .filter(UsuarioDB.id == usuario_id)
        .one_or_none()
    )

    if usuario is None or usuario.status != "ATIVO":
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

    if resolver_limite is not None:
        _exigir_vaga(db, empresa_id, resolver_limite)

    vinculo.ativo = True

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