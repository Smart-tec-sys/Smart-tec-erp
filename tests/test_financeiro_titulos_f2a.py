from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from sqlalchemy.exc import IntegrityError

from app.models.financeiro import FinanceiroBaixaDB as Baixa
from app.models.financeiro import FinanceiroDB as T
from app.schemas.financeiro_titulos import TituloCreate, TituloUpdate
from app.services import financeiro_cadastros_service as cad
from app.services import financeiro_titulos_service as svc

# Registra todos os models para resolver as FKs/relationships (empresas, pedidos, ...).
import importlib
import pkgutil

import app.models as _models

for _m in pkgutil.iter_modules(_models.__path__):
    importlib.import_module(f"app.models.{_m.name}")

A = SimpleNamespace(empresa_id=1)
B = SimpleNamespace(empresa_id=2)


@pytest.fixture()
def db():
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys=ON"))
    with engine.begin() as c:
        c.execute(text("CREATE TABLE empresas (id INTEGER PRIMARY KEY)"))
        c.execute(text("INSERT INTO empresas VALUES (1), (2)"))
        c.execute(text("CREATE TABLE pedidos (id INTEGER PRIMARY KEY, numero TEXT)"))
        c.execute(text("INSERT INTO pedidos VALUES (1, 'VEN-000001'), (6, 'VEN-000006')"))
    for m in (cad.ContaFinanceiraDB, cad.FormaPagamentoDB, cad.PlanoContaDB, cad.SituacaoFinanceiraDB, cad.CentroCustoDB):
        m.__table__.create(engine)
    T.__table__.create(engine)
    Baixa.__table__.create(engine)
    with engine.begin() as c:
        for tabela in ("clientes", "fornecedores"):
            c.execute(text(f"CREATE TABLE {tabela} (id INTEGER PRIMARY KEY, empresa_id INTEGER, nome TEXT)"))
        for tabela in ("representantes_rt", "contabilidade_obrigacoes"):
            c.execute(text(f"CREATE TABLE {tabela} (id INTEGER PRIMARY KEY, financeiro_id INTEGER)"))
        c.execute(text("INSERT INTO clientes VALUES (1, 1, 'Cliente A'), (2, 2, 'Cliente B')"))
        c.execute(text("INSERT INTO fornecedores VALUES (1, 1, 'Fornecedor A'), (2, 2, 'Fornecedor B')"))
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()


def cadastros(db, tenant):
    e = tenant.empresa_id
    return {
        "conta": cad.criar(db, "contas-financeiras", tenant, {"nome": f"Caixa {e}", "tipo": "CAIXA", "saldo_inicial": 0, "ativo": True}),
        "forma": cad.criar(db, "formas-pagamento", tenant, {"nome": f"PIX {e}", "tipo": "PIX", "conta_financeira_id": None, "disponivel_para": "AMBOS", "ativo": True}),
        "plano_r": cad.criar(db, "plano-contas", tenant, {"codigo": "1.01", "nome": "Receitas", "tipo": "RECEITA", "pai_id": None, "ativo": True}),
        "plano_p": cad.criar(db, "plano-contas", tenant, {"codigo": "2.01", "nome": "Despesas", "tipo": "DESPESA", "pai_id": None, "ativo": True}),
        "centro": cad.criar(db, "centros-custo", tenant, {"nome": "Showroom", "observacao": None, "ativo": True}),
        "aberto": cad.criar(db, "situacoes", tenant, {"nome": "Aberto", "tipo": "AMBOS", "quitado": False, "padrao": True, "ativo": True}),
        "pago": cad.criar(db, "situacoes", tenant, {"nome": "Pago", "tipo": "AMBOS", "quitado": True, "padrao": False, "ativo": True}),
    }


def novo(tipo="R", **extra):
    base = {"tipo": tipo, "descricao": "Titulo manual", "valor_original": "100.00", "vencimento": "2026-12-10"}
    base.update(extra)
    return TituloCreate(**base).dict()


