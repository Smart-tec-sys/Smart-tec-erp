import json
from html import escape

from app.services.producao_service import serializar


def ficha_html(db, ordem):
    dados = serializar(db, ordem)
    e = lambda valor: escape(str(valor if valor is not None else ""))
    linhas = "".join(
        "<tr>" + "".join(f"<td>{e(peca[campo])}</td>" for campo in (
            "codigo", "modelo", "tecido", "cor", "largura", "altura", "acionamento",
            "quantidade", "ambiente", "observacoes", "modo_fabricacao",
            "versao_ficha", "conferido_por", "status",
        )) + "</tr>" for peca in dados["pecas"]
    )
    composicoes = []
    for peca in dados["pecas"]:
        componentes = peca.get("componentes") or []
        if not componentes:
            continue
        composicoes.append(
            f"<h3>{e(peca['codigo'])} — composição manual supervisionada "
            "(não representa BOM homologada)</h3><table><thead><tr>"
            "<th>Produto</th><th>ID</th><th>Quantidade</th><th>Unidade</th>"
            "<th>Corte</th><th>Custo unitário informado/cadastro</th>"
            "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join(f"<td>{e(componente.get(campo))}</td>" for campo in (
                    "descricao", "produto_id", "quantidade", "unidade",
                    "comprimento_corte", "custo_unitario",
                )) + "</tr>"
                for componente in componentes
            )
            + "</tbody></table><p>Especificações: "
            + e(json.dumps(peca.get("especificacoes_fabricacao") or {}, ensure_ascii=False))
            + "</p>"
        )
    composicoes_html = "".join(composicoes)
    pendencias = "".join(f"<li>{e(p)}</li>" for p in dados["pendencias"])
    calculos = e(json.dumps(dados["calculos_por_peca"], ensure_ascii=False, indent=2))
    situacao = "LIBERADA" if ordem.liberado_em else "NÃO LIBERADA PARA FABRICAÇÃO"
    return f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>Ficha OP-{ordem.id:06d}</title>
<style>body{{font:12px Arial;color:#111}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #aaa;padding:5px;text-align:left;overflow-wrap:anywhere}}
pre{{white-space:pre-wrap}}tr{{break-inside:avoid}}@media print{{button{{display:none}}}}
@page{{size:A4 landscape;margin:10mm}}</style>
<button onclick="window.print()">Imprimir ficha</button>
<h1>OP-{ordem.id:06d} — {e(ordem.snapshot['empresa'])}</h1>
<h2>{situacao}</h2><p>Venda: {e(ordem.snapshot['pedido'])} |
Prazo: {e(ordem.snapshot['prazo_entrega'])} | Medidas em metros</p>
<p>Confirmação: usuário {e(ordem.confirmado_por)}, {e(ordem.confirmado_em)}<br>
Liberação: usuário {e(ordem.liberado_por)}, {e(ordem.liberado_em)}</p>
<ul>{pendencias}</ul><table><thead><tr>
<th>Peça</th><th>Modelo</th><th>Tecido</th><th>Cor</th><th>Largura</th><th>Altura</th>
<th>Acionamento</th><th>Quantidade</th><th>Ambiente</th><th>Observações</th>
<th>Modo</th><th>Versão</th><th>Conferido por</th><th>Status</th>
</tr></thead><tbody>{linhas}</tbody></table>
{composicoes_html}
<h2>Cálculos e insumos por peça (não multiplicar novamente)</h2><pre>{calculos}</pre>
<p>Sem reserva ou baixa de estoque. Faturamento não significa fabricação.</p></html>"""


def _dados_etiqueta(ordem, peca):
    observacoes = peca.observacoes or ""
    if peca.modo_fabricacao == "MANUAL_SUPERVISIONADA":
        observacoes = "COMPOSIÇÃO MANUAL SUPERVISIONADA — NÃO HOMOLOGADA. " + observacoes
    especificacoes = peca.especificacoes_fabricacao or {}
    if especificacoes:
        observacoes = f"{observacoes} | Especificações: {json.dumps(especificacoes, ensure_ascii=False)}"
    dados = {
        "empresa": ordem.snapshot["empresa"], "pedido": ordem.snapshot["pedido"],
        "cliente": ordem.snapshot.get("cliente", ""),
        "codigo": f"OP-{ordem.id:06d}-I{peca.pedido_item_id}-P{peca.sequencia:04d}",
        "item": f"{peca.pedido_item_id}/{peca.sequencia}", "tipo_etiqueta": "PRODUCAO",
        "data": ordem.liberado_em.isoformat() if ordem.liberado_em else "",
        "largura": f"{peca.largura} m", "altura": f"{peca.altura} m",
        "quantidade": str(peca.quantidade),
        **{campo: getattr(peca, campo) for campo in (
            "modelo", "tecido", "cor", "acionamento", "ambiente",
        )},
        "observacoes": observacoes,
    }
    return {campo: escape(str(valor or "")) for campo, valor in dados.items()}


def etiqueta_da_peca(ordem, peca):
    from modulos.produtos_etiquetas import gerar_html_impressao

    documento = gerar_html_impressao(
        _dados_etiqueta(ordem, peca), 1, 2, 90, 60, mostrar_qr=True, mostrar_barcode=True,
        abrir_impressao=False, modelo_layout="Completo",
    )
    return documento.replace("<body>", """<body>
<style>@media print { .op-imprimir { display:none } }</style>
<button class="op-imprimir" onclick="window.print()">Imprimir etiqueta</button>""", 1)


def etiquetas_lote_html(ordem):
    from modulos.produtos_etiquetas import gerar_html_impressao_lote

    dados = [_dados_etiqueta(ordem, peca) for peca in ordem.pecas]
    documento = gerar_html_impressao_lote(
        dados, 2, 90, 60, mostrar_qr=True, mostrar_barcode=True,
        abrir_impressao=False, modelo_layout="Completo",
    )
    return documento.replace("<body>", """<body>
<style>@media print { .op-imprimir { display:none } }</style>
<button class="op-imprimir" onclick="window.print()">Imprimir etiquetas do lote</button>""", 1)
