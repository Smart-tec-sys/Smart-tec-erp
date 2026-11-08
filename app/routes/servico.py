from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.servico import ServicoInput
from app.services import servico_service
from app.tenant.dependencies import TenantContext, get_current_tenant

router = APIRouter()


@router.get("/")
def listar(
    busca: str | None = Query(default=None, max_length=120),
    incluir_inativos: bool = True,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return servico_service.listar(db, tenant, busca, incluir_inativos)
    except Exception:
        db.rollback()
        raise


@router.get("/{servico_id}")
def obter(
    servico_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        item = servico_service.obter(db, servico_id, tenant)
    except Exception:
        db.rollback()
        raise
    if item is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado para a empresa ativa.")
    return item


@router.post("/", status_code=201)
def criar(
    data: ServicoInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return servico_service.criar(db, tenant, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/{servico_id}")
def atualizar(
    servico_id: int,
    data: ServicoInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        item = servico_service.atualizar(db, servico_id, tenant, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado para a empresa ativa.")
    return item
