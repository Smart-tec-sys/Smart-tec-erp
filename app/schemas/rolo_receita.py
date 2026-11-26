from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class FaixaTuboRolo(DadosReceitaRolo):
    diametro_mm: Literal[32, 38, 41, 43, 53, 56, 70]
    largura_min_m: float = Field(ge=0, allow_inf_nan=False)
    largura_max_m: float = Field(gt=0, allow_inf_nan=False)
    altura_max_m: float = Field(gt=0, allow_inf_nan=False)
    origem: str = Field(min_length=5)

    @model_validator(mode="after")
    def conferir_limites(self):
        if self.largura_max_m <= self.largura_min_m:
            raise ValueError("Faixa de largura inválida na receita Rolô.")
        return self


class AcessorioComandoRolo(DadosReceitaRolo):
    insumo: InsumoReceitaRolo
    tipo: Literal["CONTROLE_RF", "BOTAO", "INTERRUPTOR"]
    canais: Literal[1, 6, 16] | None = None

    @model_validator(mode="after")
    def conferir_canais(self):
        if (self.tipo == "CONTROLE_RF") != (self.canais is not None):
            raise ValueError("Controle RF exige canais; botão ou interruptor não usa canais.")
        if self.insumo.unidade_tecnica != "UN":
            raise ValueError("Acessório de comando deve ser cadastrado por unidade.")
        return self


class ConjuntoMotorRolo(DadosReceitaRolo):
    motor: InsumoReceitaRolo
    torque_nm: float = Field(gt=0, allow_inf_nan=False)
    tecnologia: Literal["RF", "WIFI_RF", "CONTATO_SECO"]
    tubos: dict[str, InsumoReceitaRolo]
    kits_motor: dict[str, InsumoReceitaRolo]
    faixas_tubo: list[FaixaTuboRolo] = Field(min_length=1)
    compatibilidades: dict[str, str] = Field(default_factory=dict)
    acessorios_comando: list[AcessorioComandoRolo] = Field(default_factory=list)
    capacidade_kg: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    peso_barra_kg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    peso_estimado_kg_m2: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    origem_carga: str | None = None

    @model_validator(mode="after")
    def conferir_acessorios(self):
        ids = [acessorio.insumo.produto_id for acessorio in self.acessorios_comando]
        if len(ids) != len(set(ids)):
            raise ValueError("Acessório de comando duplicado no motor.")
        for acessorio in self.acessorios_comando:
            if (self.tecnologia == "CONTATO_SECO") == (acessorio.tipo == "CONTROLE_RF"):
                raise ValueError("Tipo de acessório incompatível com a tecnologia do motor.")
        if set(self.tubos) != set(self.kits_motor):
            raise ValueError("Cada tubo do conjunto motorizado exige kit explicitamente vinculado.")
        for bitola, kit in self.kits_motor.items():
            diametro_tubo = int(bitola.removesuffix("mm")) if bitola.endswith("mm") else None
            if diametro_tubo not in {32, 38, 41, 43, 53, 56, 70}:
                raise ValueError("Bitola inválida no conjunto motorizado.")
            if (kit.diametro_mm not in (None, diametro_tubo)
                    and not self.compatibilidades.get(bitola, "").strip()):
                raise ValueError(
                    "Kit de diâmetro diferente exige compatibilidade explícita e sua fonte técnica."
                )
        if any(not origem.strip() for origem in self.compatibilidades.values()):
            raise ValueError("Compatibilidade de tubo exige fonte técnica.")
        return self


class ReceitaRolo(DadosReceitaRolo):
    versao: Literal[1]
    custeio_tecido: Literal["AREA_CORTE", "FAIXA_INTEGRAL_ML"] = "AREA_CORTE"
    acabamento: str = Field(min_length=1)
    cor_tecido: str = Field(min_length=1)
    largura_bobina_m: float = Field(gt=0, allow_inf_nan=False)
    tecido: InsumoReceitaRolo
    componentes: dict[str, InsumoReceitaRolo]
    tubos: dict[str, InsumoReceitaRolo]
    comandos: dict[str, InsumoReceitaRolo] = Field(default_factory=dict)
    # Sem faixas presumidas: motorização depende da aprovação do fornecedor.
    faixas_tubo: list[FaixaTuboRolo] = Field(default_factory=list)
    motores: dict[str, InsumoReceitaRolo] = Field(default_factory=dict)
    kits_motor: dict[str, InsumoReceitaRolo] = Field(default_factory=dict)
    conjuntos_motor: list[ConjuntoMotorRolo] = Field(default_factory=list)

    @model_validator(mode="after")
    def conferir_motores_unicos(self):
        ids = [conjunto.motor.produto_id for conjunto in self.conjuntos_motor]
        if len(ids) != len(set(ids)):
            raise ValueError("Motor duplicado na receita Rolô.")
        return self
