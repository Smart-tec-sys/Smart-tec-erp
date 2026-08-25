from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class TransportadoraDB(Base):
    __tablename__ = "transportadoras"

    id = Column(Integer, primary_key=True, index=True)

    tipo = Column(String(50), nullable=False)  # Pessoa Física / Pessoa Jurídica
    situacao = Column(String(20), default="Ativo")  # Ativo / Inativo
    nome = Column(String(255), nullable=False)  # Nome fantasia / Nome

    documento = Column(String(50), nullable=True)  # CPF / CNPJ
    razao_social = Column(String(255), nullable=True)
    inscricao_estadual = Column(String(80), nullable=True)
    inscricao_municipal = Column(String(80), nullable=True)
    responsavel = Column(String(120), nullable=True)

    email = Column(String(255), nullable=True)
    telefone = Column(String(50), nullable=True)
    celular = Column(String(50), nullable=True)

    cep = Column(String(20), nullable=True)
    logradouro = Column(String(255), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(255), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade_uf = Column(String(150), nullable=True)

    observacoes = Column(Text, nullable=True)
