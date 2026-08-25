from sqlalchemy.orm import Session

from app.models.cliente import ClienteDB
from app.schemas.cliente import ClienteCreate, ClienteUpdate


def get_all(db: Session):
    """Busca todos os clientes cadastrados no banco de dados."""
    try:
        return db.query(ClienteDB).order_by(ClienteDB.id.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar clientes no service: {e}")
        return []


def get_by_id(db: Session, cliente_id: int):
    """Busca um cliente específico pelo ID."""
    try:
        return db.query(ClienteDB).filter(ClienteDB.id == cliente_id).first()
    except Exception as e:
        print(f"Erro ao buscar cliente por ID no service: {e}")
        return None


def create(db: Session, data: ClienteCreate):
    """Cria um novo cliente."""
    try:
        dados_cliente = data.dict()
        novo_cliente = ClienteDB(**dados_cliente)

        db.add(novo_cliente)
        db.commit()
        db.refresh(novo_cliente)

        return novo_cliente

    except Exception as e:
        db.rollback()
        print(f"Erro crítico dentro de cliente_service.create: {e}")
        raise e


def update(db: Session, cliente_id: int, data: ClienteUpdate):
    """Atualiza um cliente existente."""
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == cliente_id).first()

        if not cliente:
            return None

        dados_cliente = data.dict()

        for campo, valor in dados_cliente.items():
            setattr(cliente, campo, valor)

        db.commit()
        db.refresh(cliente)

        return cliente

    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar cliente no service: {e}")
        raise e


def delete(db: Session, cliente_id: int):
    """Remove um cliente pelo ID."""
    try:
        cliente = db.query(ClienteDB).filter(ClienteDB.id == cliente_id).first()

        if cliente:
            db.delete(cliente)
            db.commit()
            return cliente

        return None

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar cliente no service: {e}")
        return None
