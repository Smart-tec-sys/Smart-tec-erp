from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.transportadora import Transportadora, TransportadoraCreate, TransportadoraUpdate
from app.services.transportadora_service import get_all, get_by_id, create, update, delete

router = APIRouter()


@router.get("/", response_model=List[Transportadora])
def listar(db: Session=Depends(get_db)):
    try:
        transportadoras = get_all(db)
        if transportadoras is None:
            return []
        return transportadoras

    except Exception as e:
        print(f"Erro na rota listar transportadoras: {e}")
        return []


@router.get("/{transportadora_id}", response_model=Transportadora)
def buscar_por_id(transportadora_id: int, db: Session=Depends(get_db)):
    transportadora = get_by_id(db, transportadora_id)

    if not transportadora:
        raise HTTPException(status_code=404, detail="Transportadora não encontrada")

    return transportadora


@router.post("/", response_model=Transportadora)
def criar(data: TransportadoraCreate, db: Session=Depends(get_db)):
    try:
        return create(db, data)

    except Exception as e:
        print(f"Erro na rota criar transportadora: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar transportadora no banco.")


@router.put("/{transportadora_id}", response_model=Transportadora)
def atualizar(transportadora_id: int, data: TransportadoraUpdate, db: Session=Depends(get_db)):
    try:
        transportadora = update(db, transportadora_id, data)

        if not transportadora:
            raise HTTPException(status_code=404, detail="Transportadora não encontrada")

        return transportadora

    except HTTPException:
        raise

    except Exception as e:
        print(f"Erro na rota atualizar transportadora: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar transportadora no banco.")


@router.delete("/{transportadora_id}")
def deletar(transportadora_id: int, db: Session=Depends(get_db)):
    transportadora = delete(db, transportadora_id)

    if not transportadora:
        raise HTTPException(status_code=404, detail="Transportadora não encontrada")

    return {"mensagem": "Transportadora removida com sucesso"}
