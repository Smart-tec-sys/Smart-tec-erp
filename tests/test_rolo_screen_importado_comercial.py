"""Screen 84: preço comercial separado da fabricação, só SQLite em memória.

Os vínculos motorizados deste arquivo são fictícios e não aprovam componentes
reais nem ativam receitas no DEV, staging ou produção.
"""
import copy
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.models.cliente import ClienteDB
from app.models.empresa import EmpresaDB
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB, OrcamentoParcelaDB
from app.models.produto import ProdutoDB
from app.schemas.orcamento import OrcamentoInput
from app.services import orcamento_service, rolo_receita
from app.services.composicao_comercial import MULTIPLICADORES, calcular_itens
from app.services.rolo_simulacao import RoloSimulacaoInput
from app.tenant.context import TenantContext
from test_rolo_picasso import acabado, ativar, configurar_screen_importado, picasso  # noqa: F401


CENTAVO = Decimal("0.01")
TABELA = {"DECORADOR": Decimal("115.80"), "VAREJO": Decimal("120.00"),
          "CONSUMIDOR_FINAL": Decimal("150.00")}
CORES = ("BRANCO", "BEGE", "CINZA", "PRETO")

MINIMOS_MANUAL = {
    "DECORADOR": Decimal("90.00"),
    "VAREJO": Decimal("120.00"),
    "CONSUMIDOR_FINAL": Decimal("150.00"),
}


