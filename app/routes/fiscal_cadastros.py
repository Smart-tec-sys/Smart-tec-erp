"""Cadastro fiscal para NF-e V1: sem emissão ou transmissão."""
from fastapi import APIRouter, Depends, Path
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
