"""XML NF-e 4.00 de HOMOLOGAÇÃO: primeiro protótipo, exclusivamente fictício.

Gera um documento *não assinado* para testar estrutura e serialização.
NÃO é uma NF-e autorizável: o schema nfe_v4.00.xsd exige Signature.
NÃO usa dados do ERP, contas de clientes, certificados nem SEFAZ.
A tributação sintética dos testes não deve ser aplicada a qualquer venda real.

Documentação: Portal Nacional da NF-e, pacotes de schemas 010g v1.03
(26/10/2026); verificar NT 2025.002 v1.53 e NT 2026.008 v1.01.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re
from xml.etree import ElementTree as ET

NS_NFE = "http://www.portalfiscal.inf.br/nfe"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"
ET.register_namespace("", NS_NFE)
EXEMPLO_CNPJ = "11222333000181"  # Documento fictício de testes.
EXEMPLO_CPF = "52998224725"     # CPF de exemplo público para teste dos dígitos.
VERSAO_XML = "4.00"
_TWOPLACES = Decimal("0.01")
_FOURPLACES = Decimal("0.0001")


class XmlFiscalNaoHabilitado(ValueError):
    """Uma operação não homologada tentou produzir XML fiscal utilizável."""


def _e(parent: ET.Element, tag: str, value: str) -> ET.Element:
    if not isinstance(value, str) or not value.strip():
        raise XmlFiscalNaoHabilitado(f"Campo obrigatório do exemplo ausente: {tag}")
    return _insert(parent, tag, value)


def _insert(parent: ET.Element, tag: str, value: str) -> ET.Element:
    child = ET.SubElement(parent, f"{{{NS_NFE}}}{tag}")
    child.text = value
    return child


def _g(parent: ET.Element, tag: str) -> ET.Element:
    return ET.SubElement(parent, f"{{{NS_NFE}}}{tag}")


def _validar_decimal(value: str, quant: Decimal, *, positive: bool = True) -> Decimal:
    try:
        num = Decimal(value)
    except (ValueError, TypeError, ArithmeticError) as exc:
        raise XmlFiscalNaoHabilitado("Valor inválido para exemplo XML.") from exc
    if not num.is_finite() or (positive and num <= 0) or (not positive and num < 0):
        raise XmlFiscalNaoHabilitado("Valor não finito, negativo ou zerado no exemplo.")
    if num != num.quantize(quant):
        raise XmlFiscalNaoHabilitado("Precisão do exemplo excede a escala permitida.")
    return num


def _dv_chave(base43: str) -> str:
    """Dígito verificador módulo 11 para 43 algarismos de chave de acesso."""
    if re.fullmatch(r"[0-9]{43}", base43) is None:
        raise XmlFiscalNaoHabilitado("Base da chave sintética deve ter 43 dígitos.")
    soma = sum(int(n) * (i % 8 + 2) for i, n in enumerate(reversed(base43)))
    resto = soma % 11
    return str(0 if resto in (0, 1) else 11 - resto)


def _identificador_sintetico(dt: datetime, numero: int, serie: int, codigo: str) -> tuple[str, str]:
    """Id exclusivamente para XML fictício; NUNCA reservar numeração fiscal."""
    if dt.utcoffset() is None or not 1 <= numero <= 999999999 or not 1 <= serie <= 899:
        raise XmlFiscalNaoHabilitado("Identificação inválida no exemplo.")
    if not re.fullmatch(r"[0-9]{8}", codigo):
        raise XmlFiscalNaoHabilitado("Código numérico sintético inválido.")
    base = (
        "35" + dt.strftime("%y%m") + EXEMPLO_CNPJ + "55"
        + f"{serie:03d}" + f"{numero:09d}" + "1" + codigo
    )
    dv = _dv_chave(base)
    return "NFe" + base + dv, dv


def gerar_xml_ficticio_nao_assinado(
    *,
    quantidade: str = "2.5000",
    preco_unitario: str = "100.0000",
    subtotal: str = "250.00",
) -> bytes:
    """Gera NFe 4.00 *não assinada*, só com emitente/destinatário fictícios.

    Não aceita CNPJ real, cliente, empresa, itens nem payload externo. Os códigos
    de classificação e imposto são estritamente ilustrativos e não são
    recomendação fiscal; os campos da Reforma Tributária ficam pendentes.
    """
    q = _validar_decimal(quantidade, _FOURPLACES)
    vu = _validar_decimal(preco_unitario, _FOURPLACES)
    total = _validar_decimal(subtotal, _TWOPLACES)
    if abs(q * vu - total) > _TWOPLACES:
        raise XmlFiscalNaoHabilitado("Total do exemplo não reconcilia quantidade x preço.")
    dt = datetime.fromisoformat("2026-11-14T12:00:00-03:00")
    chave, dv = _identificador_sintetico(dt, 1, 1, "12345678")

    root = _g_no_parent("NFe")
    inf = _g(root, "infNFe")
    inf.set("Id", chave)
    inf.set("versao", VERSAO_XML)

    ide = _g(inf, "ide")
    for t, v in (
        ("cUF", "35"), ("cNF", "12345678"), ("natOp", "OPERACAO FICTICIA DE TESTE"),
        ("mod", "55"), ("serie", "1"), ("nNF", "1"),
        ("dhEmi", dt.isoformat(timespec="seconds")),
        ("tpNF", "1"), ("idDest", "1"), ("cMunFG", "3550308"),
        ("tpImp", "1"), ("tpEmis", "1"), ("cDV", dv), ("tpAmb", "2"),
        ("finNFe", "1"), ("indFinal", "1"), ("indPres", "1"),
        ("procEmi", "0"), ("verProc", "Smarttec-XML-TESTE-0.1"),
    ):
        _e(ide, t, v)

    emit = _g(inf, "emit")
    _e(emit, "CNPJ", EXEMPLO_CNPJ)
    _e(emit, "xNome", "EMPRESA FICTICIA DE HOMOLOGACAO")
    end_emit = _g(emit, "enderEmit")
    for t, v in (
        ("xLgr", "RUA DE TESTES"), ("nro", "10"), ("xBairro", "CENTRO"),
        ("cMun", "3550308"), ("xMun", "SAO PAULO"), ("UF", "SP"),
        ("CEP", "01001000"), ("cPais", "1058"), ("xPais", "BRASIL"),
    ):
        _e(end_emit, t, v)
    _e(emit, "IE", "ISENTO")
    _e(emit, "CRT", "1")

    dest = _g(inf, "dest")
    _e(dest, "CPF", EXEMPLO_CPF)
    _e(dest, "xNome", "CLIENTE FICTICIO SEM VALOR FISCAL")
    end_dest = _g(dest, "enderDest")
    for t, v in (
        ("xLgr", "RUA TESTE"), ("nro", "20"), ("xBairro", "CENTRO"),
        ("cMun", "3550308"), ("xMun", "SAO PAULO"), ("UF", "SP"),
        ("CEP", "01001000"), ("cPais", "1058"), ("xPais", "BRASIL"),
    ):
        _e(end_dest, t, v)
    _e(dest, "indIEDest", "9")

    det = _g(inf, "det")
    det.set("nItem", "1")
    prod = _g(det, "prod")
    for t, v in (
        ("cProd", "DEMO-001"), ("cEAN", "SEM GTIN"),
        ("xProd", "PRODUTO FICTICIO PARA TESTE DE XML"),
        ("NCM", "63039200"), ("CFOP", "5102"),
        ("uCom", "UN"), ("qCom", f"{q:.4f}"),
        ("vUnCom", f"{vu:.4f}"), ("vProd", f"{total:.2f}"),
        ("cEANTrib", "SEM GTIN"), ("uTrib", "UN"),
        ("qTrib", f"{q:.4f}"), ("vUnTrib", f"{vu:.4f}"),
        ("indTot", "1"),
    ):
        _e(prod, t, v)

    imposto = _g(det, "imposto")
    icms = _g(imposto, "ICMS")
    icms_sn = _g(icms, "ICMSSN102")
    _e(icms_sn, "orig", "0")
    _e(icms_sn, "CSOSN", "102")
    pis = _g(imposto, "PIS")
    _e(_g(pis, "PISNT"), "CST", "08")
    cofins = _g(imposto, "COFINS")
    _e(_g(cofins, "COFINSNT"), "CST", "08")
    # IBS/CBS, IS e grupos de tributação vigentes devem ser calculados antes
    # de gerar um documento com validade fiscal. Aqui NÃO são inferidos.

    totals = _g(inf, "total")
    icms_tot = _g(totals, "ICMSTot")
    values = (
        ("vBC", "0.00"), ("vICMS", "0.00"), ("vICMSDeson", "0.00"),
        ("vFCP", "0.00"), ("vBCST", "0.00"), ("vST", "0.00"),
        ("vFCPST", "0.00"), ("vFCPSTRet", "0.00"),
        ("vProd", f"{total:.2f}"), ("vFrete", "0.00"),
        ("vSeg", "0.00"), ("vDesc", "0.00"), ("vII", "0.00"),
        ("vIPI", "0.00"), ("vIPIDevol", "0.00"),
        ("vPIS", "0.00"), ("vCOFINS", "0.00"),
        ("vOutro", "0.00"), ("vNF", f"{total:.2f}"),
    )
    for t, v in values:
        _e(icms_tot, t, v)

    transp = _g(inf, "transp")
    _e(transp, "modFrete", "9")
    pag = _g(inf, "pag")
    det_pag = _g(pag, "detPag")
    _e(det_pag, "tPag", "90")
    _e(det_pag, "vPag", "0.00")

    adic = _g(inf, "infAdic")
    _e(adic, "infCpl", "TESTE FICTICIO - SEM VALOR FISCAL - XML NAO ASSINADO - NAO TRANSMITIR")

    buffer = BytesIO()
    ET.ElementTree(root).write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def _g_no_parent(tag: str) -> ET.Element:
    return ET.Element(f"{{{NS_NFE}}}{tag}")


def validar_xsd_documento_assinado(xml: bytes, caminho_schema: Path) -> None:
    """Bloqueia rascunhos sem Signature; valida com schema disponível offline.

    Os schemas oficiais são insumos externos versionados; não se autoriza
    transmissão por esta função. Exige lxml instalada no ambiente.
    """
    try:
        from lxml import etree
    except ImportError as exc:
        raise XmlFiscalNaoHabilitado("Validador lxml não instalado.") from exc
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    try:
        root = etree.fromstring(xml, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise XmlFiscalNaoHabilitado("XML malformado.") from exc
    if root.tag != f"{{{NS_NFE}}}NFe":
        raise XmlFiscalNaoHabilitado("A raiz XML não é NFe.")
    if root.find(f"{{{NS_DS}}}Signature") is None:
        raise XmlFiscalNaoHabilitado(
            "O exemplo não está assinado. Proibido alegar validação XSD de NF-e."
        )
    if not caminho_schema.is_file() or caminho_schema.name != "nfe_v4.00.xsd":
        raise XmlFiscalNaoHabilitado("Schema oficial local nfe_v4.00.xsd não disponível.")
    try:
        schema = etree.XMLSchema(etree.parse(str(caminho_schema), parser=parser))
        if not schema.validate(root):
            raise XmlFiscalNaoHabilitado("XML não passou no schema XSD local.")
    except (etree.XMLSchemaParseError, etree.XMLSyntaxError, OSError) as exc:
        raise XmlFiscalNaoHabilitado("Schema inválido ou inacessível.") from exc
