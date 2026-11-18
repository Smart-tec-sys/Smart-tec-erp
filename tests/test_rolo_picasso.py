"""Picasso: dados isolados, sem alteração do catálogo real."""
import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from app.database import Base, get_db
from app.models.empresa import EmpresaDB
from app.models.produto import ProdutoDB
from app.models.funcionario import FuncionarioDB  # noqa: F401
from app.models.cliente import ClienteDB  # noqa: F401
from app.models.servico import ServicoDB  # noqa: F401
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
from app.models.pedido import PedidoDB, PedidoItemDB  # noqa: F401
from app.routes.orcamento import router
from app.schemas.orcamento import OrcamentoInput
from app.schemas.pedido import PedidoCreate
from app.services.composicao_comercial import calcular_itens
from app.services.rolo_picasso_ativacao import ativar_picasso
from app.services.rolo_receita import simular_rolo_catalogo
from app.services.rolo_simulacao import RoloSimulacaoInput, simular_rolo
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

MANIFEST = Path(__file__).resolve().parents[1] / "docs" / "rolo-picasso-acao-v1.json"


@compiles(JSONB, "sqlite")
def _sqlite_jsonb(tipo, compiler, **kwargs):
    return "JSON"


MEDIDAS = [
    ("Sala", "BK", 1.38, 2.52, 2, "32mm"),
    ("Escritório", "TR", 1.65, 1.65, 1, "32mm"),
    ("Quarto 1", "TR", 1.79, 1.70, 1, "32mm"),
    ("Quarto 2", "TR", 1.90, 1.70, 1, "38mm"),
]


@pytest.fixture
def picasso():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    nomes = ["empresas", "funcionarios", "clientes", "produtos", "servicos", "orcamentos",
             "orcamentos_itens", "parceiros_comerciais", "representantes", "pedidos", "pedidos_itens"]
    Base.metadata.create_all(engine, tables=[Base.metadata.tables[n] for n in nomes])
    manifesto = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with Session(engine) as db:
        db.add_all([
            EmpresaDB(id=1, nome=manifesto["empresa_nome"], slug="smarttec", documento=None, configuracoes={"preservar": {"valor": 42}}),
            EmpresaDB(id=2, nome="Empresa Outra", slug="outra", configuracoes={}),
        ])
        db.flush()
        for chave, item in manifesto["insumos"].items():
            if item.get("criar_se_ausente"):
                continue
            db.add(ProdutoDB(
                empresa_id=1, nome=item.get("nome_legado", item["nome"]), codigo_interno=item["codigo_interno"],
                tipo_produto="Componente", unidade_venda=item["unidade_tecnica"],
                valor_custo=item["preco_compra"], custo_final=item["preco_compra"], situacao="Ativo",
            ))
        for modelo in manifesto["modelos"]:
            for variacao in modelo["variacoes"]:
                db.add(ProdutoDB(
                    empresa_id=1, nome=variacao["nome_tecido"], codigo_interno=variacao["codigo_tecido"],
                    tipo_produto="Componente", grupo_produto="Tecidos", unidade_venda="M2", largura=2.5,
                    valor_custo=19.72 if "Translúcido" in modelo["nome"] else 33.824, situacao="Ativo",
                ))
        fita = manifesto["insumos"]["fita_tubo"]
        db.add(ProdutoDB(empresa_id=1, nome=fita["nome"], codigo_interno=fita["codigo_interno"],
                        tipo_produto="Componente", unidade_venda="UN", custo_final=84, situacao="Ativo"))
        db.add(ProdutoDB(empresa_id=1, nome="Rolô legado", modelo_tecnico="ROLO", tipo_produto="Produto Fabricado",
                        unidade_venda="M2", custo_final=100, situacao="Ativo"))
        db.commit()
        yield db, manifesto
    engine.dispose()


def ativar(fixture):
    db, manifesto = fixture
    resultado = ativar_picasso(db, 1, manifesto)
    db.commit()
    return resultado


def acabado(db, categoria="TR", cor="AMENDOA"):
    return db.query(ProdutoDB).filter_by(codigo_interno=f"ST-ROLO-PICASSO-{categoria}-{cor}", empresa_id=1).one()


