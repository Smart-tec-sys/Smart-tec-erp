from sqlalchemy.orm import Session

from app.models.funcionario import FuncionarioDB
from app.schemas.funcionario import FuncionarioCreate, FuncionarioUpdate


def get_all(db: Session):
    try:
        return db.query(FuncionarioDB).order_by(FuncionarioDB.id.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar funcionários no service: {e}")
        return []


def get_by_id(db: Session, funcionario_id: int):
    try:
        return db.query(FuncionarioDB).filter(FuncionarioDB.id == funcionario_id).first()
    except Exception as e:
        print(f"Erro ao buscar funcionário por ID no service: {e}")
        return None


def create(db: Session, data: FuncionarioCreate):
    try:
        dados_funcionario = data.dict()
        novo_funcionario = FuncionarioDB(**dados_funcionario)

        db.add(novo_funcionario)
        db.commit()
        db.refresh(novo_funcionario)
        return novo_funcionario

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em funcionario_service.create: {e}")
        raise e


def update(db: Session, funcionario_id: int, data: FuncionarioUpdate):
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == funcionario_id).first()

        if not funcionario:
            return None

        dados_funcionario = data.dict()

        for campo, valor in dados_funcionario.items():
            setattr(funcionario, campo, valor)

        db.commit()
        db.refresh(funcionario)
        return funcionario

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em funcionario_service.update: {e}")
        raise e


def delete(db: Session, funcionario_id: int):
    try:
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id == funcionario_id).first()

        if funcionario:
            db.delete(funcionario)
            db.commit()
            return funcionario

        return None

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar funcionário: {e}")
        return None
