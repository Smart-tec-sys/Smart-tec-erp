import os
import re
import logging

from app.schemas.consultas_cadastro import (
    ConsultaCadastroResponse,
    normalizar_cnpj,
)
from app.services.consultas_cadastro_adapters import (
    ConsultaCadastroError,
    CnpjaContatosAdapter,
    obter_adapter_cep,
    obter_adapter_cnpj,
)


def _provedor_configurado(setting: str, default: str, label: str):
    selected = os.getenv(setting, default).strip().lower()
    if selected == "off":
        raise ConsultaCadastroError(503, f"Consulta de {label} desabilitada.")
    return selected


def _fallback_configurado():
    fallback = os.getenv("SMARTTEC_CNPJ_CONTATOS_FALLBACK", "cnpja").strip().lower()
    if fallback not in {"cnpja", "off"}:
        raise ConsultaCadastroError(503, "Provedor de enriquecimento não configurado.")
    return fallback


def _consultar_contatos(cnpj: str):
    try:
        contatos = CnpjaContatosAdapter().consultar(cnpj)
    except ConsultaCadastroError as exc:
        logging.getLogger(__name__).warning(
            "Enriquecimento cadastral indisponivel; fonte=cnpja; status=%s",
            exc.status_code,
        )
        raise
    logging.getLogger(__name__).info(
        "Enriquecimento cadastral concluido; fonte=cnpja; campos=%s",
        ",".join(contatos) or "nenhum",
    )
    return contatos


def _recuperar_indisponibilidade(cnpj: str, falha: ConsultaCadastroError):
    logging.getLogger(__name__).warning(
        "Consulta cadastral indisponivel; fonte=brasilapi; status=%s",
        falha.status_code,
    )
    if _fallback_configurado() == "off":
        raise ConsultaCadastroError(
            falha.status_code,
            "BrasilAPI indisponível e fonte alternativa desabilitada. Continue o cadastro manualmente.",
        ) from falha
    try:
        contatos = _consultar_contatos(cnpj)
    except ConsultaCadastroError as exc:
        raise ConsultaCadastroError(
            exc.status_code,
            f"BrasilAPI indisponível; CNPJá não concluiu a consulta: {exc.detail} Continue o cadastro manualmente.",
        ) from exc
    if not contatos:
        raise ConsultaCadastroError(
            503,
            "BrasilAPI indisponível e CNPJá sem contatos disponíveis. Continue o cadastro manualmente.",
        )
    return ConsultaCadastroResponse(
        dados=contatos, fonte="cnpja",
        fontes_campos={campo: "cnpja" for campo in contatos},
        avisos=[
            "BrasilAPI temporariamente indisponível. Apenas contatos disponíveis na CNPJá foram recuperados; complete os demais campos manualmente."
        ],
    )


def consultar_cnpj(documento: str, *, enriquecer_contatos: bool = False) -> ConsultaCadastroResponse:
    cnpj = normalizar_cnpj(documento)
    provider = _provedor_configurado(
        "SMARTTEC_CNPJ_CONSULTA_PROVIDER", "brasilapi", "CNPJ"
    )
    adapter = obter_adapter_cnpj(provider)
    try:
        resposta = adapter.consultar(cnpj)
    except ConsultaCadastroError as exc:
        if not enriquecer_contatos or provider != "brasilapi" or exc.status_code not in {429, 503}:
            raise
        return _recuperar_indisponibilidade(cnpj, exc)
    if not enriquecer_contatos or provider != "brasilapi":
        return resposta
    campos = ("email", "telefone_comercial")
    ausentes = [campo for campo in campos if not getattr(resposta.dados, campo)]
    if not ausentes:
        return resposta
    dados = resposta.dados.model_dump(exclude_none=True)
    fontes = {campo: "brasilapi" for campo in dados}
    avisos = []
    fallback = _fallback_configurado()
    if fallback == "off":
        avisos.append("Enriquecimento de contatos desabilitado. Complete os dados manualmente.")
    else:
        try:
            contatos = _consultar_contatos(cnpj)
        except ConsultaCadastroError as exc:
            avisos.append(
                f"Enriquecimento CNPJá não concluído: {exc.detail} Os dados da BrasilAPI foram preservados."
            )
        else:
            recuperados = [campo for campo in ausentes if contatos.get(campo)]
            for campo in recuperados:
                dados[campo] = contatos[campo]
                fontes[campo] = "cnpja"
            if len(recuperados) != len(ausentes):
                avisos.append("CNPJá não forneceu todos os contatos ausentes. Complete os dados manualmente.")
    return ConsultaCadastroResponse(
        dados=dados, fonte=resposta.fonte, consultado_em=resposta.consultado_em,
        fontes_campos=fontes, avisos=avisos or None,
    )


def consultar_cep(cep: str) -> ConsultaCadastroResponse:
    cep = re.sub(r"\D", "", cep)
    if len(cep) != 8:
        raise ConsultaCadastroError(422, "Informe um CEP com oito dígitos.")
    provider = _provedor_configurado(
        "SMARTTEC_CEP_CONSULTA_PROVIDER", "viacep", "CEP"
    )
    adapter = obter_adapter_cep(provider)
    return adapter.consultar(cep)
