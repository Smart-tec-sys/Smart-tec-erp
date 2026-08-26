from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

class OrcamentoItemInput(BaseModel):
    tipo_item: str = "PRODUTO"
    produto_id: Optional[int] = None
    descricao: str
    codigo_interno: Optional[str] = None
    grupo_tecnico: Optional[str] = None
    modelo_tecnico: Optional[str] = None
    unidade: Optional[str] = None
    quantidade: float = Field(default=1, gt=0)
    largura: float = Field(default=0, ge=0)
    altura: float = Field(default=0, ge=0)
    area: float = Field(default=0, ge=0)
    preco_unitario: float = Field(default=0, ge=0)
    desconto: float = Field(default=0, ge=0)
    subtotal: float = Field(default=0, ge=0)
    observacao_item: Optional[str] = None
    material: Optional[str] = None
    cor: Optional[str] = None
    acionamento: Optional[str] = None
    lado_comando: Optional[str] = None
    calculo_producao_status: Optional[str] = None

class OrcamentoInput(BaseModel):
    cliente_id: int
    status: str = "EM_ABERTO"
    validade: Optional[date] = None
    observacao: Optional[str] = None
    desconto: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    total_final: float = Field(default=0, ge=0)
    itens: List[OrcamentoItemInput] = Field(default_factory=list)

class OrcamentoUpdate(OrcamentoInput):
    pass
