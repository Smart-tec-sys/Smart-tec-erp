from datetime import date
from decimal import Decimal as D

import pytest

from tests.test_financeiro_titulos_f2a import A, B, cadastros, db, legado, novo  # noqa: F401
from app.schemas.financeiro_titulos import BaixaCreate
from app.services import financeiro_cadastros_service as cad
from app.services import financeiro_fluxo_caixa_service as fx
from app.services import financeiro_titulos_service as svc

INI, FIM = date(2026, 12, 1), date(2026, 12, 31)


def baixa(db, tid, valor, dia="2026-12-05", tenant=A, **kw):
    return svc.baixar(db, tid, tenant, BaixaCreate(data_baixa=dia, valor=str(valor), **kw).dict())


def titulo(db, tipo="R", valor="100.00", tenant=A, **kw):
    return svc.criar(db, tenant, novo(tipo, valor_original=valor, **kw))


def calc(db, tenant=A, **kw):
    kw.setdefault("data_inicial", INI)
    kw.setdefault("data_final", FIM)
    return fx.calcular(db, tenant, **kw)


def conta(db, nome, saldo, tenant=A):
    return cad.criar(db, "contas-financeiras", tenant, {"nome": nome, "tipo": "BANCO", "saldo_inicial": saldo, "ativo": True})


def test_recebimento_e_pagamento_realizados(db):
    r = titulo(db, "R", "300.00")
    p = titulo(db, "P", "120.00")
    baixa(db, r["id"], 300)
    baixa(db, p["id"], 120, "2026-12-06")
    res = calc(db)["resumo"]
    assert res["recebimentos"] == D("300.00") and res["pagamentos"] == D("120.00")
    assert res["saldo_realizado"] == D("180.00") and res["saldo_previsto"] == D("180.00")


def test_baixa_parcial_divide_realizado_e_previsto(db):
    r = titulo(db, "R", "100.00")
    baixa(db, r["id"], 40)
    out = calc(db)
    assert out["resumo"]["recebimentos"] == D("40.00") and out["resumo"]["recebimentos_previstos"] == D("60.00")
    assert out["resumo"]["saldo_previsto"] == D("100.00")
    nat = sorted((m["natureza"], m["valor"]) for m in out["movimentos"])
    assert nat == [("PREVISTO", D("60.00")), ("REALIZADO", D("40.00"))]  # sem duplicar


def test_baixa_total_sai_do_previsto(db):
    r = titulo(db, "R", "100.00")
    baixa(db, r["id"], 100)
    out = calc(db)
    assert out["resumo"]["recebimentos_previstos"] == 0
    assert [m["natureza"] for m in out["movimentos"]] == ["REALIZADO"]


def test_estorno_volta_ao_previsto(db):
    r = titulo(db, "R", "100.00")
    b = baixa(db, r["id"], 100)["baixa"]
    svc.estornar(db, b["id"], A)
    out = calc(db)
    assert out["resumo"]["recebimentos"] == 0 and out["resumo"]["recebimentos_previstos"] == D("100.00")
    assert [m["natureza"] for m in out["movimentos"]] == ["PREVISTO"]


def test_baixa_com_juros_e_desconto_usa_dinheiro_efetivo(db):
    r = titulo(db, "R", "100.00")
    baixa(db, r["id"], 105, juros=5)
    res = calc(db)["resumo"]
    assert res["recebimentos"] == D("105.00") and res["recebimentos_previstos"] == 0


def test_titulo_legado_pago_sem_baixas(db):
    legado(db, pedido_id=None, status="PAGO", pagamento="2026-12-12", valor=250, vencimento="2026-12-01")
    out = calc(db)
    assert out["resumo"]["recebimentos"] == D("250.00") and out["resumo"]["recebimentos_previstos"] == 0
    mov = out["movimentos"][0]
    assert mov["legado"] and mov["situacao"] == "Realizado (legado)" and mov["data"] == date(2026, 12, 12) and mov["baixa_id"] is None
    assert db.execute(__import__("sqlalchemy").text("SELECT count(*) FROM financeiro_baixas")).scalar() == 0


