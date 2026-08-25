from pydantic import BaseModel
from typing import Optional


class TransportadoraBase(BaseModel):
    tipo: str
    situacao: str = "Ativo"
    nome: str

    documento: Optional[str] = None
    razao_social: Optional[str] = None
    inscricao_estadual: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    responsavel: Optional[str] = None

    email: Optional[str] = None
    telefone: Optional[str] = None
    celular: Optional[str] = None

    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade_uf: Optional[str] = None

    observacoes: Optional[str] = None


class TransportadoraCreate(TransportadoraBase):
    pass


class TransportadoraUpdate(TransportadoraBase):
    pass


class Transportadora(TransportadoraBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True
