from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, conint


class RomanaTetoSimulacaoInput(BaseModel):
    produto_id: int = Field(gt=0)
    largura_modulo_m: float = Field(gt=0, allow_inf_nan=False)
    comprimento_avanco_m: float = Field(gt=0, allow_inf_nan=False)
    quantidade_modulos: conint(strict=True, gt=0)
    acionamento: Literal["MANUAL_BASTAO", "MANUAL_CORRENTE", "MOTORIZADA"]
    lado_comando: Optional[Literal["ESQUERDA", "DIREITA"]] = None
    comprimento_bastao_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    comprimento_corrente_sem_fim_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    perfil_comercial: Literal["DECORADOR", "VAREJO", "CONSUMIDOR_FINAL"] = "VAREJO"
    desconto: float = Field(default=0, ge=0, allow_inf_nan=False)
    cor: Optional[str] = None


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
    dados_tecnicos: Optional[dict] = None
    largura_modulo_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    comprimento_avanco_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    quantidade_modulos: Optional[int] = Field(default=None, gt=0)
    acionamento_romana_teto: Optional[str] = None
    comprimento_bastao_m: Optional[float] = Field(default=None, allow_inf_nan=False)
    comprimento_corrente_sem_fim_m: Optional[float] = Field(default=None, allow_inf_nan=False)

class OrcamentoInput(BaseModel):
    cliente_id: int
    perfil_comercial: Literal["DECORADOR", "VAREJO", "CONSUMIDOR_FINAL"] = "VAREJO"
    status: str = "EM_ABERTO"
    validade: Optional[date] = None
    observacao: Optional[str] = None
    observacao_interna: Optional[str] = None
    desconto: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    total_final: float = Field(default=0, ge=0)
    itens: List[OrcamentoItemInput] = Field(default_factory=list)

class OrcamentoUpdate(OrcamentoInput):
    pass
