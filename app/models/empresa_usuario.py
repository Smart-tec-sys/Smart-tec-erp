from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.database import Base


class EmpresaUsuarioDB(Base):
    __tablename__ = "empresa_usuarios"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "usuario_id",
            name="uq_empresa_usuarios_empresa_usuario",
        ),
        CheckConstraint(
            "papel IN ('OWNER', 'ADMIN', 'USUARIO')",
            name="ck_empresa_usuarios_papel",
        ),
    )

    id = Column(Integer, primary_key=True)

    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id"),
        nullable=False,
    )

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id"),
        nullable=False,
    )

    papel = Column(String(20), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)

    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )