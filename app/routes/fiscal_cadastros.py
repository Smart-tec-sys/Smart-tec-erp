"""Cadastro fiscal para NF-e V1: sem emissão ou transmissão."""
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.fiscal_cadastros import FiscalEmpresaPatch, FiscalProdutoPatch
from app.services import fiscal_cadastros
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

router = APIRouter()

@router.get("/empresa")
def empresa_fiscal(db: Session = Depends(get_db),
                   tenant: TenantContext = Depends(get_current_tenant)):
    return fiscal_cadastros.ler_empresa(db, tenant)

@router.patch("/empresa")
def salvar_empresa_fiscal(dados: FiscalEmpresaPatch, db: Session = Depends(get_db),
                         tenant: TenantContext = Depends(get_current_tenant)):
    return fiscal_cadastros.atualizar_empresa(db, tenant, dados)

@router.get("/produtos/{produto_id}")
def produto_fiscal(produto_id: int = Path(gt=0), db: Session = Depends(get_db),
                   tenant: TenantContext = Depends(get_current_tenant)):
    return fiscal_cadastros.ler_produto(db, tenant, produto_id)

@router.patch("/produtos/{produto_id}")
def salvar_produto_fiscal(dados: FiscalProdutoPatch, produto_id: int = Path(gt=0),
                         db: Session = Depends(get_db),
                         tenant: TenantContext = Depends(get_current_tenant)):
    return fiscal_cadastros.atualizar_produto(db, tenant, produto_id, dados)


@router.get("/certificado-a1/status")
def certificado_a1_status(db: Session = Depends(get_db),
                          tenant: TenantContext = Depends(get_current_tenant)):
    """Status administrativo por empresa, sem PFX/senha, cofre ou emissão."""
    from app.services.fiscal_certificado_a1 import status_a1_empresa
    return status_a1_empresa(db, tenant)


@router.get("/certificado-a1/laboratorio")
def certificado_lab_status(db: Session = Depends(get_db),
                           tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_importacao_a1_lab import status_importacao_lab
    return status_importacao_lab(db, tenant)


@router.post("/certificado-a1/laboratorio")
async def importar_certificado_lab(request: Request, db: Session = Depends(get_db),
                                    tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_importacao_a1_lab import (
        MAX_CORPO_LAB, importacao_lab_disponivel, importar_envelope_lab,
    )
    if not importacao_lab_disponivel(tenant):
        raise HTTPException(404, "Importação de laboratório indisponível.")
    await run_in_threadpool(fiscal_cadastros.exigir_admin, db, tenant)
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise HTTPException(415, "Envie o PFX de laboratório pelo formulário fiscal.")
    corpo = bytearray()
    async for parte in request.stream():
        if len(corpo) + len(parte) > MAX_CORPO_LAB:
            raise HTTPException(413, "Arquivo PFX acima do limite de laboratório.")
        corpo.extend(parte)
    return await run_in_threadpool(importar_envelope_lab, db, tenant, corpo)


@router.post("/certificado-a1/laboratorio/verificar")
def verificar_certificado_lab(db: Session = Depends(get_db),
                              tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_importacao_a1_lab import verificar_envelope_lab
    return verificar_envelope_lab(db, tenant)
