from sqlalchemy.orm import Session

from app.models.opcao_auxiliar import OpcaoAuxiliarDB
from app.schemas.opcao_auxiliar import OpcaoAuxiliarCreate


def get_all(db: Session):
    try:
        return (
            db.query(OpcaoAuxiliarDB)
            .order_by(OpcaoAuxiliarDB.categoria.asc(), OpcaoAuxiliarDB.ordem.asc(), OpcaoAuxiliarDB.nome.asc())
            .all()
        )
    except Exception as e:
        print(f"Erro ao buscar opções auxiliares no service: {e}")
        return []


def get_by_categoria(db: Session, categoria: str):
    try:
        return (
            db.query(OpcaoAuxiliarDB)
            .filter(OpcaoAuxiliarDB.categoria == categoria)
            .order_by(OpcaoAuxiliarDB.ordem.asc(), OpcaoAuxiliarDB.nome.asc())
            .all()
        )
    except Exception as e:
        print(f"Erro ao buscar opções auxiliares por categoria: {e}")
        return []


def get_by_id(db: Session, opcao_id: int):
    try:
        return (
            db.query(OpcaoAuxiliarDB)
            .filter(OpcaoAuxiliarDB.id == opcao_id)
            .first()
        )
    except Exception as e:
        print(f"Erro ao buscar opção auxiliar por ID: {e}")
        return None


def create(db: Session, data: OpcaoAuxiliarCreate):
    try:
        dados_opcao = data.dict()
        nova_opcao = OpcaoAuxiliarDB(**dados_opcao)

        db.add(nova_opcao)
        db.commit()
        db.refresh(nova_opcao)

        return nova_opcao

    except Exception as e:
        db.rollback()
        print(f"Erro crítico em opcao_auxiliar.create: {e}")
        raise e


def update(db: Session, opcao_id: int, data: OpcaoAuxiliarCreate):
    try:
        opcao = (
            db.query(OpcaoAuxiliarDB)
            .filter(OpcaoAuxiliarDB.id == opcao_id)
            .first()
        )

        if not opcao:
            return None

        dados_opcao = data.dict(exclude_unset=True)

        for campo, valor in dados_opcao.items():
            setattr(opcao, campo, valor)

        db.commit()
        db.refresh(opcao)

        return opcao

    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar opção auxiliar: {e}")
        raise e


def delete(db: Session, opcao_id: int):
    try:
        opcao = (
            db.query(OpcaoAuxiliarDB)
            .filter(OpcaoAuxiliarDB.id == opcao_id)
            .first()
        )

        if not opcao:
            return False

        db.delete(opcao)
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar opção auxiliar: {e}")
        return False
