"""Screen Standard consolidada: dados sintéticos, sem conexão com banco real."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.rolo_receita import simular_rolo_catalogo
from app.services.rolo_simulacao import RoloSimulacaoInput, simular_rolo


def produto(**campos):
    dados = dict(id=503, empresa_id=1, nome="ROL? SCREEN 3% STANDARD",
                 modelo_tecnico="ROLO", grupo_tecnico="PERSIANA_ROLO",
                 grupo_produto="Motorização",
                 tipo_produto="Produto fabricado", situacao="Ativo", unidade_venda="M²",
                 custo_final=66.08, valor_custo=66.08, valor_venda=116.8)
    return SimpleNamespace(**(dados | campos))


def banco(receitas=None):
    db = MagicMock()
    empresa = SimpleNamespace(configuracoes={"receitas_rolo_v1": receitas or {}})
    db.query.return_value.filter_by.return_value.one_or_none.return_value = empresa
    db.commit.side_effect = AssertionError("Simulação não pode gravar")
    db.flush.side_effect = AssertionError("Simulação não pode gravar")
    return db, empresa


def entrada(**campos):
    return RoloSimulacaoInput(**(dict(produto_id=503, largura=1.5, altura=2,
                                     quantidade=1, cor="BRANCO") | campos))


@pytest.mark.parametrize("cor", ["BRANCO", "CINZA"])
@pytest.mark.parametrize("perfil,preco", [("DECORADOR", "99.12"), ("VAREJO", "132.16"),
                                         ("CONSUMIDOR_FINAL", "165.20")])
def test_preco_do_acabado_e_mesmo_motor(cor, perfil, preco):
    db, empresa = banco()
    p = produto()
    antes = deepcopy(vars(p)), deepcopy(empresa.configuracoes)
    dados = entrada(cor=cor, perfil_comercial=perfil)
    result = simular_rolo_catalogo(db, p, dados, 1)
    assert result == simular_rolo(p, dados)
    assert result["preco_disponivel"]
    assert result["preco_unitario"] == Decimal(preco)
    assert result["subtotal"] == Decimal(preco) * 3
    assert result["custo_cadastrado"] == 66.08
    assert result["custo_tecnico"] is None, "não inventar composição técnica precificada"
    assert result["origem_preco"] == "CUSTO_CADASTRADO"
    assert (vars(p), empresa.configuracoes) == antes
    db.commit.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize("largura,bitola", [(1.8, "32mm"), (1.81, "38mm"),
                                           (2.5, "38mm"), (2.51, "43mm"), (3.2, "43mm")])
def test_bitola_existente(largura, bitola):
    db, _ = banco()
    assert simular_rolo_catalogo(db, produto(), entrada(largura=largura), 1)["bitola_tecnica"] == bitola


def test_area_minima_e_desconto():
    db, _ = banco()
    result = simular_rolo_catalogo(db, produto(), entrada(largura=.8, altura=1, quantidade=2, desconto=10), 1)
    assert result["minimo_faturavel_aplicado"]
    assert result["area_faturavel_m2"] == Decimal("3.0")
    assert result["subtotal"] == Decimal("386.48")


@pytest.mark.parametrize("campos,preco,origem", [
    ({"custo_final": 0}, "132.16", "CUSTO_CADASTRADO"),
    ({"custo_final": 0, "valor_custo": 0}, "116.80", "VALOR_VENDA_CADASTRADO"),
    ({"custo_final": 0, "valor_custo": 0, "valor_venda": 0}, "0.00", "VALOR_VENDA_CADASTRADO"),
])
def test_somente_dados_comerciais_validos(campos, preco, origem):
    db, _ = banco()
    result = simular_rolo_catalogo(db, produto(**campos), entrada(), 1)
    assert result["preco_unitario"] == Decimal(preco)
    assert result["preco_disponivel"] == (Decimal(preco) > 0)
    assert result["origem_preco"] == origem


@pytest.mark.parametrize("cor", [None, "", "BEGE", "PRETO"])
def test_nao_inclui_cores_importadas(cor):
    db, _ = banco()
    with pytest.raises(ValueError, match="BRANCO ou CINZA"):
        simular_rolo_catalogo(db, produto(), entrada(cor=cor), 1)


@pytest.mark.parametrize("receitas", [{"503": {}}, {"503:manual": {}}])
def test_receita_configurada_tem_precedencia_mesmo_se_invalida(receitas):
    db, _ = banco(receitas)
    with pytest.raises(ValueError, match="Receita Rol"):
        simular_rolo_catalogo(db, produto(), entrada(), 1)


@pytest.mark.parametrize("p", [produto(id=3530, nome="ROLÔ BK NAPOLES"),
                              produto(id=1290, nome="ROLÔ BK.BRISK 32MM BEGE"),
                              produto(id=7, nome="ROLO SCREEN 3% IMPORTADO"),
                              produto(nome="ROLO SCREEN 3% IMPORTADO"),
                              produto(tipo_produto="Componente"),
                              produto(id=523, tipo_produto="Componente"),
                              produto(situacao="Inativo")])
def test_fallback_nao_muda_outras_colecoes_ou_componentes(p):
    db, _ = banco()
    with pytest.raises(ValueError, match="não configurada"):
        simular_rolo_catalogo(db, p, entrada(produto_id=p.id), 1)


def test_motor_e_empresa_continuam_validados():
    db, _ = banco()
    with pytest.raises(ValueError, match="manual proibido"):
        simular_rolo_catalogo(db, produto(), entrada(largura=3.21), 1)
    with pytest.raises(ValueError, match="Selecione um motor"):
        simular_rolo_catalogo(db, produto(), entrada(acionamento="motorizado"), 1)
    with pytest.raises(ValueError, match="incompat"):
        simular_rolo_catalogo(db, produto(), entrada(), 2)
