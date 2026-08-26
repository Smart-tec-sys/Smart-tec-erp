import unittest

from app.services.romana_calculo_producao import (
    RomanaCalculoEntrada,
    calcular_producao_romana,
)


class RomanaCalculoProducaoTest(unittest.TestCase):
    def assert_calculo(self, altura, gomos, tamanho, base):
        resultado = calcular_producao_romana(
            RomanaCalculoEntrada(largura_cm=120, altura_cm=altura, quantidade=1)
        )
        self.assertEqual(resultado.quantidade_gomos, gomos)
        self.assertEqual(resultado.quantidade_gomos_inteiros, gomos - 1)
        self.assertAlmostEqual(resultado.tamanho_gomo_cm, tamanho, places=2)
        self.assertAlmostEqual(resultado.tamanho_base_cm, base, places=2)
        self.assertEqual(resultado.regra_varetas_status, "PENDENTE_CONFIRMACAO")
        self.assertEqual(resultado.calculo_tecido_producao, "PENDENTE")

    def test_casos_de_referencia(self):
        casos = (
            (120, 5, 26.67, 13.33),
            (150, 6, 27.27, 13.64),
            (180, 7, 27.69, 13.85),
            (200, 8, 26.67, 13.33),
            (220, 9, 25.88, 12.94),
            (260, 10, 27.37, 13.68),
        )
        for caso in casos:
            with self.subTest(altura=caso[0]):
                self.assert_calculo(*caso)

    def test_arredondamento_comercial_em_fronteiras(self):
        abaixo = calcular_producao_romana(RomanaCalculoEntrada(100, 62.49, 1))
        metade = calcular_producao_romana(RomanaCalculoEntrada(100, 62.50, 1))
        acima = calcular_producao_romana(RomanaCalculoEntrada(100, 62.51, 1))
        self.assertEqual(abaixo.quantidade_gomos, 2)
        self.assertEqual(metade.quantidade_gomos, 3)
        self.assertEqual(acima.quantidade_gomos, 3)

    def test_quantidade_de_gomos_nunca_menor_que_um(self):
        resultado = calcular_producao_romana(RomanaCalculoEntrada(100, 1, 1))
        self.assertEqual(resultado.quantidade_gomos, 1)
        self.assertEqual(resultado.quantidade_gomos_inteiros, 0)

    def test_valores_invalidos(self):
        for entrada in (
            RomanaCalculoEntrada(0, 120, 1),
            RomanaCalculoEntrada(-1, 120, 1),
            RomanaCalculoEntrada(100, 0, 1),
            RomanaCalculoEntrada(100, -1, 1),
            RomanaCalculoEntrada(100, 120, 0),
            RomanaCalculoEntrada(100, 120, -1),
        ):
            with self.subTest(entrada=entrada):
                with self.assertRaises(ValueError):
                    calcular_producao_romana(entrada)

    def test_romana_teto_e_motorizada_nao_usam_a_formula(self):
        with self.assertRaises(ValueError):
            calcular_producao_romana(RomanaCalculoEntrada(100, 120, 1, tipo="ROMANA_TETO"))
        with self.assertRaises(ValueError):
            calcular_producao_romana(RomanaCalculoEntrada(100, 120, 1, acionamento="MOTORIZADO"))


if __name__ == "__main__":
    unittest.main()

