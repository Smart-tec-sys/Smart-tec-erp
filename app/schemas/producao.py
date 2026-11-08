from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, StrictBool

StatusProducao = Literal["AGUARDANDO", "CORTE", "MONTAGEM", "CONFERENCIA", "CONCLUIDA"]


class ConfirmarProducaoInput(BaseModel):
    confirmar_fabricacao: StrictBool

    class Config:
        extra = "forbid"


class AtualizarPecaInput(BaseModel):
    ambiente: str | None = Field(default=None, max_length=200)
    largura: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    altura: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    quantidade: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    observacoes: str | None = Field(default=None, max_length=5000)
    especificacoes_fabricacao: dict[str, str] | None = None
    modo_fabricacao: Literal["AUTOMATICA", "MANUAL_SUPERVISIONADA"] | None = None
    justificativa: str = Field(min_length=5, max_length=1000)

    class Config:
        extra = "forbid"


class ComponenteProducaoInput(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: Decimal = Field(gt=0, allow_inf_nan=False)
    unidade: str = Field(min_length=1, max_length=50)
    comprimento_corte: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    custo_unitario: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    observacoes: str = Field(default="", max_length=2000)
    justificativa: str = Field(min_length=5, max_length=1000)

    class Config:
        extra = "forbid"


class JustificativaProducaoInput(BaseModel):
    justificativa: str = Field(min_length=5, max_length=1000)

    class Config:
        extra = "forbid"


class ConferirPecaInput(BaseModel):
    confirmar_conferencia: StrictBool
    justificativa: str = Field(min_length=5, max_length=1000)

    class Config:
        extra = "forbid"


class AvancarPecaInput(BaseModel):
    status_atual: StatusProducao
    status: StatusProducao

    class Config:
        extra = "forbid"
