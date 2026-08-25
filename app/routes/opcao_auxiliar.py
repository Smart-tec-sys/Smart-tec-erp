from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.opcao_auxiliar import OpcaoAuxiliar, OpcaoAuxiliarCreate
from app.services.opcao_auxiliar import (
    get_all,
    get_by_categoria,
    create,
    update,
    delete,
)

router = APIRouter()


@router.get("/")
def listar(db: Session=Depends(get_db)):
    try:
        return get_all(db)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar opções auxiliares: {str(e)}"
        )


@router.get("/categoria/{categoria}")
def listar_por_categoria(categoria: str, db: Session=Depends(get_db)):
    try:
        return get_by_categoria(db, categoria)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar opções por categoria: {str(e)}"
        )


@router.post("/")
def criar(data: OpcaoAuxiliarCreate, db: Session=Depends(get_db)):
    try:
        nova_opcao = create(db, data)
        return nova_opcao
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar opção auxiliar: {str(e)}"
        )


@router.put("/{opcao_id}")
def atualizar(opcao_id: int, data: OpcaoAuxiliarCreate, db: Session=Depends(get_db)):
    opcao = update(db, opcao_id, data)

    if not opcao:
        raise HTTPException(status_code=404, detail="Opção auxiliar não encontrada")

    return opcao


@router.delete("/{opcao_id}")
def deletar(opcao_id: int, db: Session=Depends(get_db)):
    sucesso = delete(db, opcao_id)

    if not sucesso:
        raise HTTPException(status_code=404, detail="Opção auxiliar não encontrada")

    return {"mensagem": "Opção auxiliar removida com sucesso"}
