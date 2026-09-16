from sqlalchemy.orm import Session

from app.models.transportadora import TransportadoraDB
from app.schemas.transportadora import TransportadoraCreate, TransportadoraUpdate
from app.tenant.context import TenantContext
from app.tenant.isolation import apply_tenant_filter, require_tenant


def get_all(db: Session, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        query = apply_tenant_filter(db.query(TransportadoraDB), TransportadoraDB, empresa_id)
        return query.order_by(TransportadoraDB.id.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar transportadoras no service: {e}")
        return []


def get_by_id(db: Session, transportadora_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        return db.query(TransportadoraDB).filter(
            TransportadoraDB.id == transportadora_id,
            TransportadoraDB.empresa_id == empresa_id,
        ).first()
    except Exception as e:
        print(f"Erro ao buscar transportadora por ID no service: {e}")
        return None


def create(db: Session, data: TransportadoraCreate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        dados_transportadora = data.dict()
        dados_transportadora.pop("empresa_id", None)
        nova_transportadora = TransportadoraDB(**dados_transportadora, empresa_id=empresa_id)

        db.add(nova_transportadora)
        db.commit()
        db.refresh(nova_transportadora)

        return nova_transportadora

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em transportadora_service.create: {e}")
        raise e


def update(db: Session, transportadora_id: int, data: TransportadoraUpdate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        transportadora = db.query(TransportadoraDB).filter(
            TransportadoraDB.id == transportadora_id,
            TransportadoraDB.empresa_id == empresa_id,
        ).first()

        if not transportadora:
            return None

        dados_transportadora = data.dict()
        dados_transportadora.pop("empresa_id", None)

        for campo, valor in dados_transportadora.items():
            setattr(transportadora, campo, valor)

        db.commit()
        db.refresh(transportadora)

        return transportadora

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em transportadora_service.update: {e}")
        raise e


def delete(db: Session, transportadora_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        transportadora = db.query(TransportadoraDB).filter(
            TransportadoraDB.id == transportadora_id,
            TransportadoraDB.empresa_id == empresa_id,
        ).first()

        if transportadora:
            db.delete(transportadora)
            db.commit()
            return transportadora

        return None

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar transportadora: {e}")
        return None
