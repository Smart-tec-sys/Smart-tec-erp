"""Configuração fiscal de produto, sempre limitada a empresa_id + produto_id."""
from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, func
from app.database import Base


class FiscalProdutoDB(Base):
    __tablename__ = "fiscal_produtos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["produto_id", "empresa_id"],
            ["produtos.id", "produtos.empresa_id"],
            name="fk_fiscal_produto_tenant",
            ondelete="CASCADE",
        ),
    )

    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"),
                        primary_key=True, nullable=False)
    produto_id = Column(Integer, primary_key=True, nullable=False)
    ncm = Column(String(8), nullable=True)
    cfop_padrao_saida = Column(String(4), nullable=True)
    cest = Column(String(7), nullable=True)
    origem_mercadoria = Column(String(1), nullable=True)
    cst_icms = Column(String(2), nullable=True)
    csosn = Column(String(3), nullable=True)
    cst_pis = Column(String(2), nullable=True)
    cst_cofins = Column(String(2), nullable=True)
    cst_ibs_cbs = Column(String(3), nullable=True)
    cclass_trib_ibs_cbs = Column(String(6), nullable=True)
    atualizado_em = Column(DateTime(timezone=True), nullable=False,
                           server_default=func.now(), onupdate=func.now())
