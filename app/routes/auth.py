"""Endpoints autenticados sem login improvisado ou escolha livre de tenant."""

from fastapi import UploadFile, File, APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth.service import ExternalIdentity
from app.auth.dependencies import get_verified_external_identity
from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB
from app.database import get_db
from app.media_storage import ImagemInvalida, MediaStorageError, remover_imagem, trocar_imagem


router = APIRouter()
VALID_ROLES = {"OWNER", "ADMIN", "USUARIO"}
class AuthMeUpdate(BaseModel):
    nome: str




def _usuario_ativo(db: Session, identity: ExternalIdentity, status_ausente: int):
    usuario = db.query(UsuarioDB).filter(
        UsuarioDB.provedor == identity.provider,
        UsuarioDB.provedor_subject == identity.subject,
        UsuarioDB.status == "ATIVO",
    ).one_or_none()
    if usuario is None:
        detalhe = "usuário sem acesso" if status_ausente == status.HTTP_403_FORBIDDEN else "Usuário não encontrado."
        raise HTTPException(status_code=status_ausente, detail=detalhe)
    return usuario


@router.post("/me/photo")
async def upload_auth_me_photo(
    file: UploadFile = File(...),
    identity: ExternalIdentity = Depends(get_verified_external_identity),
    db: Session = Depends(get_db),
):
    usuario = _usuario_ativo(db, identity, status.HTTP_403_FORBIDDEN)
    conteudo = await file.read()
    try:
        foto_url = await run_in_threadpool(
            trocar_imagem, db, usuario, "foto_url",
            conteudo=conteudo, content_type=file.content_type,
            pasta="usuarios", dono_id=usuario.id, prefixo_legado="user", nome="avatar",
        )
    except ImagemInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except MediaStorageError:
        raise HTTPException(status_code=503, detail="armazenamento de imagens indisponível") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="não foi possível salvar a foto") from None
    return {"foto_url": foto_url}


@router.delete("/me/photo")
def delete_auth_me_photo(
    identity: ExternalIdentity = Depends(get_verified_external_identity),
    db: Session = Depends(get_db),
):
    usuario = _usuario_ativo(db, identity, status.HTTP_404_NOT_FOUND)
    try:
        remover_imagem(db, usuario, "foto_url", pasta="usuarios", dono_id=usuario.id, prefixo_legado="user")
    except MediaStorageError:
        raise HTTPException(status_code=503, detail="armazenamento de imagens indisponível") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="não foi possível remover a foto") from None
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
