"""Picasso: dados isolados, sem alteração do catálogo real."""
import copy
import json
from decimal import Decimal, ROUND_HALF_UP
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
from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB  # noqa: F401
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
from app.services.rolo_receita import (
    _bitolas_motor_compativeis, _tecido_screen_importado, listar_acessorios_comando_rolo,
    listar_motores_rolo, simular_rolo_catalogo,
)
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
             "orcamentos_itens", "parceiros_comerciais", "representantes", "pedidos", "pedidos_itens",
             "empresa_equivalencias_tecnicas"]
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
        ({"acionamento": "motorizado"}, "Selecione um motor"), ({"largura": 0.02}, "cortes"),
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


def test_legado_sem_receita_preserva_preco_e_nao_inventa_composicao(picasso):
    db, _ = picasso
    p = db.query(ProdutoDB).filter_by(nome="Rolô legado").one()
    entrada = RoloSimulacaoInput(produto_id=p.id, largura=1.5, altura=2, quantidade=1)
    antes = (p.custo_final, p.valor_custo, p.valor_venda)
    legado = simular_rolo(p, entrada)
    assert legado["preco_unitario"] == Decimal("200.00")
    with pytest.raises(ValueError, match="manual não configurada"):
        simular_rolo_catalogo(db, p, entrada, 1)
    assert (p.custo_final, p.valor_custo, p.valor_venda) == antes


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


SCREEN_IMPORTADO_TECIDOS = {
    "BRANCO": [(2.0, "JPTEC-0001"), (2.5, "JPTEC-0005"), (3.0, "JPTEC-0009")],
    "BEGE": [(2.0, "JPTEC-0002"), (2.5, "JPTEC-0006"), (3.0, "JPTEC-0010")],
    "CINZA": [(2.0, "JPTEC-0003"), (2.5, "JPTEC-0007"), (3.0, "JPTEC-0011")],
    "PRETO": [(2.0, "JPTEC-0004"), (2.5, "JPTEC-0008"), (3.0, "JPTEC-0012")],
}


def configurar_screen_importado(db):
    empresa = db.get(EmpresaDB, 1)
    configuracoes = copy.deepcopy(empresa.configuracoes)
    receitas = configuracoes["receitas_rolo_v1"]
    receita = copy.deepcopy(next(iter(receitas.values())))
    receita["custeio_tecido"] = "AREA_CORTE"
    receita["cor_tecido"] = "BRANCO"
    receita["largura_bobina_m"] = 2.0
    receita["tecido"] = {
        "produto_id": 6001,
        "codigo_interno": "JPTEC-0001",
        "unidade_tecnica": "M2",
        "preco_compra": 22.98,
        "ipi_percentual": None,
        "unidades_por_compra": 2.0,
        "origem": "Custo sintético de teste por M²; não aplicado ao catálogo",
        "base_preco": "CUSTO_CADASTRADO",
        "diametro_mm": None,
    }
    db.add(ProdutoDB(
        id=84, empresa_id=1, nome="ROLO SCREEN 3% IMPORTADO",
        grupo_produto="PERSIANAS", grupo_tecnico="PERSIANA_ROLO",
        modelo_tecnico="ROLO", tipo_produto="Produto Fabricado",
        unidade_venda="M2", situacao="Ativo", custo_final=60, valor_custo=60,
    ))
    for cor, tecidos in SCREEN_IMPORTADO_TECIDOS.items():
        for largura, codigo in tecidos:
            produto_id = 6000 + int(codigo[-4:])
            db.add(ProdutoDB(
                id=produto_id, empresa_id=1,
                nome=f"SCREEN 3% JP IMPORTADA - {cor} - {largura:.2f}M",
                codigo_interno=codigo, material_tecido="SCREEN 3% JP IMPORTADA",
                grupo_tecnico="TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL",
                cor=cor, largura=largura, tipo_produto="Componente",
                unidade_venda="M²", custo_final=22.98, valor_custo=22.98,
                situacao="Ativo",
                observacoes="Regra teste: tecido já está com custo por M²; não reconverter por largura.",
            ))
    db.flush()
    receitas["84:manual:BRANCO"] = receita
    empresa.configuracoes = configuracoes
    db.flush()
    return db.get(ProdutoDB, 84)


