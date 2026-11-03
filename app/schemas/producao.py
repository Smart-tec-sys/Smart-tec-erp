from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

StatusProducao = Literal["AGUARDANDO", "CORTE", "MONTAGEM", "CONFERENCIA", "CONCLUIDA"]


class ConfirmarProducaoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmar_fabricacao: StrictBool


class AtualizarPecaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ambiente: str = Field(max_length=200)
    observacoes: str = Field(max_length=5000)


class AvancarPecaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status_atual: StatusProducao
    status: StatusProducao
