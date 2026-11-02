import re
from typing import Protocol

import requests

from app.schemas.consultas_cadastro import (
    ConsultaCadastroResponse,
    normalizar_cnpj,
)


_TIMEOUT = (3.05, 10)
_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


class ConsultaCadastroError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ConsultaCNPJAdapter(Protocol):
    fonte: str

    def consultar(self, cnpj: str) -> ConsultaCadastroResponse:
        ...


class ConsultaCEPAdapter(Protocol):
    fonte: str

    def consultar(self, cep: str) -> ConsultaCadastroResponse:
        ...


def _buscar_json(url: str):
    try:
        response = requests.get(url, timeout=_TIMEOUT, allow_redirects=False)
    except requests.exceptions.Timeout as exc:
        raise ConsultaCadastroError(
            503, "Provedor de consulta temporariamente indisponível."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ConsultaCadastroError(
            503, "Provedor de consulta temporariamente indisponível."
        ) from exc

    if response.status_code == 404:
        raise ConsultaCadastroError(404, "Cadastro não encontrado no provedor.")
    if response.status_code != 200:
        status = 503 if response.status_code >= 500 else 502
        raise ConsultaCadastroError(
            status, "Provedor de consulta retornou uma resposta inválida."
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ConsultaCadastroError(
            502, "Provedor de consulta retornou dados inválidos."
        ) from exc
    if not isinstance(payload, dict):
        raise ConsultaCadastroError(502, "Provedor de consulta retornou dados inválidos.")
    return payload


def _texto(payload, key: str, limite: int):
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConsultaCadastroError(502, "Provedor retornou campo cadastral inválido.")
    value = value.strip()
    if not value:
        return None
    if len(value) > limite:
        raise ConsultaCadastroError(502, "Provedor retornou campo cadastral inválido.")
    return value


def _cep_normalizado(payload, key: str):
    value = _texto(payload, key, 10)
    if value is None:
        return None
    if not re.fullmatch(r"[0-9.\-/\s]+", value):
        raise ConsultaCadastroError(502, "Provedor retornou CEP inválido.")
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        raise ConsultaCadastroError(502, "Provedor retornou CEP inválido.")
    return digits


def _uf_normalizada(payload, key: str):
    value = _texto(payload, key, 2)
    if value is None:
        return None
    value = value.upper()
    if value not in _UFS:
        raise ConsultaCadastroError(502, "Provedor retornou UF inválida.")
    return value


def _resposta(dados: dict, fonte: str):
    try:
        return ConsultaCadastroResponse(
            dados={key: value for key, value in dados.items() if value is not None},
            fonte=fonte,
        )
    except (TypeError, ValueError) as exc:
        raise ConsultaCadastroError(
            502, "Provedor retornou dados cadastrais inválidos."
        ) from exc


def _inscricao_estadual_ativa(payload, uf_empresa):
    registros = payload.get("inscricoes_estaduais")
    if registros is None:
        return None
    if not isinstance(registros, list):
        raise ConsultaCadastroError(502, "Provedor retornou dados cadastrais inválidos.")

    elegiveis = []
    for registro in registros:
        if not isinstance(registro, dict):
            raise ConsultaCadastroError(502, "Provedor retornou dados cadastrais inválidos.")
        inscricao = _texto(registro, "inscricao_estadual", 80)
        uf = _uf_normalizada(registro, "uf")
        ativa = registro.get("ativo")
        if ativa is not None and not isinstance(ativa, bool):
            raise ConsultaCadastroError(502, "Provedor retornou dados cadastrais inválidos.")
        if ativa is True and uf_empresa is not None and uf == uf_empresa and inscricao:
            elegiveis.append(inscricao)
    return elegiveis[0] if len(elegiveis) == 1 else None


class BrasilApiCNPJAdapter:
    fonte = "brasilapi"
    base_url = "https://brasilapi.com.br/api/cnpj/v1/"

    def consultar(self, cnpj: str) -> ConsultaCadastroResponse:
        payload = _buscar_json(f"{self.base_url}{cnpj}")
        returned_cnpj = _texto(payload, "cnpj", 18)
        if returned_cnpj is None or normalizar_cnpj(returned_cnpj) != cnpj:
            raise ConsultaCadastroError(502, "Provedor retornou um CNPJ divergente.")

        uf = _uf_normalizada(payload, "uf")
        dados = {
            "razao_social": _texto(payload, "razao_social", 255),
            "nome_fantasia": _texto(payload, "nome_fantasia", 255),
            "situacao_cadastral": (
                _texto(payload, "descricao_situacao_cadastral", 100)
                or _texto(payload, "situacao_cadastral", 100)
            ),
            "email": (_texto(payload, "email", 255) or "").lower() or None,
            "telefone_comercial": _texto(payload, "ddd_telefone_1", 50),
            "inscricao_estadual": _inscricao_estadual_ativa(payload, uf),
            "cep": _cep_normalizado(payload, "cep"),
            "logradouro": _texto(payload, "logradouro", 255),
            "numero": _texto(payload, "numero", 30),
            "complemento": _texto(payload, "complemento", 255),
            "bairro": _texto(payload, "bairro", 100),
            "cidade": _texto(payload, "municipio", 150),
            "estado": uf,
        }
        return _resposta(dados, self.fonte)


class ViaCepAdapter:
    fonte = "viacep"
    base_url = "https://viacep.com.br/ws/"

    def consultar(self, cep: str) -> ConsultaCadastroResponse:
        payload = _buscar_json(f"{self.base_url}{cep}/json/")
        if payload.get("erro") is True:
            raise ConsultaCadastroError(404, "CEP não encontrado no provedor.")
        returned_cep = _cep_normalizado(payload, "cep")
        if returned_cep is None or returned_cep != cep:
            raise ConsultaCadastroError(502, "Provedor retornou um CEP divergente.")
        dados = {
            "cep": returned_cep,
            "logradouro": _texto(payload, "logradouro", 255),
            "bairro": _texto(payload, "bairro", 100),
            "cidade": _texto(payload, "localidade", 150),
            "estado": _uf_normalizada(payload, "uf"),
        }
        return _resposta(dados, self.fonte)


_CNPJ_ADAPTERS: dict[str, ConsultaCNPJAdapter] = {
    "brasilapi": BrasilApiCNPJAdapter(),
}
_CEP_ADAPTERS: dict[str, ConsultaCEPAdapter] = {
    "viacep": ViaCepAdapter(),
}


def obter_adapter_cnpj(provedor: str) -> ConsultaCNPJAdapter:
    adapter = _CNPJ_ADAPTERS.get(provedor)
    if adapter is None:
        raise ConsultaCadastroError(503, "Provedor de consulta de CNPJ não configurado.")
    return adapter


def obter_adapter_cep(provedor: str) -> ConsultaCEPAdapter:
    adapter = _CEP_ADAPTERS.get(provedor)
    if adapter is None:
        raise ConsultaCadastroError(503, "Provedor de consulta de CEP não configurado.")
    return adapter
