"""Consulta autenticada de status da NF-e em homologação da SEFAZ-SP."""
import os
import ssl
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from fastapi import HTTPException
from lxml import etree

from app.services.fiscal_cadastros import _empresa, exigir_admin
from app.services.fiscal_certificado_a1 import CertificadoA1Invalido, conferir_pfx_a1_local
from app.services.fiscal_cofre_a1 import CofreIndisponivel, abrir_a1_interno
from app.services.fiscal_cofre_a1_repository import consultar_envelope_interno
from app.services.fiscal_importacao_a1_empresa import importacao_empresa_disponivel
from app.services.fiscal_kms_aws import criar_provedor_kms_staging

URL = "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx"
NFE = "http://www.portalfiscal.inf.br/nfe"
SOAP = "http://www.w3.org/2003/05/soap-envelope"
SERVICO = f"{NFE}/wsdl/NFeStatusServico4"
MAX_RESPOSTA = 64 * 1024
CONSULTA = f"""<soap:Envelope xmlns:soap="{SOAP}">
<soap:Body><nfeDadosMsg xmlns="{SERVICO}">
<consStatServ xmlns="{NFE}" versao="4.00">
<tpAmb>2</tpAmb><cUF>35</cUF><xServ>STATUS</xServ>
</consStatServ></nfeDadosMsg></soap:Body></soap:Envelope>""".encode("UTF-8")


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def consulta_status_disponivel(tenant) -> bool:
    empresa_configurada = os.getenv("SMARTTEC_FISCAL_SEFAZ_SP_EMPRESA_ID")
    return (
        os.getenv("SMARTTEC_ENV") == "staging"
        and importacao_empresa_disponivel(tenant)
        and str(tenant.empresa_id) == empresa_configurada
        and hasattr(os, "memfd_create")
    )


def _contexto_tls(pfx: bytes, senha: bytes) -> ssl.SSLContext:
    chave, certificado, cadeia = pkcs12.load_key_and_certificates(pfx, senha)
    if chave is None or certificado is None:
        raise ValueError("PFX sem certificado ou chave")
    contexto = ssl.create_default_context()
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    # O OpenSSL requer um caminho. O descritor existe só em memória no Linux.
    with os.fdopen(os.memfd_create("sefaz-a1", flags=os.MFD_CLOEXEC), "wb") as pem:
        for item in (certificado, *(cadeia or ())):
            pem.write(item.public_bytes(serialization.Encoding.PEM))
        pem.write(chave.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
        ))
        pem.flush()
        contexto.load_cert_chain(f"/proc/self/fd/{pem.fileno()}")
    return contexto


def _ler_status(conteudo: bytes) -> dict:
    if not 0 < len(conteudo) <= MAX_RESPOSTA:
        raise ValueError("Resposta fora do limite")
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    envelope = etree.fromstring(conteudo, parser)
    if envelope.tag != f"{{{SOAP}}}Envelope" or envelope.getroottree().docinfo.doctype:
        raise ValueError("Envelope SOAP inválido")
    status = envelope.find(f"{{{SOAP}}}Body/{{{SERVICO}}}nfeResultMsg/{{{NFE}}}retConsStatServ")
    if status is None or status.findtext(f"{{{NFE}}}tpAmb") != "2" or status.findtext(f"{{{NFE}}}cUF") != "35":
        raise ValueError("Ambiente ou UF divergente na resposta")
    codigo = status.findtext(f"{{{NFE}}}cStat", "")
    motivo = status.findtext(f"{{{NFE}}}xMotivo", "").strip()
    if len(codigo) != 3 or not codigo.isascii() or not codigo.isdigit() or not 0 < len(motivo) <= 255:
        raise ValueError("Status ausente ou inválido")
    return {"tpAmb": 2, "cStat": int(codigo), "xMotivo": motivo}


def _consultar(contexto: ssl.SSLContext) -> dict:
    cliente = build_opener(HTTPSHandler(context=contexto), SemRedirecionamento())
    pedido = Request(URL, data=CONSULTA, headers={
        "Content-Type": f'application/soap+xml; charset=utf-8; action="{SERVICO}/nfeStatusServicoNF"',
    }, method="POST")
    with cliente.open(pedido, timeout=12) as resposta:
        return _ler_status(resposta.read(MAX_RESPOSTA + 1))


def consultar_status_sefaz_sp(db, tenant) -> dict:
    if not consulta_status_disponivel(tenant):
        raise HTTPException(404, "Consulta de homologação indisponível.")
    exigir_admin(db, tenant)
    empresa = _empresa(db, tenant)
    try:
        envelope = consultar_envelope_interno(db, tenant)
        if envelope is None:
            raise HTTPException(409, "Cadastre o certificado A1 da empresa antes de consultar a SEFAZ.")
        pfx, senha = abrir_a1_interno(empresa.id, envelope, criar_provedor_kms_staging())
        conferir_pfx_a1_local(pfx, senha, cnpj_emitente=empresa.documento)
        contexto = _contexto_tls(pfx, senha)
    except CofreIndisponivel:
        raise HTTPException(503, "Não foi possível recuperar o A1 do cofre de homologação.") from None
    except (CertificadoA1Invalido, UnsupportedAlgorithm, ValueError, OSError):
        raise HTTPException(422, "Não foi possível usar o A1 cadastrado para autenticar a consulta.") from None
    try:
        return _consultar(contexto)
    except (URLError, OSError, ValueError, etree.XMLSyntaxError):
        raise HTTPException(502, "A consulta de status da SEFAZ-SP falhou em homologação.") from None
