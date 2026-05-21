from pydantic import BaseModel
from typing import Optional


class ClienteBase(BaseModel):
    tipo: str
    situacao: str = "Ativo"
    nome: str
    email: Optional[str] = None
    telefone_comercial: Optional[str] = None
    telefone_celular: Optional[str] = None
    documento: Optional[str] = None
    site: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    limite_credito: float = 0.0
    permitir_exceder: bool = False


class ClienteCreate(ClienteBase):
    pass


class Cliente(ClienteBase):
    id: int

    class Config:
        from_attributes = True