def legado(db, **kw):
    """Insere como os writers atuais: sem nenhum campo da F2A."""
    cols = {"tipo": "R", "descricao": "Venda VEN-1", "valor": 463.81, "vencimento": "2026-11-04",
            "status": "ABERTO", "pedido_id": 6, "categoria": "VENDAS", "empresa_id": 1}
    cols.update(kw)
    nomes = ", ".join(cols)
    marcas = ", ".join(f":{k}" for k in cols)
    db.execute(text(f"INSERT INTO financeiro ({nomes}) VALUES ({marcas})"), cols)
    db.commit()
    return db.execute(text("SELECT max(id) FROM financeiro")).scalar()


def test_registro_antigo_compativel(db):
    tid = legado(db)
    out = svc.obter(db, tid, A)
    assert out["valor"] == Decimal("463.81")
    assert out["valor_original"] == Decimal("463.81")  # NULL -> valor
    assert out["desconto"] == 0 and out["juros"] == 0 and out["valor_pago"] == 0
    assert out["recorrente"] is False and out["conta_financeira_id"] is None
    assert out["saldo"] == Decimal("463.81") and out["vinculado"] is True
    # leitura nao altera o registro historico
    assert db.execute(text("SELECT valor_original FROM financeiro WHERE id=:i"), {"i": tid}).scalar() is None


def test_criacao_manual_receber(db):
    c = cadastros(db, A)
    out = svc.criar(db, A, novo("R", cliente_id=1, desconto="10", juros="2.5",
                                conta_financeira_id=c["conta"].id, forma_pagamento_id=c["forma"].id,
                                plano_conta_id=c["plano_r"].id, centro_custo_id=c["centro"].id,
                                situacao_financeira_id=c["aberto"].id, categoria="SERVICOS"))
    assert out["valor"] == Decimal("92.50") and out["valor_original"] == Decimal("100.00")
    assert out["status"] == "ABERTO" and out["empresa_id"] == 1 and out["saldo"] == Decimal("92.50")
    assert out["vinculado"] is False


def test_criacao_manual_pagar_sem_vinculos(db):
    out = svc.criar(db, A, novo("P"))
    assert out["tipo"] == "P" and out["fornecedor_id"] is None and out["valor"] == Decimal("100.00")
    out = svc.criar(db, A, novo("P", fornecedor_id=1))
    assert out["fornecedor_id"] == 1


def test_tipo_e_pessoa_incompativeis(db):
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", fornecedor_id=1))
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("P", cliente_id=1))
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", cliente_id=2))  # cliente de outra empresa
    with pytest.raises(Exception):
        TituloCreate(**{**novo("R"), "tipo": "X"})
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", desconto="100"))  # liquido zero


def test_recusa_cadastros_de_outra_empresa(db):
    cb = cadastros(db, B)
    for campo, chave in (("conta_financeira_id", "conta"), ("forma_pagamento_id", "forma"),
                         ("plano_conta_id", "plano_r"), ("centro_custo_id", "centro"),
                         ("situacao_financeira_id", "aberto")):
        with pytest.raises(svc.TituloInvalido):
            svc.criar(db, A, novo("R", **{campo: cb[chave].id}))
    assert db.query(T).count() == 0


def test_compatibilidade_plano_situacao_forma(db):
    c = cadastros(db, A)
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", plano_conta_id=c["plano_p"].id))
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", situacao_financeira_id=c["pago"].id))
    so_pagar = cad.criar(db, "formas-pagamento", A, {"nome": "Boleto", "tipo": "BOLETO", "conta_financeira_id": None, "disponivel_para": "PAGAR", "ativo": True})
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", forma_pagamento_id=so_pagar.id))
    svc.criar(db, A, novo("P", forma_pagamento_id=so_pagar.id))


def test_inativo_recusado(db):
    c = cadastros(db, A)
    cad.atualizar(db, "contas-financeiras", c["conta"].id, A, {"ativo": False})
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", conta_financeira_id=c["conta"].id))


