from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.pedido import ConverterOrcamentoInput, GerarContaReceberInput, PedidoUpdate, PedidoCreate
from app.services import pedido_service
from app.tenant.dependencies import (
    TenantContext,
    get_current_tenant,
)


router = APIRouter()


@router.get("/")
def listar(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return pedido_service.listar(db, tenant)


@router.get("/{pedido_id}")
def obter(
    pedido_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    pedido = pedido_service.obter(
        db,
        pedido_id,
        tenant,
    )

    if pedido is None:
        raise HTTPException(
            status_code=404,
            detail="Venda/pedido não encontrado.",
        )

    return pedido


@router.post("/converter-orcamento/{orcamento_id}")
def converter_orcamento(
    orcamento_id: int,
    data: ConverterOrcamentoInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return pedido_service.converter_orcamento(
            db=db,
            orcamento_id=orcamento_id,
            tenant=tenant,
            prazo_entrega=data.prazo_entrega,
            canal_venda=data.canal_venda,
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise

@router.post("/{pedido_id}/conta-receber")
def gerar_conta_receber(
    pedido_id: int,
    data: GerarContaReceberInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return pedido_service.gerar_conta_receber(
            db=db,
            pedido_id=pedido_id,
            tenant=tenant,
            vencimento=data.vencimento,
            categoria=data.categoria,
            observacao=data.observacao,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise

@router.patch("/{pedido_id}")
def atualizar(pedido_id: int, data: "PedidoUpdate", db: Session = Depends(get_db),
              tenant: TenantContext = Depends(get_current_tenant)):
    try:
        result = pedido_service.atualizar(db, pedido_id, tenant, data)
        if result is None:
            raise HTTPException(status_code=404, detail="Venda/pedido não encontrado.")
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.delete("/{pedido_id}", status_code=204)
def remover(pedido_id: int, db: Session = Depends(get_db),
            tenant: TenantContext = Depends(get_current_tenant)):
    from sqlalchemy.exc import IntegrityError
    try:
        if not pedido_service.remover(db, pedido_id, tenant):
            raise HTTPException(status_code=404, detail="Venda/pedido não encontrado.")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Venda não pode ser excluída porque possui vínculo operacional.") from exc
    except Exception:
        db.rollback()
        raise


@router.post("/", status_code=201)
def criar(data: PedidoCreate, db: Session = Depends(get_db),
          tenant: TenantContext = Depends(get_current_tenant)):
    try:
        return pedido_service.criar(db, data, tenant)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
