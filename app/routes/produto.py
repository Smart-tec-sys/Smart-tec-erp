import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.produto import ProdutoCreate, ProdutoUpdate
from app.services.produto_service import (
    create,
    delete,
    get_all,
    get_by_id,
    get_history,
    get_technical_classifications,
    update,
)
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/classificacoes-tecnicas")
def listar_classificacoes_tecnicas(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return get_technical_classifications(db, tenant)
    except Exception as e:
        logger.exception("Falha ao consultar classificações técnicas")
        raise HTTPException(
            status_code=500,
            detail="Erro ao consultar classificações técnicas.",
        ) from e


@router.get("/")
def listar(skip: int=0, limit: int=100, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        return get_all(db, tenant, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produtos no banco: {str(e)}"
        )


@router.get("/{produto_id}")
def buscar_por_id(produto_id: int, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        produto = get_by_id(db, produto_id, tenant)

        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return produto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produto: {str(e)}"
        )


@router.post("/")
def criar(data: ProdutoCreate, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        return create(db, data, tenant)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar produto no banco: {str(e)}"
        )


@router.put("/{produto_id}")
def atualizar(produto_id: int, data: ProdutoUpdate, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        produto = update(db, produto_id, data, tenant)

        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return produto

    except PermissionError as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Falha ao atualizar produto %s", produto_id)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao atualizar produto; nenhuma alteração foi confirmada."
        ) from e


@router.get("/{produto_id}/historico")
def historico(produto_id: int, db: Session = Depends(get_db),
              tenant: TenantContext = Depends(get_current_tenant)):
    try:
        registros = get_history(db, produto_id, tenant)
        if registros is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        return [{
            "id": item.id,
            "produto_id": item.produto_id,
            "usuario_id": item.usuario_id,
            "criado_em": item.criado_em,
            "alteracoes": item.alteracoes,
        } for item in registros]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Falha ao consultar histórico do produto %s", produto_id)
        raise HTTPException(status_code=500, detail="Erro ao consultar histórico do produto.") from e


@router.delete("/{produto_id}")
def deletar(produto_id: int, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        sucesso = delete(db, produto_id, tenant)

        if not sucesso:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return {"mensagem": "Produto removido com sucesso"}

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar produto: {str(e)}"
        )
