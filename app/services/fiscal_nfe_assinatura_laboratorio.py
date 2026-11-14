"""Assinatura XMLDSig apenas para o laboratório NF-e 4.00 da Smart-tec.

ATENÇÃO: EXCLUSIVAMENTE CERTIFICADOS AUTOSSINADOS DO LABORATÓRIO.
Este módulo NÃO aceita certificados de clientes/ICP-Brasil, não persiste PFX,
não faz transmissão SEFAZ e não é um assinador fiscal de produção.

O MOC NF-e documenta XMLDSig enveloped/C14N/RSA-SHA1/SHA1. SHA-1 é legado;
não ampliar o seu uso para qualquer outro cenário. A homologação real requer
revisão criptográfica independente e os schemas oficiais vigentes.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import re

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from lxml import etree

from app.services.fiscal_nfe_xml_homologacao import (
    NS_DS, NS_NFE, XmlFiscalNaoHabilitado,
    gerar_xml_ficticio_nao_assinado,
)

LAB_CN = "SMARTTEC-LAB-NFE-NAO-REAL"
C14N_URI = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ENVELOPED_URI = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
RSA_SHA1_URI = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
SHA1_URI = "http://www.w3.org/2000/09/xmldsig#sha1"
MAX_XML = 65536
MAX_PFX = 32768


def _parse(data: bytes) -> etree._Element:
    if not isinstance(data, bytes) or len(data) > MAX_XML or len(data) < 50:
        raise XmlFiscalNaoHabilitado("XML de laboratório ausente ou fora do limite.")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                             huge_tree=False, remove_blank_text=False)
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise XmlFiscalNaoHabilitado("XML de laboratório malformado.") from exc
    if root.getroottree().docinfo.doctype:
        raise XmlFiscalNaoHabilitado("DTD não permitido.")
    if root.tag != f"{{{NS_NFE}}}NFe":
        raise XmlFiscalNaoHabilitado("A raiz precisa ser NFe.")
    return root


def _verificar_certificado_laboratorio(cert: x509.Certificate):
    try:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if len(cn) != 1 or cn[0].value != LAB_CN:
            raise XmlFiscalNaoHabilitado("Certificado não é do laboratório.")
        if cert.issuer != cert.subject:
            raise XmlFiscalNaoHabilitado("Certificado não é autossinado do laboratório.")
        key = cert.public_key()
        if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 2048:
            raise XmlFiscalNaoHabilitado("Certificado de laboratório exige RSA 2048+.")
        now = datetime.now(timezone.utc)
        if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
            raise XmlFiscalNaoHabilitado("Certificado de laboratório fora da validade.")
        try:
            key_usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
        except x509.ExtensionNotFound as exc:
            raise XmlFiscalNaoHabilitado("Certificado sem extensão de assinatura.") from exc
        if not key_usage.digital_signature:
            raise XmlFiscalNaoHabilitado("Certificado não permite assinatura digital.")
        key.verify(cert.signature, cert.tbs_certificate_bytes,
                   padding.PKCS1v15(), cert.signature_hash_algorithm)
    except InvalidSignature as exc:
        raise XmlFiscalNaoHabilitado("Certificado do laboratório inválido.") from exc
    return key


def _canonical(el: etree._Element) -> bytes:
    return etree.tostring(el, method="c14n", exclusive=False, with_comments=False)


def _element(parent: etree._Element, tag: str, content: str | None = None):
    el = etree.SubElement(parent, f"{{{NS_DS}}}{tag}")
    if content is not None:
        el.text = content
    return el


def assinar_xml_ficticio_pfx_laboratorio(pfx: bytes, senha: bytes) -> bytes:
    """Assina SOMENTE o XML constante gerado pelo laboratório (nunca um pedido real).

    Os bytes de PFX são recebidos apenas em memória, não são armazenados.
    Exige o CN de laboratório + certificado autossinado, não ICP-Brasil.
    """
    if not isinstance(pfx, bytes) or not (0 < len(pfx) <= MAX_PFX):
        raise XmlFiscalNaoHabilitado("PFX de laboratório inválido.")
    if not isinstance(senha, bytes) or not (0 < len(senha) <= 128):
        raise XmlFiscalNaoHabilitado("Senha de laboratório inválida.")
    try:
        key, cert, chain = pkcs12.load_key_and_certificates(pfx, senha)
    except (ValueError, TypeError) as exc:
        raise XmlFiscalNaoHabilitado("PFX de laboratório ou senha inválidos.") from exc
    if cert is None or not isinstance(key, rsa.RSAPrivateKey) or chain:
        raise XmlFiscalNaoHabilitado("PFX deve conter somente chave RSA e certificado de laboratório.")
    pubkey = _verificar_certificado_laboratorio(cert)
    if pubkey.public_numbers() != key.public_key().public_numbers():
        raise XmlFiscalNaoHabilitado("Chave privada não corresponde ao certificado.")

    root = _parse(gerar_xml_ficticio_nao_assinado())
    inf = root.find(f"{{{NS_NFE}}}infNFe")
    if inf is None:
        raise XmlFiscalNaoHabilitado("infNFe do laboratório ausente.")
    id_ref = inf.get("Id")
    if not id_ref or not re.fullmatch(r"NFe[0-9]{44}", id_ref):
        raise XmlFiscalNaoHabilitado("Id do XML de laboratório inválido.")

    # Assinatura irmã de infNFe, conforme nfe_v4.00.xsd.
    signature = etree.SubElement(root, f"{{{NS_DS}}}Signature", nsmap={"ds": NS_DS})
    signed_info = _element(signature, "SignedInfo")
    etree.SubElement(signed_info, f"{{{NS_DS}}}CanonicalizationMethod",
                     Algorithm=C14N_URI)
    etree.SubElement(signed_info, f"{{{NS_DS}}}SignatureMethod",
                     Algorithm=RSA_SHA1_URI)
    reference = etree.SubElement(signed_info, f"{{{NS_DS}}}Reference", URI="#" + id_ref)
    transforms = _element(reference, "Transforms")
    etree.SubElement(transforms, f"{{{NS_DS}}}Transform", Algorithm=ENVELOPED_URI)
    etree.SubElement(transforms, f"{{{NS_DS}}}Transform", Algorithm=C14N_URI)
    etree.SubElement(reference, f"{{{NS_DS}}}DigestMethod", Algorithm=SHA1_URI)

    # Assina o infNFe identificado por ID, não a nota inteira.
    digest = hashlib.sha1(_canonical(inf)).digest()  # exigência legada da NF-e
    _element(reference, "DigestValue", base64.b64encode(digest).decode("ascii"))
    signature_bytes = key.sign(_canonical(signed_info), padding.PKCS1v15(), hashes.SHA1())
    _element(signature, "SignatureValue", base64.b64encode(signature_bytes).decode("ascii"))

    key_info = _element(signature, "KeyInfo")
    x509_data = _element(key_info, "X509Data")
    der = cert.public_bytes(serialization.Encoding.DER)
    _element(x509_data, "X509Certificate", base64.b64encode(der).decode("ascii"))
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def verificar_xml_assinado_laboratorio(xml: bytes) -> bool:
    """Verifica referência, digest, assinatura RSA e certificado LAB, sem SEFAZ.

    Rejeita XMLs com elementos extras, IDs duplicados, algoritmo substituído,
    conteúdo alterado, certificado inválido ou referência fora do infNFe.
    """
    root = _parse(xml)
    inf_tag = f"{{{NS_NFE}}}infNFe"
    sig_tag = f"{{{NS_DS}}}Signature"
    if [x.tag for x in root] != [inf_tag, sig_tag]:
        raise XmlFiscalNaoHabilitado("Estrutura assinada inválida.")
    inf, sig = root[0], root[1]
    nfe_id = inf.get("Id")
    if not nfe_id or re.fullmatch(r"NFe[0-9]{44}", nfe_id) is None:
        raise XmlFiscalNaoHabilitado("Identificador do infNFe inválido.")
    if inf.get("versao") != "4.00":
        raise XmlFiscalNaoHabilitado("Versão NF-e inesperada.")

    si = sig.find(f"{{{NS_DS}}}SignedInfo")
    signature_value = sig.find(f"{{{NS_DS}}}SignatureValue")
    cert_element = sig.find(f"{{{NS_DS}}}KeyInfo/{{{NS_DS}}}X509Data/{{{NS_DS}}}X509Certificate")
    if si is None or signature_value is None or cert_element is None:
        raise XmlFiscalNaoHabilitado("Assinatura XMLDSig incompleta.")
    c14n_method = si.find(f"{{{NS_DS}}}CanonicalizationMethod")
    sig_method = si.find(f"{{{NS_DS}}}SignatureMethod")
    refs = si.findall(f"{{{NS_DS}}}Reference")
    if (c14n_method is None or sig_method is None
            or c14n_method.get("Algorithm") != C14N_URI
            or sig_method.get("Algorithm") != RSA_SHA1_URI or len(refs) != 1):
        raise XmlFiscalNaoHabilitado("Parâmetros XMLDSig não esperados.")
    ref = refs[0]
    if ref.get("URI") != "#" + nfe_id:
        raise XmlFiscalNaoHabilitado("Referência deve apontar ao infNFe.")
    transforms = ref.find(f"{{{NS_DS}}}Transforms")
    if transforms is None or [t.get("Algorithm") for t in transforms] != [
        ENVELOPED_URI, C14N_URI,
    ]:
        raise XmlFiscalNaoHabilitado("Transformações XMLDSig inesperadas.")
    digest_method = ref.find(f"{{{NS_DS}}}DigestMethod")
    digest_value = ref.find(f"{{{NS_DS}}}DigestValue")
    if (digest_method is None or digest_method.get("Algorithm") != SHA1_URI
            or digest_value is None or not digest_value.text):
        raise XmlFiscalNaoHabilitado("Digest XMLDSig não conforme.")
    try:
        digest = base64.b64decode(digest_value.text, validate=True)
        signature = base64.b64decode(signature_value.text or "", validate=True)
        der_cert = base64.b64decode(cert_element.text or "", validate=True)
        cert = x509.load_der_x509_certificate(der_cert)
    except (ValueError, TypeError) as exc:
        raise XmlFiscalNaoHabilitado("Codificação da assinatura inválida.") from exc
    if len(digest) != 20 or len(signature) < 256:
        raise XmlFiscalNaoHabilitado("Comprimento da assinatura inválido.")
    if not hmac.compare_digest(digest, hashlib.sha1(_canonical(inf)).digest()):
        raise XmlFiscalNaoHabilitado("Conteúdo do infNFe alterado após a assinatura.")
    public_key = _verificar_certificado_laboratorio(cert)
    try:
        public_key.verify(signature, _canonical(si), padding.PKCS1v15(), hashes.SHA1())
    except InvalidSignature as exc:
        raise XmlFiscalNaoHabilitado("Assinatura digital não confere.") from exc
    return True
