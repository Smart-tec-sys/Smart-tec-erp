"""Negociação e parcelas: exclusivamente SQLite em memória e simuladores com mocks."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from test_orcamento_pagamentos import db, entrada, salvar  # noqa: F401
from test_motores_paridade_10l68 import MODELS, setup
from app.models.orcamento import OrcamentoDB
from app.models.produto import ProdutoDB
from app.schemas.orcamento import OrcamentoInput, OrcamentoItemInput, OrcamentoCondicoesRevendaInput
from app.schemas.pedido import PedidoCreate
from app.services import orcamento_service
from app.services.composicao_comercial import calcular_itens
from app.tenant.context import TenantContext

TENANT = TenantContext(empresa_id=1)


def dinheiro(valor):
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def item_produto(**mudancas):
    return dict(produto_id=10, descricao="Produto de teste", quantidade=2,
                largura=1.2, altura=2, preco_unitario=99999, subtotal=99999, **mudancas)


@pytest.mark.parametrize("unidade,base,base_editada", [
    ("UN", "2", "3"), ("ML", "2.4", "2.1"), ("M2", "4.8", "4.5"),
])
def test_criar_editar_reabrir_restaurar_sem_alterar_cadastro(db, unidade, base, base_editada):
    produto = ProdutoDB(id=10, empresa_id=1, nome="Produto de teste", modelo_tecnico="ACESSORIO",
                        unidade_venda=unidade, custo_final=100, valor_custo=80, valor_venda=230)
    db.add(produto)
    db.commit()
    criado = salvar(db, entrada(itens=[item_produto()]))
    assert criado["itens"][0]["preco_unitario"] == 200
    assert dinheiro(criado["total"]) == dinheiro(Decimal(base) * 200)
    assert criado["itens"][0]["preco_unitario_manual"] is False
    assert criado["itens"][0]["preco_unitario_sugerido"] == 200

    negociado = item_produto()
    negociado.update(preco_unitario=37.1256, preco_unitario_manual=True)
    orcamento_service.atualizar(db, criado["id"], entrada(itens=[negociado]), TENANT)
    db.expire_all()
    reaberto = orcamento_service.obter(db, criado["id"], TENANT)
    assert reaberto["itens"][0]["preco_unitario"] == 37.1256
    assert reaberto["itens"][0]["preco_unitario_manual"] is True
    assert dinheiro(reaberto["total"]) == dinheiro(Decimal(base) * Decimal("37.1256"))
    assert db.get(ProdutoDB, 10).custo_final == 100
    assert db.get(ProdutoDB, 10).valor_custo == 80
    assert db.get(ProdutoDB, 10).valor_venda == 230

    # O cadastro pode mudar; medidas e quantidade não autorizam perder a negociação.
    db.get(ProdutoDB, 10).custo_final = 120
    db.commit()
    editado = dict(reaberto["itens"][0], largura=.7, altura=.7, quantidade=3)
    atualizado = orcamento_service.atualizar(db, criado["id"], entrada(itens=[editado]), TENANT)
    assert atualizado["itens"][0]["preco_unitario"] == 37.1256
    assert atualizado["itens"][0]["preco_unitario_sugerido"] == 240
    assert dinheiro(atualizado["total"]) == dinheiro(Decimal(base_editada) * Decimal("37.1256"))
    assert orcamento_service.obter(db, criado["id"], TenantContext(empresa_id=2)) is None

    editado["preco_unitario_manual"] = False
    restaurado = orcamento_service.atualizar(db, criado["id"], entrada(itens=[editado]), TENANT)
    assert restaurado["itens"][0]["preco_unitario"] == 240
    assert restaurado["itens"][0]["preco_unitario_manual"] is False
    assert dinheiro(restaurado["total"]) == dinheiro(Decimal(base_editada) * 240)
    assert db.get(ProdutoDB, 10).valor_venda == 230


@pytest.mark.parametrize("modelo", MODELS)
@pytest.mark.parametrize("largura,quantidade", [(1.82, 1), (2, 2)])
def test_negociacao_preserva_motor_tecnico_e_pedidos(modelo, largura, quantidade):
    produto, item, esperado = setup(modelo, largura, quantidade)
    item.update(preco_unitario=77.7777, preco_unitario_manual=True, desconto=1.23)
    banco = MagicMock()
    banco.query.return_value.filter.return_value.first.return_value = produto
    documento = SimpleNamespace(itens=[])
    calcular_itens(banco, documento, OrcamentoInput(cliente_id=1, itens=[item]), 1, SimpleNamespace)
    salvo = documento.itens[0]
    base = Decimal(str(quantidade if modelo == "CORTINA" else esperado["area_faturavel_m2"]))
    assert salvo.preco_unitario == Decimal("77.7777")
    assert salvo.subtotal == dinheiro(base * Decimal("77.7777") - Decimal("1.23"))
    assert documento.total == salvo.subtotal
    assert salvo.calculo_producao_status == "SIMULACAO_RECALCULADA"
    assert salvo.dados_tecnicos["comercial"]["preco_unitario_sugerido"] == float(esperado["preco_unitario"])
    if modelo == "CORTINA":
        assert salvo.dados_tecnicos["cortina"]["result"]["custo_total"] == esperado["custo_total"]
    assert produto.custo_final == produto.valor_custo == 100
    banco.commit.assert_not_called()

    pedido = SimpleNamespace(itens=[])
    item_pedido = {k: v for k, v in item.items() if k != "preco_unitario_manual"}
    calcular_itens(banco, pedido, PedidoCreate(cliente_id=1, itens=[item_pedido]), 1, SimpleNamespace)
    assert pedido.itens[0].preco_unitario == esperado["preco_unitario"]
    assert dinheiro(pedido.itens[0].subtotal) == dinheiro(Decimal(str(esperado["subtotal"])) - Decimal("1.23"))


def test_preco_manual_nao_contorna_validacao_tecnica():
    produto, item, _ = setup("ROMANA_TETO")
    item.update(cor=None, preco_unitario=123, preco_unitario_manual=True)
    banco = MagicMock()
    banco.query.return_value.filter.return_value.first.return_value = produto
    with pytest.raises(ValueError, match="Preço técnico indisponível"):
        calcular_itens(banco, SimpleNamespace(itens=[]), OrcamentoInput(cliente_id=1, itens=[item]), 1, SimpleNamespace)


def plano(total):
    return dict(pagamento_modalidade="PARCELADO", pagamento_numero_parcelas=2,
                pagamento_intervalo_dias=30, pagamento_primeiro_vencimento=date(2026, 11, 10),
                pagamento_parcelas=[
                    dict(numero=1, valor=str(dinheiro(Decimal(str(total)) / 2)), vencimento="2026-11-10", forma_pagamento_id=1),
                    dict(numero=2, valor=str(Decimal(str(total)) - dinheiro(Decimal(str(total)) / 2)), vencimento="2026-12-10", forma_pagamento_id=1),
                ])


def servico(preco=100, quantidade=1):
    return dict(tipo_item="SERVICO", descricao="Instalação", quantidade=quantidade,
                preco_unitario=preco, preco_unitario_manual=True, subtotal=999999)


def test_servico_negociado_parcelado_edicoes_repetidas_e_taxa_unica(db):
    condicoes = dict(incluir_rt=True, tipo_rt="PERCENTUAL", percentual_rt=10,
                     incluir_taxa_bancaria=True, taxa_bancaria_percentual=10)
    criado = salvar(db, entrada(itens=[servico(81)], **condicoes, **plano(99)))
    assert criado["total_final"] == 81 and criado["valor_rt"] == 8.1
    assert criado["base_protegida"] == 89.1 and criado["valor_taxa_bancaria"] == 9.9
    assert criado["total_cliente_final"] == criado["pagamento_total"] == 99
    for preco, quantidade, total in [(90, 1, 110), (75, 2, 183.33), (45, 1, 55)]:
        salvo = orcamento_service.atualizar(db, criado["id"], entrada(
            itens=[servico(preco, quantidade)], **condicoes, **plano(total)), TENANT)
        db.expire_all()
        reaberto = orcamento_service.obter(db, criado["id"], TENANT)
        assert salvo["id"] == criado["id"]
        assert reaberto["pagamento_total"] == reaberto["total_cliente_final"] == total
        assert reaberto["itens"][0]["preco_unitario"] == preco
        assert reaberto["itens"][0]["preco_unitario_manual"] is True
        assert len(reaberto["pagamento_parcelas"]) == 2


@pytest.mark.parametrize("enviar_plano", [False, True])
def test_divergencia_parcelas_faz_rollback_integral(db, enviar_plano):
    criado = salvar(db, entrada(itens=[servico()], **plano(100)))
    kwargs = plano(100) if enviar_plano else {}
    with pytest.raises(ValueError, match="soma das parcelas"):
        orcamento_service.atualizar(db, criado["id"], entrada(itens=[servico(150)], **kwargs), TENANT)
    db.expire_all()
    reaberto = orcamento_service.obter(db, criado["id"], TENANT)
    assert reaberto["total_cliente_final"] == reaberto["pagamento_total"] == 100
    assert reaberto["itens"][0]["preco_unitario"] == 100
    assert [p["valor"] for p in reaberto["pagamento_parcelas"]] == [50, 50]


def test_plano_omitido_preservado_quando_total_nao_muda(db):
    criado = salvar(db, entrada(itens=[servico()], **plano(100)))
    atualizado = orcamento_service.atualizar(db, criado["id"], entrada(
        itens=[servico()], observacao="Alteração sem mudança comercial"), TENANT)
    assert atualizado["pagamento_total"] == 100
    assert [p["id"] for p in atualizado["pagamento_parcelas"]] == [p["id"] for p in criado["pagamento_parcelas"]]


def test_condicoes_revenda_rejeitam_parcelas_desatualizadas(db):
    criado = salvar(db, entrada(itens=[servico()], **plano(100)))
    orcamento = db.get(OrcamentoDB, criado["id"])
    orcamento.parceiro_id = 1
    db.commit()
    data = OrcamentoCondicoesRevendaInput(
        base_smarttec_esperada=100, total_cliente_esperado=100,
        atualizado_em_esperado=orcamento.atualizado_em, percentual_parceiro=50,
        desconto_pagamento_percentual=0, acrescimo_cartao_percentual=0, parcelas_cartao=1,
        observacao_comercial="Texto comercial", observacao_interna="Interno")
    with pytest.raises(ValueError, match="soma das parcelas"):
        orcamento_service.atualizar_condicoes_revenda(db, criado["id"], data, TENANT)
    db.expire_all()
    reaberto = orcamento_service.obter(db, criado["id"], TENANT)
    assert reaberto["total_cliente_final"] == reaberto["pagamento_total"] == 100
    assert reaberto["percentual_parceiro"] == 0


@pytest.mark.parametrize("campo", ["preco_unitario", "quantidade", "largura", "altura", "area", "desconto", "subtotal"])
@pytest.mark.parametrize("valor", [float("inf"), float("nan")])
def test_rejeita_numeros_nao_finitos(campo, valor):
    with pytest.raises(ValidationError):
        OrcamentoItemInput(**(dict(descricao="Item", preco_unitario_manual=True) | {campo: valor}))


@pytest.mark.parametrize("modelo", MODELS)
def test_modelo_tecnico_negociado_persiste_apos_edicao(db, modelo):
    produto, item, _ = setup(modelo, 2, 2)
    db.add(ProdutoDB(**vars(produto), empresa_id=1, largura=1.5, situacao="Ativo"))
    db.commit()
    item.update(preco_unitario=55.4321, preco_unitario_manual=True)
    criado = salvar(db, entrada(itens=[item]))
    db.expire_all()
    reaberto = orcamento_service.obter(db, criado["id"], TENANT)
    assert reaberto["itens"][0]["preco_unitario"] == 55.4321
    assert reaberto["itens"][0]["preco_unitario_manual"] is True
    editado = dict(reaberto["itens"][0], largura=1.8, altura=2, quantidade=3)
    atualizado = orcamento_service.atualizar(db, criado["id"], entrada(itens=[editado]), TENANT)
    db.expire_all()
    persistido = orcamento_service.obter(db, criado["id"], TENANT)
    base = Decimal("3") if modelo == "CORTINA" else Decimal("10.8")
    assert persistido["itens"][0]["preco_unitario"] == 55.4321
    assert dinheiro(persistido["total"]) == dinheiro(base * Decimal("55.4321"))
    assert atualizado["total"] == persistido["total"]
    assert db.get(ProdutoDB, 1).custo_final == 100
    assert db.get(ProdutoDB, 1).valor_venda == 250


def test_quantidade_fracionada_m2_nao_e_truncada(db):
    db.add(ProdutoDB(id=10, empresa_id=1, nome="Produto fracionado", unidade_venda="M2",
                     custo_final=100, modelo_tecnico="ACESSORIO"))
    db.commit()
    item = item_produto()
    item.update(quantidade=1.5, largura=1, altura=1, unidade="M2", preco_unitario=40, preco_unitario_manual=True)
    criado = salvar(db, entrada(itens=[item]))
    assert criado["itens"][0]["quantidade"] == 1.5
    assert criado["total"] == 90
    assert criado["itens"][0]["area_faturavel_m2"] == 2.25


def test_resposta_legada_identifica_falta_de_marcador(db):
    criado = salvar(db, entrada())
    item = db.get(OrcamentoDB, criado["id"]).itens[0]
    item.dados_tecnicos = None
    db.commit()
    reaberto = orcamento_service.obter(db, criado["id"], TENANT)
    assert reaberto["itens"][0]["preco_unitario_manual"] is None
    assert reaberto["itens"][0]["preco_unitario_sugerido"] is None