@pytest.mark.parametrize("ambiente,categoria,largura,altura,quantidade,bitola", MEDIDAS)
def test_medidas_rosy_motor_custo_e_comercial(picasso, ambiente, categoria, largura, altura, quantidade, bitola):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db, categoria)
    entrada = RoloSimulacaoInput(produto_id=produto.id, largura=largura, altura=altura, quantidade=quantidade,
                                 cor="AMENDOA", perfil_comercial="CONSUMIDOR_FINAL")
    resultado = simular_rolo_catalogo(db, produto, entrada, 1)
    assert resultado["bitola_tecnica"] == bitola and resultado["preco_disponivel"]
    assert resultado["custo_tecnico"] > 0
    componentes = resultado["fabricacao_por_peca"]["componentes"]
    assert len(componentes) == 10
    tecido = next(c for c in componentes if c["categoria"] == "Tecido")
    custo_m2 = Decimal("103.53" if categoria == "BK" else "60.09") * Decimal("1.0325") / Decimal("2.5")
    assert tecido["custo_unitario"] == pytest.approx(float(custo_m2 * Decimal("2.5") / Decimal(str(largura - 0.03))), abs=0.0001)
    assert tecido["quantidade"] == pytest.approx(round((largura - 0.03) * (altura + 0.15) * 1.05 * quantidade, 4))
    compra_ml = (altura + 0.15) * 1.05 * quantidade
    assert resultado["componentes_tecnicos"]["tecido"]["quantidade_compra_ml"] == pytest.approx(compra_ml)
    assert tecido["custo_total"] == pytest.approx(float(custo_m2 * Decimal("2.5")) * compra_ml, abs=0.0001)
    assert resultado["receita"]["custeio_tecido"] == "FAIXA_INTEGRAL_ML"
    assert Decimal(str(resultado["subtotal"])) == (
        Decimal(str(resultado["preco_unitario"])) * Decimal(str(resultado["area_faturavel_m2"]))
    ).quantize(Decimal(".01"))
    assert resultado["receita"]["acabamento"] == "CINZA"
    expected_price = Decimal(str(resultado["custo_tecnico"])) * Decimal("2.5") / resultado["area_faturavel_m2"]
    assert resultado["preco_unitario"] == expected_price.quantize(Decimal(".01"))


def test_idempotencia_variações_e_preservacao(picasso):
    db, manifesto = picasso
    tecidos_antes = [(p.id, p.nome, p.valor_custo, p.custo_final) for p in db.query(ProdutoDB).all()
                     if "PICASSO" in p.nome.upper()]
    primeira = ativar(picasso)
    segunda = ativar(picasso)
    assert len(primeira["acabados"]) == 10
    assert len(primeira["produtos_criados"]) == 11
    assert len(primeira["produtos_corrigidos"]) == 1
    assert segunda["produtos_criados"] == [] and segunda["produtos_corrigidos"] == []
    assert primeira["acabados"] == segunda["acabados"]
    assert db.get(EmpresaDB, 1).configuracoes["preservar"] == {"valor": 42}
    assert db.get(EmpresaDB, 2).configuracoes == {}
    for id_, nome, custo, custo_final in tecidos_antes:
        p = db.get(ProdutoDB, id_)
        assert (p.nome, p.valor_custo, p.custo_final) == (nome, custo, custo_final)
    assert {p["codigo_tecido"] for m in manifesto["modelos"] for p in m["variacoes"]} == {
        "00217800050", "00217800020", "00217800980", "00217801420", "00217803020",
        "00124100050", "00124100020", "00124100980", "00124101420", "00124103020",
    }


def test_rollback_falha_de_vinculo(picasso):
    db, manifesto = picasso
    antes = db.query(ProdutoDB).count()
    quebrado = copy.deepcopy(manifesto)
    quebrado["modelos"][-1]["variacoes"][-1]["codigo_tecido"] = "INEXISTENTE"
    with pytest.raises(ValueError, match="correspondência única"):
        ativar_picasso(db, 1, quebrado)
    db.rollback()
    assert db.query(ProdutoDB).count() == antes
    assert "receitas_rolo_v1" not in db.get(EmpresaDB, 1).configuracoes


@pytest.mark.parametrize("categoria", ["TR", "BK"])
@pytest.mark.parametrize("cor", ["AMENDOA", "BEGE", "CINZA", "FENDI", "GELO"])
def test_dez_variacoes_calculam_sem_tecido_duplicado(picasso, categoria, cor):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db, categoria, cor)
    result = simular_rolo_catalogo(db, p, RoloSimulacaoInput(produto_id=p.id, largura=1.5, altura=2, quantidade=1, cor=cor), 1)
    assert result["componentes_tecnicos"]["tecido"]["cor"] == cor
    assert result["custo_tecnico"] > 0


