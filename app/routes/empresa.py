from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.empresa import EmpresaDB
from app.tenant.dependencies import get_current_tenant
from app.tenant.context import TenantContext


router = APIRouter()


@router.post("/logo")
async def upload_empresa_logo(
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    empresa = (
        db.query(EmpresaDB)
        .filter(
            EmpresaDB.id == tenant.empresa_id,
            EmpresaDB.status == "ATIVA",
        )
        .one_or_none()
    )

    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="empresa não encontrada",
        )

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    extension = allowed_types.get(file.content_type or "")

    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="formato de imagem não permitido",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="arquivo vazio",
        )

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="imagem deve ter no máximo 5 MB",
        )

    media_dir = Path("media") / "empresas"
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f"empresa-{empresa.id}-{uuid.uuid4().hex}{extension}"
    destination = media_dir / filename

    destination.write_bytes(content)

    old_logo = empresa.logo_url

    empresa.logo_url = f"/media/empresas/{filename}"

    db.commit()
    db.refresh(empresa)

    if old_logo and old_logo.startswith("/media/empresas/"):
        old_path = Path(old_logo.lstrip("/"))

        if old_path.exists() and old_path != destination:
            try:
                old_path.unlink()
            except OSError:
                pass

    return {
        "logo_url": empresa.logo_url
    }


@router.delete("/logo")
def delete_empresa_logo(
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    empresa = (
        db.query(EmpresaDB)
        .filter(
            EmpresaDB.id == tenant.empresa_id,
            EmpresaDB.status == "ATIVA",
        )
        .one_or_none()
    )

    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="empresa não encontrada",
        )

    old_logo = empresa.logo_url

    empresa.logo_url = None

    db.commit()
    db.refresh(empresa)

    if old_logo and old_logo.startswith("/media/empresas/"):
        old_path = Path(old_logo.lstrip("/"))

        if old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass

    return {
        "logo_url": None
    }