@pytest.mark.parametrize(
    "cor,largura,largura_bobina,codigo",
    [
        (cor, largura_produto, largura_tecido, codigo)
        for cor, tecidos in SCREEN_IMPORTADO_TECIDOS.items()
        for largura_produto, largura_tecido, codigo in [
            (1.5, 2.0, tecidos[0][1]),
            (2.2, 2.5, tecidos[1][1]),
            (2.5, 2.5, tecidos[1][1]),
        ]
    ],
)
@pytest.mark.parametrize(
    "perfil,preco_final",
    [("DECORADOR", Decimal("90.00")), ("VAREJO", Decimal("120.00")),
     ("CONSUMIDOR_FINAL", Decimal("150.00"))],
)
def test_screen_importado_resolve_cor_bobina_custo_e_perfil(
    picasso, cor, largura, largura_bobina, codigo, perfil, preco_final
):
    db, _ = picasso
    ativar(picasso)
    produto = configurar_screen_importado(db)
    configuracoes_antes = copy.deepcopy(db.get(EmpresaDB, 1).configuracoes)
    resultado = simular_rolo_catalogo(
        db, produto,
        RoloSimulacaoInput(
            produto_id=84, largura=largura, altura=1.72, quantidade=1,
            cor=cor, perfil_comercial=perfil,
        ),
        1,
    )

    tecido_id = 6000 + int(codigo[-4:])
    componente_tecido = resultado["componentes_tecnicos"]["tecido"]
    assert produto.id == 84
    assert componente_tecido["produto_id"] == tecido_id
    assert componente_tecido["cor"] == cor
    assert componente_tecido["largura_bobina_m"] == largura_bobina
    componentes = resultado["fabricacao_por_peca"]["componentes"]
    assert len(componentes) == 10
    assert sum(componente["categoria"] == "Tecido" for componente in componentes) == 1
    tecido_calculado = next(
        componente for componente in componentes if componente["categoria"] == "Tecido"
    )
    assert tecido_calculado["custo_unitario"] == pytest.approx(22.98)
    assert sum(custo["produto_id"] == tecido_id for custo in resultado["receita"]["custos"]) == 1
    assert resultado["custo_tecnico"] == pytest.approx(
        sum(componente["custo_total"] for componente in componentes), abs=0.0002
    )
    from app.services.composicao_comercial import MULTIPLICADORES, _dinheiro
    preco_tecnico = _dinheiro(
        Decimal(str(resultado["custo_tecnico"])) * MULTIPLICADORES[perfil]
        / Decimal(str(resultado["area_faturavel_m2"])))

    assert resultado["preco_unitario"] == max(
        preco_tecnico, preco_final
    )

    origem_esperada = (
        "TABELA_COMERCIAL_PROTEGIDA"
        if preco_final > preco_tecnico
        else "RECEITA_TECNICA_EMPRESA"
    )

    assert resultado["origem_preco"] == origem_esperada
    assert db.get(EmpresaDB, 1).configuracoes == configuracoes_antes


@pytest.mark.parametrize("cor", ["", "AZUL", "AMARELO", None])
def test_screen_importado_rejeita_cor_nao_configurada(picasso, cor):
    db, _ = picasso
    ativar(picasso)
    produto = configurar_screen_importado(db)
    with pytest.raises(ValueError, match="BRANCO, BEGE, CINZA ou PRETO"):
        simular_rolo_catalogo(
            db, produto,
            RoloSimulacaoInput(produto_id=84, largura=1.5, altura=1.72,
                               quantidade=1, cor=cor),
            1,
        )


