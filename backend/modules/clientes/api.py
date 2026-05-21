# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.modules.clientes import crud
from backend.modules.clientes.schemas import ClienteCreate, ClienteUpdate, ClienteOut

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("/contagem")
def total_clientes(db: Session=Depends(get_db)):
    total = db.query(__import__(
        'backend.modules.clientes.models', fromlist=['Cliente']
    ).Cliente).count()
    return {"total": total}


@router.get("/", response_model=List[ClienteOut])
def listar(db: Session=Depends(get_db)):
    return crud.get_all(db)


@router.get("/{cliente_id}", response_model=ClienteOut)
def buscar(cliente_id: int, db: Session=Depends(get_db)):
    cliente = crud.get_by_id(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return cliente


@router.post("/", response_model=ClienteOut)
def criar(data: ClienteCreate, db: Session=Depends(get_db)):
    return crud.create(db, data)


@router.put("/{cliente_id}", response_model=ClienteOut)
def atualizar(cliente_id: int, data: ClienteUpdate, db: Session=Depends(get_db)):
    cliente = crud.update(db, cliente_id, data)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return cliente


@router.delete("/{cliente_id}")
def deletar(cliente_id: int, db: Session=Depends(get_db)):
    cliente = crud.delete(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return {"mensagem": "Cliente deletado"}
