# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Optional


class ClienteBase(BaseModel):
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    ativo: bool = True


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class ClienteOut(ClienteBase):
    id: int

    class Config:
        orm_mode = True
