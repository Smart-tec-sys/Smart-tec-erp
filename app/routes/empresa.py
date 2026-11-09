from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.database import get_db
from app.media_storage import ImagemInvalida, MediaStorageError, remover_imagem, trocar_imagem
from app.models.empresa import EmpresaDB
from app.schemas.empresa_perfil import EmpresaPerfilUpdate, PerfilPublicoEmpresa
from app.tenant.dependencies import get_current_tenant
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant


router = APIRouter()


def _empresa_ativa(db: Session, tenant: TenantContext):
    empresa = db.query(EmpresaDB).filter(
        EmpresaDB.id == require_tenant(tenant), EmpresaDB.status == "ATIVA",
    ).one_or_none()
    if empresa is None:
        raise HTTPException(status_code=404, detail="empresa ativa não encontrada")
    return empresa


def _dados_publicos(empresa: EmpresaDB):
    # Não expor o JSON completo: ele também pode conter configurações internas.
    configuracoes = empresa.configuracoes if isinstance(empresa.configuracoes, dict) else {}
    fonte = configuracoes.get("perfil_publico", {})
    fonte = fonte if isinstance(fonte, dict) else {}
    perfil = {}
    for campo in PerfilPublicoEmpresa.model_fields:
        valor = fonte.get(campo)
        try:
            validado = PerfilPublicoEmpresa.model_validate({campo: valor})
        except ValidationError:
            continue
        if getattr(validado, campo):
            perfil[campo] = getattr(validado, campo)
    return {
        "id": empresa.id, "nome": empresa.nome, "nome_fantasia": empresa.nome_fantasia,
        "documento": empresa.documento, "logo_url": empresa.logo_url,
        "perfil_publico": perfil,
    }


@router.get("/atual")
def obter_empresa_atual(
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return _dados_publicos(_empresa_ativa(db, tenant))


@router.put("/atual")
def atualizar_empresa_atual(
    dados: EmpresaPerfilUpdate,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    empresa = _empresa_ativa(db, tenant)
    empresa.nome = dados.nome
    empresa.nome_fantasia = dados.nome_fantasia
    empresa.documento = dados.documento
    configuracoes = dict(empresa.configuracoes) if isinstance(empresa.configuracoes, dict) else {}
    configuracoes["perfil_publico"] = dados.perfil_publico.model_dump(exclude_none=True)
    empresa.configuracoes = configuracoes
    try:
        db.commit()
        db.refresh(empresa)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="não foi possível salvar os dados da empresa") from exc
    return _dados_publicos(empresa)


@router.post("/logo")
async def upload_empresa_logo(
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    empresa = _empresa_ativa(db, tenant)
    conteudo = await file.read()
    try:
        logo_url = await run_in_threadpool(
            trocar_imagem, db, empresa, "logo_url",
            conteudo=conteudo, content_type=file.content_type,
            pasta="empresas", dono_id=empresa.id, prefixo_legado="empresa", nome="logo",
        )
    except ImagemInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    except MediaStorageError:
        raise HTTPException(status_code=503, detail="armazenamento de imagens indisponível") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="não foi possível salvar a logo") from None
    return {"logo_url": logo_url}


@router.delete("/logo")
def delete_empresa_logo(
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    empresa = _empresa_ativa(db, tenant)
    try:
        remover_imagem(db, empresa, "logo_url", pasta="empresas", dono_id=empresa.id, prefixo_legado="empresa")
    except MediaStorageError:
        raise HTTPException(status_code=503, detail="armazenamento de imagens indisponível") from None
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="não foi possível remover a logo") from None
    return {"logo_url": None}
