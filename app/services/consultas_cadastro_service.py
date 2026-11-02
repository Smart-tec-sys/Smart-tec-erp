import os
import re

from app.schemas.consultas_cadastro import (
    ConsultaCadastroResponse,
    normalizar_cnpj,
)
from app.services.consultas_cadastro_adapters import (
    ConsultaCadastroError,
    obter_adapter_cep,
    obter_adapter_cnpj,
)


def _provedor_configurado(setting: str, default: str, label: str):
    selected = os.getenv(setting, default).strip().lower()
    if selected == "off":
        raise ConsultaCadastroError(503, f"Consulta de {label} desabilitada.")
    return selected


def consultar_cnpj(documento: str) -> ConsultaCadastroResponse:
    cnpj = normalizar_cnpj(documento)
    provider = _provedor_configurado(
        "SMARTTEC_CNPJ_CONSULTA_PROVIDER", "brasilapi", "CNPJ"
    )
    adapter = obter_adapter_cnpj(provider)
    return adapter.consultar(cnpj)


def consultar_cep(cep: str) -> ConsultaCadastroResponse:
    cep = re.sub(r"\D", "", cep)
    if len(cep) != 8:
        raise ConsultaCadastroError(422, "Informe um CEP com oito dígitos.")
    provider = _provedor_configurado(
        "SMARTTEC_CEP_CONSULTA_PROVIDER", "viacep", "CEP"
    )
    adapter = obter_adapter_cep(provider)
    return adapter.consultar(cep)
