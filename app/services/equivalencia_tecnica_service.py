from sqlalchemy.orm import Session

from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.fornecedor import FornecedorDB
from app.models.produto import ProdutoDB
from app.schemas.equivalencia_tecnica import EquivalenciaTecnicaCreate, EquivalenciaTecnicaUpdate
from app.technical.catalog import TECHNICAL_CATALOG
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant


def is_valid_technical_function(code: str) -> bool:
    return str(code or "").strip().upper() in TECHNICAL_CATALOG


def _technical_code(code: str) -> str:
    normalized = str(code or "").strip().upper()
    if not is_valid_technical_function(normalized):
        raise ValueError("função técnica inexistente")
    return normalized


def _owned_product(db: Session, empresa_id: int, produto_id: int):
    product = db.query(ProdutoDB).filter(
        ProdutoDB.id == produto_id, ProdutoDB.empresa_id == empresa_id
    ).first()
    if product is None:
        raise PermissionError("produto não pertence à empresa atual")
    return product


def _owned_supplier(db: Session, empresa_id: int, fornecedor_id: int | None):
    if fornecedor_id is None:
        return None
    supplier = db.query(FornecedorDB).filter(
        FornecedorDB.id == fornecedor_id, FornecedorDB.empresa_id == empresa_id
    ).first()
    if supplier is None:
        raise PermissionError("fornecedor não pertence à empresa atual")
    return supplier


def _demote_preferred(db: Session, empresa_id: int, technical_code: str, except_id: int | None = None):
    query = db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.empresa_id == empresa_id,
        EmpresaEquivalenciaTecnicaDB.funcao_tecnica == technical_code,
    )
    for row in query.all():
        if row.preferencial and row.ativo and (except_id is None or row.id != except_id):
            row.preferencial = False


def list_all(db: Session, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    return db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.empresa_id == empresa_id
    ).order_by(
        EmpresaEquivalenciaTecnicaDB.funcao_tecnica,
        EmpresaEquivalenciaTecnicaDB.prioridade,
        EmpresaEquivalenciaTecnicaDB.id,
    ).all()


def list_by_function(db: Session, tenant: TenantContext, technical_function: str):
    empresa_id = require_tenant(tenant)
    code = _technical_code(technical_function)
    return db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.empresa_id == empresa_id,
        EmpresaEquivalenciaTecnicaDB.funcao_tecnica == code,
    ).order_by(EmpresaEquivalenciaTecnicaDB.prioridade, EmpresaEquivalenciaTecnicaDB.id).all()


def get_by_id(db: Session, tenant: TenantContext, equivalence_id: int):
    empresa_id = require_tenant(tenant)
    return db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.id == equivalence_id,
        EmpresaEquivalenciaTecnicaDB.empresa_id == empresa_id,
    ).first()


def create(db: Session, tenant: TenantContext, data: EquivalenciaTecnicaCreate):
    empresa_id = require_tenant(tenant)
    code = _technical_code(data.funcao_tecnica)
    _owned_product(db, empresa_id, data.produto_id)
    _owned_supplier(db, empresa_id, data.fornecedor_id)
    if data.prioridade < 0:
        raise ValueError("prioridade deve ser não negativa")
    if data.preferencial and data.ativo:
        _demote_preferred(db, empresa_id, code)
    values = data.dict()
    values.pop("empresa_id", None)
    values["funcao_tecnica"] = code
    row = EmpresaEquivalenciaTecnicaDB(**values, empresa_id=empresa_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, tenant: TenantContext, equivalence_id: int, data: EquivalenciaTecnicaUpdate):
    empresa_id = require_tenant(tenant)
    row = get_by_id(db, tenant, equivalence_id)
    if row is None:
        return None
    values = data.dict(exclude_unset=True)
    values.pop("empresa_id", None)
    code = _technical_code(values.get("funcao_tecnica", row.funcao_tecnica))
    product_id = values.get("produto_id", row.produto_id)
    supplier_id = values.get("fornecedor_id", row.fornecedor_id)
    _owned_product(db, empresa_id, product_id)
    _owned_supplier(db, empresa_id, supplier_id)
    priority = values.get("prioridade", row.prioridade)
    if priority < 0:
        raise ValueError("prioridade deve ser não negativa")
    values["funcao_tecnica"] = code
    preferred = values.get("preferencial", row.preferencial)
    active = values.get("ativo", row.ativo)
    if preferred and active:
        _demote_preferred(db, empresa_id, code, except_id=row.id)
    for field, value in values.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def resolve_commercial_candidates(db: Session, tenant: TenantContext, technical_function: str):
    rows = [
        row for row in list_by_function(db, tenant, technical_function)
        if row.ativo
    ]
    result = []
    for row in sorted(rows, key=lambda item: (not item.ativo, not item.preferencial, item.prioridade, item.id)):
        product = _owned_product(db, row.empresa_id, row.produto_id)
        supplier = _owned_supplier(db, row.empresa_id, row.fornecedor_id)
        result.append({
            "technical_function": row.funcao_tecnica,
            "produto_id": product.id,
            "produto_nome": product.nome,
            "fornecedor_id": supplier.id if supplier else None,
            "fornecedor_nome": supplier.nome if supplier else None,
            "preferencial": row.preferencial,
            "prioridade": row.prioridade,
            "ativo": row.ativo,
        })
    return result
