from sqlalchemy.orm import Session
from app.models.produto import ProdutoDB
from app.schemas.produto import ProdutoCreate


def get_all(db: Session, skip: int=0, limit: int=100):
    return (
        db.query(ProdutoDB)
        .order_by(ProdutoDB.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_by_id(db: Session, produto_id: int):
    return db.query(ProdutoDB).filter(ProdutoDB.id == produto_id).first()


def create(db: Session, data: ProdutoCreate):
    try:
        dados = data.dict()
        novo_produto = ProdutoDB(**dados)

        # Calcula custo final básico
        novo_produto.custo_final = (
            float(novo_produto.valor_custo or 0)
            +float(novo_produto.despesas_acessorias or 0)
            +float(novo_produto.outras_despesas or 0)
        )

        db.add(novo_produto)
        db.commit()
        db.refresh(novo_produto)
        return novo_produto

    except Exception as e:
        db.rollback()
        print(f"Erro ao criar produto: {e}")
        raise e


def update(db: Session, produto_id: int, data: ProdutoCreate):
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == produto_id).first()

        if not produto:
            return None

        dados = data.dict(exclude_unset=True)

        for key, value in dados.items():
            setattr(produto, key, value)

        produto.custo_final = (
            float(produto.valor_custo or 0)
            +float(produto.despesas_acessorias or 0)
            +float(produto.outras_despesas or 0)
        )

        db.commit()
        db.refresh(produto)
        return produto

    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar produto: {e}")
        raise e


def delete(db: Session, produto_id: int):
    try:
        produto = db.query(ProdutoDB).filter(ProdutoDB.id == produto_id).first()

        if produto:
            db.delete(produto)
            db.commit()
            return True

        return False

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar produto: {e}")
        return False
