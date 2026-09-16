from sqlalchemy.orm import Session
from app.models.produto import ProdutoDB
from app.schemas.produto import ProdutoCreate
from app.tenant.context import TenantContext
from app.tenant.isolation import require_tenant


def get_all(db: Session, tenant: TenantContext, skip: int=0, limit: int=100):
    empresa_id = require_tenant(tenant)
    return (
        db.query(ProdutoDB)
        .filter(ProdutoDB.empresa_id == empresa_id)
        .order_by(ProdutoDB.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_by_id(db: Session, produto_id: int, tenant: TenantContext):
    empresa_id = require_tenant(tenant)
    return db.query(ProdutoDB).filter(
        ProdutoDB.id == produto_id, ProdutoDB.empresa_id == empresa_id
    ).first()


def create(db: Session, data: ProdutoCreate, tenant: TenantContext):
    try:
        dados = data.dict()
        novo_produto = ProdutoDB(**dados, empresa_id=require_tenant(tenant))

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


def update(db: Session, produto_id: int, data: ProdutoCreate, tenant: TenantContext):
    try:
        produto = get_by_id(db, produto_id, tenant)

        if not produto:
            return None

        dados = data.dict(exclude_unset=True)
        dados.pop("empresa_id", None)

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


def delete(db: Session, produto_id: int, tenant: TenantContext):
    try:
        produto = get_by_id(db, produto_id, tenant)

        if produto:
            db.delete(produto)
            db.commit()
            return True

        return False

    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar produto: {e}")
        return False
