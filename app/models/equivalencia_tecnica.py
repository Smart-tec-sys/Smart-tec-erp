from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, func

from app.database import Base


class EmpresaEquivalenciaTecnicaDB(Base):
    __tablename__ = "empresa_equivalencias_tecnicas"
    __table_args__ = (
        CheckConstraint("prioridade >= 0", name="ck_equivalencias_prioridade"),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    funcao_tecnica = Column(String(100), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    prioridade = Column(Integer, nullable=False, default=100)
    preferencial = Column(Boolean, nullable=False, default=False)
    ativo = Column(Boolean, nullable=False, default=True)
    configuracoes_locais = Column(JSON, nullable=False, default=dict)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
