"""Diagnóstico preliminar de NF-e a partir de venda. Não gera, assina ou transmite XML."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from app.models.cliente import ClienteDB
from app.models.empresa import EmpresaDB
from app.services import pedido_service
from app.services.fiscal_nfe_cadastros import conferir_cadastros_fiscais

_CENT = Decimal("0.01")
_DIGITS = re.compile(r"\D")


def _money(value) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            return None
        return number.quantize(_CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _document(value) -> str:
    return _DIGITS.sub("", str(value or ""))


def _valid_document(value) -> bool:
    digits = _document(value)
    if len(digits) not in (11, 14) or len(set(digits)) == 1:
        return False
    if len(digits) == 11:
        for size in (9, 10):
            total = sum(int(n) * w for n, w in zip(digits[:size], range(size + 1, 1, -1)))
            digit = (total * 10) % 11
            if digit == 10:
                digit = 0
            if digit != int(digits[size]):
                return False
        return True
    for size, weights in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
                          (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        rest = sum(int(d) * w for d, w in zip(digits[:size], weights)) % 11
        digit = 0 if rest < 2 else 11 - rest
        if digit != int(digits[size]):
            return False
    return True


def analisar_venda_nfe(pedido: dict, empresa: dict, destinatario: dict | None) -> dict:
    """Operação pura. Campos ausentes geram pendências; nunca supõe tributação."""
    pendencias: list[dict] = []

    def add(codigo: str, mensagem: str, campo: str, nivel: str = "bloqueante"):
        pendencias.append({"codigo": codigo, "campo": campo, "nivel": nivel, "mensagem": mensagem})

    if not _valid_document(empresa.get("documento")) or len(_document(empresa.get("documento"))) != 14:
        add("EMITENTE_CNPJ", "CNPJ do emitente ausente ou inválido.", "emitente.documento")
    if not destinatario:
        add("DESTINATARIO", "Vincule um cliente cadastrado à venda para preparar a NF-e.", "venda.cliente_id")
    else:
        if not str(destinatario.get("nome") or "").strip():
            add("DESTINATARIO_NOME", "Nome ou razão social do destinatário ausente.", "destinatario.nome")
        if not _valid_document(destinatario.get("documento")):
            add("DESTINATARIO_DOCUMENTO", "CPF/CNPJ do destinatário ausente ou inválido.", "destinatario.documento")
        for field, message in (
            ("cep", "CEP"), ("logradouro", "logradouro"), ("numero", "número"),
            ("bairro", "bairro"), ("cidade", "cidade"), ("estado", "UF"),
        ):
            if not str(destinatario.get(field) or "").strip():
                add("DESTINATARIO_ENDERECO_" + field.upper(), f"Informe {message} do destinatário.", "destinatario." + field)

    itens = pedido.get("itens") or []
    if not itens:
        add("SEM_ITENS", "A venda não possui itens.", "venda.itens")

    soma = Decimal("0.00")
    itens_validos = 0
    for idx, item in enumerate(itens, start=1):
        scope = f"venda.itens[{idx}]"
        if str(item.get("tipo_item") or "PRODUTO").upper() != "PRODUTO":
            add("SERVICO_NA_NFE", "Item de serviço requer classificação fiscal própria; avaliar NFS-e.", scope + ".tipo_item")
            continue
        if not item.get("produto_id"):
            add("PRODUTO_SEM_ID", "Produto sem vínculo cadastral.", scope + ".produto_id")
        if not str(item.get("descricao") or "").strip():
            add("ITEM_SEM_DESCRICAO", "Descrição do item ausente.", scope + ".descricao")
        quantidade = _money(item.get("quantidade"))
        subtotal = _money(item.get("subtotal"))
        if quantidade is None or quantidade <= 0:
            add("QUANTIDADE_INVALIDA", "Quantidade ausente ou inválida.", scope + ".quantidade")
        if subtotal is None or subtotal < 0:
            add("SUBTOTAL_INVALIDO", "Subtotal ausente ou inválido.", scope + ".subtotal")
        else:
            soma += subtotal
        itens_validos += 1

    total = _money(pedido.get("total"))
    desconto = _money(pedido.get("desconto"))
    final = _money(pedido.get("total_final"))
    if total is None or total < 0 or final is None or final <= 0 or desconto is None or desconto < 0:
        add("TOTAIS_INVALIDOS", "Total, desconto ou total final inválidos.", "venda.total_final")
    else:
        if (soma - total).copy_abs() > _CENT:
            add("DIVERGENCIA_ITENS", "A soma dos subtotais não confere com o total da venda.", "venda.total")
        if (total - desconto - final).copy_abs() > _CENT:
            add("DIVERGENCIA_DESCONTO", "O desconto não reconcilia o total final.", "venda.total_final")

    # O preço de venda ao cliente final pode incluir parceiro/RT/taxa financeira.
    # Não escolher automaticamente entre as bases comerciais para tributação.
    total_cliente = _money(pedido.get("total_cliente_final"))
    if total_cliente is not None and final is not None and (total_cliente - final).copy_abs() > _CENT:
        add("BASE_FATURAMENTO_A_DEFINIR",
            "Há diferença entre total interno e total ao cliente; confirme a base fiscal com a contabilidade.",
            "venda.total_cliente_final")

    # Não existem CFOP/NCM/CST/CSOSN/CRT nem XML/SEFAZ implementados neste fluxo.
    for code, message in (
        ("CONFIGURACAO_TRIBUTARIA", "Completar e validar CRT, CFOP, NCM, CST/CSOSN e tributos por item."),
        ("EMITENTE_ENDERECO_FISCAL", "Completar cadastro fiscal e endereço do estabelecimento emitente."),
        ("SEFAZ_NAO_INTEGRADA", "Assinatura, esquema XML, certificado e autorização SEFAZ não integrados."),
    ):
        add(code, message, "fiscal")

    return {
        "documento": "NFE",
        "estado": "NAO_APTO_EMISSAO",
        "simulacao": True,
        "transmitido": False,
        "empresa_id": empresa.get("id"),
        "pedido_id": pedido.get("id"),
        "numero_venda": pedido.get("numero"),
        "resumo": {
            "total_itens": len(itens),
            "itens_produto": itens_validos,
            "soma_subtotais": str(soma.quantize(_CENT)),
            "total_venda": str(total) if total is not None else None,
            "desconto": str(desconto) if desconto is not None else None,
            "total_final": str(final) if final is not None else None,
            "total_cliente_final": str(total_cliente) if total_cliente is not None else None,
        },
        "pendencias": pendencias,
        "quantidade_pendencias": len(pendencias),
        "aviso": "Pré-validação apenas. Este resultado não é nota fiscal, XML autorizado ou DANFE.",
    }


def preparar_venda_nfe(db, pedido_id: int, tenant):
    empresa_id = pedido_service._empresa_id(tenant)
    pedido = pedido_service.obter(db, pedido_id, tenant)
    if pedido is None:
        return None
    empresa = db.query(EmpresaDB).filter(EmpresaDB.id == empresa_id).first()
    if empresa is None:
        raise ValueError("Empresa ativa não encontrada.")
    cliente = None
    if pedido.get("cliente_id"):
        row = db.query(ClienteDB).filter(
            ClienteDB.id == pedido["cliente_id"], ClienteDB.empresa_id == empresa_id
        ).first()
        if row is not None:
            cliente = {field: getattr(row, field) for field in (
                "nome", "documento", "cep", "logradouro", "numero", "bairro", "cidade", "estado"
            )}
    resultado = analisar_venda_nfe(
        pedido,
        {"id": empresa.id, "documento": empresa.documento},
        cliente,
    )
    # Validação cadastral complementar por empresa e SKU: apenas leitura.
    pendencias_fiscais, resumo_cadastros = conferir_cadastros_fiscais(
        db, pedido, empresa, empresa_id,
    )
    # Mensagens de cadastro detalhadas complementam o diagnóstico geral.
    resultado["pendencias"].extend(pendencias_fiscais)
    resultado["quantidade_pendencias"] = len(resultado["pendencias"])
    resultado["cadastros_fiscais"] = resumo_cadastros
    return resultado
