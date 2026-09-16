from sqlalchemy import Column, ForeignKey, Integer, String, Float, Text
from app.database import Base


class FuncionarioDB(Base):
    __tablename__ = "funcionarios"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)

    # Dados gerais
    nome = Column(String, nullable=False)
    cpf = Column(String, nullable=True)
    rg = Column(String, nullable=True)
    data_nascimento = Column(String, nullable=True)
    sexo = Column(String, nullable=True)
    email = Column(String, nullable=True)
    comissao = Column(Float, nullable=True, default=0)
    situacao = Column(String, default="Ativo")
    permite_acesso = Column(String, nullable=True, default="Não")
    observacoes = Column(Text, nullable=True)

    # Campos já existentes / compatibilidade
    cargo = Column(String, nullable=True)
    departamento = Column(String, nullable=True)
    salario = Column(Float, nullable=True, default=0)

    # Contatos
    telefone = Column(String, nullable=True)
    celular1 = Column(String, nullable=True)
    celular2 = Column(String, nullable=True)

    # Endereço
    cep = Column(String, nullable=True)
    logradouro = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    complemento = Column(String, nullable=True)
    bairro = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)
