from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class ProdutoHistoricoAlteracaoDB(Base):
    __tablename__ = "produtos_historico_alteracoes"
    __table_args__ = (
        Index(
            "ix_produtos_historico_empresa_produto_data",
            "empresa_id", "produto_id", "criado_em", "id",
        ),
        ForeignKeyConstraint(
            ["produto_id", "empresa_id"],
            ["produtos.id", "produtos.empresa_id"],
            name="fk_produto_historico_produto_empresa",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["empresa_id", "usuario_id"],
            ["empresa_usuarios.empresa_id", "empresa_usuarios.usuario_id"],
            name="fk_produto_historico_empresa_usuario",
            ondelete="RESTRICT",
        ),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    produto_id = Column(Integer, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    alteracoes = Column(JSONB, nullable=False)