def test_empresa_cor_e_bitola_incompatíveis_bloqueados(picasso):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db)
    with pytest.raises(ValueError, match="empresa"):
        simular_rolo_catalogo(db, p, RoloSimulacaoInput(produto_id=p.id, largura=1, altura=2, quantidade=1), 2)
    for valores, mensagem in [
        ({"cor": "BEGE"}, "Cor"), ({"largura": 2.6}, "43mm"), ({"largura": 3.3}, "manual proibido"),
        ({"acionamento": "motorizado"}, "manual"), ({"largura": 0.02}, "cortes"),
    ]:
        entrada = RoloSimulacaoInput(produto_id=p.id, **({"largura": 1, "altura": 2, "quantidade": 1} | valores))
        with pytest.raises(ValueError, match=mensagem):
            simular_rolo_catalogo(db, p, entrada, 1)
    empresa = db.get(EmpresaDB, 1)
    cfg = copy.deepcopy(empresa.configuracoes)
    cfg["receitas_rolo_v1"][str(p.id)]["largura_bobina_m"] = 1
    empresa.configuracoes = cfg
    with pytest.raises(ValueError, match="bobina"):
        simular_rolo_catalogo(db, p, RoloSimulacaoInput(produto_id=p.id, largura=1.5, altura=2, quantidade=1), 1)


def test_legado_mantem_resultado_exato(picasso):
    db, _ = picasso
    p = db.query(ProdutoDB).filter_by(nome="Rolô legado").one()
    entrada = RoloSimulacaoInput(produto_id=p.id, largura=1.5, altura=2, quantidade=1)
    assert simular_rolo_catalogo(db, p, entrada, 1) == simular_rolo(p, entrada)


def test_receita_rateada_preserva_custo_por_area(picasso):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db)
    empresa = db.get(EmpresaDB, 1)
    cfg = copy.deepcopy(empresa.configuracoes)
    cfg["receitas_rolo_v1"][str(p.id)]["custeio_tecido"] = "AREA_CORTE"
    empresa.configuracoes = cfg
    result = simular_rolo_catalogo(db, p, RoloSimulacaoInput(produto_id=p.id, largura=1.5, altura=2, quantidade=1), 1)
    tecido = next(c for c in result["fabricacao_por_peca"]["componentes"] if c["categoria"] == "Tecido")
    assert tecido["custo_unitario"] == pytest.approx(60.09 * 1.0325 / 2.5, abs=0.0001)
    assert "quantidade_compra_ml" not in result["componentes_tecnicos"]["tecido"]


@pytest.mark.parametrize("schema,item_model", [(OrcamentoInput, OrcamentoItemDB), (PedidoCreate, PedidoItemDB)])
def test_orcamento_e_venda_recalculam_precos_e_snapshot(picasso, schema, item_model):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db)
    input = {"produto_id": p.id, "descricao": p.nome, "unidade": "M2", "largura": 1.79, "altura": 1.70,
             "quantidade": 1, "cor": "AMENDOA", "acionamento": "manual", "preco_unitario": 999999, "subtotal": 999999,
             "desconto": 5}
    documento = SimpleNamespace(itens=[])
    calcular_itens(db, documento, schema(cliente_id=1, itens=[input]), 1, item_model)
    result = simular_rolo_catalogo(db, p, RoloSimulacaoInput(produto_id=p.id, largura=1.79, altura=1.70,
                                                          quantidade=1, cor="AMENDOA", desconto=5), 1)
    assert documento.itens[0].preco_unitario == result["preco_unitario"]
    assert documento.itens[0].subtotal == result["subtotal"]
    assert documento.itens[0].dados_tecnicos["rolo"]["bitola"] == "32mm"
    assert documento.itens[0].dados_tecnicos["rolo"]["receita"]["custos"]
    assert documento.total == result["subtotal"]


def test_preco_negociado_nao_muda_receita(picasso):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db)
    antes = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes)
    documento = SimpleNamespace(itens=[])
    calcular_itens(db, documento, OrcamentoInput(itens=[{
        "produto_id": p.id, "descricao": p.nome, "largura": 1.5, "altura": 2, "cor": "AMENDOA",
        "preco_unitario": 123.45, "preco_unitario_manual": True,
    }]), 1, OrcamentoItemDB)
    assert documento.itens[0].preco_unitario == Decimal("123.4500")
    assert documento.itens[0].subtotal == Decimal("370.35")
    assert db.get(EmpresaDB, 1).configuracoes == antes


def test_endpoint_usa_receita_e_nao_persiste(picasso):
    db, _ = picasso
    ativar(picasso)
    p = acabado(db)
    app = FastAPI()
    app.include_router(router, prefix="/orcamentos")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_tenant] = lambda: TenantContext(empresa_id=1, user_id=1)
    with TestClient(app) as client, patch.object(db, "commit", side_effect=AssertionError("Não persistir simulação")):
        r = client.post("/orcamentos/simulacao-rolo", json={
            "produto_id": p.id, "largura": 1.9, "altura": 1.7, "quantidade": 1, "cor": "AMENDOA",
        })
        assert r.status_code == 200, r.text
        assert r.json()["bitola_tecnica"] == "38mm"
        assert r.json()["origem_preco"] == "RECEITA_TECNICA_EMPRESA"
    assert db.query(OrcamentoDB).count() == 0
