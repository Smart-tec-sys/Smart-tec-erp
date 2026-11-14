"""Pré-conferência A1 do emitente, isolada e SEM armazenamento de PFX ou senha.

Não valida a cadeia ICP-Brasil, revogação, políticas do certificado ou
credenciamento na SEFAZ. Não habilita NF-e: resultado é apenas triagem local.
Nenhuma rota de upload/assinatura está exposta pelo ERP.

A identificação do CNPJ exige otherName OID=2.16.76.1.3.3, NÃO usa CN;
certificados matriz/filial são comparados pela raiz de oito dígitos.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import re

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtensionOID, ObjectIdentifier

CNPJ_OID = ObjectIdentifier("2.16.76.1.3.3")
MAX_PFX_BYTES = 128 * 1024
MAX_SENHA_BYTES = 256


class CertificadoA1Invalido(ValueError):
    """Certificado não adequado nem para triagem de cadastro."""


def _documento(value: str) -> str:
    digits = re.sub(r"\D", "", value if isinstance(value, str) else "")
    if len(digits) != 14:
        raise CertificadoA1Invalido("CNPJ do cadastro deve ter 14 dígitos.")
    return digits


def _cnpj_certificado(cert: x509.Certificate) -> str:
    """Extrai somente o CNPJ DER otherName; não confia em CN/razão social."""
    try:
        san = cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        ).value
        matches = [
            item for item in san
            if isinstance(item, x509.OtherName) and item.type_id == CNPJ_OID
        ]
    except x509.ExtensionNotFound as exc:
        raise CertificadoA1Invalido("Certificado sem identificação de CNPJ ICP-Brasil.") from exc
    if len(matches) != 1:
        raise CertificadoA1Invalido("Identificação de CNPJ ausente ou ambígua.")
    encoded = matches[0].value
    # otherName carrega um valor ASN.1; aceitar apenas OCTET STRING, UTF8,
    # PrintableString ou IA5 de comprimento curto, com 14 dígitos ASCII.
    if len(encoded) != 16 or encoded[0] not in (0x04, 0x0c, 0x13, 0x16) or encoded[1] != 14:
        raise CertificadoA1Invalido("CNPJ do certificado possui formato não reconhecido.")
    try:
        value = encoded[2:].decode("ascii")
    except UnicodeDecodeError as exc:
        raise CertificadoA1Invalido("CNPJ do certificado não é numérico.") from exc
    if re.fullmatch(r"\d{14}", value) is None:
        raise CertificadoA1Invalido("CNPJ do certificado não é numérico.")
    return value


def conferir_pfx_a1_local(pfx: bytes, senha: bytes, *, cnpj_emitente: str,
                          instante: datetime | None = None) -> dict:
    """Recebe PFX/senha SOMENTE em memória; retorna diagnóstico sem segredo.

    Não consulta rede, banco ou cofre. Nunca exibir PFX/senha no navegador.
    Certificado de cadeia desconhecida NÃO pode ser habilitado para emissão.
    """
    if not isinstance(pfx, bytes) or not 0 < len(pfx) <= MAX_PFX_BYTES:
        raise CertificadoA1Invalido("Arquivo A1 não reconhecido ou fora do limite.")
    if not isinstance(senha, bytes) or len(senha) > MAX_SENHA_BYTES:
        raise CertificadoA1Invalido("Senha do A1 inválida.")
    target = _documento(cnpj_emitente)
    try:
        private_key, cert, _chain = pkcs12.load_key_and_certificates(pfx, senha)
    except (ValueError, TypeError) as exc:
        raise CertificadoA1Invalido("Certificado A1 ou senha inválidos.") from exc
    if cert is None or not isinstance(private_key, rsa.RSAPrivateKey):
        raise CertificadoA1Invalido("PFX não contém certificado com chave privada RSA.")
    pub = cert.public_key()
    if not isinstance(pub, rsa.RSAPublicKey) or private_key.public_key().public_numbers() != pub.public_numbers():
        raise CertificadoA1Invalido("Chave privada não confere com o certificado.")
    if pub.key_size < 2048:
        raise CertificadoA1Invalido("Chave RSA inferior ao mínimo da triagem.")
    if cert.issuer == cert.subject:
        raise CertificadoA1Invalido("Certificado autossinado não é A1 ICP-Brasil.")
    try:
        constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
    except x509.ExtensionNotFound:
        constraints = None
    if constraints is not None and constraints.ca:
        raise CertificadoA1Invalido("Certificado de autoridade certificadora não serve como emitente.")
    try:
        usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound as exc:
        raise CertificadoA1Invalido("Certificado sem permissão de assinatura.") from exc
    if not usage.digital_signature:
        raise CertificadoA1Invalido("Certificado sem permissão de assinatura.")

    cert_cnpj = _cnpj_certificado(cert)
    if cert_cnpj[:8] != target[:8]:
        raise CertificadoA1Invalido("CNPJ-base do A1 não corresponde à empresa ativa.")
    now = instante or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise CertificadoA1Invalido("A data de verificação deve possuir fuso horário.")
    exp = cert.not_valid_after_utc
    start = cert.not_valid_before_utc
    if now < start:
        raise CertificadoA1Invalido("Certificado ainda não está dentro da validade.")
    if now >= exp:
        raise CertificadoA1Invalido("Certificado vencido.")
    # Não entregar DER, chave, senha, serial, SAN ou CNPJ completo no resultado.
    return {
        "tipo": "A1",
        "verificacao": "TRIAGEM_LOCAL_INCOMPLETA",
        "cnpj_base_compatível": True,
        "validade_ate": exp.isoformat(),
        "dias_restantes": max(0, (exp - now).days),
        "cadeia_icp_brasil_verificada": False,
        "revogacao_verificada": False,
        "armazenado_em_cofre": False,
        "emissao_habilitada": False,
        "aviso": "Validação de cadeia ICP-Brasil, revogação e políticas da SEFAZ ainda pendente.",
    }


def status_a1_empresa(db, tenant) -> dict:
    """Status seguro por tenant; não exibe PFX e não inventa certificado salvo."""
    # Importação local para não acoplar o parser ao módulo de CRUD na inicialização.
    from app.services.fiscal_cadastros import _empresa, exigir_admin
    from app.tenant.isolation import require_tenant

    exigir_admin(db, tenant)
    empresa = _empresa(db, tenant)
    empresa_id = require_tenant(tenant)
    if empresa.id != empresa_id:
        raise CertificadoA1Invalido("Identidade da empresa divergente.")
    return {
        "empresa_id": empresa_id,
        "tipo": "A1",
        "situacao": "NAO_CONFIGURADO",
        "cofre_configurado": False,
        "certificado_armazenado": False,
        "emissao_habilitada": False,
        "aviso": "Cofre seguro e rotina de importação A1 ainda não integrados.",
    }
