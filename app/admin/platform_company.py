import os
from fastapi import HTTPException
from sqlalchemy import text


def get_platform_empresa_id(db):
    raw_id = os.getenv("SMARTTEC_PLATFORM_EMPRESA_ID", "").strip()
    slug = os.getenv("SMARTTEC_PLATFORM_EMPRESA_SLUG", "").strip() or "smart-tec-persianas"
    try:
        if raw_id:
            empresa_id = int(raw_id)
            if empresa_id <= 0:
                raise ValueError()
            condition, params = "id = :id", {"id": empresa_id}
        else:
            condition, params = "slug = :slug", {"slug": slug}
        empresa = db.execute(text(f"SELECT id, status FROM empresas WHERE {condition}"), params).mappings().first()
    except ValueError as exc:
        raise HTTPException(503, "Empresa da plataforma configurada com ID inválido.") from exc
    if not empresa or str(empresa["status"]).upper() != "ATIVA":
        raise HTTPException(503, "Empresa da plataforma inexistente ou inativa. Verifique a configuração administrativa.")
    return empresa["id"]
