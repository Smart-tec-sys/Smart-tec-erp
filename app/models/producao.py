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
        CheckConstraint("quantidade > 0", name="ck_producao_quantidade"),
        CheckConstraint("versao_ficha > 0", name="ck_producao_versao_ficha"),
        CheckConstraint("modo_fabricacao IN ('AUTOMATICA','MANUAL_SUPERVISIONADA')", name="ck_producao_modo_fabricacao"),
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
    quantidade = Column(Numeric(12, 3), nullable=False, default=1)
    acionamento = Column(String(100))
    modo_fabricacao = Column(String(30), nullable=False, default="AUTOMATICA")
    especificacoes_fabricacao = Column(JSON, nullable=False, default=dict)
    versao_ficha = Column(Integer, nullable=False, default=1)
    conferido_por = Column(String(100))
    conferido_em = Column(DateTime(timezone=True))
    ambiente = Column(String(200), nullable=False, default="")
    observacoes = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="AGUARDANDO")
    historico = Column(JSON, nullable=False, default=list)
    componentes = relationship(
        "ComponenteProducaoDB", cascade="all, delete-orphan",
        order_by="ComponenteProducaoDB.id",
    )
    revisoes = relationship(
        "RevisaoFichaProducaoDB", cascade="all, delete-orphan",
        order_by="RevisaoFichaProducaoDB.versao",
    )


class ComponenteProducaoDB(Base):
    __tablename__ = "producao_componentes"
    __table_args__ = (
        Index("ix_producao_componentes_peca", "peca_id"),
        CheckConstraint("quantidade > 0", name="ck_producao_componente_quantidade"),
        CheckConstraint("comprimento_corte IS NULL OR comprimento_corte > 0",
                        name="ck_producao_componente_corte"),
        CheckConstraint("custo_unitario >= 0", name="ck_producao_componente_custo"),
        CheckConstraint("origem_custo IN ('CADASTRO','INFORMADO')",
                        name="ck_producao_componente_origem_custo"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ordem_id = Column(Integer, ForeignKey("ordens_producao.id", ondelete="RESTRICT"), nullable=False)
    peca_id = Column(Integer, ForeignKey("producao_pecas.id", ondelete="RESTRICT"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="RESTRICT"), nullable=False)
    descricao = Column(Text, nullable=False)
    codigo_interno = Column(String(100))
    quantidade = Column(Numeric(12, 3), nullable=False)
    unidade = Column(String(50), nullable=False)
    comprimento_corte = Column(Numeric(12, 3))
    custo_unitario = Column(Numeric(14, 4), nullable=False)
    origem_custo = Column(String(20), nullable=False)
    observacoes = Column(Text, nullable=False, default="")


class RevisaoFichaProducaoDB(Base):
    __tablename__ = "producao_revisoes_ficha"
    __table_args__ = (
        UniqueConstraint("peca_id", "versao", name="uq_producao_ficha_versao"),
        CheckConstraint("versao > 1", name="ck_producao_revisao_versao"),
        Index("ix_producao_revisoes_peca", "peca_id"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    ordem_id = Column(Integer, ForeignKey("ordens_producao.id", ondelete="RESTRICT"), nullable=False)
    peca_id = Column(Integer, ForeignKey("producao_pecas.id", ondelete="RESTRICT"), nullable=False)
    versao = Column(Integer, nullable=False)
    usuario = Column(String(100), nullable=False)
    justificativa = Column(Text, nullable=False)
    antes = Column(JSON, nullable=False)
    depois = Column(JSON, nullable=False)
    criado_em = Column(DateTime(timezone=True), nullable=False)
