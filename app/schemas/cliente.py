from pydantic import BaseModel
from typing import Optional


class ClienteBase(BaseModel):
    # Dados gerais
    tipo: str
    situacao: str = "Ativo"
    nome: str
    email: Optional[str] = None
    telefone_comercial: Optional[str] = None
    telefone_celular: Optional[str] = None
    documento: Optional[str] = None
    site: Optional[str] = None
    vendedor_responsavel: Optional[str] = None

    # Endereço
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None

    # Financeiro
    limite_credito: float = 0.0
    permitir_exceder: bool = False

    # Observações
    observacoes: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class Cliente(ClienteBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True
