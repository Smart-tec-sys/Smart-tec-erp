"""Cenarios comerciais; acrescimo do parceiro e taxa nao sao receita da fabrica."""

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP


def _centavos(valor):
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_condicoes_revenda(base_smarttec, percentual_parceiro, desconto_percentual,
                               acrescimo_cartao_percentual, parcelas):
    valores = [Decimal(str(v)) for v in (
        base_smarttec, percentual_parceiro, desconto_percentual, acrescimo_cartao_percentual,
    )]
    if not all(v.is_finite() for v in valores):
        raise ValueError("Os valores comerciais devem ser finitos.")
    base, percentual, desconto, taxa = valores
    if base <= 0 or percentual < 0 or percentual > 1000 or not 0 <= desconto < 100 or not 0 <= taxa < 100:
        raise ValueError("Base ou percentuais comerciais invalidos.")
    if type(parcelas) is not int or not 1 <= parcelas <= 12:
        raise ValueError("Informe de 1 a 12 parcelas inteiras.")
    base = _centavos(base)
    if base <= 0:
        raise ValueError("A base deve ser de pelo menos um centavo.")
    parceiro = _centavos(base * percentual / 100)
    preco = base + parceiro
    pix = _centavos(preco * (1 - desconto / 100))
    smart_pix = _centavos(base * (1 - desconto / 100))
    # O residual de centavos fica com o parceiro, mantendo a soma igual ao recebido.
    parceiro_pix = pix - smart_pix
    cartao = _centavos(preco * (1 + taxa / 100))
    parcela = (cartao / parcelas).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    prestacoes = [parcela] * (parcelas - 1) + [cartao - parcela * (parcelas - 1)]
    entrada = _centavos(pix / 2)
    return dict(
        base_smarttec=base, percentual_parceiro=percentual, acrescimo_parceiro=parceiro,
        preco_cliente=preco, desconto_percentual=desconto, desconto_total=preco - pix,
        total_descontado=pix, smarttec_descontado=smart_pix, parceiro_descontado=parceiro_pix,
        entrada=entrada, saldo=pix - entrada,
        acrescimo_cartao_percentual=taxa, acrescimo_cartao=cartao - preco,
        total_cartao=cartao, parcelas=prestacoes,
    )


def _moeda(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _percentual(valor):
    return format(valor.normalize(), "f").replace(".", ",")


def textos_condicoes_revenda(c):
    parcelas = " + ".join(_moeda(v) for v in c["parcelas"])
    publico = (
        "CONDICOES DE PAGAMENTO (alternativas, nao cumulativas):\n"
        f"Valor comercial: {_moeda(c['preco_cliente'])}.\n"
        f"A vista via Pix: {_percentual(c['desconto_percentual'])}% de desconto "
        f"({_moeda(c['desconto_total'])}); total {_moeda(c['total_descontado'])}.\n"
        f"Entrada e saldo na instalacao: {_percentual(c['desconto_percentual'])}% de desconto; "
        f"total {_moeda(c['total_descontado'])}; entrada de {_moeda(c['entrada'])} "
        f"e saldo na instalacao de {_moeda(c['saldo'])}.\n"
        f"Cartao ou link de pagamento em ate {len(c['parcelas'])}x: "
        f"total {_moeda(c['total_cartao'])}. Em {len(c['parcelas'])}x: {parcelas}."
    )
    interno = (
        "DEMONSTRATIVO COMERCIAL DA REVENDA - PROJECAO, NAO E RECEBIMENTO:\n"
        f"Base Smart-tec, incluindo instalacao: {_moeda(c['base_smarttec'])}.\n"
        f"Acrescimo da parceira: {_percentual(c['percentual_parceiro'])}% SOBRE a base Smart-tec "
        f"= {_moeda(c['acrescimo_parceiro'])}. Nao e divisao do recebido ou do lucro.\n"
        f"Preco comercial: {_moeda(c['preco_cliente'])}. "
        f"Smart-tec: {_moeda(c['base_smarttec'])}; parceira: {_moeda(c['acrescimo_parceiro'])}.\n"
        f"Pix / entrada e saldo: desconto proporcional de {_percentual(c['desconto_percentual'])}% "
        f"= {_moeda(c['desconto_total'])}. Cliente paga {_moeda(c['total_descontado'])}; "
        f"Smart-tec recebe {_moeda(c['smarttec_descontado'])}; "
        f"parceira recebe {_moeda(c['parceiro_descontado'])}.\n"
        f"Cartao / link: acrescimo simples de {_percentual(c['acrescimo_cartao_percentual'])}% "
        f"= {_moeda(c['acrescimo_cartao'])}, reservado para a taxa financeira, nao lucro. "
        f"Cliente paga {_moeda(c['total_cartao'])}; "
        f"Smart-tec: {_moeda(c['base_smarttec'])}; parceira: {_moeda(c['acrescimo_parceiro'])}.\n"
        "Valores Smart-tec antes dos custos industriais e da instalacao. "
        "O acrescimo simples e a condicao comercial aprovada; nao e calculo por dentro "
        "nem garante compensacao exata da tarifa efetiva do banco sobre o valor cobrado. "
        "A tarifa efetiva deve ser conciliada quando houver recebimento."
    )
    return publico, interno
