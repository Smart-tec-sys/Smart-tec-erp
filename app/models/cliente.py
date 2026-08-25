from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from app.database import Base


class ClienteDB(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)

    # Dados gerais
    tipo = Column(String, nullable=False)
    situacao = Column(String, default="Ativo")
    nome = Column(String, nullable=False)
    email = Column(String, nullable=True)
    telefone_comercial = Column(String, nullable=True)
    telefone_celular = Column(String, nullable=True)
    documento = Column(String, nullable=True)
    site = Column(String, nullable=True)
    vendedor_responsavel = Column(String, nullable=True)

    # Endereço
    cep = Column(String, nullable=True)
    logradouro = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)

    # Financeiro
    limite_credito = Column(Float, default=0.0)
    permitir_exceder = Column(Boolean, default=False)

    # Observações
    observacoes = Column(Text, nullable=True)
