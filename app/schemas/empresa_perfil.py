"""Dados públicos da empresa usados nas propostas comerciais."""
import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PerfilPublicoEmpresa(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    logradouro: str | None = Field(default=None, max_length=255)
    numero: str | None = Field(default=None, max_length=30)
    complemento: str | None = Field(default=None, max_length=150)
    bairro: str | None = Field(default=None, max_length=100)
    cidade: str | None = Field(default=None, max_length=100)
    estado: str | None = Field(default=None, max_length=2)
    cep: str | None = Field(default=None, max_length=9)
    telefone_comercial: str | None = Field(default=None, max_length=30)
    telefone_celular: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    site: str | None = Field(default=None, max_length=255)

    @field_validator("*", mode="before")
    @classmethod
    def limpar_texto(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, value):
        if value is not None and not re.fullmatch(r"[A-Za-z]{2}", value):
            raise ValueError("estado deve conter a sigla de duas letras")
        return value.upper() if value else None

    @field_validator("cep")
    @classmethod
    def validar_cep(cls, value):
        if value is not None and not re.fullmatch(r"\d{5}-?\d{3}", value):
            raise ValueError("CEP deve conter oito dígitos")
        return value

    @field_validator("telefone_comercial", "telefone_celular")
    @classmethod
    def validar_telefone(cls, value):
        if value is not None and (not re.fullmatch(r"[+()\d\s.-]+", value) or not 10 <= len(re.sub(r"\D", "", value)) <= 13):
            raise ValueError("telefone deve conter de dez a treze dígitos")
        return value

    @field_validator("email")
    @classmethod
    def validar_email(cls, value):
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("e-mail inválido")
        return value

    @field_validator("site")
    @classmethod
    def validar_site(cls, value):
        if value is None:
            return None
        candidate = value if "://" in value else "https://" + value
        parsed = urlsplit(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or "." not in parsed.hostname or parsed.username or parsed.password or re.search(r"\s", candidate):
            raise ValueError("site deve ser um endereço HTTP ou HTTPS válido")
        return candidate


class EmpresaPerfilUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    nome: str = Field(min_length=1, max_length=255)
    nome_fantasia: str | None = Field(default=None, max_length=255)
    documento: str | None = Field(default=None, max_length=50)
    perfil_publico: PerfilPublicoEmpresa

    @field_validator("nome_fantasia", "documento", mode="before")
    @classmethod
    def limpar_opcional(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, value):
        if value is not None and (not re.fullmatch(r"[\d./-]+", value) or len(re.sub(r"\D", "", value)) not in {11, 14}):
            raise ValueError("documento deve conter CPF ou CNPJ com onze ou quatorze dígitos")
        return value
