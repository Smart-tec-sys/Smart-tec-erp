"""Entidade Empresa da base multiempresa; tabela ainda não criada no banco."""

from sqlalchemy import JSON, CheckConstraint, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class EmpresaDB(Base):
    __tablename__ = "empresas"
    __table_args__ = (
        CheckConstraint("status IN ('ATIVA', 'INATIVA')", name="ck_empresas_status"),
    )

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    documento = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="ATIVA")
    slug = Column(String(100), nullable=False, unique=True)
    configuracoes = Column(JSON, nullable=False, default=dict)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    portfolio = relationship(
        "EmpresaPortfolioDB",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
