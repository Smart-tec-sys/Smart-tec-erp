from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, Text, UniqueConstraint, func, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
from app.models.funcionario import FuncionarioDB  # noqa: F401

# Referências de metadata para tabelas comerciais existentes.
# Estas tabelas são administradas atualmente por SQL bruto no
# representante_service.py. Aqui registramos somente a chave primária
# necessária para que as ForeignKeys de OrcamentoDB sejam resolvidas.
Table(
    "parceiros_comerciais",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    extend_existing=True,
)

Table(
    "representantes",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    extend_existing=True,
)

class OrcamentoDB(Base):
    __tablename__ = "orcamentos"
    __table_args__ = (UniqueConstraint("id", "empresa_id", name="uq_orcamentos_id_empresa"),)
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    numero = Column(String, nullable=False, unique=True)
    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id"),
        nullable=True,
    )
    cliente_final_nome = Column(Text, nullable=True)
    cliente_final_documento = Column(Text, nullable=True)
    cliente_final_telefone = Column(Text, nullable=True)
    cliente_final_email = Column(Text, nullable=True)
    cliente_final_endereco = Column(Text, nullable=True)

    perfil_comercial = Column(String(30), nullable=False, default="VAREJO")
    status = Column(String, nullable=False, default="EM_ABERTO")
    validade = Column(Date)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    desconto = Column(Numeric(14, 2), nullable=False, default=0)
    total_final = Column(Numeric(14, 2), nullable=False, default=0)

    # Camada comercial do parceiro.
    # total_final permanece sendo o valor interno da empresa.
    parceiro_id = Column(
        Integer,
        ForeignKey("parceiros_comerciais.id", ondelete="SET NULL"),
        nullable=True,
    )
    representante_id = Column(
        Integer,
        ForeignKey("representantes.id", ondelete="SET NULL"),
        nullable=True,
    )

    vendedor_id = Column(
        Integer,
        ForeignKey("funcionarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    percentual_parceiro = Column(
        Numeric(8, 4),
        nullable=False,
        default=0,
    )

    incluir_rt = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    tipo_rt = Column(String(20))
    percentual_rt = Column(
        Numeric(8, 4),
        nullable=False,
        default=0,
    )
    valor_rt = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    incluir_taxa_bancaria = Column(
        Boolean,
        nullable=False,
        default=False,
    )
    taxa_bancaria_percentual = Column(
        Numeric(8, 4),
        nullable=False,
        default=0,
    )

    valor_parceiro = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )
    base_protegida = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )
    valor_taxa_bancaria = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )
    total_cliente_final = Column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    pagamento_modalidade = Column(String(20), nullable=True)
    pagamento_numero_parcelas = Column(Integer, nullable=True)
    pagamento_intervalo_dias = Column(Integer, nullable=True)
    pagamento_primeiro_vencimento = Column(Date, nullable=True)

    observacao = Column(Text)
    observacao_interna = Column(Text)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())
    cliente = relationship("ClienteDB")
    itens = relationship("OrcamentoItemDB", cascade="all, delete-orphan", back_populates="orcamento")
    parcelas_pagamento = relationship(
        "OrcamentoParcelaDB", cascade="all, delete-orphan", back_populates="orcamento",
        order_by="OrcamentoParcelaDB.numero",
    )


class OrcamentoParcelaDB(Base):
    __tablename__ = "orcamento_parcelas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["orcamento_id", "empresa_id"], ["orcamentos.id", "orcamentos.empresa_id"],
            name="fk_orcamento_parcelas_orcamento_empresa", ondelete="CASCADE",
        ),
        UniqueConstraint("orcamento_id", "numero", name="uq_orcamento_parcelas_numero"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    orcamento_id = Column(Integer, nullable=False, index=True)
    numero = Column(Integer, nullable=False)
    tipo = Column(String(20), nullable=False, default="PARCELA")
    valor = Column(Numeric(14, 2), nullable=False)
    vencimento = Column(Date, nullable=False)
    forma_pagamento_id = Column(Integer, ForeignKey("formas_pagamento.id", ondelete="RESTRICT"), nullable=False)
    forma_pagamento_nome = Column(String(80), nullable=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    orcamento = relationship("OrcamentoDB", back_populates="parcelas_pagamento")

class OrcamentoItemDB(Base):
    __tablename__ = "orcamentos_itens"
    id = Column(Integer, primary_key=True)
    orcamento_id = Column(Integer, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False)
    tipo_item = Column(String, nullable=False, default="PRODUTO")
    produto_id = Column(Integer, ForeignKey("produtos.id"))
    descricao = Column(Text)
    codigo_interno = Column(String)
    grupo_tecnico = Column(String)
    modelo_tecnico = Column(String)
    unidade = Column(String)
    quantidade = Column(Numeric(14, 4), nullable=False)
    largura = Column(Numeric(12, 3), nullable=False, default=0)
    altura = Column(Numeric(12, 3), nullable=False, default=0)
    area = Column(Numeric(14, 4), nullable=False, default=0)
    preco_unitario = Column("preco_unit", Numeric(14, 4), nullable=False)
    desconto = Column(Numeric(14, 2), nullable=False, default=0)
    subtotal = Column("total", Numeric(14, 2), nullable=False, default=0)
    observacao_item = Column(Text)
    material = Column(String)
    cor = Column(String)
    acionamento = Column(String)
    lado_comando = Column(String)
    calculo_producao_status = Column(String)
    dados_tecnicos = Column(JSONB, nullable=True)
    orcamento = relationship("OrcamentoDB", back_populates="itens")
