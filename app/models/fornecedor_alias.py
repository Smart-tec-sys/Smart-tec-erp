from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class FornecedorAliasDB(Base):
    __tablename__ = "fornecedor_aliases"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('NOME_HISTORICO', 'NOME_IMPORTACAO', 'VARIANTE_GRAFIA', "
            "'NOME_COMERCIAL', 'OUTRO')",
            name="ck_fornecedor_alias_tipo",
        ),
        CheckConstraint(
            "nivel_confianca IN ('FORTE', 'PROVAVEL', 'AMBIGUA')",
            name="ck_fornecedor_alias_confianca",
        ),
        CheckConstraint(
            "status_revisao IN ('PENDENTE', 'APROVADO', 'REJEITADO')",
            name="ck_fornecedor_alias_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=False)
    alias_original = Column(String(500), nullable=False)
    alias_normalizado = Column(String(500), nullable=False)
    tipo = Column(String(40), nullable=False)
    origem = Column(String(500), nullable=False)
    nivel_confianca = Column(String(20), nullable=False)
    status_revisao = Column(String(20), nullable=False, default="PENDENTE")
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    revisado_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
