from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class OrdemProducaoDB(Base):
    __tablename__ = "ordens_producao"
    __table_args__ = (
        UniqueConstraint("empresa_id", "pedido_id", name="uq_op_empresa_pedido"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="RESTRICT"), nullable=False)
    confirmado_por = Column(String(100), nullable=False)
    confirmado_em = Column(DateTime(timezone=True), nullable=False)
    liberado_por = Column(String(100))
    liberado_em = Column(DateTime(timezone=True))
    snapshot = Column(JSON, nullable=False)
    pecas = relationship("PecaProducaoDB", cascade="all, delete-orphan", order_by="PecaProducaoDB.id")


class PecaProducaoDB(Base):
    __tablename__ = "producao_pecas"
    __table_args__ = (
        Index("ix_producao_pecas_ordem", "ordem_id"),
        UniqueConstraint("pedido_item_id", "sequencia", name="uq_producao_item_peca"),
        CheckConstraint("sequencia > 0", name="ck_producao_sequencia"),
        CheckConstraint("largura >= 0 AND altura >= 0", name="ck_producao_medidas"),
        CheckConstraint("status IN ('AGUARDANDO','CORTE','MONTAGEM','CONFERENCIA','CONCLUIDA')", name="ck_producao_status"),
    )

    id = Column(Integer, primary_key=True)
    ordem_id = Column(Integer, ForeignKey("ordens_producao.id", ondelete="RESTRICT"), nullable=False)
    pedido_item_id = Column(Integer, ForeignKey("pedidos_itens.id", ondelete="RESTRICT"), nullable=False)
    sequencia = Column(Integer, nullable=False)
    modelo = Column(String(100))
    tecido = Column(Text)
    cor = Column(String(100))
    largura = Column(Numeric(12, 3), nullable=False)
    altura = Column(Numeric(12, 3), nullable=False)
    acionamento = Column(String(100))
    ambiente = Column(String(200), nullable=False, default="")
    observacoes = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="AGUARDANDO")
    historico = Column(JSON, nullable=False, default=list)
