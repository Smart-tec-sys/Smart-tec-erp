from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ParceiroCreate(BaseModel):
    nome: str
    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    percentual_padrao: Decimal = Decimal("0")
    observacao: Optional[str] = None


class RepresentanteCreate(BaseModel):
    nome: str
    parceiro_id: Optional[int] = None

    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

    tipo_rt_padrao: str = "PERCENTUAL"
    percentual_rt_padrao: Decimal = Decimal("0")
    valor_rt_padrao: Decimal = Decimal("0")

    observacao: Optional[str] = None


class RTCreate(BaseModel):
    pedido_id: int
    representante_id: int

    competencia: str
    vencimento: Optional[date] = None

    tipo_calculo: Optional[str] = None
    percentual: Optional[Decimal] = None
    valor_fixo: Optional[Decimal] = None

    observacao: Optional[str] = None


class RTPagamentoInput(BaseModel):
    pagamento: date

# ============================================================
# CARTEIRA DO PARCEIRO
# ============================================================

class ParceiroRepresentanteCreate(BaseModel):
    nome: str

    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None


class ParceiroClienteCreate(BaseModel):
    nome: str

    representante_parceiro_id: Optional[int] = None

    documento: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None

    cadastro_completo: bool = False