from sqlalchemy.orm import Session

from app.models.funcionario import FuncionarioDB
from app.schemas.funcionario import FuncionarioCreate, FuncionarioUpdate
from app.tenant.context import TenantContext
from app.tenant.isolation import apply_tenant_filter, require_tenant


def get_all(db: Session, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        query = apply_tenant_filter(db.query(FuncionarioDB), FuncionarioDB, empresa_id)
        return query.order_by(FuncionarioDB.id.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar funcionários no service: {e}")
        return []


def get_by_id(db: Session, funcionario_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        return db.query(FuncionarioDB).filter(
            FuncionarioDB.id == funcionario_id,
            FuncionarioDB.empresa_id == empresa_id,
        ).first()
    except Exception as e:
        print(f"Erro ao buscar funcionário por ID no service: {e}")
        return None


def create(db: Session, data: FuncionarioCreate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        dados_funcionario = data.dict()
        dados_funcionario.pop("empresa_id", None)
        novo_funcionario = FuncionarioDB(**dados_funcionario, empresa_id=empresa_id)

        db.add(novo_funcionario)
        db.commit()
        db.refresh(novo_funcionario)
        return novo_funcionario

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em funcionario_service.create: {e}")
        raise e


def update(db: Session, funcionario_id: int, data: FuncionarioUpdate, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        funcionario = db.query(FuncionarioDB).filter(
            FuncionarioDB.id == funcionario_id,
            FuncionarioDB.empresa_id == empresa_id,
        ).first()

        if not funcionario:
            return None

        dados_funcionario = data.dict()
        dados_funcionario.pop("empresa_id", None)

        for campo, valor in dados_funcionario.items():
            setattr(funcionario, campo, valor)

        db.commit()
        db.refresh(funcionario)
        return funcionario

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em funcionario_service.update: {e}")
        raise e


def delete(db: Session, funcionario_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    try:
        funcionario = db.query(FuncionarioDB).filter(
            FuncionarioDB.id == funcionario_id,
            FuncionarioDB.empresa_id == empresa_id,
        ).first()

        if funcionario:
            db.delete(funcionario)
            db.commit()
            return funcionario

        return None

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar funcionário: {e}")
        return None
