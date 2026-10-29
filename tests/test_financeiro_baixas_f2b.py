from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from tests.test_financeiro_titulos_f2a import A, B, cadastros, db, legado, novo  # noqa: F401
from app.models.financeiro import FinanceiroBaixaDB as Baixa
from app.schemas.financeiro_titulos import BaixaCreate
from app.services import financeiro_cadastros_service as cad
from app.services import financeiro_titulos_service as svc


def pagar(db, tid, valor, tenant=A, **kw):
    dados = {"data_baixa": "2026-12-05", "valor": str(valor)}
    dados.update(kw)
    return svc.baixar(db, tid, tenant, BaixaCreate(**dados).dict())


def titulo(db, tipo="R", valor="100.00", **kw):
    return svc.criar(db, A, novo(tipo, valor_original=valor, **kw))


def test_baixa_total(db):
    c = cadastros(db, A)
    t = titulo(db, situacao_financeira_id=c["aberto"].id)
    r = pagar(db, t["id"], 100, conta_financeira_id=c["conta"].id, forma_pagamento_id=c["forma"].id)
    assert r["baixa"]["ativa"] and r["baixa"]["conta_financeira_id"] == c["conta"].id
    out = r["titulo"]
    assert out["status"] == "PAGO" and out["saldo"] == 0 and out["valor_pago"] == D("100.00")
    assert out["data_baixa"] == date(2026, 12, 5) and out["pagamento"] == date(2026, 12, 5)
    assert out["situacao_financeira_id"] == c["pago"].id  # situacao quitada aplicada
    assert out["pode_baixar"] is False and out["pode_excluir"] is False


def test_baixa_parcial_e_multiplas(db):
    t = titulo(db)
    r = pagar(db, t["id"], 40, data_baixa="2026-12-03")
    assert r["titulo"]["status"] == "ABERTO" and r["titulo"]["saldo"] == D("60.00")
    assert r["titulo"]["valor_pago"] == D("40.00") and r["titulo"]["pagamento"] is None
    r = pagar(db, t["id"], 25, data_baixa="2026-12-10")
    assert r["titulo"]["saldo"] == D("35.00") and r["titulo"]["data_baixa"] == date(2026, 12, 10)
    r = pagar(db, t["id"], 35, data_baixa="2026-12-07")
    assert r["titulo"]["status"] == "PAGO" and r["titulo"]["saldo"] == 0
    assert r["titulo"]["data_baixa"] == date(2026, 12, 10)  # ultima data valida
    assert [b["valor"] for b in svc.listar_baixas(db, t["id"], A)] == [D("40.00"), D("35.00"), D("25.00")]


def test_juros_e_desconto_da_baixa_nao_alteram_o_titulo(db):
    t = titulo(db, valor="100.00", desconto="10", juros="0")  # valor liquido 90
    r = pagar(db, t["id"], 50, juros=5, desconto=0)  # paga 50 em dinheiro, quita 45
    assert r["titulo"]["saldo"] == D("45.00") and r["titulo"]["valor_pago"] == D("50.00")
    assert r["titulo"]["valor"] == D("90.00") and r["titulo"]["desconto"] == D("10.00") and r["titulo"]["juros"] == 0
    r = pagar(db, t["id"], 40, desconto=5)  # paga 40, quita 45 -> zera
    assert r["titulo"]["status"] == "PAGO" and r["titulo"]["saldo"] == 0
    assert r["titulo"]["valor_pago"] == D("90.00") and r["titulo"]["valor"] == D("90.00")


def test_baixa_acima_do_saldo_e_invalidos(db):
    t = titulo(db)
    pagar(db, t["id"], 70)
    with pytest.raises(svc.TituloInvalido):
        pagar(db, t["id"], 31)
    with pytest.raises(svc.TituloInvalido):
        pagar(db, t["id"], 10, juros=10)  # quitacao zero
    with pytest.raises(Exception):
        BaixaCreate(data_baixa="2026-12-01", valor="0")
    with pytest.raises(Exception):
        BaixaCreate(data_baixa="2026-12-01", valor="1", juros="-1")
    pagar(db, t["id"], 30)
    with pytest.raises(svc.TituloConflito):
        pagar(db, t["id"], 1)  # ja quitado


