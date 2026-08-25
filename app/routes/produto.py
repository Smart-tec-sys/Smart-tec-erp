from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.produto import ProdutoCreate
from app.services.produto_service import get_all, get_by_id, create, update, delete

router = APIRouter()


@router.get("/")
def listar(skip: int=0, limit: int=100, db: Session=Depends(get_db)):
    try:
        return get_all(db, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produtos no banco: {str(e)}"
        )


@router.get("/{produto_id}")
def buscar_por_id(produto_id: int, db: Session=Depends(get_db)):
    try:
        produto = get_by_id(db, produto_id)

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
def criar(data: ProdutoCreate, db: Session=Depends(get_db)):
    try:
        return create(db, data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar produto no banco: {str(e)}"
        )


@router.put("/{produto_id}")
def atualizar(produto_id: int, data: ProdutoCreate, db: Session=Depends(get_db)):
    try:
        produto = update(db, produto_id, data)

        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return produto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar produto: {str(e)}"
        )


@router.delete("/{produto_id}")
def deletar(produto_id: int, db: Session=Depends(get_db)):
    try:
        sucesso = delete(db, produto_id)

        if not sucesso:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return {"mensagem": "Produto removido com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar produto: {str(e)}"
        )
