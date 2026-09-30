import json
import unicodedata

from sqlalchemy.orm import Session

from app.models.fornecedor import FornecedorDB
from app.models.funcao_tecnica_referencia import FuncaoTecnicaReferenciaDB
from app.schemas.funcao_tecnica_referencia import (
    FuncaoTecnicaReferenciaCreate,
    FuncaoTecnicaReferenciaUpdate,
)
from app.technical.catalog import TECHNICAL_CATALOG
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant


VALID_CONFIDENCE_LEVELS = frozenset({"FORTE", "PROVAVEL", "AMBIGUA"})
VALID_REVIEW_STATUSES = frozenset({"PENDENTE", "APROVADA", "REJEITADA"})


def normalize_reference_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.casefold().split())


def _technical_code(value: str) -> str:
    code = str(value or "").strip().upper()
    if code not in TECHNICAL_CATALOG:
        raise ValueError("função técnica inexistente")
    return code


def _validate_confidence(value: str) -> str:
    confidence = str(value or "").strip().upper()
    if confidence not in VALID_CONFIDENCE_LEVELS:
        raise ValueError("nível de confiança inválido")
    return confidence


def _validate_status(value: str) -> str:
    status = str(value or "").strip().upper()
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError("status de revisão inválido")
    return status


def _owned_supplier(db: Session, empresa_id: int, fornecedor_id: int | None):
    if fornecedor_id is None:
        return None
    supplier = db.query(FornecedorDB).filter(
        FornecedorDB.id == fornecedor_id,
        FornecedorDB.empresa_id == empresa_id,
    ).first()
    if supplier is None:
        raise PermissionError("fornecedor não pertence à empresa atual")
    return supplier


def _context_key(values: dict) -> tuple:
    attributes = json.dumps(
        values.get("atributos_referencia") or {}, sort_keys=True, separators=(",", ":")
    )
    document = str(values.get("origem_hash") or values.get("origem") or "").strip().casefold()
    return (
        values["empresa_id"],
        values["funcao_tecnica"],
        values.get("fornecedor_id"),
        values["nome_normalizado"],
        str(values.get("codigo_referencia") or "").strip(),
        document,
        attributes,
    )


def _ensure_not_duplicate(db: Session, values: dict, except_id: int | None = None) -> None:
    target = _context_key(values)
    rows = db.query(FuncaoTecnicaReferenciaDB).filter(
        FuncaoTecnicaReferenciaDB.empresa_id == values["empresa_id"],
        FuncaoTecnicaReferenciaDB.funcao_tecnica == values["funcao_tecnica"],
    ).all()
    for row in rows:
        if except_id is not None and row.id == except_id:
            continue
        current = {
            "empresa_id": row.empresa_id,
            "funcao_tecnica": row.funcao_tecnica,
            "fornecedor_id": row.fornecedor_id,
            "nome_normalizado": row.nome_normalizado,
            "codigo_referencia": row.codigo_referencia,
            "origem": row.origem,
            "origem_hash": row.origem_hash,
            "atributos_referencia": row.atributos_referencia,
        }
        if _context_key(current) == target:
            raise ValueError("referência contextual duplicada")


def list_all(db: Session, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    return db.query(FuncaoTecnicaReferenciaDB).filter(
        FuncaoTecnicaReferenciaDB.empresa_id == empresa_id
    ).order_by(
        FuncaoTecnicaReferenciaDB.funcao_tecnica,
        FuncaoTecnicaReferenciaDB.nome_normalizado,
        FuncaoTecnicaReferenciaDB.id,
    ).all()


def get_by_id(db: Session, tenant: TenantContext, reference_id: int):
    empresa_id = require_tenant(tenant)
    return db.query(FuncaoTecnicaReferenciaDB).filter(
        FuncaoTecnicaReferenciaDB.id == reference_id,
        FuncaoTecnicaReferenciaDB.empresa_id == empresa_id,
    ).first()


def create(db: Session, tenant: TenantContext, data: FuncaoTecnicaReferenciaCreate):
    empresa_id = require_tenant(tenant)
    values = data.dict()
    values["empresa_id"] = empresa_id
    values["funcao_tecnica"] = _technical_code(data.funcao_tecnica)
    values["nivel_confianca"] = _validate_confidence(data.nivel_confianca)
    values["status_revisao"] = _validate_status(data.status_revisao)
    values["nome_normalizado"] = normalize_reference_name(data.nome_referencia)
    if not values["nome_normalizado"]:
        raise ValueError("nome de referência vazio")
    _owned_supplier(db, empresa_id, data.fornecedor_id)
    _ensure_not_duplicate(db, values)
    row = FuncaoTecnicaReferenciaDB(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(
    db: Session,
    tenant: TenantContext,
    reference_id: int,
    data: FuncaoTecnicaReferenciaUpdate,
):
    empresa_id = require_tenant(tenant)
    row = get_by_id(db, tenant, reference_id)
    if row is None:
        return None
    changes = data.dict(exclude_unset=True)
    merged = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    merged.update(changes)
    merged["empresa_id"] = empresa_id
    merged["funcao_tecnica"] = _technical_code(merged["funcao_tecnica"])
    merged["nivel_confianca"] = _validate_confidence(merged["nivel_confianca"])
    merged["status_revisao"] = _validate_status(merged["status_revisao"])
    merged["nome_normalizado"] = normalize_reference_name(merged["nome_referencia"])
    _owned_supplier(db, empresa_id, merged.get("fornecedor_id"))
    _ensure_not_duplicate(db, merged, except_id=row.id)
    changes["funcao_tecnica"] = merged["funcao_tecnica"]
    changes["nivel_confianca"] = merged["nivel_confianca"]
    changes["status_revisao"] = merged["status_revisao"]
    changes["nome_normalizado"] = merged["nome_normalizado"]
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
