from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class OpcaoAuxiliarDB(Base):
    __tablename__ = "opcoes_auxiliares"

    id = Column(Integer, primary_key=True, index=True)

    categoria = Column(String(100), nullable=False, index=True)
    nome = Column(String(255), nullable=False)

    descricao = Column(Text, nullable=True)
    tipo_campo = Column(String(50), nullable=True)
    obrigatorio = Column(String(10), default="Não")
    situacao = Column(String(20), default="Ativo")
    ordem = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())
