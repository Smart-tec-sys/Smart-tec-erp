"""Portfólio técnico selecionado por empresa; sem dados iniciais."""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class EmpresaPortfolioDB(Base):
    __tablename__ = "empresa_portfolio"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "modelo_tecnico",
            name="uq_empresa_portfolio_empresa_modelo",
        ),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
    )
    modelo_tecnico = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    configuracoes_locais = Column(JSON, nullable=False, default=dict)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    empresa = relationship("EmpresaDB", back_populates="portfolio")