def test_filtros(db):
    c = cadastros(db, A)
    r1 = svc.criar(db, A, novo("R", descricao="Venda alfa", vencimento="2026-12-01", cliente_id=1, categoria="VENDAS", conta_financeira_id=c["conta"].id))
    p1 = svc.criar(db, A, novo("P", descricao="Aluguel", vencimento="2026-12-20", fornecedor_id=1, categoria="FIXAS", plano_conta_id=c["plano_p"].id, centro_custo_id=c["centro"].id))
    svc.criar(db, B, novo("R", descricao="Venda alfa B"))
    ids = lambda **f: [i["id"] for i in svc.listar(db, A, **f)]
    assert ids() == [r1["id"], p1["id"]]
    assert ids(tipo="r") == [r1["id"]] and ids(tipo="P") == [p1["id"]]
    assert ids(status="aberto") == [r1["id"], p1["id"]] and ids(status="PAGO") == []
    assert ids(vencimento_inicial=date(2026, 12, 10)) == [p1["id"]]
    assert ids(vencimento_final=date(2026, 12, 10)) == [r1["id"]]
    assert ids(cliente_id=1) == [r1["id"]] and ids(fornecedor_id=1) == [p1["id"]]
    assert ids(categoria="vendas") == [r1["id"]]
    assert ids(conta_financeira_id=c["conta"].id) == [r1["id"]]
    assert ids(plano_conta_id=c["plano_p"].id) == [p1["id"]]
    assert ids(centro_custo_id=c["centro"].id) == [p1["id"]]
    assert ids(q="ALFA") == [r1["id"]] and ids(q="alug") == [p1["id"]]


def test_edicao_recalcula_valor(db):
    t = svc.criar(db, A, novo("R"))
    out = svc.atualizar(db, t["id"], A, TituloUpdate(descricao=" Novo ", juros="5", desconto="2").dict(exclude_unset=True))
    assert out["descricao"] == "Novo" and out["valor"] == Decimal("103.00")
    out = svc.atualizar(db, t["id"], A, {"valor_original": Decimal("200")})
    assert out["valor"] == Decimal("203.00")
    with pytest.raises(svc.TituloInvalido):
        svc.atualizar(db, t["id"], A, {"desconto": Decimal("500")})
    assert svc.obter(db, t["id"], A)["valor"] == Decimal("203.00")


def test_edicao_nao_altera_tipo_status_baixa(db):
    t = svc.criar(db, A, novo("R"))
    patch = TituloUpdate(**{"descricao": "x", "tipo": "P", "status": "PAGO", "valor_pago": 50}).dict(exclude_unset=True)
    assert set(patch) == {"descricao"}
    out = svc.atualizar(db, t["id"], A, patch)
    assert out["tipo"] == "R" and out["status"] == "ABERTO" and out["valor_pago"] == 0


def test_titulo_vinculado_protege_valores_mas_aceita_metadados(db):
    c = cadastros(db, A)
    tid = legado(db)
    with pytest.raises(svc.TituloConflito):
        svc.atualizar(db, tid, A, {"desconto": Decimal("10")})
    out = svc.atualizar(db, tid, A, {"conta_financeira_id": c["conta"].id, "plano_conta_id": c["plano_r"].id, "observacao": "ok"})
    assert out["conta_financeira_id"] == c["conta"].id and out["valor"] == Decimal("463.81")
    assert db.execute(text("SELECT valor_original FROM financeiro WHERE id=:i"), {"i": tid}).scalar() is None


def test_titulo_pago_protege_valores(db):
    tid = legado(db, tipo="P", pedido_id=None, status="PAGO", categoria="CONTABILIDADE", descricao="DAS")
    with pytest.raises(svc.TituloConflito):
        svc.atualizar(db, tid, A, {"juros": Decimal("1")})


def test_isolamento_por_empresa(db):
    t = svc.criar(db, A, novo("R"))
    with pytest.raises(svc.TituloNaoEncontrado):
        svc.obter(db, t["id"], B)
    with pytest.raises(svc.TituloNaoEncontrado):
        svc.atualizar(db, t["id"], B, {"descricao": "x"})
    with pytest.raises(svc.TituloNaoEncontrado):
        svc.remover(db, t["id"], B)
    assert svc.listar(db, B) == []


