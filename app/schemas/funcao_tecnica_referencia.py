from typing import Any, Optional

from pydantic import BaseModel, Field


class FuncaoTecnicaReferenciaCreate(BaseModel):
    funcao_tecnica: str
    nome_referencia: str
    codigo_referencia: Optional[str] = None
    unidade_referencia: Optional[str] = None
    fornecedor_id: Optional[int] = None
    tipo_referencia: str = "CATALOGO_FORNECEDOR"
    nivel_confianca: str
    status_revisao: str = "PENDENTE"
    atributos_referencia: dict[str, Any] = Field(default_factory=dict)
    origem: str
    origem_localizador: Optional[str] = None
    origem_hash: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: bool = True
    revisado_por_usuario_id: Optional[int] = None


class FuncaoTecnicaReferenciaUpdate(BaseModel):
    funcao_tecnica: Optional[str] = None
    nome_referencia: Optional[str] = None
    codigo_referencia: Optional[str] = None
    unidade_referencia: Optional[str] = None
    fornecedor_id: Optional[int] = None
    tipo_referencia: Optional[str] = None
    nivel_confianca: Optional[str] = None
    status_revisao: Optional[str] = None
    atributos_referencia: Optional[dict[str, Any]] = None
    origem: Optional[str] = None
    origem_localizador: Optional[str] = None
    origem_hash: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None
    revisado_por_usuario_id: Optional[int] = None


class FuncaoTecnicaReferenciaRead(FuncaoTecnicaReferenciaCreate):
    id: int
    empresa_id: int
    nome_normalizado: str

    class Config:
        orm_mode = True
        from_attributes = True