def test_screen_importado_bloqueia_corte_maior_que_todas_as_bobinas(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = configurar_screen_importado(db)
    with pytest.raises(ValueError, match="bobina suficiente"):
        simular_rolo_catalogo(
            db, produto,
            RoloSimulacaoInput(produto_id=84, largura=3.04, altura=1.72,
                               quantidade=1, cor="PRETO"),
            1,
        )


@pytest.mark.parametrize("cor,tecidos", SCREEN_IMPORTADO_TECIDOS.items())
def test_screen_importado_resolve_bobina_3m_sem_liberar_bitola_nao_configurada(
    picasso, cor, tecidos
):
    db, _ = picasso
    ativar(picasso)
    produto = configurar_screen_importado(db)
    largura_corte = 2.51
    tecido, largura_bobina = _tecido_screen_importado(db, 1, cor, largura_corte)
    assert tecido["codigo_interno"] == tecidos[2][1]
    assert largura_bobina == 3.0
    with pytest.raises(ValueError, match="tubo 43mm validado"):
        simular_rolo_catalogo(
            db, produto,
            RoloSimulacaoInput(produto_id=84, largura=2.54, altura=1.72,
                               quantidade=1, cor=cor),
            1,
        )


def _componente_tecnico(db, nome, unidade, custo, empresa_id=1):
    produto = ProdutoDB(
        empresa_id=empresa_id, nome=nome, codigo_interno=f"TEST-{empresa_id}-{nome.upper().replace(' ', '-')}",
        tipo_produto="Componente", unidade_venda=unidade, situacao="Ativo",
        valor_custo=custo, custo_final=custo,
    )
    db.add(produto)
    db.flush()
    return produto


def _equivalencia_tecnica(db, produto, funcao, configuracao, empresa_id=1):
    equivalencia = EmpresaEquivalenciaTecnicaDB(
        empresa_id=empresa_id, funcao_tecnica=funcao, produto_id=produto.id,
        ativo=True, configuracoes_locais=configuracao,
    )
    db.add(equivalencia)
    db.flush()
    return equivalencia


def _vincular_perfil_emteco(db, diametro, perfil, familia, codigo_kit):
    tubo = _componente_tecnico(db, f"Tubo {diametro} Emteco", "ML", 20 + diametro)
    _equivalencia_tecnica(db, tubo, f"TUBO_ROLO_{diametro}MM", {
        "fabricante": "EMTECO", "perfil_tubo": perfil, "diametro_mm": diametro,
    })
    kit = _componente_tecnico(db, f"Kit {diametro} Emteco", "KIT", 45 + diametro)
    _equivalencia_tecnica(db, kit, "KIT_INSTALACAO_MOTOR_ROLO", {
        "fabricante": "EMTECO", "papel": "KIT_INSTALACAO", "perfil_tubo": perfil,
        "diametro_mm": diametro, "familia_instalacao": familia, "codigo_kit": codigo_kit,
    })
    for papel in ("SUPORTE", "ADAPTADOR", "PONTEIRA"):
        acessorio = _componente_tecnico(db, f"{papel.title()} {diametro}", "UN", 3)
        _equivalencia_tecnica(db, acessorio, "ACESSORIO_MOTOR", {
            "fabricante": "EMTECO", "papel": papel, "perfil_tubo": perfil,
            "diametro_mm": diametro, "familia_instalacao": familia,
            "tecnologias_compativeis": ["RF"], "quantidade_por_persiana": 1,
        })


def _preparar_motores_dinamicos(db):
    motor_12 = _componente_tecnico(db, "Motor Emteco 1.2 Nm RF", "UN", 120)
    _equivalencia_tecnica(db, motor_12, "MOTOR_PERSIANA", {
        "fabricante": "EMTECO", "familia": "ROLO", "torque_nm": 1.2,
        "tipo_motor": "ELETRONICO", "familia_instalacao": "1.2/1NM", "tecnologia": "RF",
    })
    _vincular_perfil_emteco(db, 38, "1221", "1.2/1NM", "KIT 38 BR")

    motor_6 = _componente_tecnico(db, "Motor Emteco 6 Nm RF", "UN", 180)
    _equivalencia_tecnica(db, motor_6, "MOTOR_PERSIANA", {
        "fabricante": "EMTECO", "familia": "ROLO", "torque_nm": 6,
        "tipo_motor": "PLUG", "familia_instalacao": "628/1014NM", "tecnologia": "RF",
    })
    _vincular_perfil_emteco(db, 43, "1740", "628/1014NM", "KIT 43 BR")
    _vincular_perfil_emteco(db, 53, "3268", "628/1014NM", "KIT 53 IMP")
    return motor_12, motor_6


def _kit_sintetico(db, diametro):
    return next(
        item.produto_id for item in db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
            empresa_id=1, funcao_tecnica="KIT_INSTALACAO_MOTOR_ROLO", ativo=True,
        ).all()
        if item.configuracoes_locais.get("diametro_mm") == diametro
    )


