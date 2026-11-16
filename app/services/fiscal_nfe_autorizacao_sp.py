"""Cliente interno para autorização de uma NF-e em homologação na SEFAZ-SP."""
from __future__ import annotations

from dataclasses import dataclass, field
from http.client import HTTPException, HTTPSConnection
import re
import ssl

from lxml import etree

from app.services.fiscal_nfe_xml_homologacao import NS_DS, NS_NFE, VERSAO_XML

_HOST = "homologacao.nfe.fazenda.sp.gov.br"
_PATH = "/ws/nfeautorizacao4.asmx"
_SOAP = "http://www.w3.org/2003/05/soap-envelope"
_WSDL = f"{NS_NFE}/wsdl/NFeAutorizacao4"
_MAX_RESPOSTA = 512 * 1024
_MAX_NOTA = 500 * 1024
_NS = {"n": NS_NFE, "ds": NS_DS, "s": _SOAP}


class RetornoAutorizacaoInconclusivo(RuntimeError):
    """Consultar o protocolo pela chave antes de repetir a transmissão."""


@dataclass(frozen=True)
class RetornoAutorizacao:
    status_lote: str
    motivo_lote: str
    status_nfe: str | None
    motivo_nfe: str | None
    protocolo: str | None
    recibo: str | None
    xml_resposta: bytes = field(repr=False)

    @property
    def autorizada(self) -> bool:
        return self.status_lote == "104" and self.status_nfe == "100" and bool(self.protocolo)


def _ler_xml(xml: bytes):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    raiz = etree.fromstring(xml, parser)
    if raiz.getroottree().docinfo.doctype:
        raise ValueError("DTD não permitido.")
    return raiz


def _montar_requisicao(xml_assinado: bytes, id_lote: str) -> tuple[bytes, str]:
    if not 0 < len(xml_assinado) <= _MAX_NOTA:
        raise ValueError("XML da NF-e ausente ou acima do limite.")
    if re.fullmatch(r"[1-9][0-9]{0,14}", id_lote) is None:
        raise ValueError("ID do lote inválido.")
    try:
        nota = _ler_xml(xml_assinado)
    except etree.XMLSyntaxError as exc:
        raise ValueError("XML assinado malformado.") from exc
    if nota.tag != f"{{{NS_NFE}}}NFe" or [no.tag for no in nota] != [
        f"{{{NS_NFE}}}infNFe", f"{{{NS_DS}}}Signature",
    ]:
        raise ValueError("O lote exige uma única NF-e assinada.")
    inf = nota[0]
    ident = inf.get("Id", "")
    if (
        inf.get("versao") != VERSAO_XML
        or re.fullmatch(r"NFe[0-9]{44}", ident) is None
        or inf.findtext("n:ide/n:tpAmb", namespaces=_NS) != "2"
        or inf.findtext("n:ide/n:cUF", namespaces=_NS) != "35"
        or inf.findtext("n:ide/n:mod", namespaces=_NS) != "55"
        or nota.findtext("ds:Signature/ds:SignatureValue", namespaces=_NS) in (None, "")
        or nota.find("ds:Signature/ds:SignedInfo/ds:Reference", _NS) is None
        or nota.find("ds:Signature/ds:SignedInfo/ds:Reference", _NS).get("URI") != "#" + ident
    ):
        raise ValueError("O XML precisa ser uma NF-e 4.00 assinada de homologação de SP.")

    # Preserve os bytes do XML após a assinatura, incluindo os namespaces.
    dados = xml_assinado.removeprefix(b"\xef\xbb\xbf").lstrip()
    if dados.startswith(b"<?xml"):
        _, _, dados = dados.partition(b"?>")
    if not dados.lstrip().startswith(b"<"):
        raise ValueError("O XML assinado precisa estar em UTF-8.")
    try:
        dados.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("O XML assinado precisa estar em UTF-8.") from exc
    inicio = (
        f'<Envelope xmlns="{_SOAP}"><Body><nfeDadosMsg xmlns="{_WSDL}">'
        f'<enviNFe xmlns="{NS_NFE}" versao="{VERSAO_XML}">'
        f"<idLote>{id_lote}</idLote><indSinc>1</indSinc>"
    ).encode("ascii")
    return inicio + dados + b"</enviNFe></nfeDadosMsg></Body></Envelope>", ident[3:]


