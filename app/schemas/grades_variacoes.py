from typing import Optional
from pydantic import BaseModel, Field, validator


class GradeCreate(BaseModel):
    class Config:
        extra = "forbid"

    # Compatibility with the existing service, without changing its PATCH contract.
    def model_dump(self, **kwargs):
        return self.dict(**kwargs)
    nome: str = Field(min_length=1, max_length=120)
    descricao: Optional[str] = None
    ativo: bool = True
    ordem: int = Field(default=0, ge=0)

    @validator("nome")
    def nome_limpo(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Informe o nome da grade.")
        return value


class GradeUpdate(BaseModel):
    class Config:
        extra = "forbid"

    # Compatibility with the existing service, without changing its PATCH contract.
    def model_dump(self, **kwargs):
        return self.dict(**kwargs)
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[str] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = Field(default=None, ge=0)

    @validator("nome", "ativo", "ordem")
    def obrigatorio_quando_enviado(cls, value):
        if value is None or isinstance(value, str) and not value.strip():
            raise ValueError("O campo enviado não pode ser vazio ou nulo.")
        return value.strip() if isinstance(value, str) else value


class ValorCreate(BaseModel):
    class Config:
        extra = "forbid"

    # Compatibility with the existing service, without changing its PATCH contract.
    def model_dump(self, **kwargs):
        return self.dict(**kwargs)
    valor: str = Field(min_length=1, max_length=150)
    ativo: bool = True
    ordem: int = Field(default=0, ge=0)

    @validator("valor")
    def valor_limpo(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Informe o valor da grade.")
        return value


class ValorUpdate(BaseModel):
    class Config:
        extra = "forbid"

    # Compatibility with the existing service, without changing its PATCH contract.
    def model_dump(self, **kwargs):
        return self.dict(**kwargs)
    valor: Optional[str] = Field(default=None, min_length=1, max_length=150)
    ativo: Optional[bool] = None
    ordem: Optional[int] = Field(default=None, ge=0)

    @validator("valor", "ativo", "ordem")
    def obrigatorio_quando_enviado(cls, value):
        if value is None or isinstance(value, str) and not value.strip():
            raise ValueError("O campo enviado não pode ser vazio ou nulo.")
        return value.strip() if isinstance(value, str) else value
