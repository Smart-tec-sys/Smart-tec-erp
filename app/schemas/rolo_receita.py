from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DadosReceitaRolo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InsumoReceitaRolo(DadosReceitaRolo):
    produto_id: int = Field(gt=0)
    codigo_interno: str = Field(min_length=1)
    unidade_tecnica: Literal["M2", "ML", "UN", "KIT"]
    preco_compra: float = Field(gt=0, allow_inf_nan=False)
    ipi_percentual: float | None = Field(ge=0, le=100, allow_inf_nan=False)
    unidades_por_compra: float = Field(gt=0, allow_inf_nan=False)
    origem: str = Field(min_length=5)
    base_preco: Literal["TABELA_2", "CUSTO_CADASTRADO"] = "TABELA_2"
    diametro_mm: int | None = Field(default=None, gt=0)


class ReceitaRolo(DadosReceitaRolo):
    versao: Literal[1]
    custeio_tecido: Literal["AREA_CORTE", "FAIXA_INTEGRAL_ML"] = "AREA_CORTE"
    acabamento: str = Field(min_length=1)
    cor_tecido: str = Field(min_length=1)
    largura_bobina_m: float = Field(gt=0, allow_inf_nan=False)
    tecido: InsumoReceitaRolo
    componentes: dict[str, InsumoReceitaRolo]
    tubos: dict[str, InsumoReceitaRolo]
    comandos: dict[str, InsumoReceitaRolo]
