from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)

from app.database import Base


class FinanceiroDB(Base):
    __tablename__ = "financeiro"
    __table_args__ = (UniqueConstraint("id", "empresa_id", name="uq_financeiro_id_empresa"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)

    tipo = Column(String(1), nullable=False)
    descricao = Column(String, nullable=False)

    valor = Column(Numeric(14, 2), nullable=False)
    vencimento = Column(Date, nullable=False)
    pagamento = Column(Date, nullable=True)

    status = Column(String, nullable=True, default="ABERTO")

    cliente_id = Column(Integer, nullable=True)
    fornecedor_id = Column(Integer, nullable=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=True)

    categoria = Column(String, nullable=True)
    observacao = Column(Text, nullable=True)

    criado_em = Column(DateTime, nullable=True, server_default=func.now())

    # F2A: valor_original NULL em titulos historicos => usar `valor`.
    competencia = Column(Date, nullable=True)
    conta_financeira_id = Column(Integer, ForeignKey("contas_financeiras.id", ondelete="SET NULL"), nullable=True)
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id", ondelete="SET NULL"), nullable=True)
    plano_conta_id = Column(Integer, ForeignKey("plano_contas.id", ondelete="SET NULL"), nullable=True)
    centro_custo_id = Column(Integer, ForeignKey("centros_custo.id", ondelete="SET NULL"), nullable=True)
    situacao_financeira_id = Column(Integer, ForeignKey("situacoes_financeiras.id", ondelete="SET NULL"), nullable=True)
    valor_original = Column(Numeric(14, 2), nullable=True)
    desconto = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    juros = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    valor_pago = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    data_baixa = Column(Date, nullable=True)
    numero_parcela = Column(Integer, nullable=True)
    total_parcelas = Column(Integer, nullable=True)
    parcelamento_grupo = Column(String(40), nullable=True)
    recorrente = Column(Boolean, nullable=False, default=False, server_default=false())
    recorrencia_grupo = Column(String(40), nullable=True)


class FinanceiroBaixaDB(Base):
    """Baixas de titulos (F2A.1). Somente estrutura; sem fluxo de baixa ainda."""

    __tablename__ = "financeiro_baixas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["financeiro_id", "empresa_id"], ["financeiro.id", "financeiro.empresa_id"],
            name="fk_financeiro_baixas_titulo",
        ),
        CheckConstraint("valor > 0", name="ck_financeiro_baixas_valor"),
        CheckConstraint("juros >= 0", name="ck_financeiro_baixas_juros"),
        CheckConstraint("desconto >= 0", name="ck_financeiro_baixas_desconto"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    financeiro_id = Column(Integer, nullable=False, index=True)
    data_baixa = Column(Date, nullable=False, index=True)
    valor = Column(Numeric(14, 2), nullable=False)
    juros = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    desconto = Column(Numeric(14, 2), nullable=False, default=0, server_default="0")
    conta_financeira_id = Column(Integer, ForeignKey("contas_financeiras.id", ondelete="SET NULL"), nullable=True, index=True)
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id", ondelete="SET NULL"), nullable=True)
    observacao = Column(Text, nullable=True)
    estornada_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())