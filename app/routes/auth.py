from pathlib import Path
import uuid
"""Endpoints autenticados sem login improvisado ou escolha livre de tenant."""

from fastapi import UploadFile, File, APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.auth.service import ExternalIdentity
from app.auth.dependencies import get_verified_external_identity
from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB
from app.database import get_db


router = APIRouter()
VALID_ROLES = {"OWNER", "ADMIN", "USUARIO"}
class AuthMeUpdate(BaseModel):
    nome: str




@router.post("/me/photo")
async def upload_auth_me_photo(
    file: UploadFile = File(...),
    identity: ExternalIdentity = Depends(get_verified_external_identity),
    db: Session = Depends(get_db),
):
    usuario = db.query(UsuarioDB).filter(
        UsuarioDB.provedor == identity.provider,
        UsuarioDB.provedor_subject == identity.subject,
        UsuarioDB.status == "ATIVO",
    ).one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="usuário sem acesso",
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

    media_dir = Path("media") / "usuarios"
    media_dir.mkdir(parents=True, exist_ok=True)

    filename = f"user-{usuario.id}-{uuid.uuid4().hex}{extension}"
    destination = media_dir / filename

    destination.write_bytes(content)

    old_photo = usuario.foto_url

    usuario.foto_url = f"/media/usuarios/{filename}"

    db.commit()
    db.refresh(usuario)

    if old_photo and old_photo.startswith("/media/usuarios/"):
        old_path = Path(old_photo.lstrip("/"))

        if old_path.exists() and old_path != destination:
            try:
                old_path.unlink()
            except OSError:
                pass

    return {
        "foto_url": usuario.foto_url
    }
@router.delete("/me/photo")
def delete_auth_me_photo(
    identity: ExternalIdentity = Depends(get_verified_external_identity),
    db: Session = Depends(get_db),
):
    usuario = db.query(UsuarioDB).filter(
        UsuarioDB.provedor == identity.provider,
        UsuarioDB.provedor_subject == identity.subject,
        UsuarioDB.status == "ATIVO",
    ).one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usu?rio n?o encontrado.",
        )

    old_photo = usuario.foto_url

    usuario.foto_url = None
    db.commit()
    db.refresh(usuario)

    if old_photo and old_photo.startswith("/media/usuarios/"):
        old_path = Path(old_photo.lstrip("/"))

        if old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass

    return {"foto_url": None}


@router.patch("/me")
def update_auth_me(
    payload: AuthMeUpdate,
    identity: ExternalIdentity = Depends(get_verified_external_identity),
    db: Session = Depends(get_db),
):
    usuario = db.query(UsuarioDB).filter(
        UsuarioDB.provedor == identity.provider,
        UsuarioDB.provedor_subject == identity.subject,
        UsuarioDB.status == "ATIVO",
    ).one_or_none()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="usuário sem acesso",
        )

    nome = payload.nome.strip()

    if len(nome) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="nome inválido",
        )

    if len(nome) > 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="nome muito longo",
        )

    usuario.nome = nome

    db.commit()
    db.refresh(usuario)

    return {
        "user": {
            "id": usuario.id,
            "email": usuario.email,
            "nome": usuario.nome,
        }
    }

@router.get("/me")
def auth_me(
    identity: ExternalIdentity = Depends(get_verified_external_identity),
    db: Session = Depends(get_db),
):
    usuario = db.query(UsuarioDB).filter(
        UsuarioDB.provedor == identity.provider,
        UsuarioDB.provedor_subject == identity.subject,
        UsuarioDB.status == "ATIVO",
    ).one_or_none()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="usuário sem acesso")

    if identity.email:
        normalized_identity_email = identity.email.strip().lower()
        normalized_user_email = (usuario.email or "").strip().lower()

        if normalized_identity_email != normalized_user_email:
            usuario.email = normalized_identity_email
            db.commit()
            db.refresh(usuario)

    vinculos = db.query(EmpresaUsuarioDB).filter(
        EmpresaUsuarioDB.usuario_id == usuario.id,
        EmpresaUsuarioDB.ativo.is_(True),
        EmpresaUsuarioDB.papel.in_(VALID_ROLES),
    ).all()

    empresas = []
    for vinculo in vinculos:
        empresa = db.query(EmpresaDB).filter(
            EmpresaDB.id == vinculo.empresa_id,
            EmpresaDB.status == "ATIVA",
        ).one_or_none()
        if empresa is not None:
            empresas.append({
                "id": empresa.id,
                "nome": empresa.nome,
                "nome_fantasia": empresa.nome_fantasia,
                "logo_url": empresa.logo_url,
                "slug": empresa.slug,
                "papel": vinculo.papel,
            })

    if not empresas:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="usuário sem vínculo empresarial ativo")

    return {
        "user": {"id": usuario.id, "email": usuario.email, "nome": usuario.nome, "foto_url": usuario.foto_url},
        "empresas": empresas,
    }
