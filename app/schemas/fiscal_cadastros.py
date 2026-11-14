"""Cadastro fiscal V1: metadados, sem certificado e sem regras de emissão."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FiscalEmpresaDados(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inscricao_estadual: str | None = Field(default=None, max_length=20)
    inscricao_municipal: str | None = Field(default=None, max_length=30)
    cnae_principal: str | None = Field(default=None, pattern=r"^\d{7}$")
    regime_especial_tributacao: str | None = Field(default=None, max_length=80)
    informacoes_complementares: str | None = Field(default=None, max_length=2000)
    crt: Literal["1", "2", "3", "4"] | None = None
    uf: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    municipio_codigo_ibge: str | None = Field(default=None, pattern=r"^\d{7}$")
    cidade: str | None = Field(default=None, max_length=120)
    cep: str | None = Field(default=None, pattern=r"^\d{8}$")
    logradouro: str | None = Field(default=None, max_length=255)
    numero: str | None = Field(default=None, max_length=30)
    bairro: str | None = Field(default=None, max_length=120)
    complemento: str | None = Field(default=None, max_length=120)
    serie_nfe: int | None = Field(default=None, ge=1, le=899)
    ambiente: Literal["HOMOLOGACAO"] = "HOMOLOGACAO"

    @field_validator("inscricao_estadual", "inscricao_municipal", "regime_especial_tributacao", "informacoes_complementares", "cidade", "logradouro", "numero", "bairro", "complemento")
    @classmethod
    def normalizar_texto(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("uf")
    @classmethod
    def normalizar_uf(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("cep")
    @classmethod
    def normalizar_cep(cls, value):
        return value.replace("-", "").strip() if isinstance(value, str) else value


class FiscalEmpresaPatch(FiscalEmpresaDados):
    # PATCH parcial: somente campos explicitamente enviados são alterados.
    pass


class FiscalProdutoDados(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ncm: str | None = Field(default=None, pattern=r"^\d{8}$")
    cfop_padrao_saida: str | None = Field(default=None, pattern=r"^\d{4}$")
    cest: str | None = Field(default=None, pattern=r"^\d{7}$")
    origem_mercadoria: str | None = Field(default=None, pattern=r"^[0-8]$")
    cst_icms: str | None = Field(default=None, pattern=r"^\d{2}$")
    csosn: str | None = Field(default=None, pattern=r"^\d{3}$")
    cst_pis: str | None = Field(default=None, pattern=r"^\d{2}$")
    cst_cofins: str | None = Field(default=None, pattern=r"^\d{2}$")
    cst_ibs_cbs: str | None = Field(default=None, pattern=r"^\d{3}$")
    cclass_trib_ibs_cbs: str | None = Field(default=None, pattern=r"^\d{6}$")

    @field_validator("ncm", "cfop_padrao_saida", "cest", "origem_mercadoria", "cst_icms",
                     "csosn", "cst_pis", "cst_cofins", "cst_ibs_cbs", "cclass_trib_ibs_cbs")
    @classmethod
    def aparar_codigo(cls, value):
        return value.strip() if isinstance(value, str) else value


class FiscalProdutoPatch(FiscalProdutoDados):
    pass
