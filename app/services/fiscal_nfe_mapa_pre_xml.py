"""Mapa preparatório dos grupos XML da NF-e, sem gerar um documento fiscal.

O resultado é um checklist estrutural, não contém CNPJ/CPF, nomes ou valores,
nunca define tributos, não assina e não transmite. NFe/infNFe/Signature NÃO são
gerados. Toda validação XSD e adequação às notas técnicas vigentes é pendente.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation


def _exists(value) -> bool:
    if value is None or isinstance(value, bool):
        return False
    return bool(str(value).strip())


def _positive(value) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        number = Decimal(str(value))
        return number.is_finite() and number > 0
    except (InvalidOperation, ValueError, TypeError):
        return False


def _add(grupo, tag, descricao, status):
    grupo["campos"].append({
        "campo_xml": tag, "descricao": descricao, "situacao": status,
    })


def _field(grupo, tag, descricao, available):
    _add(grupo, tag, descricao, "INFORMADO" if available else "PENDENTE")


def _pending(grupo, tag, descricao):
    _add(grupo, tag, descricao, "INTEGRACAO_PENDENTE")


def _group(key: str, title: str):
    return {"grupo": key, "titulo": title, "situacao": "BLOQUEADO", "campos": []}


def montar_mapa_pre_xml(
    analise: dict, pedido: dict, emitente: dict,
    destinatario: dict | None, fiscal_emitente: dict | None,
) -> dict:
    """Transforma informações já consultadas no tenant em checklist sem dados sensíveis."""
    codigos = {p.get("codigo") for p in analise.get("pendencias", [])}
    fiscal = fiscal_emitente if isinstance(fiscal_emitente, dict) else {}
    dest = destinatario if isinstance(destinatario, dict) else {}
    itens = pedido.get("itens") or []
    produtos = [
        item for item in itens
        if isinstance(item, dict) and str(item.get("tipo_item") or "PRODUTO").upper() == "PRODUTO"
    ]

    ide = _group("ide", "Identificação da NF-e")
    _field(ide, "mod", "Modelo 55 — NF-e de produtos", True)
    _field(ide, "tpAmb", "Ambiente de homologação", fiscal.get("ambiente") == "HOMOLOGACAO")
    _field(ide, "serie", "Série cadastrada da NF-e", _positive(fiscal.get("serie_nfe")))
    _field(ide, "cMunFG", "Município do fato gerador", _exists(fiscal.get("municipio_codigo_ibge")))
    for tag, label in (
        ("cUF", "Código da UF do emitente"),
        ("nNF", "Número fiscal (não confundir com número da venda)"),
        ("natOp", "Natureza da operação"),
        ("dhEmi", "Data/hora oficial de emissão"),
        ("tpNF", "Tipo de operação validado"),
        ("finNFe", "Finalidade da NF-e"),
    ):
        _pending(ide, tag, label)

    emit = _group("emit", "Emitente")
    _field(emit, "CNPJ", "CNPJ do emitente com validação", "EMITENTE_CNPJ" not in codigos)
    _field(emit, "xNome", "Razão social do emitente", _exists(emitente.get("nome")))
    _field(emit, "IE", "Inscrição Estadual ou situação fiscal verificada",
           _exists(fiscal.get("inscricao_estadual")))
    _field(emit, "CRT", "Código de regime tributário", _exists(fiscal.get("crt")))
    _field(emit, "enderEmit", "Endereço e código IBGE do emitente",
           all(_exists(fiscal.get(k)) for k in (
               "uf", "municipio_codigo_ibge", "cidade", "cep", "logradouro", "numero", "bairro"
           )))

    dest_group = _group("dest", "Destinatário")
    _field(dest_group, "CPF/CNPJ", "Documento do destinatário validado",
           bool(dest) and "DESTINATARIO_DOCUMENTO" not in codigos)
    _field(dest_group, "xNome", "Nome/razão social do destinatário", _exists(dest.get("nome")))
    _field(dest_group, "enderDest", "Endereço do destinatário",
           bool(dest) and all(_exists(dest.get(k)) for k in (
               "cep", "logradouro", "numero", "bairro", "cidade", "estado"
           )))
    _pending(dest_group, "indIEDest", "Indicador de IE / contribuinte do ICMS")

    det = _group("det", "Itens e produtos")
    _field(det, "det[]", "Existência de produtos elegíveis", bool(produtos))
    for idx, item in enumerate(produtos, start=1):
        prefix = f"det[{idx}]/prod/"
        _field(det, prefix + "cProd", f"Item {idx}: código do produto",
               _exists(item.get("codigo_interno")))
        _field(det, prefix + "xProd", f"Item {idx}: descrição", _exists(item.get("descricao")))
        _field(det, prefix + "uCom", f"Item {idx}: unidade comercial",
               _exists(item.get("unidade")))
        _field(det, prefix + "qCom", f"Item {idx}: quantidade",
               _positive(item.get("quantidade")))
        _field(det, prefix + "vUnCom", f"Item {idx}: valor unitário",
               _positive(item.get("preco_unitario")))
        _field(det, prefix + "vProd", f"Item {idx}: subtotal",
               _positive(item.get("subtotal")))
        # Cadastro NCM/CFOP por SKU já é conferido em fiscal_nfe_cadastros.
        # A validação por operação/UF e o XML continuam fora de escopo.
        _pending(det, prefix + "NCM", f"Item {idx}: NCM fiscal validado")
        _pending(det, prefix + "CFOP", f"Item {idx}: CFOP fiscal por operação")

    impostos = _group("imposto", "Tributação por item")
    _pending(impostos, "ICMS", "ICMS, CST/CSOSN e base por operação")
    _pending(impostos, "PIS/COFINS", "PIS e COFINS por item")
    _pending(impostos, "IBS/CBS", "IBS/CBS e cClassTrib conforme NT vigente")
    _pending(impostos, "IPI/IS", "IPI/Imposto Seletivo quando aplicável")

    totais = _group("total", "Totais")
    _field(totais, "vProd", "Soma dos subtotais conciliada",
           "DIVERGENCIA_ITENS" not in codigos
           and "SUBTOTAL_INVALIDO" not in codigos and bool(produtos))
    _pending(totais, "vNF", "Valor fiscal: confirmar base e totalizar tributos")
    _pending(totais, "ICMSTot", "Totais de ICMS, PIS, COFINS, etc.")
    _pending(totais, "IBSCBSTot", "Totalização IBS/CBS conforme NT vigente")

    transp = _group("transp", "Transporte")
    _pending(transp, "modFrete", "Modalidade de frete / transportadora")

    pag = _group("pag", "Pagamento e cobrança")
    _pending(pag, "detPag", "Formas de pagamento ligadas à venda")
    _pending(pag, "cobr", "Faturas/duplicatas quando aplicável")

    adicionais = _group("infAdic", "Informações adicionais")
    _field(adicionais, "infCpl", "Texto complementar cadastrado",
           _exists(fiscal.get("informacoes_complementares")))

    assinatura = _group("Signature", "Assinatura, validação e autorização")
    for tag, label in (
        ("infNFe/@Id", "Identificador e chave de acesso NF-e"),
        ("XSD", "Validação contra schemas oficiais vigentes"),
        ("Signature", "Assinatura digital com certificado A1"),
        ("SEFAZ", "Autorização e protocolo"),
        ("DANFE", "DANFE após emissão autorizada"),
    ):
        _pending(assinatura, tag, label)

    groups = [ide, emit, dest_group, det, impostos, totais, transp, pag, adicionais, assinatura]
    counted = [f for g in groups for f in g["campos"]]
    return {
        "tipo": "MAPA_PRE_XML_NFE",
        "versao_mapa": 1,
        "modelo": "55",
        "estado": "NAO_APTO_EMISSAO",
        "xml_gerado": False,
        "schema_validado": False,
        "chave_gerada": False,
        "assinado": False,
        "transmitido": False,
        "grupos": groups,
        "resumo": {
            "grupos_total": len(groups),
            "campos_informados": sum(c["situacao"] == "INFORMADO" for c in counted),
            "campos_pendentes": sum(c["situacao"] == "PENDENTE" for c in counted),
            "integracoes_pendentes": sum(c["situacao"] == "INTEGRACAO_PENDENTE" for c in counted),
        },
        "aviso": (
            "Checklist cadastral e técnico, NÃO é XML NF-e válido, rascunho fiscal, "
            "DANFE ou autorização. Regras tributárias e NTs vigentes exigem homologação."
        ),
    }
