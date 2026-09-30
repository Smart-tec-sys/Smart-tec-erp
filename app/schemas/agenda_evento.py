from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgendaEventoBase(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    categoria: str = "GERAL"
    status: str = "AGENDADO"

    inicio: datetime
    fim: Optional[datetime] = None
    dia_inteiro: bool = False

    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None

    responsavel_ref: Optional[str] = None
    responsavel_nome: Optional[str] = None

    local: Optional[str] = None
    endereco: Optional[str] = None
    observacoes: Optional[str] = None

    origem: str = "ERP"
    origem_ref: Optional[str] = None
    origem_updated_at: Optional[datetime] = None
    sincronizacao_status: str = "LOCAL"

    metadados: Dict[str, Any] = Field(default_factory=dict)


class AgendaEventoCreate(AgendaEventoBase):
    external_uid: Optional[str] = None


class AgendaEventoUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    categoria: Optional[str] = None
    status: Optional[str] = None

    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    dia_inteiro: Optional[bool] = None

    cliente_id: Optional[int] = None
    cliente_nome: Optional[str] = None

    responsavel_ref: Optional[str] = None
    responsavel_nome: Optional[str] = None

    local: Optional[str] = None
    endereco: Optional[str] = None
    observacoes: Optional[str] = None

    origem: Optional[str] = None
    origem_ref: Optional[str] = None
    origem_updated_at: Optional[datetime] = None
    sincronizacao_status: Optional[str] = None

    metadados: Optional[Dict[str, Any]] = None


class AgendaEvento(AgendaEventoBase):
    id: int
    empresa_id: int
    external_uid: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
