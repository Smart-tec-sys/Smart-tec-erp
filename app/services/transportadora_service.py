from sqlalchemy.orm import Session

from app.models.transportadora import TransportadoraDB
from app.schemas.transportadora import TransportadoraCreate, TransportadoraUpdate


def get_all(db: Session):
    try:
        return db.query(TransportadoraDB).order_by(TransportadoraDB.id.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar transportadoras no service: {e}")
        return []


def get_by_id(db: Session, transportadora_id: int):
    try:
        return db.query(TransportadoraDB).filter(TransportadoraDB.id == transportadora_id).first()
    except Exception as e:
        print(f"Erro ao buscar transportadora por ID no service: {e}")
        return None


def create(db: Session, data: TransportadoraCreate):
    try:
        dados_transportadora = data.dict()
        nova_transportadora = TransportadoraDB(**dados_transportadora)

        db.add(nova_transportadora)
        db.commit()
        db.refresh(nova_transportadora)

        return nova_transportadora

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em transportadora_service.create: {e}")
        raise e


def update(db: Session, transportadora_id: int, data: TransportadoraUpdate):
    try:
        transportadora = db.query(TransportadoraDB).filter(TransportadoraDB.id == transportadora_id).first()

        if not transportadora:
            return None

        dados_transportadora = data.dict()

        for campo, valor in dados_transportadora.items():
            setattr(transportadora, campo, valor)

        db.commit()
        db.refresh(transportadora)

        return transportadora

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em transportadora_service.update: {e}")
        raise e


def delete(db: Session, transportadora_id: int):
    try:
        transportadora = db.query(TransportadoraDB).filter(TransportadoraDB.id == transportadora_id).first()

        if transportadora:
            db.delete(transportadora)
            db.commit()
            return transportadora

        return None

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar transportadora: {e}")
        return None
