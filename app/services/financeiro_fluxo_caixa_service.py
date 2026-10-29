"""Fluxo de caixa (F3) — calculo unico reutilizado por resumo, diario e movimentos.

Nao existe tabela propria: tudo deriva de `financeiro`, `financeiro_baixas` e
`contas_financeiras`.

REALIZADO (dinheiro efetivo)
  * cada baixa ATIVA (estornada_em IS NULL) vira um movimento na data da baixa,
    no valor em dinheiro da baixa (`valor`);
  * titulo legado: status PAGO e nenhuma baixa ativa => um movimento na data de
    `pagamento` (ou data_baixa / vencimento) no valor do titulo. Nao ha baixa artificial.
PREVISTO
  * titulo nao quitado (status diferente de PAGO/CANCELADO) com saldo > 0, na data do
    vencimento, pelo SALDO calculado por `calcular_valores` (mesma regra da F2B).
  * baixa parcial => parte realizada em REALIZADO, restante em PREVISTO; baixa total
    => nada em PREVISTO; estorno => sai do REALIZADO e o saldo volta ao PREVISTO.
Titulos CANCELADOS nunca entram. Empresa sempre filtrada.

SALDOS
  saldo_inicial_periodo = sum(contas.saldo_inicial) + realizado anterior a data_inicial
  saldo_realizado       = saldo_inicial_periodo + recebimentos - pagamentos (no periodo)
  saldo_previsto        = saldo_realizado + recebimentos_previstos - pagamentos_previstos
  Conta informada: so a conta (saldo inicial e movimentos dela). Sem conta: consolidado,
  incluindo movimentos "Sem conta definida".
  Com filtro de centro de custo, plano de contas ou origem o saldo inicial das contas nao
  e incluido (saldo bancario nao pertence a uma dimensao analitica).
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.financeiro import FinanceiroBaixaDB as B
from app.models.financeiro import FinanceiroDB as T
from app.models.financeiro_cadastros import ContaFinanceiraDB
from app.services import financeiro_titulos_service as titulos

ZERO = Decimal("0")
CENT = Decimal("0.01")
MAX_DIAS = 366
SEM_CONTA = "Sem conta definida"
MODOS = ("realizado", "previsto", "ambos")


class FluxoInvalido(Exception):
    pass


def _q(valor) -> Decimal:
    return Decimal(valor or 0).quantize(CENT)


def _periodo(data_inicial: Optional[date], data_final: Optional[date], hoje: Optional[date]):
    hoje = hoje or date.today()
    if data_inicial is None:
        data_inicial = hoje.replace(day=1)
    if data_final is None:
        proximo = (data_inicial.replace(day=28) + timedelta(days=4)).replace(day=1)
        data_final = proximo - timedelta(days=1)
    if data_final < data_inicial:
        raise FluxoInvalido("A data final deve ser igual ou posterior a data inicial.")
    if (data_final - data_inicial).days + 1 > MAX_DIAS:
        raise FluxoInvalido(f"O periodo maximo e de {MAX_DIAS} dias.")
    return data_inicial, data_final


def _movimentos_base(db: Session, empresa_id: int, plano_conta_id, centro_custo_id) -> list:
    consulta = db.query(T).filter(T.empresa_id == empresa_id)
    if plano_conta_id:
        consulta = consulta.filter(T.plano_conta_id == plano_conta_id)
    if centro_custo_id:
        consulta = consulta.filter(T.centro_custo_id == centro_custo_id)
    itens = [t for t in consulta.all() if (t.status or "ABERTO").upper() != "CANCELADO" and (t.tipo or "").upper() in ("R", "P")]
    if not itens:
        return []
    ids = [t.id for t in itens]
    baixas = db.query(B).filter(B.empresa_id == empresa_id, B.financeiro_id.in_(ids)).all()
    por_titulo = defaultdict(list)
    for b in baixas:
        por_titulo[b.financeiro_id].append(b)
    rt_ids = titulos._ids_vinculo(db, "representantes_rt", ids)
    contab_ids = titulos._ids_vinculo(db, "contabilidade_obrigacoes", ids)

    movimentos = []
    for t in itens:
        tipo = t.tipo.upper()
        origem = titulos._origem(t, rt_ids, contab_ids)
        ativas = [b for b in por_titulo.get(t.id, []) if b.estornada_em is None]
        cash = sum((b.valor for b in ativas), ZERO)
        credito = sum((b.valor - b.juros + b.desconto for b in ativas), ZERO)
        base = {"tipo": tipo, "origem": origem, "titulo_id": t.id, "descricao": t.descricao,
                "pedido_id": t.pedido_id, "centro_custo_id": t.centro_custo_id, "plano_conta_id": t.plano_conta_id}
        for b in ativas:
            movimentos.append({**base, "natureza": "REALIZADO", "legado": False, "data": b.data_baixa,
                               "valor": _q(b.valor), "baixa_id": b.id,
                               "conta_financeira_id": b.conta_financeira_id or t.conta_financeira_id})
        _, saldo = titulos.calcular_valores(t.valor, t.status, cash, credito, len(ativas))
        if not ativas and (t.status or "").upper() == "PAGO":
            movimentos.append({**base, "natureza": "REALIZADO", "legado": True,
                               "data": t.pagamento or t.data_baixa or t.vencimento,
                               "valor": _q(t.valor), "baixa_id": None, "conta_financeira_id": t.conta_financeira_id})
        elif saldo > 0 and (t.status or "ABERTO").upper() != "PAGO":
            movimentos.append({**base, "natureza": "PREVISTO", "legado": False, "data": t.vencimento,
                               "valor": _q(saldo), "baixa_id": None, "conta_financeira_id": t.conta_financeira_id})
    return movimentos


def calcular(db: Session, tenant, *, data_inicial=None, data_final=None, conta_financeira_id=None,
             centro_custo_id=None, plano_conta_id=None, origem=None, modo="ambos", hoje=None) -> dict:
    """Unico calculo do fluxo de caixa; resumo/diario/movimentos apenas fatiam o resultado."""
    empresa_id = titulos._empresa_id(tenant)
    modo = (modo or "ambos").lower()
    if modo not in MODOS:
        raise FluxoInvalido("Modo invalido. Use realizado, previsto ou ambos.")
    origem = origem.upper() if origem else None
    if origem and origem not in ("VENDA", "CONTABILIDADE", "RT", "MANUAL"):
        raise FluxoInvalido("Origem invalida.")
    inicio, fim = _periodo(data_inicial, data_final, hoje)

    contas = {c.id: c for c in db.query(ContaFinanceiraDB).filter(ContaFinanceiraDB.empresa_id == empresa_id).all()}
    if conta_financeira_id and conta_financeira_id not in contas:
        raise FluxoInvalido("Conta financeira nao encontrada nesta empresa.")
    for tabela, valor, rotulo in (("centros_custo", centro_custo_id, "Centro de custo"), ("plano_contas", plano_conta_id, "Plano de contas")):
        if valor and not titulos._nomes(db, tabela, [valor], empresa_id):
            raise FluxoInvalido(f"{rotulo} nao encontrado nesta empresa.")

    todos = _movimentos_base(db, empresa_id, plano_conta_id, centro_custo_id)
    if origem:
        todos = [m for m in todos if m["origem"] == origem]
    if conta_financeira_id:
        todos = [m for m in todos if m["conta_financeira_id"] == conta_financeira_id]

    incluir_saldo_contas = not (centro_custo_id or plano_conta_id or origem)
    saldo_contas = ZERO
    if incluir_saldo_contas:
        escolhidas = [contas[conta_financeira_id]] if conta_financeira_id else list(contas.values())
        saldo_contas = sum((_q(c.saldo_inicial) for c in escolhidas), ZERO)

    realizados = [m for m in todos if m["natureza"] == "REALIZADO"]
    previstos = [m for m in todos if m["natureza"] == "PREVISTO"]
    sinal = lambda m: m["valor"] if m["tipo"] == "R" else -m["valor"]

    saldo_inicial = saldo_contas + sum((sinal(m) for m in realizados if m["data"] < inicio), ZERO)
    no_periodo_real = [m for m in realizados if inicio <= m["data"] <= fim]
    no_periodo_prev = [m for m in previstos if inicio <= m["data"] <= fim]
    atrasados = [m for m in previstos if m["data"] < inicio]

    soma = lambda lista, tipo: sum((m["valor"] for m in lista if m["tipo"] == tipo), ZERO)
    rec, pag = soma(no_periodo_real, "R"), soma(no_periodo_real, "P")
    rec_prev, pag_prev = soma(no_periodo_prev, "R"), soma(no_periodo_prev, "P")
    if modo == "realizado":
        rec_prev = pag_prev = ZERO
    elif modo == "previsto":
        rec = pag = ZERO
    saldo_realizado = saldo_inicial + rec - pag
    saldo_previsto = saldo_realizado + rec_prev - pag_prev

    real_dia, prev_dia = defaultdict(lambda: [ZERO, ZERO]), defaultdict(lambda: [ZERO, ZERO])
    if modo != "previsto":
        for m in no_periodo_real:
            real_dia[m["data"]][0 if m["tipo"] == "R" else 1] += m["valor"]
    if modo != "realizado":
        for m in no_periodo_prev:
            prev_dia[m["data"]][0 if m["tipo"] == "R" else 1] += m["valor"]
    diario, corrente, acumulado_previsto = [], saldo_inicial, ZERO
    dia = inicio
    while dia <= fim:
        r, p = real_dia[dia] if dia in real_dia else (ZERO, ZERO)
        pr, pp = prev_dia[dia] if dia in prev_dia else (ZERO, ZERO)
        saldo_dia = corrente + r - p
        acumulado_previsto += pr - pp
        diario.append({"data": dia, "saldo_inicial": corrente, "recebimentos": r, "pagamentos": p,
                       "saldo_dia": saldo_dia, "recebimentos_previstos": pr, "pagamentos_previstos": pp,
                       "saldo_previsto": saldo_dia + acumulado_previsto})
        corrente = saldo_dia
        dia += timedelta(days=1)

    visiveis = (no_periodo_real if modo != "previsto" else []) + (no_periodo_prev if modo != "realizado" else [])
    visiveis.sort(key=lambda m: (m["data"], 0 if m["natureza"] == "REALIZADO" else 1, m["titulo_id"], m["baixa_id"] or 0))
    movimentos = [{
        "data": m["data"], "descricao": m["descricao"], "tipo": m["tipo"], "natureza": m["natureza"],
        "situacao": ("Realizado (legado)" if m["legado"] else "Realizado") if m["natureza"] == "REALIZADO" else "Previsto",
        "origem": m["origem"], "conta_financeira_id": m["conta_financeira_id"],
        "conta": contas[m["conta_financeira_id"]].nome if m["conta_financeira_id"] in contas else SEM_CONTA,
        "valor": m["valor"], "titulo_id": m["titulo_id"], "baixa_id": m["baixa_id"], "pedido_id": m["pedido_id"],
        "legado": m["legado"],
    } for m in visiveis]

    resumo = {
        "data_inicial": inicio, "data_final": fim, "modo": modo,
        "conta_financeira_id": conta_financeira_id or None,
        "saldo_inicial": saldo_inicial, "recebimentos": rec, "pagamentos": pag,
        "saldo_realizado": saldo_realizado,
        "recebimentos_previstos": rec_prev, "pagamentos_previstos": pag_prev, "saldo_previsto": saldo_previsto,
        "saldo_inicial_contas_incluido": incluir_saldo_contas,
        "atrasados_receber": soma(atrasados, "R") if modo != "realizado" else ZERO,
        "atrasados_pagar": soma(atrasados, "P") if modo != "realizado" else ZERO,
    }
    return {"resumo": resumo, "diario": diario, "movimentos": movimentos}


def resumo(db, tenant, **filtros) -> dict:
    return calcular(db, tenant, **filtros)["resumo"]


def diario(db, tenant, **filtros) -> list:
    return calcular(db, tenant, **filtros)["diario"]


def movimentos(db, tenant, *, limit: int = 200, offset: int = 0, **filtros) -> dict:
    itens = calcular(db, tenant, **filtros)["movimentos"]
    return {"total": len(itens), "itens": itens[offset:offset + limit]}
