import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, StrictStr, ValidationInfo, field_validator


def normalizar_cnpj(valor: str) -> str:
    if not isinstance(valor, str) or not re.fullmatch(r"[0-9A-Za-z./\-\s]+", valor.strip()):
        return ""
    return re.sub(r"[./\-\s]", "", valor).upper()


def _digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def cnpj_valido(valor: str) -> bool:
    documento = normalizar_cnpj(valor)
    if (
        len(documento) != 14
        or not re.fullmatch(r"[A-Z0-9]{14}", documento)
        or len(set(documento)) == 1
    ):
        return False
    for tamanho in (12, 13):
        soma = 0
        peso = 2
        for caractere in reversed(documento[:tamanho]):
            soma += (ord(caractere) - ord("0")) * peso
            peso = 2 if peso == 9 else peso + 1
        resto = soma % 11
        verificador = 0 if resto < 2 else 11 - resto
        if verificador != ord(documento[tamanho]) - ord("0"):
            return False
    return True


class ConsultaCNPJInput(BaseModel):
    documento: str

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, value):
        documento = normalizar_cnpj(value)
        if not cnpj_valido(documento):
            raise ValueError("Informe um CNPJ válido.")
        return documento

    class Config:
        extra = "forbid"


class ConsultaCEPInput(BaseModel):
    cep: str

    @field_validator("cep")
    @classmethod
    def validar_cep(cls, value):
        if not re.fullmatch(r"[0-9.\-/\s]+", value.strip()):
            raise ValueError("Informe um CEP com oito dígitos.")
        cep = _digitos(value)
        if len(cep) != 8:
            raise ValueError("Informe um CEP com oito dígitos.")
        return cep

    class Config:
        extra = "forbid"


class ConsultaCadastroResponse(BaseModel):
    class Dados(BaseModel):
        razao_social: Optional[StrictStr] = None
        nome_fantasia: Optional[StrictStr] = None
        situacao_cadastral: Optional[StrictStr] = None
        email: Optional[StrictStr] = None
        telefone_comercial: Optional[StrictStr] = None
        inscricao_estadual: Optional[StrictStr] = None
        cep: Optional[StrictStr] = None
        logradouro: Optional[StrictStr] = None
        numero: Optional[StrictStr] = None
        complemento: Optional[StrictStr] = None
        bairro: Optional[StrictStr] = None
        cidade: Optional[StrictStr] = None
        estado: Optional[StrictStr] = None

        @field_validator("razao_social", "nome_fantasia", "cidade", "bairro", "logradouro", "complemento", "numero", "inscricao_estadual", "email", "telefone_comercial", "situacao_cadastral")
        @classmethod
        def validar_tipos_comprimentos(cls, value, info: ValidationInfo):
            limits = {
                "razao_social": 255, "nome_fantasia": 255, "situacao_cadastral": 100,
                "email": 255, "telefone_comercial": 50, "inscricao_estadual": 80,
                "logradouro": 255, "numero": 30, "complemento": 255, "bairro": 100,
                "cidade": 150,
            }
            if value is not None and len(value) > limits[info.field_name]:
                raise ValueError(f"{info.field_name} excede o limite permitido.")
            return value

        @field_validator("cep")
        @classmethod
        def validar_cep(cls, value):
            if value is not None and not re.fullmatch(r"\d{8}", value):
                raise ValueError("CEP retornado pelo provedor é inválido.")
            return value

        @field_validator("estado")
        @classmethod
        def validar_uf(cls, value):
            if value is not None and value not in {
                "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
                "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
                "RS", "RO", "RR", "SC", "SP", "SE", "TO",
            }:
                raise ValueError("UF retornada pelo provedor é inválida.")
            return value

        class Config:
            extra = "forbid"

    dados: Dados
    fonte: Literal["brasilapi", "viacep"]
    consultado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Config:
        extra = "forbid"