def _receita_motorizada_sintetica(db, produto, bitolas):
    empresa = db.get(EmpresaDB, 1)
    config = copy.deepcopy(empresa.configuracoes)
    receitas = config["receitas_rolo_v1"]
    chave_manual = "84:manual:BRANCO" if produto.id == 84 else str(produto.id)
    receita = copy.deepcopy(receitas[chave_manual])
    receita["tubos"] = {}
    receita["faixas_tubo"] = []
    for diametro, minimo, maximo in bitolas:
        vinculo = db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
            empresa_id=1, funcao_tecnica=f"TUBO_ROLO_{diametro}MM", ativo=True,
        ).one()
        tubo = db.get(ProdutoDB, vinculo.produto_id)
        receita["tubos"][f"{diametro}mm"] = {
            "produto_id": tubo.id, "codigo_interno": tubo.codigo_interno,
            "unidade_tecnica": "ML", "preco_compra": float(tubo.custo_final),
            "ipi_percentual": None, "unidades_por_compra": 1,
            "base_preco": "CUSTO_CADASTRADO", "diametro_mm": diametro,
            "origem": "Receita sintética isolada; sem validade comercial",
        }
        receita["faixas_tubo"].append({
            "diametro_mm": diametro, "largura_min_m": minimo, "largura_max_m": maximo,
            "altura_max_m": 6, "origem": "Faixa sintética isolada de teste",
        })
    receitas[f"{produto.id}:motorizado"] = receita
    empresa.configuracoes = config
    db.flush()


def test_conjunto_legado_12nm_sem_identificacao_do_fabricante_nao_e_selecionavel():
    conjunto = SimpleNamespace(torque_nm=1.2, tubos={})
    assert _bitolas_motor_compativeis(conjunto, SimpleNamespace()) == []


def test_conjunto_legado_12nm_nao_aparece_nem_simula(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    motor, motor_6 = _preparar_motores_dinamicos(db)
    empresa = db.get(EmpresaDB, 1)
    configuracoes = copy.deepcopy(empresa.configuracoes)
    receita = configuracoes["receitas_rolo_v1"][str(produto.id)]
    tubo = receita["tubos"]["38mm"]
    insumo_motor = {
        "produto_id": motor.id, "codigo_interno": motor.codigo_interno,
        "unidade_tecnica": "UN", "preco_compra": 120, "ipi_percentual": 0,
        "unidades_por_compra": 1, "origem": "Fixture sintética",
    }
    kit = _componente_tecnico(db, "Kit legado sintético", "KIT", 20)
    insumo_kit = {**insumo_motor, "produto_id": kit.id, "codigo_interno": kit.codigo_interno,
                   "unidade_tecnica": "KIT", "preco_compra": 20}
    receita["conjuntos_motor"] = [{
        "motor": insumo_motor, "torque_nm": 1.2, "tecnologia": "RF",
        "tubos": {"38mm": tubo}, "kits_motor": {"38mm": insumo_kit},
        "faixas_tubo": [{"diametro_mm": 38, "largura_min_m": 0,
                         "largura_max_m": 2, "altura_max_m": 3,
                         "origem": "Fixture sintética"}],
    }]
    empresa.configuracoes = configuracoes
    db.flush()
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1,
        cor="AMENDOA", acionamento="motorizado",
    )
    assert [opcao["produto_id"] for opcao in listar_motores_rolo(db, produto, entrada, 1)] == [motor_6.id]
    with pytest.raises(ValueError, match="Motor sem tubo, kit, faixa técnica"):
        simular_rolo_catalogo(db, produto, entrada.model_copy(update={
            "motor_produto_id": motor.id, "kit_produto_id": kit.id,
        }), 1)


