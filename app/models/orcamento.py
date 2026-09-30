from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class OrcamentoDB(Base):
    __tablename__ = "orcamentos"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    numero = Column(String, nullable=False, unique=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    perfil_comercial = Column(String(30), nullable=False, default="VAREJO")
    status = Column(String, nullable=False, default="EM_ABERTO")
    validade = Column(Date)
    total = Column(Numeric(14, 2), nullable=False, default=0)
    desconto = Column(Numeric(14, 2), nullable=False, default=0)
    total_final = Column(Numeric(14, 2), nullable=False, default=0)
    observacao = Column(Text)
    observacao_interna = Column(Text)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())
    cliente = relationship("ClienteDB")
    itens = relationship("OrcamentoItemDB", cascade="all, delete-orphan", back_populates="orcamento")

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
