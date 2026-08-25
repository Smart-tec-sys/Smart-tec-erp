from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.fornecedor import Fornecedor, FornecedorCreate, FornecedorUpdate
from app.services.fornecedor_service import get_all, get_by_id, create, update, delete

router = APIRouter()


@router.get("/", response_model=List[Fornecedor])
def listar(db: Session=Depends(get_db)):
    try:
        fornecedores = get_all(db)
        if fornecedores is None:
            return []
        return fornecedores

    except Exception as e:
        print(f"Erro na rota listar fornecedores: {e}")
        return []


@router.get("/{fornecedor_id}", response_model=Fornecedor)
def buscar_por_id(fornecedor_id: int, db: Session=Depends(get_db)):
    fornecedor = get_by_id(db, fornecedor_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    return fornecedor


@router.post("/", response_model=Fornecedor)
def criar(data: FornecedorCreate, db: Session=Depends(get_db)):
    try:
        return create(db, data)

    except Exception as e:
        print(f"Erro na rota criar fornecedor: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar fornecedor no banco.")


@router.put("/{fornecedor_id}", response_model=Fornecedor)
def atualizar(fornecedor_id: int, data: FornecedorUpdate, db: Session=Depends(get_db)):
    try:
        fornecedor = update(db, fornecedor_id, data)

        if not fornecedor:
            raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

        return fornecedor

    except HTTPException:
        raise

    except Exception as e:
        print(f"Erro na rota atualizar fornecedor: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar fornecedor no banco.")


@router.delete("/{fornecedor_id}")
def deletar(fornecedor_id: int, db: Session=Depends(get_db)):
    fornecedor = delete(db, fornecedor_id)

    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    return {"mensagem": "Fornecedor deletado"}
