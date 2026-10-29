from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import financeiro_titulos as s
from app.services import financeiro_titulos_service as service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

router = APIRouter()


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, service.TituloNaoEncontrado):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, service.TituloInvalido):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


_ERROS = (service.TituloNaoEncontrado, service.TituloInvalido, service.TituloConflito)


@router.get("/titulos", response_model=List[s.TituloOut])
def listar_titulos(
    tipo: Optional[str] = Query(None, regex="^[RPrp]$"),
    status: Optional[str] = None,
    vencimento_inicial: Optional[date] = None,
    vencimento_final: Optional[date] = None,
    cliente_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    categoria: Optional[str] = None,
    conta_financeira_id: Optional[int] = None,
    plano_conta_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    situacao_financeira_id: Optional[int] = None,
    forma_pagamento_id: Optional[int] = None,
    pedido_id: Optional[int] = None,
    vencimento_status: Optional[str] = Query(None, regex="^(VENCIDO|HOJE|A_VENCER)$"),
    q: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return service.listar(
        db, tenant, tipo=tipo, status=status,
        vencimento_inicial=vencimento_inicial, vencimento_final=vencimento_final,
        cliente_id=cliente_id, fornecedor_id=fornecedor_id, categoria=categoria,
        conta_financeira_id=conta_financeira_id, plano_conta_id=plano_conta_id,
        centro_custo_id=centro_custo_id, situacao_financeira_id=situacao_financeira_id,
        forma_pagamento_id=forma_pagamento_id, pedido_id=pedido_id,
        vencimento_status=vencimento_status,
        q=q, limit=limit, offset=offset,
    )


@router.get("/titulos/indicadores", response_model=s.IndicadoresOut)
def indicadores_titulos(
    tipo: Optional[str] = Query(None, regex="^[RPrp]$"),
    vencimento_inicial: Optional[date] = None,
    vencimento_final: Optional[date] = None,
    cliente_id: Optional[int] = None,
    fornecedor_id: Optional[int] = None,
    categoria: Optional[str] = None,
    conta_financeira_id: Optional[int] = None,
    forma_pagamento_id: Optional[int] = None,
    plano_conta_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    situacao_financeira_id: Optional[int] = None,
    pedido_id: Optional[int] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return service.indicadores(
        db, tenant, tipo=tipo,
        vencimento_inicial=vencimento_inicial, vencimento_final=vencimento_final,
        cliente_id=cliente_id, fornecedor_id=fornecedor_id, categoria=categoria,
        conta_financeira_id=conta_financeira_id, forma_pagamento_id=forma_pagamento_id,
        plano_conta_id=plano_conta_id, centro_custo_id=centro_custo_id,
        situacao_financeira_id=situacao_financeira_id, pedido_id=pedido_id, q=q,
    )

@router.get("/titulos/{titulo_id}", response_model=s.TituloOut)
def obter_titulo(
    titulo_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return service.obter(db, titulo_id, tenant)
    except _ERROS as exc:
        raise _http(exc)


@router.post("/titulos", response_model=s.TituloOut, status_code=201)
def criar_titulo(
    data: s.TituloCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return service.criar(db, tenant, data.dict())
    except _ERROS as exc:
        db.rollback()
        raise _http(exc)


@router.patch("/titulos/{titulo_id}", response_model=s.TituloOut)
def atualizar_titulo(
    titulo_id: int,
    data: s.TituloUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return service.atualizar(db, titulo_id, tenant, data.dict(exclude_unset=True))
    except _ERROS as exc:
        db.rollback()
        raise _http(exc)


@router.delete("/titulos/{titulo_id}", status_code=204)
def remover_titulo(
    titulo_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        service.remover(db, titulo_id, tenant)
    except _ERROS as exc:
        db.rollback()
        raise _http(exc)
    return Response(status_code=204)

@router.get("/titulos/{titulo_id}/baixas", response_model=List[s.BaixaOut])
def listar_baixas(
    titulo_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return service.listar_baixas(db, titulo_id, tenant)
    except _ERROS as exc:
        raise _http(exc)


@router.post("/titulos/{titulo_id}/baixar", response_model=s.BaixaResultado, status_code=201)
def baixar_titulo(
    titulo_id: int,
    data: s.BaixaCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return service.baixar(db, titulo_id, tenant, data.dict())
    except _ERROS as exc:
        db.rollback()
        raise _http(exc)


@router.post("/baixas/{baixa_id}/estornar", response_model=s.BaixaResultado)
def estornar_baixa(
    baixa_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return service.estornar(db, baixa_id, tenant)
    except _ERROS as exc:
        db.rollback()
        raise _http(exc)