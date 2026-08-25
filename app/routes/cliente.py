from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.cliente import Cliente, ClienteCreate, ClienteUpdate
from app.services import cliente_service

router = APIRouter()


@router.get("/", response_model=List[Cliente])
def listar(db: Session=Depends(get_db)):
    try:
        clientes = cliente_service.get_all(db)
        return clientes or []

    except Exception as e:
        print(f"Erro na rota listar clientes: {e}")
        return []


@router.get("/{cliente_id}", response_model=Cliente)
def buscar_por_id(cliente_id: int, db: Session=Depends(get_db)):
    cliente = cliente_service.get_by_id(db, cliente_id)

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    return cliente


@router.post("/", response_model=Cliente)
def criar(data: ClienteCreate, db: Session=Depends(get_db)):
    try:
        return cliente_service.create(db, data)

    except Exception as e:
        print(f"Erro na rota criar cliente: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar cliente no banco.")


@router.put("/{cliente_id}", response_model=Cliente)
def atualizar(cliente_id: int, data: ClienteUpdate, db: Session=Depends(get_db)):
    try:
        cliente = cliente_service.update(db, cliente_id, data)

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

        return cliente

    except HTTPException:
        raise

    except Exception as e:
        print(f"Erro na rota atualizar cliente: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar cliente no banco.")


@router.delete("/{cliente_id}")
def deletar(cliente_id: int, db: Session=Depends(get_db)):
    cliente = cliente_service.delete(db, cliente_id)

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    return {"mensagem": "Cliente deletado com sucesso."}
