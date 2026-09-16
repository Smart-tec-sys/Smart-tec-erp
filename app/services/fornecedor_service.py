from sqlalchemy.orm import Session

from app.models.fornecedor import FornecedorDB
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant


def get_all(db: Session, tenant: TenantContext):
    try:
        return db.query(FornecedorDB).filter(
            FornecedorDB.empresa_id == require_tenant(tenant)
        ).order_by(FornecedorDB.id.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar fornecedores no service: {e}")
        return []


def get_by_id(db: Session, fornecedor_id: int, tenant: TenantContext):
    try:
        return db.query(FornecedorDB).filter(
            FornecedorDB.id == fornecedor_id,
            FornecedorDB.empresa_id == require_tenant(tenant),
        ).first()
    except Exception as e:
        print(f"Erro ao buscar fornecedor por ID no service: {e}")
        return None


def create(db: Session, data: FornecedorCreate, tenant: TenantContext):
    try:
        dados_fornecedor = data.dict()
        novo_fornecedor = FornecedorDB(**dados_fornecedor, empresa_id=require_tenant(tenant))

        db.add(novo_fornecedor)
        db.commit()
        db.refresh(novo_fornecedor)
        return novo_fornecedor

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em fornecedor_service.create: {e}")
        raise e


def update(db: Session, fornecedor_id: int, data: FornecedorUpdate, tenant: TenantContext):
    try:
        fornecedor = get_by_id(db, fornecedor_id, tenant)

        if not fornecedor:
            return None

        dados_fornecedor = data.dict()
        dados_fornecedor.pop("empresa_id", None)

        for campo, valor in dados_fornecedor.items():
            setattr(fornecedor, campo, valor)

        db.commit()
        db.refresh(fornecedor)
        return fornecedor

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em fornecedor_service.update: {e}")
        raise e


def delete(db: Session, fornecedor_id: int, tenant: TenantContext):
    try:
        fornecedor = get_by_id(db, fornecedor_id, tenant)

        if fornecedor:
            db.delete(fornecedor)
            db.commit()
            return fornecedor

        return None

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar fornecedor: {e}")
        return None
