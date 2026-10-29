from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator


def _texto_obrigatorio(valor: str) -> str:
    valor = (valor or "").strip()
    if not valor:
        raise ValueError("Campo obrigatorio.")
    return valor


def _texto_opcional(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class _Out(BaseModel):
    id: int
    empresa_id: int
    ativo: bool
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        orm_mode = True


# ---------------- Contas financeiras ----------------
TIPOS_CONTA = ("BANCO", "CAIXA")


class ContaFinanceiraCreate(BaseModel):
    nome: str = Field(..., max_length=120)
    tipo: str = "BANCO"
    banco: Optional[str] = Field(None, max_length=120)
    agencia: Optional[str] = Field(None, max_length=30)
    numero_conta: Optional[str] = Field(None, max_length=40)
    saldo_inicial: Decimal = Decimal("0")
    ativo: bool = True
    observacao: Optional[str] = None

    _nome = validator("nome", allow_reuse=True)(_texto_obrigatorio)
    _opc = validator("banco", "agencia", "numero_conta", "observacao", allow_reuse=True)(_texto_opcional)

    @validator("tipo")
    def _tipo(cls, v):
        v = (v or "").strip().upper()
        if v not in TIPOS_CONTA:
            raise ValueError(f"Tipo deve ser um de: {', '.join(TIPOS_CONTA)}.")
        return v


class ContaFinanceiraUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=120)
    tipo: Optional[str] = None
    banco: Optional[str] = Field(None, max_length=120)
    agencia: Optional[str] = Field(None, max_length=30)
    numero_conta: Optional[str] = Field(None, max_length=40)
    saldo_inicial: Optional[Decimal] = None
    ativo: Optional[bool] = None
    observacao: Optional[str] = None

    _nome = validator("nome", allow_reuse=True)(lambda v: _texto_obrigatorio(v) if v is not None else v)
    _opc = validator("banco", "agencia", "numero_conta", "observacao", allow_reuse=True)(_texto_opcional)

    @validator("tipo")
    def _tipo(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if v not in TIPOS_CONTA:
            raise ValueError(f"Tipo deve ser um de: {', '.join(TIPOS_CONTA)}.")
        return v


class ContaFinanceiraOut(_Out):
    nome: str
    tipo: str
    banco: Optional[str] = None
    agencia: Optional[str] = None
    numero_conta: Optional[str] = None
    saldo_inicial: Decimal
    observacao: Optional[str] = None


# ---------------- Formas de pagamento ----------------
TIPOS_FORMA = ("DINHEIRO", "PIX", "BOLETO", "CARTAO", "TRANSFERENCIA", "OUTRO")


def _tipo_forma(v):
    if v is None:
        return v
    v = v.strip().upper()
    if v not in TIPOS_FORMA:
        raise ValueError(f"Tipo deve ser um de: {', '.join(TIPOS_FORMA)}.")
    return v


DISPONIVEL_PARA = ("PAGAR", "RECEBER", "AMBOS")


def _disponivel_para(v):
    if v is None:
        return v
    v = v.strip().upper()
    if v not in DISPONIVEL_PARA:
        raise ValueError(f"Disponível para deve ser um de: {', '.join(DISPONIVEL_PARA)}.")
    return v


class FormaPagamentoCreate(BaseModel):
    nome: str = Field(..., max_length=80)
    tipo: str = "OUTRO"
    conta_financeira_id: Optional[int] = None
    disponivel_para: str = "AMBOS"
    ativo: bool = True

    _nome = validator("nome", allow_reuse=True)(_texto_obrigatorio)
    _tipo = validator("tipo", allow_reuse=True)(_tipo_forma)
    _disp = validator("disponivel_para", allow_reuse=True)(_disponivel_para)


class FormaPagamentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=80)
    tipo: Optional[str] = None
    conta_financeira_id: Optional[int] = None
    disponivel_para: Optional[str] = None
    ativo: Optional[bool] = None

    _nome = validator("nome", allow_reuse=True)(lambda v: _texto_obrigatorio(v) if v is not None else v)
    _tipo = validator("tipo", allow_reuse=True)(_tipo_forma)
    _disp = validator("disponivel_para", allow_reuse=True)(_disponivel_para)


class FormaPagamentoOut(_Out):
    nome: str
    tipo: str
    conta_financeira_id: Optional[int] = None
    disponivel_para: str


# ---------------- Plano de contas ----------------
TIPOS_PLANO = ("RECEITA", "DESPESA")


def _tipo_plano(v):
    if v is None:
        return v
    v = v.strip().upper()
    if v not in TIPOS_PLANO:
        raise ValueError(f"Tipo deve ser um de: {', '.join(TIPOS_PLANO)}.")
    return v


class PlanoContaCreate(BaseModel):
    codigo: str = Field(..., max_length=30)
    nome: str = Field(..., max_length=120)
    tipo: str
    pai_id: Optional[int] = None
    ativo: bool = True

    _cod = validator("codigo", "nome", allow_reuse=True)(_texto_obrigatorio)
    _tipo = validator("tipo", allow_reuse=True)(_tipo_plano)


class PlanoContaUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=30)
    nome: Optional[str] = Field(None, max_length=120)
    tipo: Optional[str] = None
    pai_id: Optional[int] = None
    ativo: Optional[bool] = None

    _cod = validator("codigo", "nome", allow_reuse=True)(lambda v: _texto_obrigatorio(v) if v is not None else v)
    _tipo = validator("tipo", allow_reuse=True)(_tipo_plano)


class PlanoContaOut(_Out):
    codigo: str
    nome: str
    tipo: str
    pai_id: Optional[int] = None


# ---------------- Situações financeiras ----------------
TIPOS_SITUACAO = ("RECEBER", "PAGAR", "AMBOS")


def _tipo_situacao(v):
    if v is None:
        return v
    v = v.strip().upper()
    if v not in TIPOS_SITUACAO:
        raise ValueError(f"Tipo deve ser um de: {', '.join(TIPOS_SITUACAO)}.")
    return v


class SituacaoFinanceiraCreate(BaseModel):
    nome: str = Field(..., max_length=80)
    tipo: str = "AMBOS"
    quitado: bool = False
    padrao: bool = False
    ativo: bool = True

    _nome = validator("nome", allow_reuse=True)(_texto_obrigatorio)
    _tipo = validator("tipo", allow_reuse=True)(_tipo_situacao)


class SituacaoFinanceiraUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=80)
    tipo: Optional[str] = None
    quitado: Optional[bool] = None
    padrao: Optional[bool] = None
    ativo: Optional[bool] = None

    _nome = validator("nome", allow_reuse=True)(lambda v: _texto_obrigatorio(v) if v is not None else v)
    _tipo = validator("tipo", allow_reuse=True)(_tipo_situacao)


class SituacaoFinanceiraOut(_Out):
    nome: str
    tipo: str
    quitado: bool
    padrao: bool


# ---------------- Centros de custo ----------------
class CentroCustoCreate(BaseModel):
    nome: str = Field(..., max_length=120)
    observacao: Optional[str] = None
    ativo: bool = True

    _nome = validator("nome", allow_reuse=True)(_texto_obrigatorio)
    _obs = validator("observacao", allow_reuse=True)(_texto_opcional)


class CentroCustoUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=120)
    observacao: Optional[str] = None
    ativo: Optional[bool] = None

    _nome = validator("nome", allow_reuse=True)(lambda v: _texto_obrigatorio(v) if v is not None else v)
    _obs = validator("observacao", allow_reuse=True)(_texto_opcional)


class CentroCustoOut(_Out):
    nome: str
    observacao: Optional[str] = None
