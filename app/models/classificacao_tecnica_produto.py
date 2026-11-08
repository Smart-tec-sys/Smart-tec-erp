from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class ClassificacaoTecnicaProdutoDB(Base):
    __tablename__ = "classificacoes_tecnicas_produtos"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "tipo",
            "nome_normalizado",
            name="uq_classificacao_tecnica_empresa_tipo_nome",
        ),
        CheckConstraint(
            "tipo IN ('grupo_tecnico', 'familia_tecnica', 'modelo_tecnico')",
            name="ck_classificacao_tecnica_tipo",
        ),
    )

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    tipo = Column(String(30), nullable=False)
    nome = Column(String(255), nullable=False)
    nome_normalizado = Column(String(255), nullable=False)
