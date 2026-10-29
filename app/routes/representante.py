from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.representante import (
    ParceiroCreate,
    RepresentanteCreate,
    RTCreate,
    RTPagamentoInput,
    ParceiroRepresentanteCreate,
    ParceiroClienteCreate,
)
from app.services import representante_service
from app.tenant.dependencies import (
    TenantContext,
    get_current_tenant,
)


router = APIRouter()


@router.get("/parceiros")
def listar_parceiros(
    ativos: bool = Query(False),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return representante_service.listar_parceiros(
        db,
        tenant,
        ativos,
    )


@router.post("/parceiros")
def criar_parceiro(
    data: ParceiroCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.criar_parceiro(
            db,
            tenant,
            data,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/")
def listar_representantes(
    ativos: bool = Query(False),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return representante_service.listar_representantes(
        db,
        tenant,
        ativos,
    )


@router.post("/")
def criar_representante(
    data: RepresentanteCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.criar_representante(
            db,
            tenant,
            data,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/rt")
def listar_rt(
    competencia: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.listar_rt(
            db,
            tenant,
            competencia,
            status,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/rt")
def criar_rt(
    data: RTCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.criar_rt(
            db,
            tenant,
            data,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/rt/{rt_id}/gerar-conta-pagar")
def gerar_conta_pagar(
    rt_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.gerar_conta_pagar(
            db,
            tenant,
            rt_id,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/rt/{rt_id}/marcar-pago")
def marcar_pago(
    rt_id: int,
    data: RTPagamentoInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.marcar_pago(
            db,
            tenant,
            rt_id,
            data.pagamento,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

# ============================================================
# CARTEIRA DO PARCEIRO
# ============================================================

@router.get(
    "/parceiros/{parceiro_id}/carteira/representantes"
)
def listar_carteira_representantes(
    parceiro_id: int,
    termo: str | None = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.listar_representantes_parceiro(
            db,
            tenant,
            parceiro_id,
            termo,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/parceiros/{parceiro_id}/carteira/representantes"
)
def criar_carteira_representante(
    parceiro_id: int,
    data: ParceiroRepresentanteCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.criar_representante_parceiro(
            db,
            tenant,
            parceiro_id,
            data,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/parceiros/{parceiro_id}/carteira/clientes"
)
def listar_carteira_clientes(
    parceiro_id: int,
    termo: str | None = Query(None),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.listar_clientes_parceiro(
            db,
            tenant,
            parceiro_id,
            termo,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/parceiros/{parceiro_id}/carteira/clientes"
)
def criar_carteira_cliente(
    parceiro_id: int,
    data: ParceiroClienteCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return representante_service.criar_cliente_parceiro(
            db,
            tenant,
            parceiro_id,
            data,
        )
    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc