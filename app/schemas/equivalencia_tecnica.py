from typing import Any, Optional

from pydantic import BaseModel, Field


class EquivalenciaTecnicaCreate(BaseModel):
    funcao_tecnica: str
    produto_id: int
    fornecedor_id: Optional[int] = None
    prioridade: int = 100
    preferencial: bool = False
    ativo: bool = True
    configuracoes_locais: dict[str, Any] = Field(default_factory=dict)


class EquivalenciaTecnicaUpdate(BaseModel):
    funcao_tecnica: Optional[str] = None
    produto_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    prioridade: Optional[int] = None
    preferencial: Optional[bool] = None
    ativo: Optional[bool] = None
    configuracoes_locais: Optional[dict[str, Any]] = None


class EquivalenciaTecnicaRead(EquivalenciaTecnicaCreate):
    id: int
    empresa_id: int

    class Config:
        orm_mode = True
        from_attributes = True


class EquivalenciaStatusUpdate(BaseModel):
    ativo: bool


class EquivalenciaPreferencialUpdate(BaseModel):
    preferencial: bool = True
