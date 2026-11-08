from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class ServicoDB(Base):
    __tablename__ = "servicos"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_servicos_empresa_codigo"),
        UniqueConstraint("id", "empresa_id", name="uq_servicos_id_empresa"),
        CheckConstraint("custo >= 0", name="ck_servicos_custo_nao_negativo"),
        CheckConstraint("preco_venda >= 0", name="ck_servicos_preco_nao_negativo"),
        CheckConstraint("comissao IS NULL OR (comissao >= 0 AND comissao <= 100)", name="ck_servicos_comissao"),
        CheckConstraint("situacao IN ('ATIVO', 'INATIVO')", name="ck_servicos_situacao"),
        CheckConstraint("unidade IN ('UN', 'ML', 'M2', 'HORA', 'SERVICO')", name="ck_servicos_unidade"),
        CheckConstraint("tipo_calculo IN ('POR_UNIDADE', 'FAIXA_ALTURA')", name="ck_servicos_tipo_calculo"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=False)
    categoria = Column(String(80), nullable=False)
    unidade = Column(String(12), nullable=False)
    tipo_calculo = Column(String(30), nullable=False, default="POR_UNIDADE")
    custo = Column(Numeric(14, 4), nullable=False, default=0)
    preco_venda = Column(Numeric(14, 4), nullable=False, default=0)
    comissao = Column(Numeric(8, 4))
    observacoes = Column(Text)
    situacao = Column(String(10), nullable=False, default="ATIVO")
    faixas_altura = Column(JSONB, nullable=False, default=list)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