def _preparar_motor_fornecedor_explicito(db):
    motor = _componente_tecnico(db, "Motor fornecedor sintético TR25", "UN", 200)
    _equivalencia_tecnica(db, motor, "MOTOR_PERSIANA", {
        "fabricante": "FABRICANTE_TESTE", "familia": "ROLO", "torque_nm": 25,
        "tecnologia": "RF",
        "perfil_rolo": {
            "perfil_tubo": "TR25-41", "diametro_mm": 41,
            "familia_instalacao": "TR25",
            "largura_max_m": 2.2, "altura_max_m": 3.0,
            "capacidade_kg": 12, "peso_barra_kg": 1,
            "peso_estimado_kg_m2": 0.5,
            "codigos_kit": ["KIT ACAO TR25-41"],
            "origem": "Dados sintéticos exclusivos de teste",
        },
    })
    tubo = _componente_tecnico(db, "Tubo fornecedor sintético TR25-41", "ML", 25)
    _equivalencia_tecnica(db, tubo, "TUBO_ROLO_41MM", {
        "fabricante": "FABRICANTE_TESTE", "perfil_tubo": "TR25-41", "diametro_mm": 41,
        "familia_instalacao": "TR25", "motores_compativeis": [motor.id],
    })
    kit = _componente_tecnico(db, "Kit fornecedor sintético TR25-41", "KIT", 50)
    _equivalencia_tecnica(db, kit, "KIT_INSTALACAO_MOTOR_ROLO", {
        "fabricante": "FABRICANTE_TESTE", "papel": "KIT_INSTALACAO",
        "perfil_tubo": "TR25-41", "diametro_mm": 41,
        "familia_instalacao": "TR25", "codigo_kit": "KIT ACAO TR25-41",
        "motores_compativeis": [motor.id],
    })
    for papel in ("SUPORTE", "ADAPTADOR", "PONTEIRA"):
        acessorio = _componente_tecnico(db, f"{papel.title()} fornecedor sintético TR25-41", "UN", 5)
        _equivalencia_tecnica(db, acessorio, "ACESSORIO_MOTOR", {
            "fabricante": "FABRICANTE_TESTE", "papel": papel, "perfil_tubo": "TR25-41",
            "diametro_mm": 41, "familia_instalacao": "TR25",
            "tecnologias_compativeis": ["RF"], "quantidade_por_persiana": 1,
            "motores_compativeis": [motor.id],
        })
    return motor


def test_motorizacao_dinamica_aceita_fornecedor_com_perfil_explicito(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    motor = _preparar_motor_fornecedor_explicito(db)
    _receita_motorizada_sintetica(db, produto, [(41, 0, 2.2)])
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1, cor="AMENDOA",
        perfil_comercial="CONSUMIDOR_FINAL", acionamento="motorizado",
    )

    opcoes = listar_motores_rolo(db, produto, entrada, 1)

    assert [opcao["produto_id"] for opcao in opcoes] == [motor.id]
    assert opcoes[0]["diametro_tubo_mm"] == 41
    assert opcoes[0]["perfil_tubo"] == "TR25-41"
    assert opcoes[0]["limite_largura_m"] == 2.2
    assert opcoes[0]["capacidade_kg"] == 12
    assert opcoes[0]["carga_estimada_kg"] == pytest.approx(2.5)

    kit = next(
        item for item in db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
            empresa_id=1, funcao_tecnica="KIT_INSTALACAO_MOTOR_ROLO",
        ).all()
        if item.produto_id != motor.id
    )
    kit.configuracoes_locais = {**kit.configuracoes_locais, "fabricante": "JP"}
    db.flush()
    with pytest.raises(ValueError, match="Nenhum conjunto dinâmico compatível"):
        listar_motores_rolo(db, produto, entrada, 1)

    kit.configuracoes_locais = {**kit.configuracoes_locais, "fabricante": "FABRICANTE_TESTE"}
    db.get(ProdutoDB, kit.produto_id).unidade_venda = "UN"
    db.flush()
    with pytest.raises(ValueError, match="Nenhum conjunto dinâmico compatível"):
        listar_motores_rolo(db, produto, entrada, 1)

    db.get(ProdutoDB, kit.produto_id).unidade_venda = "KIT"
    kit.configuracoes_locais = {**kit.configuracoes_locais, "motores_compativeis": [999]}
    db.flush()
    with pytest.raises(ValueError, match="Nenhum conjunto dinâmico compatível"):
        listar_motores_rolo(db, produto, entrada, 1)