def interpretar_retorno(resposta: bytes, chave: str) -> RetornoAutorizacao:
    if not 0 < len(resposta) <= _MAX_RESPOSTA:
        raise RetornoAutorizacaoInconclusivo("Resposta ausente ou acima do limite.")
    try:
        raiz = _ler_xml(resposta)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise RetornoAutorizacaoInconclusivo("Resposta XML inválida.") from exc

    corpo = raiz.find("s:Body", _NS)
    lote = corpo.find(".//n:retEnviNFe", _NS) if corpo is not None else None
    if lote is None or lote.findtext("n:tpAmb", namespaces=_NS) != "2":
        raise RetornoAutorizacaoInconclusivo("Retorno do lote de homologação ausente.")

    status_lote = lote.findtext("n:cStat", namespaces=_NS)
    motivo_lote = lote.findtext("n:xMotivo", namespaces=_NS)
    if not status_lote or not motivo_lote:
        raise RetornoAutorizacaoInconclusivo("Status do lote ausente.")
    recibo = lote.findtext("n:infRec/n:nRec", namespaces=_NS)
    if status_lote != "104":
        return RetornoAutorizacao(status_lote, motivo_lote, None, None, None, recibo, resposta)

    protocolos = lote.findall("n:protNFe/n:infProt", _NS)
    if len(protocolos) != 1:
        raise RetornoAutorizacaoInconclusivo("O retorno não contém exatamente um protocolo.")
    inf = protocolos[0]
    if (
        inf.findtext("n:tpAmb", namespaces=_NS) != "2"
        or inf.findtext("n:chNFe", namespaces=_NS) != chave
    ):
        raise RetornoAutorizacaoInconclusivo("Protocolo não corresponde à NF-e do lote.")
    status_nfe = inf.findtext("n:cStat", namespaces=_NS)
    motivo_nfe = inf.findtext("n:xMotivo", namespaces=_NS)
    protocolo = inf.findtext("n:nProt", namespaces=_NS)
    if not status_nfe or not motivo_nfe or (status_nfe == "100" and not protocolo):
        raise RetornoAutorizacaoInconclusivo("Resultado da nota incompleto.")
    return RetornoAutorizacao(status_lote, motivo_lote, status_nfe, motivo_nfe, protocolo, recibo, resposta)


def autorizar_homologacao_sp(
    xml_assinado: bytes, id_lote: str, contexto_tls: ssl.SSLContext,
) -> RetornoAutorizacao:
    """Envia uma nota já assinada e validada por XSD com contexto mTLS do emitente."""
    if not contexto_tls.check_hostname or contexto_tls.verify_mode != ssl.CERT_REQUIRED:
        raise ValueError("O contexto TLS deve verificar o certificado e o nome do servidor.")
    corpo, chave = _montar_requisicao(xml_assinado, id_lote)
    conexao = HTTPSConnection(_HOST, timeout=45, context=contexto_tls)
    try:
        conexao.request("POST", _PATH, body=corpo, headers={
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{_WSDL}/nfeAutorizacaoLote"',
        })
        resposta = conexao.getresponse()
        if resposta.status != 200:
            raise RetornoAutorizacaoInconclusivo(f"HTTP {resposta.status} ao autorizar NF-e.")
        xml = resposta.read(_MAX_RESPOSTA + 1)
    except (OSError, HTTPException) as exc:
        raise RetornoAutorizacaoInconclusivo("Falha de comunicação com a SEFAZ-SP.") from exc
    finally:
        conexao.close()
    return interpretar_retorno(xml, chave)
