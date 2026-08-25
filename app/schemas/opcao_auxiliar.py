from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OpcaoAuxiliarBase(BaseModel):
    categoria: str
    nome: str
    descricao: Optional[str] = None
    tipo_campo: Optional[str] = None
    obrigatorio: Optional[str] = "Não"
    situacao: Optional[str] = "Ativo"
    ordem: Optional[int] = 0


class OpcaoAuxiliarCreate(OpcaoAuxiliarBase):
    pass


class OpcaoAuxiliar(OpcaoAuxiliarBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True