def test_motorizacao_dinamica_respeita_bitolas_da_receita_sintetica(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    motor_12, motor_6 = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5), (53, 2.5, 2.8)])
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1, cor="AMENDOA",
        perfil_comercial="CONSUMIDOR_FINAL", acionamento="motorizado",
    )

    opcoes = listar_motores_rolo(db, produto, entrada, 1)
    assert {item["produto_id"] for item in opcoes} == {motor_6.id}
    assert {item["diametro_tubo_mm"] for item in opcoes} == {43}
    with pytest.raises(ValueError, match="torque ou tipo fora dos limites documentados"):
        simular_rolo_catalogo(db, produto, entrada.model_copy(update={
            "motor_produto_id": motor_12.id, "kit_produto_id": _kit_sintetico(db, 43),
        }), 1)

    resultado_43 = simular_rolo_catalogo(
        db, produto, entrada.model_copy(update={
            "motor_produto_id": motor_6.id, "kit_produto_id": _kit_sintetico(db, 43),
        }), 1,
    )
    assert resultado_43["bitola_tecnica"] == "43mm"
    componentes = resultado_43["fabricacao_por_peca"]["componentes"]
    categorias = [item["categoria"] for item in componentes]
    assert categorias.count("Tecido") == 1
    assert not {"Comando", "Corrente", "Emenda corrente"} & set(categorias)
    assert {"Motor", "Acessórios do motor"} <= set(categorias)
    assert not {"Suporte do motor", "Adaptador do motor", "Ponteira do tubo"} & set(categorias)
    assert resultado_43["custo_tecnico"] == pytest.approx(sum(item["custo_total"] for item in componentes))
    empresa = db.get(EmpresaDB, 1)
    configuracoes = copy.deepcopy(empresa.configuracoes)
    receita = configuracoes["receitas_rolo_v1"][f"{produto.id}:motorizado"]
    receita["largura_bobina_m"] = 3.0
    receita["tecido"]["unidades_por_compra"] = 3.0
    empresa.configuracoes = configuracoes
    receita_manual_antes = copy.deepcopy(empresa.configuracoes)
    resultado_53 = simular_rolo_catalogo(
        db, produto,
        entrada.model_copy(update={
            "largura": 2.7, "altura": 4.8, "motor_produto_id": motor_6.id,
            "kit_produto_id": _kit_sintetico(db, 53),
        }),
        1,
    )
    assert resultado_53["bitola_tecnica"] == "53mm"
    assert db.get(EmpresaDB, 1).configuracoes == receita_manual_antes


def test_motor_nao_substitui_tubo_da_receita_sem_vinculo(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    _, motor = _preparar_motores_dinamicos(db)
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1,
        cor="AMENDOA", acionamento="motorizado", motor_produto_id=motor.id,
        kit_produto_id=_kit_sintetico(db, 43),
    )
    manual = entrada.model_copy(update={"acionamento": "manual", "motor_produto_id": None, "kit_produto_id": None})
    antes = simular_rolo_catalogo(db, produto, manual, 1)
    assert antes["bitola_tecnica"] == "32mm"
    with pytest.raises(ValueError, match="32 mm"):
        simular_rolo_catalogo(db, produto, entrada, 1)
    assert simular_rolo_catalogo(db, produto, manual, 1) == antes