def test_exclusao_segura(db):
    manual = svc.criar(db, A, novo("R"))
    svc.remover(db, manual["id"], A)
    with pytest.raises(svc.TituloNaoEncontrado):
        svc.obter(db, manual["id"], A)

    venda = legado(db)
    with pytest.raises(svc.TituloConflito):
        svc.remover(db, venda, A)

    for tabela in ("representantes_rt", "contabilidade_obrigacoes"):
        tid = legado(db, tipo="P", pedido_id=None, categoria="X")
        db.execute(text(f"INSERT INTO {tabela} (financeiro_id) VALUES (:i)"), {"i": tid})
        db.commit()
        with pytest.raises(svc.TituloConflito):
            svc.remover(db, tid, A)

    pago = legado(db, tipo="P", pedido_id=None, status="PAGO", categoria="X")
    with pytest.raises(svc.TituloConflito):
        svc.remover(db, pago, A)

def test_limite_do_valor_legado_numeric_12_2(db):
    with pytest.raises(Exception):
        TituloCreate(**novo("R", valor_original="10000000000"))
    with pytest.raises(svc.TituloInvalido):
        svc.criar(db, A, novo("R", valor_original="9999999999.99", juros="1"))
    ok = svc.criar(db, A, novo("R", valor_original="9999999999.99"))
    assert ok["valor"] == Decimal("9999999999.99")
    t = svc.criar(db, A, novo("R"))
    with pytest.raises(svc.TituloInvalido):
        svc.atualizar(db, t["id"], A, {"valor_original": Decimal("9999999999.99"), "juros": Decimal("5")})


def baixa(db, financeiro_id, empresa_id=1, **kw):
    dados = {"empresa_id": empresa_id, "financeiro_id": financeiro_id, "data_baixa": date(2026, 12, 1), "valor": 10}
    dados.update(kw)
    db.add(Baixa(**dados))
    db.commit()


def test_baixas_multiplas_para_o_mesmo_titulo(db):
    tid = svc.criar(db, A, novo("R"))["id"]
    baixa(db, tid, valor=40)
    baixa(db, tid, valor=60, juros=1, desconto=0)
    assert db.query(Baixa).filter_by(financeiro_id=tid).count() == 2


def test_baixa_nao_referencia_titulo_de_outra_empresa(db):
    tid = svc.criar(db, A, novo("R"))["id"]
    with pytest.raises(IntegrityError):
        baixa(db, tid, empresa_id=2)
    db.rollback()
    with pytest.raises(IntegrityError):
        baixa(db, 9999)
    db.rollback()
    assert db.query(Baixa).count() == 0


@pytest.mark.parametrize("campo,valor", [("valor", 0), ("valor", -5), ("juros", -1), ("desconto", -1)])
def test_banco_recusa_valores_invalidos_na_baixa(db, campo, valor):
    tid = svc.criar(db, A, novo("R"))["id"]
    with pytest.raises(IntegrityError):
        baixa(db, tid, **{campo: valor})
    db.rollback()


def test_titulo_com_baixa_nao_pode_ser_excluido(db):
    tid = svc.criar(db, A, novo("R"))["id"]
    baixa(db, tid)
    with pytest.raises(svc.TituloConflito):
        svc.remover(db, tid, A)
    with pytest.raises(IntegrityError):  # defesa do banco (sem CASCADE)
        db.execute(text("DELETE FROM financeiro WHERE id=:i"), {"i": tid})
        db.commit()
    db.rollback()


def test_baixas_nao_alteram_titulo_historico(db):
    tid = legado(db)
    antes = db.execute(text("SELECT * FROM financeiro WHERE id=:i"), {"i": tid}).fetchall()
    baixa(db, tid)
    assert db.execute(text("SELECT * FROM financeiro WHERE id=:i"), {"i": tid}).fetchall() == antes