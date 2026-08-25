from pydantic import BaseModel
from typing import Optional


class FornecedorBase(BaseModel):
    nome: str
    tipo: str
    situacao: str = "Ativo"
    documento: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    telefone_comercial: Optional[str] = None
    telefone_celular: Optional[str] = None

    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None

    observacoes: Optional[str] = None


class FornecedorCreate(FornecedorBase):
    pass


class FornecedorUpdate(FornecedorBase):
    pass


class Fornecedor(FornecedorBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True
