"""Cadastro do A1 da empresa em homologação, com cifragem antes da gravação."""
from __future__ import annotations

from base64 import b64decode
from json import loads
import os

from cryptography.exceptions import UnsupportedAlgorithm
from fastapi import HTTPException

from app.services.fiscal_cadastros import _empresa, exigir_admin
from app.services.fiscal_certificado_a1 import (
    MAX_PFX_BYTES,
    MAX_SENHA_BYTES,
    CertificadoA1Invalido,
    conferir_pfx_a1_local,
    status_a1_empresa,
)
from app.services.fiscal_cofre_a1 import CofreIndisponivel, proteger_a1
from app.services.fiscal_cofre_a1_repository import certificado_armazenado, guardar_envelope_cifrado
from app.services.fiscal_importacao_a1_lab import EMPRESA_LAB
from app.services.fiscal_kms_aws import criar_provedor_kms_staging, situacao_kms_aws
from app.tenant.context import TenantOrigin

MAX_CORPO = 4 * ((MAX_PFX_BYTES + 2) // 3) + 2048


def importacao_empresa_disponivel(tenant) -> bool:
    """A disponibilidade exige ambiente autenticado e configuração OIDC do cofre."""
    return (
        os.getenv("SMARTTEC_FISCAL_A1_IMPORTACAO_EMPRESA") == "1"
        and tenant.origem is TenantOrigin.AUTHENTICATION
        and type(tenant.empresa_id) is int
        and tenant.empresa_id > 0
        and tenant.empresa_id != EMPRESA_LAB
        and situacao_kms_aws() == "CONFIGURACAO_OIDC_DETECTADA_NAO_VERIFICADA"
    )


def status_importacao_empresa(db, tenant) -> dict:
    status = status_a1_empresa(db, tenant)
    disponivel = importacao_empresa_disponivel(tenant)
    status["importacao_habilitada"] = disponivel
    if disponivel:
        armazenado = certificado_armazenado(db, tenant)
        status["situacao"] = "CADASTRADO" if armazenado else "NAO_CONFIGURADO"
        status["cofre_configurado"] = True
        status["certificado_armazenado"] = armazenado
        status["aviso"] = "Emissão de NF-e ainda indisponível."
    return status


def exigir_importacao_disponivel(tenant) -> None:
    if not importacao_empresa_disponivel(tenant):
        raise HTTPException(404, "Importação de certificado indisponível.")


def importar_certificado_empresa(db, tenant, corpo: bytearray) -> dict:
    exigir_importacao_disponivel(tenant)
    exigir_admin(db, tenant)
    try:
        if not 0 < len(corpo) <= MAX_CORPO:
            raise ValueError
        dados = loads(corpo)
        if not isinstance(dados, dict) or dados.keys() != {"pfx", "senha"}:
            raise ValueError
        pfx_b64, senha_texto = dados["pfx"], dados["senha"]
        if not isinstance(pfx_b64, str) or not isinstance(senha_texto, str):
            raise ValueError
        pfx = b64decode(pfx_b64, validate=True)
        senha = senha_texto.encode("utf-8")
        if not 0 < len(pfx) <= MAX_PFX_BYTES or not 0 < len(senha) <= MAX_SENHA_BYTES:
            raise ValueError
    except (ValueError, RecursionError):
        raise HTTPException(422, "Confira o arquivo do certificado A1 e a senha.") from None

    # A identificação do emitente não muda entre verificação e gravação.
    empresa = _empresa(db, tenant, bloquear=True)
    try:
        validacao = conferir_pfx_a1_local(pfx, senha, cnpj_emitente=empresa.documento)
    except (CertificadoA1Invalido, UnsupportedAlgorithm):
        raise HTTPException(422, "Confira se o certificado A1 está válido, a senha está correta e o CNPJ é da empresa.") from None

    try:
        envelope = proteger_a1(empresa.id, pfx, senha, criar_provedor_kms_staging())
    except CofreIndisponivel:
        raise HTTPException(503, "Não foi possível proteger o certificado. Tente novamente mais tarde.") from None

    guardar_envelope_cifrado(db, tenant, envelope)
    return {
        "certificado_armazenado": True,
        "validade_ate": validacao["validade_ate"],
        "emissao_habilitada": False,
    }
