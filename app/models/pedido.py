from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.orcamento import OrcamentoDB  # noqa: F401


class PedidoDB(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    numero = Column(String, nullable=True, unique=True)
    cliente_id = Column(Integer, nullable=True)

    vendedor_id = Column(
        Integer,
        ForeignKey("funcionarios.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    orcamento_id = Column(
        Integer,
        ForeignKey("orcamentos.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(String, nullable=True, default="ABERTO")
    cliente_final_nome = Column(Text, nullable=True)
    cliente_final_documento = Column(Text, nullable=True)
    cliente_final_telefone = Column(Text, nullable=True)
    cliente_final_email = Column(Text, nullable=True)
    cliente_final_endereco = Column(Text, nullable=True)

    perfil_comercial = Column(String(30), nullable=False, default="VAREJO")

    data_venda = Column(Date, nullable=True)
    prazo_entrega = Column(Date, nullable=True)
    canal_venda = Column(String(100), nullable=True)

    total = Column(Numeric(14, 2), nullable=True, default=0)
    desconto = Column(Numeric(14, 2), nullable=True, default=0)
    total_final = Column(Numeric(14, 2), nullable=True, default=0)

    # Composição salva; pedidos históricos mantêm valores desconhecidos como null.
    percentual_parceiro = Column(Numeric(8, 4), nullable=True)
    incluir_rt = Column(Boolean, nullable=True)
    tipo_rt = Column(String(20), nullable=True)
    percentual_rt = Column(Numeric(8, 4), nullable=True)
    valor_rt = Column(Numeric(14, 2), nullable=True)
    incluir_taxa_bancaria = Column(Boolean, nullable=True)
    taxa_bancaria_percentual = Column(Numeric(8, 4), nullable=True)
    valor_parceiro = Column(Numeric(14, 2), nullable=True)
    valor_taxa_bancaria = Column(Numeric(14, 2), nullable=True)
    total_cliente_final = Column(Numeric(14, 2), nullable=True)

    observacao = Column(Text, nullable=True)
    observacao_interna = Column(Text, nullable=True)

    criado_em = Column(DateTime, nullable=True, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=True, onupdate=func.now())

    orcamento = relationship("OrcamentoDB")

    itens = relationship(
        "PedidoItemDB",
        cascade="all, delete-orphan",
        back_populates="pedido",
    )


class PedidoItemDB(Base):
    __tablename__ = "pedidos_itens"

    id = Column(Integer, primary_key=True)

    pedido_id = Column(
        Integer,
        ForeignKey("pedidos.id", ondelete="CASCADE"),
        nullable=False,
    )

    tipo_item = Column(String(30), nullable=False, default="PRODUTO")
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)

    descricao = Column(Text, nullable=True)
    codigo_interno = Column(String, nullable=True)
    grupo_tecnico = Column(String, nullable=True)
    modelo_tecnico = Column(String, nullable=True)
    unidade = Column(String, nullable=True)

    quantidade = Column(Numeric(14, 4), nullable=False)
    largura = Column(Numeric(12, 3), nullable=False, default=0)
    altura = Column(Numeric(12, 3), nullable=False, default=0)
    area = Column(Numeric(14, 4), nullable=False, default=0)

    preco_unitario = Column("preco_unit", Numeric(14, 4), nullable=False)
    desconto = Column(Numeric(14, 2), nullable=True, default=0)
    subtotal = Column("total", Numeric(14, 2), nullable=True, default=0)

    observacao_item = Column(Text, nullable=True)

    material = Column(String, nullable=True)
    cor = Column(String, nullable=True)
    acionamento = Column(String, nullable=True)
    lado_comando = Column(String, nullable=True)
    calculo_producao_status = Column(String, nullable=True)
    dados_tecnicos = Column(JSONB, nullable=True)

    pedido = relationship(
        "PedidoDB",
        back_populates="itens",
    )