def dinheiro(value):
    return Decimal(str(value)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def estado(db):
    """Compara colunas persistidas sem recalcular documentos históricos."""
    return {
        model.__tablename__: [
            {attribute.key: copy.deepcopy(getattr(row, attribute.key)) for attribute in model.__mapper__.column_attrs}
            for row in db.query(model).order_by(model.id).all()
        ]
        for model in (EmpresaDB, ProdutoDB, OrcamentoDB, OrcamentoItemDB)
    }


@pytest.fixture
def screen(picasso):
    db, _ = picasso
    OrcamentoParcelaDB.__table__.create(db.get_bind(), checkfirst=True)
    ativar(picasso)
    produto = configurar_screen_importado(db)
    produto.custo_final = produto.valor_custo = 60
    db.add(ClienteDB(id=9100, empresa_id=1, tipo="Física", nome="Cliente histórico sintético"))
    historico = OrcamentoDB(id=9100, empresa_id=1, numero="HISTORICO-SINTETICO", cliente_id=9100,
                           total=Decimal("77.77"), total_final=Decimal("77.77"))
    historico.itens = [OrcamentoItemDB(
        id=9100, empresa_id=1, produto_id=84, descricao="Preço histórico preservado",
        tipo_item="PRODUTO", unidade="M2", quantidade=1, largura=1, altura=1,
        preco_unitario=Decimal("77.77"), subtotal=Decimal("77.77"),
        dados_tecnicos={"historico_sintetico": True},
    )]
    db.add(historico)
    db.commit()
    return db, produto


def entrada(produto, **changes):
    values = dict(produto_id=produto.id, largura=1.2, altura=2, quantidade=1,
                  cor="BRANCO", perfil_comercial="VAREJO", acionamento="manual")
    values.update(changes)
    return RoloSimulacaoInput(**values)


def conferir_fabricacao(result, largura, altura, quantidade, expected_count):
    componentes = result["fabricacao_por_peca"]["componentes"]
    assert len(componentes) == expected_count
    assert sum(item["categoria"] == "Tecido" for item in componentes) == 1
    tecido = next(item for item in componentes if item["categoria"] == "Tecido")
    assert tecido["quantidade"] == pytest.approx(round((largura - .03) * (altura + .15) * 1.05 * quantidade, 4))
    assert result["custo_tecnico"] == pytest.approx(sum(item["custo_total"] for item in componentes), abs=.0002)
    assert result["custo_tecnico"] > 0
    assert len(result["receita"]["custos"]) == expected_count
    tecido_id = result["componentes_tecnicos"]["tecido"]["produto_id"]
    assert sum(item["produto_id"] == tecido_id for item in result["receita"]["custos"]) == 1


@pytest.mark.parametrize("cor", CORES)
@pytest.mark.parametrize("perfil", tuple(TABELA))
@pytest.mark.parametrize("largura,altura", [(0.5, 1.0), (1.9, 2.0)])
def test_manual_tabela_por_perfil_minimo_por_peca_quantidade_desconto_e_preservacao(screen, cor, perfil, largura, altura):
    db, produto = screen
    quantidade, desconto = 3, Decimal("7.35")
    antes = estado(db)
    with patch.object(db, "commit", side_effect=AssertionError("Simulação não grava")), \
         patch.object(rolo_receita, "calcular_produto_sob_medida", wraps=rolo_receita.calcular_produto_sob_medida) as fabricar:
        result = rolo_receita.simular_rolo_catalogo(
            db, produto, entrada(produto, cor=cor, perfil_comercial=perfil, largura=largura,
                                 altura=altura, quantidade=quantidade, desconto=float(desconto)), 1,
        )
    fabricar.assert_called_once()
    assert fabricar.call_args.args[3] == quantidade
    expected_area = max(Decimal(str(largura)) * Decimal(str(altura)), Decimal("1.50")) * quantidade
    assert Decimal(str(result["area_faturavel_m2"])) == expected_area
    assert result["minimo_faturavel_aplicado"] is (largura * altura < 1.5)
    preco = max(
        dinheiro(Decimal(str(result["custo_tecnico"])) * MULTIPLICADORES[perfil] / expected_area),
        MINIMOS_MANUAL[perfil],
    )
    assert result["preco_unitario"] == preco
    assert result["subtotal"] == dinheiro(preco * expected_area - desconto)
    assert result["componentes_tecnicos"]["tecido"]["cor"] == cor
    conferir_fabricacao(result, largura, altura, quantidade, 10)
    assert estado(db) == antes


@pytest.mark.parametrize("perfil", tuple(TABELA))
def test_calcular_itens_usa_preco_final_uma_vez_e_preserva_memoria_historica(screen, perfil):
    db, produto = screen
    antes = estado(db)
    documento = SimpleNamespace(itens=[])
    with patch.object(db, "commit", side_effect=AssertionError("Composição não grava")):
        calcular_itens(db, documento, OrcamentoInput(cliente_id=9100, perfil_comercial=perfil, itens=[{
            "produto_id": 84, "descricao": produto.nome, "unidade": "M2", "cor": "PRETO",
            "largura": .6, "altura": 1, "quantidade": 2, "desconto": 5.25,
            "acionamento": "manual", "preco_unitario": 99999,
        }]), 1, OrcamentoItemDB)
    assert len(documento.itens) == 1
    row = documento.itens[0]
    assert row.produto_id == 84
    custo = sum(Decimal(str(c["custo_total"])) for c in row.dados_tecnicos["rolo"]["fabricacao"]["componentes"])
    preco = max(
        dinheiro(custo * MULTIPLICADORES[perfil] / 3),
        MINIMOS_MANUAL[perfil],
    )
    assert row.preco_unitario == preco
    assert row.subtotal == dinheiro(preco * 3 - Decimal("5.25"))
    assert documento.total == row.subtotal
    assert row.dados_tecnicos["comercial"]["preco_unitario_sugerido"] == float(preco)
    assert len(row.dados_tecnicos["rolo"]["fabricacao"]["componentes"]) == 10
    assert estado(db) == antes


def test_preco_independe_do_custo_antigo_do_acabado(screen):
    db, produto = screen
    first = rolo_receita.simular_rolo_catalogo(db, produto, entrada(produto), 1)
    produto.custo_final = 75
    db.flush()
    antes = estado(db)
    second = rolo_receita.simular_rolo_catalogo(db, produto, entrada(produto), 1)
    decorador = rolo_receita.simular_rolo_catalogo(db, produto, entrada(produto, perfil_comercial="DECORADOR"), 1)
    final = rolo_receita.simular_rolo_catalogo(db, produto, entrada(produto, perfil_comercial="CONSUMIDOR_FINAL"), 1)
    for result, perfil in [(first, "VAREJO"), (second, "VAREJO"),
                           (decorador, "DECORADOR"), (final, "CONSUMIDOR_FINAL")]:
        assert result["preco_unitario"] == max(
            dinheiro(
                Decimal(str(result["custo_tecnico"])) * MULTIPLICADORES[perfil]
                / Decimal(str(result["area_faturavel_m2"]))
            ),
            MINIMOS_MANUAL[perfil],
        )
    assert first["custo_tecnico"] == second["custo_tecnico"] == decorador["custo_tecnico"] == final["custo_tecnico"]
    assert first["fabricacao_por_peca"] == second["fabricacao_por_peca"] == decorador["fabricacao_por_peca"] == final["fabricacao_por_peca"]
    assert estado(db) == antes


def test_edicao_preserva_historico_e_calcula_apenas_novo_item(screen):
    db, _ = screen
    tenant = TenantContext(empresa_id=1)
    original = orcamento_service.obter(db, 9100, tenant)
    historico = original["itens"][0]
    with patch.object(rolo_receita, "simular_rolo_catalogo", wraps=rolo_receita.simular_rolo_catalogo) as simular:
        editado = orcamento_service.atualizar(db, 9100, OrcamentoInput(
            cliente_id=9100, perfil_comercial="VAREJO", observacao="Edição",
            itens=[historico, {"produto_id": 84, "descricao": "Screen nova",
                   "unidade": "M2", "cor": "BRANCO", "largura": 1.9, "altura": 2,
                   "quantidade": 1, "acionamento": "manual"}]), tenant)
    simular.assert_called_once()
    itens = {item["id"]: item for item in editado["itens"]}
    assert itens[historico["id"]]["preco_unitario"] == historico["preco_unitario"]
    assert itens[historico["id"]]["subtotal"] == historico["subtotal"]
    assert itens[historico["id"]]["dados_tecnicos"] == historico["dados_tecnicos"]
    assert len(itens) == 2
    assert dinheiro(editado["total"]) == dinheiro(sum(item["subtotal"] for item in itens.values()))


def test_recalculo_explicito_preserva_outro_item_e_rejeita_ids_invalidos(screen):
    db, _ = screen
    tenant = TenantContext(empresa_id=1)
    original = orcamento_service.obter(db, 9100, tenant)
    historico = original["itens"][0]
    novo = {"produto_id": 84, "descricao": "Screen nova", "unidade": "M2",
            "cor": "BRANCO", "largura": 1.9, "altura": 2, "quantidade": 1,
            "acionamento": "manual"}
    editado = orcamento_service.atualizar(db, 9100, OrcamentoInput(
        cliente_id=9100, itens=[historico, novo]), tenant)
    outro = next(item for item in editado["itens"] if item["id"] != historico["id"])
    recalc = dict(outro, recalcular=True, cor="PRETO")
    resultado = orcamento_service.atualizar(db, 9100, OrcamentoInput(
        cliente_id=9100, itens=[historico, recalc]), tenant)
    itens = {item["id"]: item for item in resultado["itens"]}
    assert itens[historico["id"]]["subtotal"] == historico["subtotal"]
    assert itens[outro["id"]]["cor"] == "PRETO"
    omitido = orcamento_service.atualizar(db, 9100, OrcamentoInput(cliente_id=9100, itens=[historico]), tenant)
    assert {item["id"] for item in omitido["itens"]} == {historico["id"], outro["id"]}
    with pytest.raises(ValueError, match="Identidade"):
        orcamento_service.atualizar(db, 9100, OrcamentoInput(cliente_id=9100, itens=[historico, historico]), tenant)
    with pytest.raises(ValueError, match="alterado"):
        orcamento_service.atualizar(db, 9100, OrcamentoInput(
            cliente_id=9100, itens=[dict(historico, preco_unitario=1), itens[outro["id"]]]), tenant)


@pytest.mark.parametrize("categoria", ["TR", "BK"])
@pytest.mark.parametrize("perfil", tuple(TABELA))
def test_tabela_84_nao_altera_precificacao_de_outra_colecao(screen, categoria, perfil):
    db, _ = screen
    produto = acabado(db, categoria)
    antes = estado(db)
    result = rolo_receita.simular_rolo_catalogo(db, produto, entrada(produto, cor="AMENDOA", perfil_comercial=perfil), 1)
    expected = dinheiro(Decimal(str(result["custo_tecnico"])) * MULTIPLICADORES[perfil]
                        / Decimal(str(result["area_faturavel_m2"])))
    assert produto.id != 84
    assert result["preco_unitario"] == expected
    assert estado(db) == antes


def insumo_sintetico(db, codigo, unidade, diametro, custo):
    produto = ProdutoDB(empresa_id=1, nome=f"Exclusivamente sintético {codigo}", codigo_interno=codigo,
                        tipo_produto="Componente", unidade_venda=unidade,
                        custo_final=custo, valor_custo=custo, situacao="Ativo")
    db.add(produto)
    db.flush()
    return {"produto_id": produto.id, "codigo_interno": codigo, "unidade_tecnica": unidade,
            "preco_compra": custo, "ipi_percentual": None, "unidades_por_compra": 1,
            "base_preco": "CUSTO_CADASTRADO", "diametro_mm": diametro,
            "origem": "Conjunto fictício aprovado apenas na fixture SQLite; sem validade comercial"}


@pytest.fixture
def motor_screen(screen):
    db, produto = screen
    empresa = db.get(EmpresaDB, 1)
    config = copy.deepcopy(empresa.configuracoes)
    receita = copy.deepcopy(config["receitas_rolo_v1"]["84:manual:BRANCO"])
    tubo = receita["tubos"]["32mm"]
    motor = insumo_sintetico(db, "TEST-84-MOTOR6RF", "UN", 32, 350)
    kit = insumo_sintetico(db, "TEST-84-KIT32", "KIT", 32, 20)
    produto._kit_teste = kit["produto_id"]
    faixas = [{"diametro_mm": 32, "largura_min_m": 0, "largura_max_m": 1.8, "altura_max_m": 3.5,
               "origem": "Faixa exclusivamente fictícia da fixture; não é especificação física aprovada"}]
    receita["conjuntos_motor"] = [{"motor": motor, "torque_nm": 6, "tecnologia": "RF",
                                   "tubos": {"32mm": tubo}, "kits_motor": {"32mm": kit},
                                   "faixas_tubo": faixas, "capacidade_kg": 10,
                                   "peso_barra_kg": 1, "peso_estimado_kg_m2": 0.5,
                                   "origem_carga": "Valores sintéticos de teste"}]
    receita["faixas_tubo"] = faixas
    config["receitas_rolo_v1"]["84:motorizado"] = receita
    empresa.configuracoes = config
    db.commit()
    return db, produto, motor


@pytest.mark.parametrize("perfil", tuple(TABELA))
def test_motorizado_84_mantem_custo_da_composicao_vezes_multiplicador(motor_screen, perfil):
    db, produto, motor = motor_screen
    antes = estado(db)
    with patch.object(db, "commit", side_effect=AssertionError("Simulação não grava")):
        result = rolo_receita.simular_rolo_catalogo(
            db, produto, entrada(produto, acionamento="motorizado", motor_produto_id=motor["produto_id"], kit_produto_id=produto._kit_teste,
                                 perfil_comercial=perfil, quantidade=2, desconto=7.25), 1,
        )
    expected = dinheiro(Decimal(str(result["custo_tecnico"])) * MULTIPLICADORES[perfil]
                        / Decimal(str(result["area_faturavel_m2"])))
    assert result["preco_unitario"] == expected
    assert result["preco_unitario"] != TABELA[perfil]
    assert result["subtotal"] == dinheiro(expected * Decimal("4.8") - Decimal("7.25"))
    assert result["componentes_tecnicos"]["motor"]["produto_id"] == motor["produto_id"]
    conferir_fabricacao(result, 1.2, 2, 2, 9)
    assert estado(db) == antes


@pytest.mark.parametrize("cor,tecido_id", [("BRANCO", 6001), ("BEGE", 6002), ("CINZA", 6003), ("PRETO", 6004)])
def test_motorizado_reusa_receita_manual_84_e_resolve_tecido_por_cor(motor_screen, cor, tecido_id):
    db, produto, motor = motor_screen
    before_manual = rolo_receita.simular_rolo_catalogo(
        db, produto, entrada(produto, cor=cor, acionamento="manual"), 1
    )
    result = rolo_receita.simular_rolo_catalogo(
        db, produto, entrada(produto, cor=cor, acionamento="motorizado",
                             motor_produto_id=motor["produto_id"], kit_produto_id=produto._kit_teste), 1
    )
    assert result["componentes_tecnicos"]["tecido"]["produto_id"] == tecido_id
    assert result["componentes_tecnicos"]["tecido"]["cor"] == cor
    assert result["componentes_tecnicos"]["motor"]["produto_id"] == motor["produto_id"]
    categories = {item["categoria"] for item in result["fabricacao_por_peca"]["componentes"]}
    assert not {"Comando", "Corrente", "Emenda corrente"} & categories
    assert before_manual["componentes_tecnicos"]["tecido"]["produto_id"] == tecido_id


@pytest.mark.parametrize("manual_price", [False, True])
def test_sem_receita_motorizada_calculo_e_salvamento_falham_mesmo_com_preco_digitado(screen, manual_price):
    db, produto = screen
    antes = estado(db)
    item = {"produto_id": 84, "descricao": produto.nome, "unidade": "M2", "cor": "BRANCO",
            "largura": 1.2, "altura": 2, "quantidade": 1, "acionamento": "motorizado",
            "preco_unitario": 99999, "preco_unitario_manual": manual_price}
    payload = OrcamentoInput(cliente_id=9100, perfil_comercial="VAREJO", itens=[item])
    documento = SimpleNamespace(itens=[])
    with pytest.raises(ValueError, match="motorizad"):
        calcular_itens(db, documento, payload, 1, OrcamentoItemDB)
    assert documento.itens == []
    with patch.object(orcamento_service, "_numero", return_value="TESTE-MOTOR-BLOQUEADO"), \
         patch.object(db, "commit", side_effect=AssertionError("Orçamento incompleto não grava")):
        with pytest.raises(ValueError, match="motorizad"):
            orcamento_service.criar(db, payload, TenantContext(empresa_id=1))
    assert estado(db) == antes
