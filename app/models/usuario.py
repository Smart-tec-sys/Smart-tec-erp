from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, func

from app.database import Base


class UsuarioDB(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ATIVO', 'INATIVO')",
            name="ck_usuarios_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="ATIVO")

    # Identidade fornecida por provedor externo.
    # Nenhuma senha é armazenada neste modelo.
    provedor = Column(String(50), nullable=True)
    provedor_subject = Column(String(255), nullable=True)

    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )