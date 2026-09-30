from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class AgendaEventoDB(Base):
    __tablename__ = "agenda_eventos"

    id = Column(Integer, primary_key=True, index=True)

    # Multiempresa
    empresa_id = Column(
        Integer,
        ForeignKey("empresas.id"),
        nullable=False,
        index=True,
    )

    # Identificador estavel para integracoes entre sistemas
    external_uid = Column(String(80), nullable=False)

    # Nucleo generico da agenda
    titulo = Column(String(180), nullable=False)
    descricao = Column(Text, nullable=True)
    categoria = Column(String(80), nullable=False, default="GERAL")
    status = Column(String(40), nullable=False, default="AGENDADO")

    inicio = Column(DateTime(timezone=True), nullable=False, index=True)
    fim = Column(DateTime(timezone=True), nullable=True)
    dia_inteiro = Column(Boolean, nullable=False, default=False)

    # Cliente e responsavel sao opcionais.
    # Isso permite compromissos internos ou eventos vindos de outros sistemas.
    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id"),
        nullable=True,
        index=True,
    )
    cliente_nome = Column(String(180), nullable=True)

    responsavel_ref = Column(String(120), nullable=True)
    responsavel_nome = Column(String(180), nullable=True)

    local = Column(String(220), nullable=True)
    endereco = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)

    # Integracao
    # Exemplos de origem:
    # ERP, VISITA_TECNICA, SHOWCASE, API, IMPORTACAO
    origem = Column(String(60), nullable=False, default="ERP")
    origem_ref = Column(String(160), nullable=True)
    origem_updated_at = Column(DateTime(timezone=True), nullable=True)

    # PENDING, SYNCED, ERROR, LOCAL
    sincronizacao_status = Column(String(30), nullable=False, default="LOCAL")

    # Extensoes especificas por modulo/segmento.
    # Ex.: dados da visita tecnica sem prender o ERP ao segmento de persianas.
    metadados = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "external_uid",
            name="uq_agenda_eventos_empresa_external_uid",
        ),
        Index(
            "ix_agenda_eventos_empresa_inicio",
            "empresa_id",
            "inicio",
        ),
    )
