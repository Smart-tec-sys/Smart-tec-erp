import unicodedata

from sqlalchemy.orm import Session

from app.models.fornecedor import FornecedorDB
from app.models.fornecedor_alias import FornecedorAliasDB
from app.schemas.fornecedor_alias import FornecedorAliasCreate, FornecedorAliasUpdate
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant


VALID_ALIAS_TYPES = frozenset({
    "NOME_HISTORICO", "NOME_IMPORTACAO", "VARIANTE_GRAFIA", "NOME_COMERCIAL", "OUTRO"
})
VALID_CONFIDENCE_LEVELS = frozenset({"FORTE", "PROVAVEL", "AMBIGUA"})
VALID_REVIEW_STATUSES = frozenset({"PENDENTE", "APROVADO", "REJEITADO"})


def normalize_supplier_alias(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.casefold().split())


def _validate_choice(value: str, allowed: frozenset[str], message: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in allowed:
        raise ValueError(message)
    return normalized


def _owned_supplier(db: Session, empresa_id: int, fornecedor_id: int):
    supplier = db.query(FornecedorDB).filter(
        FornecedorDB.id == fornecedor_id,
        FornecedorDB.empresa_id == empresa_id,
    ).first()
    if supplier is None:
        raise PermissionError("fornecedor não pertence à empresa atual")
    return supplier


def _ensure_unambiguous(
    db: Session, empresa_id: int, normalized_alias: str, fornecedor_id: int, except_id: int | None = None
) -> None:
    rows = db.query(FornecedorAliasDB).filter(
        FornecedorAliasDB.empresa_id == empresa_id,
        FornecedorAliasDB.alias_normalizado == normalized_alias,
    ).all()
    for row in rows:
        if not row.ativo:
            continue
        if except_id is not None and row.id == except_id:
            continue
        if row.fornecedor_id != fornecedor_id:
            raise ValueError("alias ambíguo: já pertence a outro fornecedor da empresa")
        raise ValueError("alias ativo duplicado para o fornecedor")


def list_all(db: Session, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    return db.query(FornecedorAliasDB).filter(
        FornecedorAliasDB.empresa_id == empresa_id
    ).order_by(FornecedorAliasDB.alias_normalizado, FornecedorAliasDB.id).all()


def create(db: Session, tenant: TenantContext, data: FornecedorAliasCreate):
    empresa_id = require_tenant(tenant)
    _owned_supplier(db, empresa_id, data.fornecedor_id)
    alias_normalizado = normalize_supplier_alias(data.alias_original)
    if not alias_normalizado:
        raise ValueError("alias vazio")
    _ensure_unambiguous(db, empresa_id, alias_normalizado, data.fornecedor_id)
    values = data.dict()
    values["tipo"] = _validate_choice(data.tipo, VALID_ALIAS_TYPES, "tipo de alias inválido")
    values["nivel_confianca"] = _validate_choice(
        data.nivel_confianca, VALID_CONFIDENCE_LEVELS, "nível de confiança inválido"
    )
    values["status_revisao"] = _validate_choice(
        data.status_revisao, VALID_REVIEW_STATUSES, "status de revisão inválido"
    )
    row = FornecedorAliasDB(
        **values, empresa_id=empresa_id, alias_normalizado=alias_normalizado
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update(db: Session, tenant: TenantContext, alias_id: int, data: FornecedorAliasUpdate):
    empresa_id = require_tenant(tenant)
    row = db.query(FornecedorAliasDB).filter(
        FornecedorAliasDB.id == alias_id,
        FornecedorAliasDB.empresa_id == empresa_id,
    ).first()
    if row is None:
        return None
    changes = data.dict(exclude_unset=True)
    original = changes.get("alias_original", row.alias_original)
    normalized = normalize_supplier_alias(original)
    active = changes.get("ativo", row.ativo)
    if active:
        _ensure_unambiguous(db, empresa_id, normalized, row.fornecedor_id, except_id=row.id)
    changes["alias_normalizado"] = normalized
    if "tipo" in changes:
        changes["tipo"] = _validate_choice(changes["tipo"], VALID_ALIAS_TYPES, "tipo de alias inválido")
    if "nivel_confianca" in changes:
        changes["nivel_confianca"] = _validate_choice(
            changes["nivel_confianca"], VALID_CONFIDENCE_LEVELS, "nível de confiança inválido"
        )
    if "status_revisao" in changes:
        changes["status_revisao"] = _validate_choice(
            changes["status_revisao"], VALID_REVIEW_STATUSES, "status de revisão inválido"
        )
    for field, value in changes.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


def recognize_supplier_candidates(db: Session, tenant: TenantContext, text: str):
    empresa_id = require_tenant(tenant)
    normalized = normalize_supplier_alias(text)
    if not normalized:
        return []
    rows = db.query(FornecedorAliasDB).filter(
        FornecedorAliasDB.empresa_id == empresa_id,
        FornecedorAliasDB.alias_normalizado == normalized,
    ).order_by(FornecedorAliasDB.id).all()
    rows = [row for row in rows if row.ativo and row.status_revisao == "APROVADO"]
    return [
        {
            "fornecedor_id": row.fornecedor_id,
            "alias_id": row.id,
            "alias_original": row.alias_original,
            "alias_normalizado": row.alias_normalizado,
            "tipo": row.tipo,
            "nivel_confianca": row.nivel_confianca,
            "status_revisao": row.status_revisao,
            "motivo": "correspondência exata de alias normalizado aprovado",
        }
        for row in rows
    ]
