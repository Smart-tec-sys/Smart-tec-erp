# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session
from backend.modules.clientes.models import Cliente
from backend.modules.clientes.schemas import ClienteCreate, ClienteUpdate


def get_all(db: Session):
    return db.query(Cliente).all()


def get_by_id(db: Session, cliente_id: int):
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


def create(db: Session, data: ClienteCreate):
    cliente = Cliente(**data.dict())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def update(db: Session, cliente_id: int, data: ClienteUpdate):
    cliente = get_by_id(db, cliente_id)
    if not cliente:
        return None
    for key, value in data.dict().items():
        setattr(cliente, key, value)
    db.commit()
    db.refresh(cliente)
    return cliente


def delete(db: Session, cliente_id: int):
    cliente = get_by_id(db, cliente_id)
    if not cliente:
        return None
    db.delete(cliente)
    db.commit()
    return cliente
