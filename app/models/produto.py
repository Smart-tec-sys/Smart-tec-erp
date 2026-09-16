from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from app.database import Base


class ProdutoDB(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)

    # Dados principais
    nome = Column(String(255), nullable=False)
    codigo_interno = Column(String(100), nullable=True)
    codigo_barras = Column(String(100), nullable=True)
    grupo_produto = Column(String(150), nullable=True)

    # Arquitetura técnica SmartTec
    modelo_tecnico = Column(String(100), nullable=True)
    grupo_tecnico = Column(String(150), nullable=True)
    familia_tecnica = Column(String(100), nullable=True)

    produto_base = Column(String(255), nullable=True)
    variacao_cor = Column(String(100), nullable=True)
    variacao_lado = Column(String(100), nullable=True)
    variacao_tamanho = Column(String(100), nullable=True)

    varia_cor = Column(Boolean, default=False)
    cor_componente = Column(String(100), nullable=True)

    status_comercial = Column(String(50), default="Ativo")

    # Fornecedor
    fornecedores = Column(Text, nullable=True)
    nome_fornecedor = Column(String(255), nullable=True)
    codigo_fornecedor = Column(String(100), nullable=True)

    # Compra / controle
    unidade_compra = Column(String(50), nullable=True)
    unidade_controle = Column(String(50), nullable=True)
    comprimento_compra = Column(Float, default=0)
    saldo_metros = Column(Float, default=0)

    # Tipo e controle
    tipo_produto = Column(String(80), nullable=True)
    unidade_venda = Column(String(50), nullable=True)
    movimenta_estoque = Column(String(10), default="Sim")
    habilitar_nota_fiscal = Column(String(10), default="Sim")
    possui_variacoes = Column(String(10), default="Não")
    possui_composicao = Column(String(10), default="Não")
    situacao = Column(String(20), default="Ativo")

    # Detalhes técnicos
    linha = Column(String(150), nullable=True)
    modelo = Column(String(150), nullable=True)
    tipo_cortina_persiana = Column(String(150), nullable=True)
    material_tecido = Column(String(150), nullable=True)
    cor = Column(String(100), nullable=True)

    largura = Column(Float, default=0)
    altura = Column(Float, default=0)
    comprimento = Column(Float, default=0)
    peso = Column(Float, default=0)

    descricao = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)

    # Valores
    valor_custo = Column(Float, default=0)
    despesas_acessorias = Column(Float, default=0)
    outras_despesas = Column(Float, default=0)
    custo_final = Column(Float, default=0)
    margem_lucro = Column(Float, default=0)
    valor_venda = Column(Float, default=0)

    # Estoque
    estoque_minimo = Column(Float, default=0)
    estoque_maximo = Column(Float, default=0)
    estoque_atual = Column(Float, default=0)

    # Fiscal básico
    ncm = Column(String(50), nullable=True)
    cest = Column(String(50), nullable=True)
    origem = Column(String(100), nullable=True)
