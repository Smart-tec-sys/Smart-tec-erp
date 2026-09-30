from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, Text, func

from app.database import Base


class FuncaoTecnicaReferenciaDB(Base):
    __tablename__ = "funcao_tecnica_referencias"
    __table_args__ = (
        CheckConstraint(
            "nivel_confianca IN ('FORTE', 'PROVAVEL', 'AMBIGUA')",
            name="ck_referencia_confianca",
        ),
        CheckConstraint(
            "status_revisao IN ('PENDENTE', 'APROVADA', 'REJEITADA')",
            name="ck_referencia_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    funcao_tecnica = Column(String(100), nullable=False)
    nome_referencia = Column(String(500), nullable=False)
    nome_normalizado = Column(String(500), nullable=False)
    codigo_referencia = Column(String(150), nullable=True)
    unidade_referencia = Column(String(50), nullable=True)
    tipo_referencia = Column(String(40), nullable=False, default="CATALOGO_FORNECEDOR")
    nivel_confianca = Column(String(20), nullable=False)
    status_revisao = Column(String(20), nullable=False, default="PENDENTE")
    atributos_referencia = Column(JSON, nullable=False, default=dict)
    origem = Column(String(500), nullable=False)
    origem_localizador = Column(String(200), nullable=True)
    origem_hash = Column(String(64), nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    revisado_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
