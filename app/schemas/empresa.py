"""Schemas da entidade Empresa."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, validator


class EmpresaStatus(str, Enum):
    ATIVA = "ATIVA"
    INATIVA = "INATIVA"


class EmpresaBase(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    nome_fantasia: str | None = Field(default=None, max_length=255)
    documento: str | None = Field(default=None, max_length=50)
    status: EmpresaStatus = EmpresaStatus.ATIVA
    slug: str = Field(max_length=100)
    configuracoes: dict[str, Any] = Field(default_factory=dict)

    @validator("slug")
    def validar_slug(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("slug deve usar letras minúsculas, números e hífens")
        return value


class EmpresaCreate(EmpresaBase):
    pass


class Empresa(EmpresaBase):
    id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class EmpresaPortfolioBase(BaseModel):
    modelo_tecnico: str = Field(min_length=1, max_length=100)
    ativo: bool = True
    configuracoes_locais: dict[str, Any] = Field(default_factory=dict)


class EmpresaPortfolioCreate(EmpresaPortfolioBase):
    empresa_id: int = Field(gt=0)


class EmpresaPortfolio(EmpresaPortfolioCreate):
    id: int
    criado_em: datetime
    atualizado_em: datetime

    model_config = ConfigDict(from_attributes=True)
