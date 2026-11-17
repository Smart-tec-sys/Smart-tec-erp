"""Acesso ao KMS por Lambda privado no Render Hobby, apenas em staging."""
from base64 import b64decode, b64encode
import json
import os
import re

from app.services.fiscal_cofre_a1 import CofreIndisponivel
from app.services.fiscal_kms_aws import AwsKmsProvedor, KEY_ARN

FUNCAO = re.compile(r"arn:aws:lambda:us-east-2:([0-9]{12}):function:[A-Za-z0-9_-]{1,64}")


def _config(empresa_id):
    ambiente = os.environ
    if (ambiente.get("SMARTTEC_ENV") != "staging"
        or ambiente.get("SMARTTEC_AUTH_MODE") != "authenticated"
        or ambiente.get("SMARTTEC_FISCAL_A1_LAMBDA_ENABLED") != "1"
        or type(empresa_id) is not int or empresa_id <= 0
        or ambiente.get("SMARTTEC_FISCAL_SEFAZ_SP_EMPRESA_ID") != str(empresa_id)):
        return None
    chave = KEY_ARN.fullmatch(ambiente.get("SMARTTEC_FISCAL_A1_KMS_KEY_ARN", ""))
    funcao = FUNCAO.fullmatch(ambiente.get("SMARTTEC_FISCAL_A1_LAMBDA_ARN", ""))
    if not chave or not funcao or chave.group(1) != "us-east-2" or chave.group(2) != funcao.group(1):
        return None
    acesso = ambiente.get("SMARTTEC_FISCAL_A1_LAMBDA_ACCESS_KEY_ID")
    segredo = ambiente.get("SMARTTEC_FISCAL_A1_LAMBDA_SECRET_ACCESS_KEY")
    if not acesso or not segredo:
        return None
    return chave.group(0), funcao.group(0), acesso, segredo


def lambda_configurado(empresa_id):
    return _config(empresa_id) is not None


class ClienteKmsViaLambda:
    def __init__(self, cliente, funcao, empresa_id):
        self.cliente = cliente
        self.funcao = funcao
        self.empresa_id = str(empresa_id)

    def _invocar(self, operacao, conteudo, contexto):
        if contexto.get("smarttec:empresa_id") != self.empresa_id:
            raise CofreIndisponivel("Empresa divergente do cofre em homologação.")
        retorno = self.cliente.invoke(
            FunctionName=self.funcao, InvocationType="RequestResponse",
            Payload=json.dumps({
                "operacao": operacao, "empresa_id": self.empresa_id,
                "conteudo": b64encode(conteudo).decode("ascii"),
            }).encode("utf-8"),
        )
        with retorno["Payload"] as stream:
            resposta = stream.read(8193)
        if retorno.get("StatusCode") != 200 or retorno.get("FunctionError") or len(resposta) > 8192:
            raise CofreIndisponivel("Resposta inválida do Lambda de homologação.")
        dados = json.loads(resposta)
        return dados["key_id"], b64decode(dados["conteudo"], validate=True)

    def encrypt(self, *, Plaintext, EncryptionContext, **_):
        chave, conteudo = self._invocar("encrypt", Plaintext, EncryptionContext)
        return {"KeyId": chave, "CiphertextBlob": conteudo}

    def decrypt(self, *, CiphertextBlob, EncryptionContext, **_):
        chave, conteudo = self._invocar("decrypt", CiphertextBlob, EncryptionContext)
        return {"KeyId": chave, "Plaintext": conteudo}


def criar_provedor_kms_via_lambda(empresa_id):
    config = _config(empresa_id)
    if config is None:
        raise CofreIndisponivel("Lambda de homologação indisponível.")
    chave, funcao, acesso, segredo = config
    import boto3
    from botocore.config import Config
    cliente = boto3.client(
        "lambda", region_name="us-east-2",
        aws_access_key_id=acesso, aws_secret_access_key=segredo,
        config=Config(connect_timeout=3, read_timeout=12, retries={"total_max_attempts": 1}),
    )
    return AwsKmsProvedor(key_arn=chave, client=ClienteKmsViaLambda(cliente, funcao, empresa_id))
