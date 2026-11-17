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
    """Status administrativo da importação, sem retornar arquivo ou senha."""
    from app.services.fiscal_importacao_a1_empresa import status_importacao_empresa
    return status_importacao_empresa(db, tenant)


@router.post("/certificado-a1/importar")
async def importar_certificado_a1_empresa(
    request: Request, db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    from app.services.fiscal_importacao_a1_empresa import (
        MAX_CORPO, exigir_importacao_disponivel, importar_certificado_empresa,
    )

    exigir_importacao_disponivel(tenant)
    await run_in_threadpool(fiscal_cadastros.exigir_admin, db, tenant)
    tipo = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if tipo != "application/json":
        raise HTTPException(415, "Use o formulário de importação do certificado.")

    corpo = bytearray()
    try:
        async for parte in request.stream():
            if len(corpo) + len(parte) > MAX_CORPO:
                raise HTTPException(413, "Arquivo de certificado acima do limite.")
            corpo.extend(parte)
        return await run_in_threadpool(importar_certificado_empresa, db, tenant, corpo)
    finally:
        corpo.clear()


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


@router.post("/certificado-a1/laboratorio/testar-assinatura")
def testar_assinatura_certificado_lab(db: Session = Depends(get_db),
                                     tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_importacao_a1_lab import verificar_envelope_lab
    return verificar_envelope_lab(db, tenant, testar_assinatura=True)


@router.post("/nfe/laboratorio/conferir-venda")
def conferir_venda_ficticia(db: Session = Depends(get_db),
                            tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_importacao_a1_lab import conferir_xml_venda_lab
    return conferir_xml_venda_lab(db, tenant)


@router.post("/nfe/laboratorio/assinar-venda")
def assinar_venda_ficticia(db: Session = Depends(get_db),
                          tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_importacao_a1_lab import conferir_xml_venda_lab
    return conferir_xml_venda_lab(db, tenant, assinar=True)


@router.post("/nfe/homologacao/sp/status-servico")
def status_servico_sefaz_sp(db: Session = Depends(get_db),
                            tenant: TenantContext = Depends(get_current_tenant)):
    from app.services.fiscal_sefaz_status_sp import consultar_status_sefaz_sp
    return consultar_status_sefaz_sp(db, tenant)