def test_baixa_conta_e_forma_de_outra_empresa(db):
    cb = cadastros(db, B)
    t = titulo(db)
    with pytest.raises(svc.TituloInvalido):
        pagar(db, t["id"], 10, conta_financeira_id=cb["conta"].id)
    with pytest.raises(svc.TituloInvalido):
        pagar(db, t["id"], 10, forma_pagamento_id=cb["forma"].id)
    assert db.query(Baixa).count() == 0
    assert svc.obter(db, t["id"], A)["valor_pago"] == 0


def test_baixa_forma_incompativel_e_defaults(db):
    c = cadastros(db, A)
    so_pagar = cad.criar(db, "formas-pagamento", A, {"nome": "Boleto", "tipo": "BOLETO", "conta_financeira_id": c["conta"].id, "disponivel_para": "PAGAR", "ativo": True})
    t = titulo(db)
    with pytest.raises(svc.TituloInvalido):
        pagar(db, t["id"], 10, forma_pagamento_id=so_pagar.id)
    p = titulo(db, "P")
    r = pagar(db, p["id"], 10, forma_pagamento_id=so_pagar.id)  # conta padrao da forma
    assert r["baixa"]["conta_financeira_id"] == c["conta"].id


def test_baixa_de_outra_empresa_e_inexistente(db):
    t = titulo(db)
    with pytest.raises(svc.TituloNaoEncontrado):
        pagar(db, t["id"], 10, tenant=B)
    with pytest.raises(svc.TituloNaoEncontrado):
        pagar(db, 9999, 10)


def test_baixa_titulo_cancelado_e_pago_legado(db):
    tid = legado(db, tipo="R", pedido_id=None, status="CANCELADO")
    with pytest.raises(svc.TituloConflito):
        pagar(db, tid, 10)
    pago = legado(db, tipo="R", pedido_id=None, status="PAGO", descricao="legado pago")
    out = svc.obter(db, pago, A)
    assert out["saldo"] == 0 and out["valor_pago"] == D("463.81") and out["pode_baixar"] is False
    with pytest.raises(svc.TituloConflito):
        pagar(db, pago, 10)


def test_baixa_titulo_de_venda_permitida_e_rt_contab_bloqueados(db):
    from sqlalchemy import text

    venda = legado(db)  # VENDA
    assert svc.obter(db, venda, A)["origem"] == "VENDA"
    r = pagar(db, venda, 100)
    assert r["titulo"]["origem"] == "VENDA" and r["titulo"]["pedido_id"] == 6 and r["titulo"]["pedido_numero"] == "VEN-000006"

    for tabela, origem in (("representantes_rt", "RT"), ("contabilidade_obrigacoes", "CONTABILIDADE")):
        tid = legado(db, tipo="P", pedido_id=None, categoria="X")
        db.execute(text(f"INSERT INTO {tabela} (financeiro_id) VALUES (:i)"), {"i": tid})
        db.commit()
        assert svc.obter(db, tid, A)["origem"] == origem
        with pytest.raises(svc.TituloConflito):
            pagar(db, tid, 10)


def test_estorno_reabre_e_recalcula(db):
    c = cadastros(db, A)
    t = titulo(db, situacao_financeira_id=c["aberto"].id)
    b1 = pagar(db, t["id"], 60, data_baixa="2026-12-02")["baixa"]
    b2 = pagar(db, t["id"], 40, data_baixa="2026-12-09")["baixa"]
    assert svc.obter(db, t["id"], A)["situacao_financeira_id"] == c["pago"].id

    r = svc.estornar(db, b2["id"], A)
    assert r["baixa"]["ativa"] is False and r["baixa"]["estornada_em"] is not None
    out = r["titulo"]
    assert out["status"] == "ABERTO" and out["saldo"] == D("40.00") and out["valor_pago"] == D("60.00")
    assert out["data_baixa"] == date(2026, 12, 2) and out["pagamento"] is None
    assert out["situacao_financeira_id"] == c["aberto"].id  # volta para a padrao

    with pytest.raises(svc.TituloConflito):
        svc.estornar(db, b2["id"], A)  # nao estorna duas vezes
    out = svc.estornar(db, b1["id"], A)["titulo"]
    assert out["valor_pago"] == 0 and out["data_baixa"] is None and out["saldo"] == D("100.00")
    assert len(svc.listar_baixas(db, t["id"], A)) == 2  # baixas nunca sao apagadas
    assert pagar(db, t["id"], 100)["titulo"]["status"] == "PAGO"  # pode baixar de novo
    with pytest.raises(svc.TituloNaoEncontrado):
        svc.estornar(db, b1["id"], B)