def test_conta_especifica_consolidado_e_sem_conta(db):
    c1, c2 = conta(db, "Banco 1", "1000"), conta(db, "Banco 2", "500")
    t1 = titulo(db, "R", "100.00", conta_financeira_id=c1.id)
    t2 = titulo(db, "R", "50.00", conta_financeira_id=c2.id)
    t3 = titulo(db, "P", "20.00")  # sem conta
    baixa(db, t1["id"], 100)
    baixa(db, t2["id"], 50, conta_financeira_id=c1.id)  # baixa prevalece sobre a conta do titulo
    baixa(db, t3["id"], 20)
    total = calc(db)
    assert total["resumo"]["saldo_realizado"] == D("1630.00")  # 1500 + 150 - 20
    assert {m["conta"] for m in total["movimentos"]} == {"Banco 1", "Sem conta definida"}
    um = calc(db, conta_financeira_id=c1.id)["resumo"]
    assert um["saldo_inicial"] == D("1000.00") and um["recebimentos"] == D("150.00") and um["saldo_realizado"] == D("1150.00")
    dois = calc(db, conta_financeira_id=c2.id)["resumo"]
    assert dois["recebimentos"] == 0 and dois["saldo_realizado"] == D("500.00")


def test_saldo_inicial_inclui_movimentos_anteriores(db):
    c = conta(db, "Banco", "1000")
    t = titulo(db, "R", "100.00", conta_financeira_id=c.id)
    baixa(db, t["id"], 100, "2026-11-20")
    res = calc(db)["resumo"]
    assert res["saldo_inicial"] == D("1100.00") and res["recebimentos"] == 0 and res["saldo_realizado"] == D("1100.00")


def test_isolamento_por_empresa(db):
    conta(db, "Banco A", "100")
    conta(db, "Banco B", "9999", tenant=B)
    tb = titulo(db, "R", "70.00", tenant=B)
    baixa(db, tb["id"], 70, tenant=B)
    ta = titulo(db, "R", "10.00")
    res = calc(db)
    assert res["resumo"]["recebimentos"] == 0 and res["resumo"]["saldo_inicial"] == D("100.00")
    assert [m["titulo_id"] for m in res["movimentos"]] == [ta["id"]]
    assert calc(db, tenant=B)["resumo"]["recebimentos"] == D("70.00")
    # conta de outra empresa nao pode ser usada como filtro
    outra = db.query(fx.ContaFinanceiraDB).filter_by(empresa_id=2).first()
    with pytest.raises(fx.FluxoInvalido):
        calc(db, conta_financeira_id=outra.id)


def test_cancelado_e_baixa_estornada_nao_entram(db):
    legado(db, pedido_id=None, status="CANCELADO", vencimento="2026-12-10")
    t = titulo(db, "R", "100.00")
    b = baixa(db, t["id"], 30)["baixa"]
    svc.estornar(db, b["id"], A)
    res = calc(db)["resumo"]
    assert res["recebimentos"] == 0 and res["recebimentos_previstos"] == D("100.00")  # so o aberto, sem o cancelado
    c = titulo(db, "R", "55.00")
    baixa(db, c["id"], 20)
    db.execute(__import__("sqlalchemy").text("UPDATE financeiro SET status='CANCELADO' WHERE id=:i"), {"i": c["id"]})
    db.commit()
    res = calc(db)["resumo"]
    assert res["recebimentos"] == 0 and res["recebimentos_previstos"] == D("100.00")


