from typing import Optional

from pydantic import BaseModel


class FornecedorAliasCreate(BaseModel):
    fornecedor_id: int
    alias_original: str
    tipo: str
    origem: str
    nivel_confianca: str
    status_revisao: str = "PENDENTE"
    observacoes: Optional[str] = None
    ativo: bool = True
    revisado_por_usuario_id: Optional[int] = None


class FornecedorAliasUpdate(BaseModel):
    alias_original: Optional[str] = None
    tipo: Optional[str] = None
    origem: Optional[str] = None
    nivel_confianca: Optional[str] = None
    status_revisao: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None
    revisado_por_usuario_id: Optional[int] = None


class FornecedorAliasRead(FornecedorAliasCreate):
    id: int
    empresa_id: int
    alias_normalizado: str

    class Config:
        orm_mode = True
        from_attributes = True


class FornecedorReconhecimentoRead(BaseModel):
    fornecedor_id: int
    alias_id: int
    alias_original: str
    alias_normalizado: str
    tipo: str
    nivel_confianca: str
    status_revisao: str
    motivo: str
