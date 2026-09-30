"""Testes do serviço de simulação do Rolô."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.rolo_simulacao import (
    RoloSimulacaoInput,
    simular_rolo,
    _tipo_rolo,
    _montar_catalogo_rolo,
)
from app.technical.rules.rolo import (
    TuboRoloDiametro,
    AcionamentoPermitido,
    MotorObrigatorioErro,
)


class MockProduto:
    def __init__(self, modelo_tecnico="ROLO", nome="Rolô Teste", **kwargs):
        self.modelo_tecnico = modelo_tecnico
        self.nome = nome
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestTipoRolo(unittest.TestCase):
    def test_rolo_manual(self):
        produto = MockProduto(modelo_tecnico="ROLO", nome="Rolô Manual")
        self.assertEqual(_tipo_rolo(produto), "MANUAL")

    def test_rolo_motorizada(self):
        produto = MockProduto(modelo_tecnico="ROLO", nome="Rolô Motorizada")
        self.assertEqual(_tipo_rolo(produto), "MOTORIZADA")

    def test_rolô_com_acento(self):
        produto = MockProduto(modelo_tecnico="ROLÔ", nome="Rolô Manual")
        self.assertEqual(_tipo_rolo(produto), "MANUAL")

    def test_nao_rolo(self):
        produto = MockProduto(modelo_tecnico="ROMANA", nome="Romana Manual")
        self.assertIsNone(_tipo_rolo(produto))

    def test_double_vision_nao_rolo(self):
        produto = MockProduto(modelo_tecnico="DOUBLE_VISION", nome="Double Vision")
        self.assertIsNone(_tipo_rolo(produto))


class TestMontarCatalogoRolo(unittest.TestCase):
    def test_catalogo_tem_todos_componentes(self):
        catalogo = _montar_catalogo_rolo(TuboRoloDiametro.D32)
        self.assertIn("tecido", catalogo)
        self.assertIn("fita_tubo", catalogo)
        self.assertIn("base", catalogo)
        self.assertIn("fita_base", catalogo)
        self.assertIn("espaguete_base", catalogo)
        self.assertIn("corrente", catalogo)
        self.assertIn("emenda_corrente", catalogo)
        self.assertIn("tampa_base", catalogo)
        self.assertIn("TUBO_ROLO_32MM", catalogo)
        self.assertIn("COMANDO_32MM", catalogo)

    def test_catalogo_tubo_65mm(self):
        catalogo = _montar_catalogo_rolo(TuboRoloDiametro.D65)
        self.assertIn("TUBO_ROLO_65MM", catalogo)
        self.assertIn("COMANDO_65MM", catalogo)


class TestSimularRolo(unittest.TestCase):
    def setUp(self):
        self.produto = MockProduto(
            modelo_tecnico="ROLO",
            nome="Rolô Manual",
            custo_final=100.0,
            valor_venda=200.0,
        )

    def test_entrada_invalida_manual_maior_320(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=3.50,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        with self.assertRaises(ValueError) as cm:
            simular_rolo(self.produto, entrada)
        self.assertIn("motorização obrigatória", str(cm.exception).lower())

    def test_entrada_valida_manual_150(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=1.50,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        self.assertEqual(resultado["bitola_tecnica"], "32mm")
        self.assertEqual(resultado["acionamento_permitido"], "manual")
        self.assertFalse(resultado["requer_confirmacao_vendedor"])
        self.assertEqual(resultado["modelo"], "ROLÔ")
        self.assertEqual(resultado["tipo_acionamento"], "MANUAL")
        self.assertEqual(resultado["quantidade_pecas"], 1)
        self.assertAlmostEqual(resultado["area_total"], Decimal("3.75"))

    def test_entrada_valida_manual_181(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=1.81,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        self.assertEqual(resultado["bitola_tecnica"], "38mm")
        self.assertEqual(resultado["acionamento_permitido"], "manual")

    def test_entrada_valida_manual_251(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.51,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        self.assertEqual(resultado["bitola_tecnica"], "43mm")
        self.assertEqual(resultado["acionamento_permitido"], "manual")

    def test_entrada_valida_manual_320(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=3.20,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        self.assertEqual(resultado["bitola_tecnica"], "43mm")
        self.assertEqual(resultado["acionamento_permitido"], "manual")

    def test_entrada_valida_motorizada_321(self):
        produto_motor = MockProduto(
            modelo_tecnico="ROLO",
            nome="Rolô Motorizada",
            custo_final=100.0,
            valor_venda=200.0,
        )
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=3.21,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="motorizado",
        )
        resultado = simular_rolo(produto_motor, entrada)
        self.assertEqual(resultado["bitola_tecnica"], "65mm")
        self.assertEqual(resultado["acionamento_permitido"], "motorizado")
        self.assertTrue(resultado["requer_confirmacao_vendedor"])
        self.assertIsNotNone(resultado["observacao_tecnica"])
        self.assertIn("65mm", resultado["observacao_tecnica"])
        self.assertIn("confirmação do vendedor", resultado["observacao_tecnica"].lower())

    def test_produto_manual_com_acionamento_motorizado_erro(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="motorizado",
        )
        with self.assertRaises(ValueError) as cm:
            simular_rolo(self.produto, entrada)
        self.assertIn("manual", str(cm.exception).lower())

    def test_produto_motorizado_com_acionamento_manual_erro(self):
        produto_motor = MockProduto(
            modelo_tecnico="ROLO",
            nome="Rolô Motorizada",
        )
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        with self.assertRaises(ValueError) as cm:
            simular_rolo(produto_motor, entrada)
        self.assertIn("motorizada", str(cm.exception).lower())

    def test_nao_rolo_rejeitado(self):
        produto_romana = MockProduto(modelo_tecnico="ROMANA", nome="Romana Manual")
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        with self.assertRaises(ValueError) as cm:
            simular_rolo(produto_romana, entrada)
        self.assertIn("somente para produtos rolô", str(cm.exception).lower())

    def test_componentes_tecnicos_presentes(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        comp = resultado["componentes_tecnicos"]
        self.assertIn("bitola_selecionada", comp)
        self.assertIn("tubo", comp)
        self.assertIn("comando", comp)
        self.assertIn("tecido", comp)
        self.assertIn("base", comp)
        self.assertIn("corrente", comp)
        self.assertIn("emenda_corrente", comp)
        self.assertIn("tampas", comp)
        self.assertIn("suportes", comp)
        self.assertIn("ponteira", comp)
        self.assertIn("bando_guias", comp)

    def test_preco_perfis(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="DECORADOR",
            desconto=0,
            acionamento="manual",
        )
        resultado_decorador = simular_rolo(self.produto, entrada)

        entrada.perfil_comercial = "VAREJO"
        resultado_varejo = simular_rolo(self.produto, entrada)

        entrada.perfil_comercial = "CONSUMIDOR_FINAL"
        resultado_consumidor = simular_rolo(self.produto, entrada)

        self.assertGreater(resultado_varejo["preco_unitario"], resultado_decorador["preco_unitario"])
        self.assertGreater(resultado_consumidor["preco_unitario"], resultado_varejo["preco_unitario"])

    def test_desconto_aplicado(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=50.0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        self.assertLess(resultado["subtotal"], resultado["preco_unitario"] * Decimal("5.0"))

    def test_quantidade_maior_que_1(self):
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=3,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(self.produto, entrada)
        self.assertEqual(resultado["quantidade_pecas"], 3)
        self.assertAlmostEqual(float(resultado["area_total"]), 15.0)

    def test_alertas_incluem_sem_custo(self):
        produto_sem_custo = MockProduto(modelo_tecnico="ROLO", nome="Rolô Manual", valor_custo=0, custo_final=0, valor_venda=0)

        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=2.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="manual",
        )
        resultado = simular_rolo(produto_sem_custo, entrada)
        alertas_texto = " ".join(resultado["alertas"])
        self.assertIn("sem custo cadastrado", alertas_texto.lower())

    def test_alerta_confirmacao_vendedor_para_65mm(self):
        produto_motor = MockProduto(
            modelo_tecnico="ROLO",
            nome="Rolô Motorizada",
            custo_final=100.0,
            valor_venda=200.0,
        )
        entrada = RoloSimulacaoInput(
            produto_id=1,
            largura=4.00,
            altura=2.50,
            quantidade=1,
            perfil_comercial="VAREJO",
            desconto=0,
            acionamento="motorizado",
        )
        resultado = simular_rolo(produto_motor, entrada)
        alertas_texto = " ".join(resultado["alertas"])
        self.assertIn("confirmação do vendedor", alertas_texto.lower())
        self.assertIn("motorização obrigatória", alertas_texto.lower())


if __name__ == "__main__":
    unittest.main()