def test_periodo_inicial_final(db):
    t = titulo(db, "R", "100.00", vencimento="2026-12-20")
    baixa(db, t["id"], 40, "2026-12-05")
    res = calc(db, data_inicial=date(2026, 12, 6), data_final=date(2026, 12, 31))["resumo"]
    assert res["recebimentos"] == 0 and res["saldo_inicial"] == D("40.00") and res["recebimentos_previstos"] == D("60.00")
    res = calc(db, data_inicial=date(2026, 12, 1), data_final=date(2026, 12, 10))["resumo"]
    assert res["recebimentos"] == D("40.00") and res["recebimentos_previstos"] == 0
    atrasado = calc(db, data_inicial=date(2026, 12, 21), data_final=date(2026, 12, 31))["resumo"]
    assert atrasado["atrasados_receber"] == D("60.00") and atrasado["recebimentos_previstos"] == 0
    with pytest.raises(fx.FluxoInvalido):
        calc(db, data_inicial=date(2026, 12, 10), data_final=date(2026, 12, 1))
    with pytest.raises(fx.FluxoInvalido):
        calc(db, data_inicial=date(2025, 1, 1), data_final=date(2026, 12, 31))


def test_saldo_diario_encadeado_e_igual_ao_resumo(db):
    conta(db, "Banco", "100")
    r = titulo(db, "R", "200.00", vencimento="2026-12-03")
    p = titulo(db, "P", "50.00", vencimento="2026-12-04")
    titulo(db, "R", "30.00", vencimento="2026-12-20")
    baixa(db, r["id"], 120, "2026-12-02")
    baixa(db, p["id"], 50, "2026-12-04")
    out = calc(db, data_inicial=date(2026, 12, 1), data_final=date(2026, 12, 5))
    d = out["diario"]
    assert len(d) == 5
    for ant, atual in zip(d, d[1:]):
        assert atual["saldo_inicial"] == ant["saldo_dia"]
    assert d[0]["saldo_inicial"] == D("100.00") and d[1]["recebimentos"] == D("120.00") and d[1]["saldo_dia"] == D("220.00")
    assert d[2]["recebimentos_previstos"] == D("80.00") and d[2]["saldo_previsto"] == D("300.00")
    assert d[3]["pagamentos"] == D("50.00") and d[3]["saldo_dia"] == D("170.00")
    assert d[-1]["saldo_dia"] == out["resumo"]["saldo_realizado"] and d[-1]["saldo_previsto"] == out["resumo"]["saldo_previsto"]


def test_modos_e_filtros_dimensionais(db):
    c = cadastros(db, A)
    conta(db, "Banco", "100")
    a = titulo(db, "R", "100.00", centro_custo_id=c["centro"].id, plano_conta_id=c["plano_r"].id)
    titulo(db, "R", "60.00")
    baixa(db, a["id"], 100)
    assert calc(db, modo="realizado")["resumo"]["recebimentos_previstos"] == 0
    prev = calc(db, modo="previsto")["resumo"]
    assert prev["recebimentos"] == 0 and prev["recebimentos_previstos"] == D("60.00")
    cc = calc(db, centro_custo_id=c["centro"].id)["resumo"]
    assert cc["recebimentos"] == D("100.00") and cc["recebimentos_previstos"] == 0
    assert cc["saldo_inicial_contas_incluido"] is False and cc["saldo_inicial"] == 0
    assert calc(db, plano_conta_id=c["plano_r"].id)["resumo"]["recebimentos"] == D("100.00")
    assert calc(db, origem="VENDA")["resumo"]["recebimentos"] == 0
    assert calc(db, origem="MANUAL")["resumo"]["recebimentos"] == D("100.00")
    with pytest.raises(fx.FluxoInvalido):
        calc(db, modo="x")


def test_movimentos_apontam_para_baixa_e_titulo(db):
    t = titulo(db, "R", "100.00")
    b = baixa(db, t["id"], 40)["baixa"]
    lista = fx.movimentos(db, A, data_inicial=INI, data_final=FIM)
    real = [m for m in lista["itens"] if m["natureza"] == "REALIZADO"][0]
    assert lista["total"] == 2 and real["baixa_id"] == b["id"] and real["titulo_id"] == t["id"] and real["origem"] == "MANUAL"
    assert fx.movimentos(db, A, data_inicial=INI, data_final=FIM, limit=1)["itens"].__len__() == 1
