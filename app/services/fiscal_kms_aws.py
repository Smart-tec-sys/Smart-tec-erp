"""AWS KMS adapter for A1 envelope keys — STAGING ONLY, disabled by default.

Boto3 SDK + Render managed OIDC credentials; no AWS long-lived access keys.
Only encrypts/decrypts random 32-byte DEKs. PFX and password never go to AWS.
AWS EncryptionContext contains non-secret tenant ID and purpose (CloudTrail visible).
No HTTP upload, certificate activation, or NF-e authorization is implemented.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping, Any

from app.services.fiscal_cofre_a1 import CofreIndisponivel, ProvedorKms

KEY_ARN = re.compile(r"^arn:aws:kms:([a-z0-9-]+):([0-9]{12}):key/([A-Za-z0-9-]{10,80})$")
ROLE_ARN = re.compile(r"^arn:aws:iam::[0-9]{12}:role/[A-Za-z0-9+=,.@_/-]+$")
CONTEXT = re.compile(rb"^smarttec:a1:tenant:([1-9][0-9]*):v1$")
PURPOSE = "smarttec-fiscal-a1-envelope-v1"


def _key_details(key_arn: str) -> tuple[str, str]:
    match = KEY_ARN.fullmatch(key_arn) if isinstance(key_arn, str) else None
    if match is None:
        raise CofreIndisponivel("AWS KMS requer ARN completo de chave simétrica.")
    return match.group(1), match.group(2)


def _encryption_context(contexto: bytes) -> dict[str, str]:
    match = CONTEXT.fullmatch(contexto) if isinstance(contexto, bytes) else None
    if match is None:
        raise CofreIndisponivel("Contexto criptográfico de empresa inválido.")
    return {"smarttec:purpose": PURPOSE, "smarttec:empresa_id": match.group(1).decode("ascii")}


class AwsKmsProvedor(ProvedorKms):
    """Implementação de contrato do cofre; cliente boto3 pode ser injetado em testes."""
    def __init__(self, *, key_arn: str, client: Any):
        _key_details(key_arn)
        if client is None or not callable(getattr(client, "encrypt", None)) or not callable(getattr(client, "decrypt", None)):
            raise CofreIndisponivel("Cliente AWS KMS não configurado.")
        self._arn = key_arn
        self._client = client

    def envelopar(self, dek: bytes, *, contexto: bytes) -> tuple[str, bytes]:
        if not isinstance(dek, bytes) or len(dek) != 32:
            raise CofreIndisponivel("Chave de dados A1 inválida.")
        ec = _encryption_context(contexto)
        try:
            response = self._client.encrypt(
                KeyId=self._arn,
                Plaintext=dek,
                EncryptionContext=ec,
                EncryptionAlgorithm="SYMMETRIC_DEFAULT",
            )
            wrapped = response["CiphertextBlob"]
            returned_key = response["KeyId"]
            if returned_key != self._arn or not isinstance(wrapped, bytes) or not 32 <= len(wrapped) <= 4096:
                raise CofreIndisponivel("Resposta criptográfica KMS inválida.")
            return self._arn, wrapped
        except CofreIndisponivel:
            raise
        except Exception as exc:
            raise CofreIndisponivel("Falha de cifragem AWS KMS.") from exc

    def desenvelopar(self, key_id: str, wrapped: bytes, *, contexto: bytes) -> bytes:
        # Reject wrong KMS ARN *before* requesting the AWS API.
        if key_id != self._arn or not isinstance(wrapped, bytes) or not 32 <= len(wrapped) <= 4096:
            raise CofreIndisponivel("Chave KMS ou envelope de dados não permitido.")
        ec = _encryption_context(contexto)
        try:
            response = self._client.decrypt(
                CiphertextBlob=wrapped,
                KeyId=self._arn,
                EncryptionContext=ec,
                EncryptionAlgorithm="SYMMETRIC_DEFAULT",
            )
            dek = response["Plaintext"]
            returned_key = response["KeyId"]
            if returned_key != self._arn or not isinstance(dek, bytes) or len(dek) != 32:
                raise CofreIndisponivel("Retorno KMS incompatível.")
            return dek
        except CofreIndisponivel:
            raise
        except Exception as exc:
            raise CofreIndisponivel("Falha de decifragem AWS KMS.") from exc


def _runtime_ready(environ: Mapping[str, str]) -> bool:
    """Only STAGING, authenticated, OIDC role and Render-issued token file.

    No AWS request occurs here. This is merely a config check, NOT IAM validation.
    """
    if (environ.get("SMARTTEC_FISCAL_A1_KMS_ADAPTER_ENABLED") != "1"
        or environ.get("SMARTTEC_ENV", "").lower() != "staging"
        or environ.get("SMARTTEC_AUTH_MODE", "").lower() != "authenticated"):
        return False
    # Explicitly reject long-lived credential configuration on Render.
    if any(environ.get(k) for k in (
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
        "AWS_PROFILE", "AWS_SHARED_CREDENTIALS_FILE",
    )):
        return False
    role = environ.get("AWS_ROLE_ARN", "")
    if not ROLE_ARN.fullmatch(role):
        return False
    key = environ.get("SMARTTEC_FISCAL_A1_KMS_KEY_ARN", "")
    try:
        region, account = _key_details(key)
    except CofreIndisponivel:
        return False
    if environ.get("AWS_REGION") != region or role.split(":")[4] != account:
        return False
    oidc_path = environ.get("AWS_WEB_IDENTITY_TOKEN_FILE", "")
    if not oidc_path or not Path(oidc_path).is_file():
        return False
    return True


def situacao_kms_aws(environ: Mapping[str, str] | None = None) -> str:
    """Diagnostic safe for an admin UI; no ARN, role or token path is returned."""
    env = os.environ if environ is None else environ
    return "CONFIGURACAO_OIDC_DETECTADA_NAO_VERIFICADA" if _runtime_ready(env) else "INATIVO"


def criar_provedor_kms_staging() -> AwsKmsProvedor:
    """Creates SDK client only when server-only feature gate & OIDC are present.

    Not used by public routes; configuring credentials must never enable issuance.
    """
    if not _runtime_ready(os.environ):
        raise CofreIndisponivel("AWS KMS inativo: autenticação OIDC do staging não configurada.")
    arn = os.environ["SMARTTEC_FISCAL_A1_KMS_KEY_ARN"]
    region, _ = _key_details(arn)
    try:
        import boto3
        from botocore.config import Config
        client = boto3.client(
            "kms",
            region_name=region,
            config=Config(connect_timeout=3, read_timeout=5,
                          retries={"mode": "standard", "max_attempts": 2}),
        )
    except Exception as exc:
        raise CofreIndisponivel("AWS SDK/KMS indisponível no staging.") from exc
    return AwsKmsProvedor(key_arn=arn, client=client)
