import json
from html import escape

from app.services.producao_service import serializar


def ficha_html(db, ordem):
    dados = serializar(db, ordem)
    e = lambda valor: escape(str(valor if valor is not None else ""))
    linhas = "".join(
        "<tr>" + "".join(f"<td>{e(peca[campo])}</td>" for campo in (
            "codigo", "modelo", "tecido", "cor", "largura", "altura", "acionamento",
            "ambiente", "observacoes", "status",
        )) + "</tr>" for peca in dados["pecas"]
    )
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
<th>Acionamento</th><th>Ambiente</th><th>Observações</th><th>Status</th>
</tr></thead><tbody>{linhas}</tbody></table>
<h2>Cálculos e insumos por peça (não multiplicar novamente)</h2><pre>{calculos}</pre>
<p>Sem reserva ou baixa de estoque. Faturamento não significa fabricação.</p></html>"""


def etiqueta_da_peca(ordem, peca):
    from modulos.produtos_etiquetas import gerar_html_impressao

    dados = {
        "empresa": ordem.snapshot["empresa"], "pedido": ordem.snapshot["pedido"],
        "codigo": f"OP-{ordem.id:06d}-I{peca.pedido_item_id}-P{peca.sequencia:04d}",
        "item": f"{peca.pedido_item_id}/{peca.sequencia}", "tipo_etiqueta": "PRODUCAO",
        "data": ordem.liberado_em.isoformat() if ordem.liberado_em else "",
        "largura": f"{peca.largura} m", "altura": f"{peca.altura} m",
        **{campo: getattr(peca, campo) for campo in (
            "modelo", "tecido", "cor", "acionamento", "ambiente",
        )},
    }
    seguros = {campo: escape(str(valor or "")) for campo, valor in dados.items()}
    documento = gerar_html_impressao(
        seguros, 1, 2, 90, 60, mostrar_qr=True, mostrar_barcode=True,
        abrir_impressao=False, modelo_layout="Completo",
    )
    return documento.replace("<body>", """<body>
<style>@media print { .op-imprimir { display:none } }</style>
<button class="op-imprimir" onclick="window.print()">Imprimir etiqueta</button>""", 1)