@pytest.mark.parametrize(
    "schema,item_model",
    [(OrcamentoInput, OrcamentoItemDB), (PedidoCreate, PedidoItemDB)],
)
def test_composicao_dinamica_e_revalidada_ao_salvar_documento(picasso, schema, item_model):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    _, motor = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    esperado = simular_rolo_catalogo(
        db, produto,
        RoloSimulacaoInput(
            produto_id=produto.id, largura=1.5, altura=2, quantidade=1,
            cor="AMENDOA", perfil_comercial="CONSUMIDOR_FINAL",
            acionamento="motorizado", motor_produto_id=motor.id, kit_produto_id=_kit_sintetico(db, 43),
        ),
        1,
    )
    payload = schema(cliente_id=1, perfil_comercial="CONSUMIDOR_FINAL", itens=[{
        "produto_id": produto.id, "descricao": produto.nome, "unidade": "M2",
        "largura": 1.5, "altura": 2, "quantidade": 1, "cor": "AMENDOA",
        "acionamento": "motorizado", "preco_unitario": 0,
        "dados_tecnicos": {"rolo": {"motor_produto_id": motor.id, "kit_produto_id": _kit_sintetico(db, 43)}},
    }])
    documento = SimpleNamespace(itens=[])
    calcular_itens(db, documento, payload, 1, item_model)
    item = documento.itens[0]
    assert item.dados_tecnicos["rolo"]["motor_produto_id"] == motor.id
    assert item.preco_unitario == esperado["preco_unitario"]
    assert item.dados_tecnicos["rolo"]["bitola"] == "43mm"


def test_motorizacao_dinamica_controles_exigem_vinculo_explicito(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    _, motor_6 = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    controle = _componente_tecnico(db, "Controle Emteco 1 canal", "UN", 60)
    _equivalencia_tecnica(db, controle, "ACESSORIO_MOTOR", {
        "fabricante": "EMTECO", "papel": "CONTROLE", "tipo": "CONTROLE_RF",
        "canais": 1, "motores_compativeis": [motor_6.id],
    })
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1, cor="AMENDOA",
        perfil_comercial="CONSUMIDOR_FINAL", acionamento="motorizado",
        motor_produto_id=motor_6.id, kit_produto_id=_kit_sintetico(db, 43),
    )
    assert listar_acessorios_comando_rolo(db, [entrada], 1) == [{
        "produto_id": controle.id, "nome": controle.nome,
        "codigo": controle.codigo_interno, "tipo": "CONTROLE_RF", "canais": 1,
    }]


@pytest.mark.parametrize("cor,tecidos", SCREEN_IMPORTADO_TECIDOS.items())
def test_screen_importado_84_motorizado_preserva_produto_cor_e_tecido(picasso, cor, tecidos):
    db, _ = picasso
    ativar(picasso)
    produto = configurar_screen_importado(db)
    _, motor = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    entrada = RoloSimulacaoInput(
        produto_id=84, largura=1.5, altura=1.72, quantidade=1, cor=cor,
        perfil_comercial="DECORADOR", acionamento="motorizado",
        motor_produto_id=motor.id, kit_produto_id=_kit_sintetico(db, 43),
    )
    resultado = simular_rolo_catalogo(db, produto, entrada, 1)
    assert produto.id == entrada.produto_id == 84
    assert resultado["componentes_tecnicos"]["tecido"]["produto_id"] == 6000 + int(tecidos[0][1][-4:])
    assert resultado["componentes_tecnicos"]["tecido"]["cor"] == cor
    assert resultado["bitola_tecnica"] == "43mm"
    categorias = [item["categoria"] for item in resultado["fabricacao_por_peca"]["componentes"]]
    assert categorias.count("Tecido") == 1
    assert not {"Comando", "Corrente", "Emenda corrente"} & set(categorias)