def test_exclusao_com_baixa_estornada_continua_proibida(db):
    t = titulo(db)
    b = pagar(db, t["id"], 10)["baixa"]
    svc.estornar(db, b["id"], A)
    out = svc.obter(db, t["id"], A)
    assert out["pode_excluir"] is False and out["qtd_baixas"] == 0 and out["qtd_baixas_total"] == 1
    with pytest.raises(svc.TituloConflito):
        svc.remover(db, t["id"], A)


def test_origem_manual_e_nomes(db):
    t = titulo(db, "R", cliente_id=1)
    assert t["origem"] == "MANUAL" and t["cliente_nome"] == "Cliente A" and t["pode_excluir"] is True and t["pode_baixar"] is True
    p = titulo(db, "P", fornecedor_id=1)
    assert p["fornecedor_nome"] == "Fornecedor A"


def test_indicadores_reais(db):
    hoje = date(2026, 12, 10)
    titulo(db, descricao="vencido", vencimento="2026-12-01", valor="100")
    titulo(db, descricao="hoje", vencimento="2026-12-10", valor="200")
    titulo(db, descricao="futuro", vencimento="2026-12-20", valor="300")
    parcial = titulo(db, descricao="parcial", vencimento="2026-12-05", valor="50")
    pagar(db, parcial["id"], 20)  # saldo 30 segue vencido
    quitado = titulo(db, descricao="quitado", vencimento="2026-12-02", valor="70")
    pagar(db, quitado["id"], 70)
    svc.criar(db, B, novo("R", valor_original="999"))  # outra empresa
    svc.criar(db, A, novo("P", valor_original="40"))

    ind = svc.indicadores(db, A, hoje=hoje, tipo="R")
    assert ind["total_periodo"] == {"quantidade": 5, "total": D("720.00")}
    assert ind["vencidos"] == {"quantidade": 2, "total": D("130.00")}  # 100 + saldo 30
    assert ind["vencem_hoje"] == {"quantidade": 1, "total": D("200.00")}
    assert ind["a_vencer"] == {"quantidade": 1, "total": D("300.00")}
    assert ind["quitados"] == {"quantidade": 1, "total": D("70.00")}
    ind = svc.indicadores(db, A, hoje=hoje, tipo="R", vencimento_inicial=date(2026, 12, 10))
    assert ind["total_periodo"]["quantidade"] == 2 and ind["vencidos"]["quantidade"] == 0
    assert svc.indicadores(db, A, hoje=hoje, tipo="P")["total_periodo"]["total"] == D("40.00")


def test_filtros_vencimento_status_pedido_e_forma(db):
    c = cadastros(db, A)
    hoje = date(2026, 12, 10)
    v = titulo(db, descricao="v", vencimento="2026-12-01", forma_pagamento_id=c["forma"].id)
    h = titulo(db, descricao="h", vencimento="2026-12-10")
    f = titulo(db, descricao="f", vencimento="2026-12-30")
    ids = lambda **q: [i["id"] for i in svc.listar(db, A, hoje=hoje, **q)]
    assert ids(vencimento_status="VENCIDO") == [v["id"]]
    assert ids(vencimento_status="HOJE") == [h["id"]]
    assert ids(vencimento_status="A_VENCER") == [f["id"]]
    assert ids(forma_pagamento_id=c["forma"].id) == [v["id"]]
    venda = legado(db)
    assert ids(pedido_id=6) == [venda]
    pagar(db, v["id"], 100)
    assert ids(vencimento_status="VENCIDO") == [venda]  # o titulo pago saiu dos vencidos