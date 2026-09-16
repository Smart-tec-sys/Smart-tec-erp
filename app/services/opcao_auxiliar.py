from sqlalchemy.orm import Session

from app.models.opcao_auxiliar import OpcaoAuxiliarDB
from app.schemas.opcao_auxiliar import OpcaoAuxiliarCreate
from app.tenant.context import TenantContext
from app.tenant.isolation import apply_tenant_filter, require_tenant


def get_all(db: Session, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        query = apply_tenant_filter(db.query(OpcaoAuxiliarDB), OpcaoAuxiliarDB, empresa_id)
        return (
            query
            .order_by(OpcaoAuxiliarDB.categoria.asc(), OpcaoAuxiliarDB.ordem.asc(), OpcaoAuxiliarDB.nome.asc())
            .all()
        )
    except Exception as e:
        print(f"Erro ao buscar opções auxiliares no service: {e}")
        return []


def get_by_categoria(db: Session, categoria: str, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        return (
            db.query(OpcaoAuxiliarDB)
            .filter(
                OpcaoAuxiliarDB.categoria == categoria,
                OpcaoAuxiliarDB.empresa_id == empresa_id,
            )
            .order_by(OpcaoAuxiliarDB.ordem.asc(), OpcaoAuxiliarDB.nome.asc())
            .all()
        )
    except Exception as e:
        print(f"Erro ao buscar opções auxiliares por categoria: {e}")
        return []


def get_by_id(db: Session, opcao_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        return (
            db.query(OpcaoAuxiliarDB)
            .filter(
                OpcaoAuxiliarDB.id == opcao_id,
                OpcaoAuxiliarDB.empresa_id == empresa_id,
            )
            .first()
        )
    except Exception as e:
        print(f"Erro ao buscar opção auxiliar por ID: {e}")
        return None


def create(db: Session, data: OpcaoAuxiliarCreate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        dados_opcao = data.dict()
        dados_opcao.pop("empresa_id", None)
        nova_opcao = OpcaoAuxiliarDB(**dados_opcao, empresa_id=empresa_id)

        db.add(nova_opcao)
        db.commit()
        db.refresh(nova_opcao)

        return nova_opcao

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em opcao_auxiliar.create: {e}")
        raise e


def update(db: Session, opcao_id: int, data: OpcaoAuxiliarCreate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        opcao = (
            db.query(OpcaoAuxiliarDB)
            .filter(
                OpcaoAuxiliarDB.id == opcao_id,
                OpcaoAuxiliarDB.empresa_id == empresa_id,
            )
            .first()
        )

        if not opcao:
            return None

        dados_opcao = data.dict(exclude_unset=True)
        dados_opcao.pop("empresa_id", None)

        for campo, valor in dados_opcao.items():
            setattr(opcao, campo, valor)

        db.commit()
        db.refresh(opcao)

        return opcao

    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar opção auxiliar: {e}")
        raise e


def delete(db: Session, opcao_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        opcao = (
            db.query(OpcaoAuxiliarDB)
            .filter(
                OpcaoAuxiliarDB.id == opcao_id,
                OpcaoAuxiliarDB.empresa_id == empresa_id,
            )
            .first()
        )

        if not opcao:
            return False

        db.delete(opcao)
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar opção auxiliar: {e}")
        return False
