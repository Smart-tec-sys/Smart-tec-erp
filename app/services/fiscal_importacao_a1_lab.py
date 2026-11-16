"""Importação de PFX autossinado exclusivamente para o tenant de laboratório."""
import os
from base64 import b64decode
from binascii import Error as Base64Error
from json import loads
from logging import getLogger
from xml.etree import ElementTree

from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.exceptions import UnsupportedAlgorithm
from fastapi import HTTPException

from app.services.fiscal_cadastros import _empresa, exigir_admin
from app.services.fiscal_certificado_a1 import MAX_PFX_BYTES, MAX_SENHA_BYTES
from app.services.fiscal_cofre_a1 import CofreIndisponivel, abrir_a1_interno, proteger_a1
from app.services.fiscal_cofre_a1_repository import consultar_envelope_interno, guardar_envelope_cifrado
from app.services.fiscal_kms_aws import AwsKmsProvedor, KEY_ARN, criar_provedor_kms_staging
from app.services.fiscal_nfe_assinatura_laboratorio import (
    XmlFiscalNaoHabilitado, _verificar_certificado_laboratorio,
    _assinar_xml_gerado_no_laboratorio,
    assinar_xml_ficticio_pfx_laboratorio, verificar_xml_assinado_laboratorio,
)
from app.services.fiscal_nfe_preparacao import analisar_venda_nfe
from app.services.fiscal_nfe_xml_homologacao import (
    EXEMPLO_CNPJ, EXEMPLO_CPF, NS_NFE, gerar_xml_ficticio_nao_assinado,
)
from app.tenant.context import TenantOrigin


