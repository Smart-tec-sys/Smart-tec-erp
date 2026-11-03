import re
import time
from collections import deque
from threading import Lock
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
    if response.status_code == 429:
        raise ConsultaCadastroError(429, "Limite de consultas do provedor atingido.")
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


def _telefones_cnpj(payload):
    telefones = []
    numeros = set()
    for key in ("ddd_telefone_1", "ddd_telefone_2"):
        telefone = _texto(payload, key, 50)
        if telefone:
            numero = re.sub(r"\D", "", telefone)
            if (numero or telefone) not in numeros:
                telefones.append(telefone)
                numeros.add(numero or telefone)
    return " / ".join(telefones) or None


def _logradouro_cnpj(payload):
    logradouro = _texto(payload, "logradouro", 255)
    tipo = _texto(payload, "descricao_tipo_de_logradouro", 100)
    if not logradouro or not tipo:
        return logradouro
    palavras = logradouro.casefold().split()
    prefixo = tipo.casefold().split()
    if palavras[:len(prefixo)] == prefixo:
        return logradouro
    return f"{tipo} {logradouro}"


def _situacao_cnpj(payload):
    descricao = _texto(payload, "descricao_situacao_cadastral", 100)
    if descricao:
        return descricao
    codigo = payload.get("situacao_cadastral")
    if codigo is None:
        return None
    situacoes = {1: "NULA", 2: "ATIVA", 3: "SUSPENSA", 4: "INAPTA", 8: "BAIXADA"}
    if isinstance(codigo, int) and not isinstance(codigo, bool):
        if codigo not in situacoes:
            raise ConsultaCadastroError(502, "Provedor retornou situação cadastral inválida.")
        return situacoes[codigo]
    texto = _texto(payload, "situacao_cadastral", 100)
    if texto and texto.isdecimal():
        if int(texto) not in situacoes:
            raise ConsultaCadastroError(502, "Provedor retornou situação cadastral inválida.")
        return situacoes[int(texto)]
    return texto


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
            "situacao_cadastral": _situacao_cnpj(payload),
            "email": (_texto(payload, "email", 255) or "").lower() or None,
            "telefone_comercial": _telefones_cnpj(payload),
            "inscricao_estadual": _inscricao_estadual_ativa(payload, uf),
            "cep": _cep_normalizado(payload, "cep"),
            "logradouro": _logradouro_cnpj(payload),
            "numero": _texto(payload, "numero", 30),
            "complemento": _texto(payload, "complemento", 255),
            "bairro": _texto(payload, "bairro", 100),
            "cidade": _texto(payload, "municipio", 150),
            "estado": uf,
        }
        return _resposta(dados, self.fonte)


class LimiteCnpja:
    # Compartilhado pelas threads do processo; o IP de saida deve ser exclusivo.
    def __init__(self):
        self._lock = Lock()
        self._consultas: deque[float] = deque()
        self._bloqueado_ate = 0.0

    def reservar(self):
        with self._lock:
            agora = time.monotonic()
            while self._consultas and self._consultas[0] <= agora - 60:
                self._consultas.popleft()
            if agora < self._bloqueado_ate or len(self._consultas) >= 5:
                raise ConsultaCadastroError(429, "Limite de enriquecimento atingido. Tente novamente em 60 segundos.")
            self._consultas.append(agora)

    def bloquear(self):
        with self._lock:
            self._bloqueado_ate = time.monotonic() + 60


_LIMITE_CNPJA = LimiteCnpja()


class CnpjaContatosAdapter:
    base_url = "https://open.cnpja.com/office/"

    def consultar(self, cnpj: str) -> dict[str, str]:
        _LIMITE_CNPJA.reservar()
        try:
            payload = _buscar_json(f"{self.base_url}{cnpj}")
        except ConsultaCadastroError as exc:
            if exc.status_code == 429:
                _LIMITE_CNPJA.bloquear()
            raise
        documento = _texto(payload, "taxId", 18)
        if documento is None or normalizar_cnpj(documento) != cnpj:
            raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou CNPJ divergente.")
        emails = payload.get("emails")
        phones = payload.get("phones")
        emails = [] if emails is None else emails
        phones = [] if phones is None else phones
        if not isinstance(emails, list) or not isinstance(phones, list):
            raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou contatos inválidos.")
        enderecos = set()
        for item in emails:
            if not isinstance(item, dict):
                raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou contatos inválidos.")
            email = _texto(item, "address", 255)
            if email:
                if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                    raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou e-mail inválido.")
                enderecos.add(email.lower())
        if len(enderecos) > 1:
            raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou e-mails ambíguos.")
        numeros = []
        for item in phones:
            if not isinstance(item, dict):
                raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou contatos inválidos.")
            area = _texto(item, "area", 2)
            numero = _texto(item, "number", 9)
            if area is None and numero is None:
                continue
            if area is None or numero is None or not re.fullmatch(r"\d{2}", area) or not re.fullmatch(r"\d{8,9}", numero):
                raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou telefone inválido.")
            telefone = area + numero
            if telefone not in numeros:
                numeros.append(telefone)
        contatos = {}
        if enderecos:
            contatos["email"] = next(iter(enderecos))
        if numeros:
            telefone = " / ".join(numeros)
            if len(telefone) > 50:
                raise ConsultaCadastroError(502, "Provedor de enriquecimento retornou telefones além do limite.")
            contatos["telefone_comercial"] = telefone
        return contatos


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