def test_kit_com_bom_inclui_suportes_sem_cobrar_itens_duplicados(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    _, motor = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    equivalencias = db.query(EmpresaEquivalenciaTecnicaDB).filter(
        EmpresaEquivalenciaTecnicaDB.empresa_id == 1,
        EmpresaEquivalenciaTecnicaDB.funcao_tecnica.in_(
            ("KIT_INSTALACAO_MOTOR_ROLO", "ACESSORIO_MOTOR"),
        ),
    ).all()
    kit = next(
        item for item in equivalencias
        if item.configuracoes_locais.get("papel") == "KIT_INSTALACAO"
        and item.configuracoes_locais.get("diametro_mm") == 43
    )
    componentes_incluidos = []
    for equivalencia in equivalencias:
        config = equivalencia.configuracoes_locais
        if config.get("diametro_mm") == 43 and config.get("papel") in {"SUPORTE", "ADAPTADOR", "PONTEIRA"}:
            componentes_incluidos.append({
                "papel": config["papel"], "produto_id": equivalencia.produto_id,
                "quantidade_por_persiana": 1,
            })
            db.delete(equivalencia)
    kit.configuracoes_locais = {
        **kit.configuracoes_locais,
        "componentes_incluidos": componentes_incluidos,
    }
    db.flush()
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1, cor="AMENDOA",
        perfil_comercial="CONSUMIDOR_FINAL", acionamento="motorizado",
        motor_produto_id=motor.id, kit_produto_id=kit.produto_id,
    )
    resultado = simular_rolo_catalogo(db, produto, entrada, 1)
    categorias = [item["categoria"] for item in resultado["fabricacao_por_peca"]["componentes"]]
    assert "Acessórios do motor" in categorias
    assert not {"Suporte do motor", "Adaptador do motor", "Ponteira do tubo"} & set(categorias)
    assert len(resultado["componentes_tecnicos"]["acessorios"]) == 1


def test_motorizacao_dinamica_bloqueia_componente_sem_custo(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    _, motor = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    suporte = next(
        item for item in db.query(ProdutoDB).filter_by(empresa_id=1).all()
        if item.nome == "Suporte 43"
    )
    suporte.custo_final = 0
    suporte.valor_custo = 0
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1, cor="AMENDOA",
        perfil_comercial="CONSUMIDOR_FINAL", acionamento="motorizado",
        motor_produto_id=motor.id, kit_produto_id=_kit_sintetico(db, 43),
    )
    with pytest.raises(ValueError, match="sem custo positivo"):
        simular_rolo_catalogo(db, produto, entrada, 1)


def test_motorizacao_dinamica_bloqueia_perfil_sem_ponteira_de_outra_empresa(picasso):
    db, _ = picasso
    ativar(picasso)
    produto = acabado(db)
    _, motor = _preparar_motores_dinamicos(db)
    _receita_motorizada_sintetica(db, produto, [(43, 0, 2.5)])
    for equivalencia in db.query(EmpresaEquivalenciaTecnicaDB).filter_by(
        empresa_id=1, funcao_tecnica="ACESSORIO_MOTOR",
    ).all():
        config = equivalencia.configuracoes_locais
        if config.get("papel") == "PONTEIRA" and config.get("diametro_mm") == 43:
            db.delete(equivalencia)
    ponteira_outra = _componente_tecnico(db, "Ponteira externa", "UN", 3, empresa_id=2)
    _equivalencia_tecnica(db, ponteira_outra, "ACESSORIO_MOTOR", {
        "fabricante": "EMTECO", "papel": "PONTEIRA", "perfil_tubo": "1740",
        "diametro_mm": 43, "familia_instalacao": "628/1014NM",
        "tecnologias_compativeis": ["RF"], "quantidade_por_persiana": 1,
    }, empresa_id=2)
    entrada = RoloSimulacaoInput(
        produto_id=produto.id, largura=1.5, altura=2, quantidade=1, cor="AMENDOA",
        perfil_comercial="CONSUMIDOR_FINAL", acionamento="motorizado",
        motor_produto_id=motor.id, kit_produto_id=_kit_sintetico(db, 43),
    )
    with pytest.raises(ValueError, match="ponteira"):
        simular_rolo_catalogo(db, produto, entrada, 1)
