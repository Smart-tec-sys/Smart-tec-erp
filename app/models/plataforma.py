from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class PlataformaFuncaoDB(Base):
    __tablename__ = "plataforma_funcoes"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), nullable=False, unique=True)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    nivel = Column(Integer, nullable=False, default=10)
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlataformaPermissaoDB(Base):
    __tablename__ = "plataforma_permissoes"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(100), nullable=False, unique=True)
    modulo = Column(String(80), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=True)
    sensivel = Column(Boolean, nullable=False, default=False)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())


class PlataformaFuncaoPermissaoDB(Base):
    __tablename__ = "plataforma_funcao_permissoes"

    __table_args__ = (
        UniqueConstraint(
            "funcao_id",
            "permissao_id",
            name="uq_plataforma_funcao_permissao",
        ),
    )

    id = Column(Integer, primary_key=True)

    funcao_id = Column(
        Integer,
        ForeignKey("plataforma_funcoes.id", ondelete="CASCADE"),
        nullable=False,
    )

    permissao_id = Column(
        Integer,
        ForeignKey("plataforma_permissoes.id", ondelete="CASCADE"),
        nullable=False,
    )

    permitido = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, nullable=False, server_default=func.now())


class PlataformaEquipeDB(Base):
    __tablename__ = "plataforma_equipe"

    id = Column(Integer, primary_key=True)

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    funcao_id = Column(
        Integer,
        ForeignKey("plataforma_funcoes.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status = Column(String(20), nullable=False, default="ATIVO")
    cargo_exibicao = Column(String(150), nullable=True)

    pode_receber_chamados = Column(Boolean, nullable=False, default=False)
    pode_receber_clientes = Column(Boolean, nullable=False, default=False)

    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlataformaEquipePermissaoDB(Base):
    __tablename__ = "plataforma_equipe_permissoes"

    __table_args__ = (
        UniqueConstraint(
            "equipe_id",
            "permissao_id",
            name="uq_plataforma_equipe_permissao",
        ),
    )

    id = Column(Integer, primary_key=True)

    equipe_id = Column(
        Integer,
        ForeignKey("plataforma_equipe.id", ondelete="CASCADE"),
        nullable=False,
    )

    permissao_id = Column(
        Integer,
        ForeignKey("plataforma_permissoes.id", ondelete="CASCADE"),
        nullable=False,
    )

    permitido = Column(Boolean, nullable=False)

    criado_em = Column(DateTime, nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuditoriaPlataformaDB(Base):
    __tablename__ = "auditoria_plataforma"

    id = Column(BigInteger, primary_key=True)

    equipe_id = Column(
        Integer,
        ForeignKey("plataforma_equipe.id", ondelete="SET NULL"),
        nullable=True,
    )

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    empresa_afetada_id = Column(
        Integer,
        ForeignKey("empresas.id", ondelete="SET NULL"),
        nullable=True,
    )

    acao = Column(String(120), nullable=False)
    recurso = Column(String(120), nullable=True)
    recurso_id = Column(String(120), nullable=True)

    detalhes = Column(JSONB, nullable=False, default=dict)

    ip_origem = Column(String(100), nullable=True)
    request_id = Column(String(255), nullable=True)

    criado_em = Column(DateTime, nullable=False, server_default=func.now())