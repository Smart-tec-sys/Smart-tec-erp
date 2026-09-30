from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.auth.service import ExternalIdentity
from app.models.plataforma import (
    PlataformaEquipeDB,
    PlataformaEquipePermissaoDB,
    PlataformaFuncaoDB,
    PlataformaFuncaoPermissaoDB,
    PlataformaPermissaoDB,
)
from app.models.usuario import UsuarioDB


@dataclass(frozen=True)
class PlatformMemberContext:
    equipe_id: int
    usuario_id: int
    nome: str
    email: str

    funcao_id: int
    funcao_codigo: str
    funcao_nome: str
    nivel: int

    cargo_exibicao: str | None

    permissions: frozenset[str]

    @property
    def is_platform_owner(self) -> bool:
        return self.funcao_codigo == "OWNER_PLATAFORMA"

    @property
    def is_platform_administrator(self) -> bool:
        return self.funcao_codigo in {
            "OWNER_PLATAFORMA",
            "ADMIN_PLATAFORMA",
        }

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


def resolve_platform_member(
    db: Session,
    *,
    identity: ExternalIdentity,
) -> PlatformMemberContext:

    if not isinstance(identity, ExternalIdentity):
        raise TypeError("identidade externa inválida")

    usuario = (
        db.query(UsuarioDB)
        .filter(
            UsuarioDB.provedor == identity.provider,
            UsuarioDB.provedor_subject == identity.subject,
            UsuarioDB.status == "ATIVO",
        )
        .one_or_none()
    )

    if usuario is None:
        raise PermissionError("usuário autenticado não encontrado")

    equipe = (
        db.query(PlataformaEquipeDB)
        .filter(
            PlataformaEquipeDB.usuario_id == usuario.id,
            PlataformaEquipeDB.status == "ATIVO",
        )
        .one_or_none()
    )

    if equipe is None:
        raise PermissionError("usuário não pertence à Equipe Smart-tec")

    funcao = (
        db.query(PlataformaFuncaoDB)
        .filter(
            PlataformaFuncaoDB.id == equipe.funcao_id,
            PlataformaFuncaoDB.ativo.is_(True),
        )
        .one_or_none()
    )

    if funcao is None:
        raise PermissionError("função administrativa inválida")

    regras = (
        db.query(
            PlataformaPermissaoDB.codigo,
            PlataformaFuncaoPermissaoDB.permitido,
        )
        .join(
            PlataformaFuncaoPermissaoDB,
            PlataformaFuncaoPermissaoDB.permissao_id
            == PlataformaPermissaoDB.id,
        )
        .filter(
            PlataformaFuncaoPermissaoDB.funcao_id == funcao.id,
        )
        .all()
    )

    effective = {
        codigo: bool(permitido)
        for codigo, permitido in regras
    }

    overrides = (
        db.query(
            PlataformaPermissaoDB.codigo,
            PlataformaEquipePermissaoDB.permitido,
        )
        .join(
            PlataformaEquipePermissaoDB,
            PlataformaEquipePermissaoDB.permissao_id
            == PlataformaPermissaoDB.id,
        )
        .filter(
            PlataformaEquipePermissaoDB.equipe_id == equipe.id,
        )
        .all()
    )

    for codigo, permitido in overrides:
        effective[codigo] = bool(permitido)

    permissions = frozenset(
        codigo
        for codigo, permitido in effective.items()
        if permitido
    )

    return PlatformMemberContext(
        equipe_id=equipe.id,
        usuario_id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        funcao_id=funcao.id,
        funcao_codigo=funcao.codigo,
        funcao_nome=funcao.nome,
        nivel=funcao.nivel,
        cargo_exibicao=equipe.cargo_exibicao,
        permissions=permissions,
    )