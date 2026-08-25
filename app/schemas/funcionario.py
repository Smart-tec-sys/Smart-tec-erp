from pydantic import BaseModel
from typing import Optional


class FuncionarioBase(BaseModel):
    nome: str

    cpf: Optional[str] = None
    rg: Optional[str] = None
    data_nascimento: Optional[str] = None
    sexo: Optional[str] = None
    email: Optional[str] = None
    comissao: Optional[float] = 0
    situacao: str = "Ativo"
    permite_acesso: Optional[str] = "Não"
    observacoes: Optional[str] = None

    cargo: Optional[str] = None
    departamento: Optional[str] = None
    salario: Optional[float] = 0

    telefone: Optional[str] = None
    celular1: Optional[str] = None
    celular2: Optional[str] = None

    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class FuncionarioCreate(FuncionarioBase):
    pass


class FuncionarioUpdate(FuncionarioBase):
    pass


class Funcionario(FuncionarioBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True
