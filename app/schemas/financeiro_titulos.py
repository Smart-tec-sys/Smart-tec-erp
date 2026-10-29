from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator

LIMITE_VALOR = Decimal("9999999999.99")  # coluna legada `valor` e NUMERIC(12,2)


def _texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class _Campos(BaseModel):
    @validator("descricao", "categoria", "observacao", check_fields=False)
    def _limpar(cls, v):
        return _texto(v)

    @validator("valor_original", "desconto", "juros", check_fields=False)
    def _valores(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("Valor nao pode ser negativo.")
        if v > LIMITE_VALOR:
            raise ValueError("Valor acima do limite permitido.")
        return v.quantize(Decimal("0.01"))

    @validator("tipo", check_fields=False)
    def _tipo(cls, v):
        v = (v or "").strip().upper()
        if v not in ("R", "P"):
            raise ValueError("Tipo deve ser R (receber) ou P (pagar).")
        return v


class TituloCreate(_Campos):
    tipo: str
    descricao: str = Field(..., max_length=200)
    competencia: Optional[date] = None
    valor_original: Decimal
    desconto: Decimal = Decimal("0")
    juros: Decimal = Decimal("0")
    vencimento: date
    cliente_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    conta_financeira_id: Optional[int] = None
    forma_pagamento_id: Optional[int] = None
    plano_conta_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    situacao_financeira_id: Optional[int] = None
    categoria: Optional[str] = Field(None, max_length=100)
    observacao: Optional[str] = None

    @validator("descricao")
    def _descricao(cls, v):
        if not v:
            raise ValueError("Informe a descricao.")
        return v


class TituloUpdate(_Campos):
    """Somente metadados financeiros. Nao altera tipo, status nem baixa."""

    descricao: Optional[str] = Field(None, max_length=200)
    competencia: Optional[date] = None
    valor_original: Optional[Decimal] = None
    desconto: Optional[Decimal] = None
    juros: Optional[Decimal] = None
    vencimento: Optional[date] = None
    cliente_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    conta_financeira_id: Optional[int] = None
    forma_pagamento_id: Optional[int] = None
    plano_conta_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    situacao_financeira_id: Optional[int] = None
    categoria: Optional[str] = Field(None, max_length=100)
    observacao: Optional[str] = None

    @validator("descricao")
    def _descricao(cls, v):
        if v is not None and not v:
            raise ValueError("Informe a descricao.")
        return v


class TituloOut(BaseModel):
    id: int
    empresa_id: Optional[int] = None
    tipo: str
    descricao: str
    competencia: Optional[date] = None
    valor_original: Optional[Decimal] = None
    desconto: Decimal = Decimal("0")
    juros: Decimal = Decimal("0")
    valor: Decimal
    valor_pago: Decimal = Decimal("0")
    saldo: Decimal = Decimal("0")
    vencimento: date
    pagamento: Optional[date] = None
    data_baixa: Optional[date] = None
    status: Optional[str] = None
    cliente_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    pedido_id: Optional[int] = None
    conta_financeira_id: Optional[int] = None
    forma_pagamento_id: Optional[int] = None
    plano_conta_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    situacao_financeira_id: Optional[int] = None
    categoria: Optional[str] = None
    observacao: Optional[str] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    parcelamento_grupo: Optional[str] = None
    recorrente: bool = False
    recorrencia_grupo: Optional[str] = None
    criado_em: Optional[datetime] = None
    vinculado: bool = False
    origem: str = "MANUAL"
    cliente_nome: Optional[str] = None
    fornecedor_nome: Optional[str] = None
    pedido_numero: Optional[str] = None
    qtd_baixas: int = 0
    qtd_baixas_total: int = 0
    pode_excluir: bool = False
    pode_baixar: bool = False

    class Config:
        orm_mode = True

class BaixaCreate(BaseModel):
    data_baixa: date
    valor: Decimal
    juros: Decimal = Decimal("0")
    desconto: Decimal = Decimal("0")
    conta_financeira_id: Optional[int] = None
    forma_pagamento_id: Optional[int] = None
    observacao: Optional[str] = None

    @validator("valor")
    def _valor(cls, v):
        if v <= 0:
            raise ValueError("O valor da baixa deve ser maior que zero.")
        if v > LIMITE_VALOR:
            raise ValueError("Valor acima do limite permitido.")
        return v.quantize(Decimal("0.01"))

    @validator("juros", "desconto")
    def _extras(cls, v):
        if v < 0:
            raise ValueError("Valor nao pode ser negativo.")
        if v > LIMITE_VALOR:
            raise ValueError("Valor acima do limite permitido.")
        return v.quantize(Decimal("0.01"))


class BaixaOut(BaseModel):
    id: int
    empresa_id: int
    financeiro_id: int
    data_baixa: date
    valor: Decimal
    juros: Decimal
    desconto: Decimal
    conta_financeira_id: Optional[int] = None
    forma_pagamento_id: Optional[int] = None
    observacao: Optional[str] = None
    estornada_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    ativa: bool = True

    class Config:
        orm_mode = True


class BaixaResultado(BaseModel):
    baixa: BaixaOut
    titulo: TituloOut


class Cartao(BaseModel):
    quantidade: int = 0
    total: Decimal = Decimal("0")


class IndicadoresOut(BaseModel):
    total_periodo: Cartao
    vencidos: Cartao
    vencem_hoje: Cartao
    a_vencer: Cartao
    quitados: Cartao