EMPRESA_LAB = 999999999
MAX_CORPO_LAB = 4 * ((MAX_PFX_BYTES + 2) // 3) + 2048
logger = getLogger(__name__)


def importacao_lab_disponivel(tenant):
    return (
        os.getenv("SMARTTEC_ENV") == "staging"
        and os.getenv("SMARTTEC_AUTH_MODE") == "authenticated"
        and os.getenv("SMARTTEC_FISCAL_A1_IMPORTACAO_LAB") == "1"
        and tenant.origem is TenantOrigin.AUTHENTICATION
        and tenant.empresa_id == EMPRESA_LAB
    )


def _provedor_lab():
    if os.getenv("SMARTTEC_FISCAL_A1_LAB_IAM_ENABLED") != "1":
        return criar_provedor_kms_staging()

    import boto3
    from botocore.config import Config

    arn = os.getenv("SMARTTEC_FISCAL_A1_KMS_KEY_ARN", "")
    key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not KEY_ARN.fullmatch(arn) or not arn.startswith("arn:aws:kms:us-east-2:") or not key_id or not secret:
        logger.warning("A1 laboratório: configuração IAM ou ARN KMS incompleto ou inválido.")
        raise CofreIndisponivel("Credencial KMS de laboratório indisponível.")
    from botocore.exceptions import BotoCoreError

    try:
        cliente = boto3.client(
            "kms", region_name="us-east-2", aws_access_key_id=key_id,
            aws_secret_access_key=secret,
            config=Config(connect_timeout=3, read_timeout=5, retries={"total_max_attempts": 2}),
        )
    except BotoCoreError as exc:
        raise CofreIndisponivel("Cliente KMS de laboratório indisponível.") from exc
    return AwsKmsProvedor(key_arn=arn, client=cliente)


def _exigir_laboratorio(tenant):
    if not importacao_lab_disponivel(tenant):
        raise HTTPException(404, "Importação de laboratório indisponível.")


def _validar_pfx_lab(pfx, senha):
    if not 0 < len(pfx) <= MAX_PFX_BYTES or not 0 < len(senha) <= MAX_SENHA_BYTES:
        raise ValueError
    chave, cert, cadeia = pkcs12.load_key_and_certificates(pfx, senha)
    if cert is None or not isinstance(chave, rsa.RSAPrivateKey) or cadeia:
        raise ValueError
    if _verificar_certificado_laboratorio(cert).public_numbers() != chave.public_key().public_numbers():
        raise ValueError


def importar_envelope_lab(db, tenant, corpo):
    _exigir_laboratorio(tenant)
    exigir_admin(db, tenant)
    _empresa(db, tenant)
    try:
        dados = loads(corpo)
        pfx = b64decode(dados["pfx"], validate=True)
        senha = dados["senha"].encode("utf-8")
        _validar_pfx_lab(pfx, senha)
    except (AttributeError, Base64Error, KeyError, TypeError, ValueError,
            UnsupportedAlgorithm, XmlFiscalNaoHabilitado):
        raise HTTPException(422, "Use um PFX autossinado do laboratório e a senha correspondente.") from None
    try:
        envelope = proteger_a1(EMPRESA_LAB, pfx, senha, _provedor_lab())
    except CofreIndisponivel as exc:
        causa = exc.__cause__
        codigo = causa.response.get("Error", {}).get("Code") if isinstance(causa, ClientError) else None
        if codigo not in (
            "AccessDenied", "AccessDeniedException", "DisabledException", "ExpiredTokenException",
            "InvalidClientTokenId", "InvalidSignatureException", "KMSInvalidStateException",
            "NotFoundException", "SignatureDoesNotMatch", "UnrecognizedClientException",
        ):
            codigo = type(causa).__name__ if causa is not None else "configuração ou resposta KMS inválida"
        logger.warning("A1 laboratório: falha no KMS (%s).", codigo)
        raise HTTPException(503, "Cofre de laboratório indisponível.") from None
    try:
        guardar_envelope_cifrado(db, tenant, envelope)
    except HTTPException as exc:
        if exc.status_code == 503:
            logger.warning("A1 laboratório: KMS concluiu a cifragem, mas o banco recusou a gravação.")
        raise
    return {"certificado_armazenado": True, "emissao_habilitada": False}


def verificar_envelope_lab(db, tenant, *, testar_assinatura=False, xml_venda=None):
    _exigir_laboratorio(tenant)
    try:
        envelope = consultar_envelope_interno(db, tenant)
        if envelope is None:
            raise HTTPException(404, "PFX fictício ausente no cofre.")
        pfx, senha = abrir_a1_interno(EMPRESA_LAB, envelope, _provedor_lab())
        if testar_assinatura or xml_venda is not None:
            xml = (assinar_xml_ficticio_pfx_laboratorio(pfx, senha) if xml_venda is None
                   else _assinar_xml_gerado_no_laboratorio(xml_venda, pfx, senha))
            if not verificar_xml_assinado_laboratorio(xml):
                raise XmlFiscalNaoHabilitado("Assinatura fictícia inválida.")
            return {"assinatura_lab_verificada": True}
        _validar_pfx_lab(pfx, senha)
    except (CofreIndisponivel, ValueError, UnsupportedAlgorithm, XmlFiscalNaoHabilitado):
        logger.warning("A1 laboratório: falha ao verificar o PFX cifrado.")
        raise HTTPException(503, "O cofre não conseguiu verificar o PFX fictício.") from None
    return {"certificado_lab_verificado": True}


def status_importacao_lab(db, tenant):
    habilitada = importacao_lab_disponivel(tenant)
    return {
        "importacao_lab_habilitada": habilitada,
        "certificado_lab_armazenado": habilitada and consultar_envelope_interno(db, tenant) is not None,
    }


def conferir_xml_venda_lab(db, tenant, *, assinar=False):
    _exigir_laboratorio(tenant)
    exigir_admin(db, tenant)
    _empresa(db, tenant)
    item = {
        "produto_id": 1, "descricao": "Produto fictício", "tipo_item": "PRODUTO",
        "quantidade": "3.0000", "preco_unitario": "42.5000", "subtotal": "127.50",
    }
    venda = {"itens": [item], "total": "127.50", "desconto": "0.00", "total_final": "127.50"}
    cliente = {
        "nome": "Cliente fictício", "documento": EXEMPLO_CPF, "cep": "01001000",
        "logradouro": "Rua Teste", "numero": "20", "bairro": "Centro",
        "cidade": "São Paulo", "estado": "SP",
    }
    diagnostico = analisar_venda_nfe(venda, {"documento": EXEMPLO_CNPJ}, cliente)
    pendencias_fiscais = {
        "CONFIGURACAO_TRIBUTARIA", "EMITENTE_ENDERECO_FISCAL", "SEFAZ_NAO_INTEGRADA",
    }
    if any(p["codigo"] not in pendencias_fiscais for p in diagnostico["pendencias"]):
        raise HTTPException(422, "A venda fictícia contém pendências de cadastro ou totais.")

    xml = gerar_xml_ficticio_nao_assinado(
        quantidade=item["quantidade"], preco_unitario=item["preco_unitario"],
        subtotal=diagnostico["resumo"]["total_final"],
    )
    inf = ElementTree.fromstring(xml).find("infNFe", {"": NS_NFE})
    campos_esperados = {
        "ide/tpAmb": "2",
        "emit/CNPJ": EXEMPLO_CNPJ,
        "dest/CPF": EXEMPLO_CPF,
        "det/prod/NCM": "63039200",
        "det/prod/CFOP": "5102",
        "det/prod/qCom": item["quantidade"],
        "det/prod/vUnCom": item["preco_unitario"],
        "det/prod/vProd": item["subtotal"],
        "total/ICMSTot/vNF": venda["total_final"],
    }
    if inf is None or any(inf.findtext(campo, namespaces={"": NS_NFE}) != valor
                          for campo, valor in campos_esperados.items()):
        raise HTTPException(503, "O XML diverge da venda ou da classificação fictícia.")
    resultado = {"campos_conferidos": len(campos_esperados), "total": venda["total_final"],
                 "assinado": False, "transmitido": False}
    if assinar:
        resultado.update(verificar_envelope_lab(db, tenant, xml_venda=xml), assinado=True)
    return resultado
