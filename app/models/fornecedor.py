from sqlalchemy import Column, ForeignKey, Integer, String, Text
from app.database import Base


class FornecedorDB(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    situacao = Column(String, default="Ativo")
    documento = Column(String, nullable=True)
    email = Column(String, nullable=True)
    site = Column(String, nullable=True)
    telefone_comercial = Column(String, nullable=True)
    telefone_celular = Column(String, nullable=True)

    cep = Column(String, nullable=True)
    logradouro = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)

    observacoes = Column(Text, nullable=True)
