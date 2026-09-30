"""Testes da regra central de área faturável (mínimo 1,50 m² para produtos vendidos em M²)."""
from decimal import Decimal
import unittest

from app.services.area_faturavel import (
    calcular_area_faturavel,
    AreaFaturavelResultado,
    MINIMO_FATURAVEL_M2,
    _unidade_eh_m2,
)


class AreaFaturavelTest(unittest.TestCase):
    """Testes da função calcular_area_faturavel."""

    def test_m2_minimo_aplicado_0_70_x_0_70_qtd_1(self):
        """0.70 x 0.70 = 0.49 m² -> faturável 1.50 m² (mínimo aplicado)."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, "M²")
        self.assertEqual(resultado.area_real_m2, Decimal("0.4900"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("1.5000"))
        self.assertTrue(resultado.minimo_faturavel_aplicado)

    def test_m2_minimo_aplicado_0_70_x_0_70_qtd_2(self):
        """0.70 x 0.70 = 0.49 m² x 2 = 0.98 m² real -> faturável 3.00 m² (1.50 x 2)."""
        resultado = calcular_area_faturavel(0.70, 0.70, 2, "M2")
        self.assertEqual(resultado.area_real_m2, Decimal("0.9800"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("3.0000"))
        self.assertTrue(resultado.minimo_faturavel_aplicado)

    def test_m2_minimo_aplicado_1_00_x_1_00(self):
        """1.00 x 1.00 = 1.00 m² -> faturável 1.50 m² (mínimo aplicado)."""
        resultado = calcular_area_faturavel(1.00, 1.00, 1, "M²")
        self.assertEqual(resultado.area_real_m2, Decimal("1.0000"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("1.5000"))
        self.assertTrue(resultado.minimo_faturavel_aplicado)

    def test_m2_minimo_nao_aplicado_1_00_x_1_50(self):
        """1.00 x 1.50 = 1.50 m² -> faturável 1.50 m² (mínimo NÃO aplicado, igual ao mínimo)."""
        resultado = calcular_area_faturavel(1.00, 1.50, 1, "M2")
        self.assertEqual(resultado.area_real_m2, Decimal("1.5000"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("1.5000"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_m2_minimo_nao_aplicado_1_20_x_1_80(self):
        """1.20 x 1.80 = 2.16 m² -> faturável 2.16 m² (mínimo NÃO aplicado, acima do mínimo)."""
        resultado = calcular_area_faturavel(1.20, 1.80, 1, "M²")
        self.assertEqual(resultado.area_real_m2, Decimal("2.1600"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("2.1600"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_unidade_un_nao_aplica_minimo(self):
        """UN não aplica mínimo de 1,50 m²."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, "UN")
        self.assertEqual(resultado.area_real_m2, Decimal("0.4900"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("0.4900"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_unidade_kit_nao_aplica_minimo(self):
        """KIT não aplica mínimo de 1,50 m²."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, "KIT")
        self.assertEqual(resultado.area_real_m2, Decimal("0.4900"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("0.4900"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_unidade_ml_nao_aplica_minimo(self):
        """ML não aplica mínimo de 1,50 m²."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, "ML")
        self.assertEqual(resultado.area_real_m2, Decimal("0.4900"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("0.4900"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_unidade_par_nao_aplica_minimo(self):
        """PAR não aplica mínimo de 1,50 m²."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, "PAR")
        self.assertEqual(resultado.area_real_m2, Decimal("0.4900"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("0.4900"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_unidade_none_nao_aplica_minimo(self):
        """None não aplica mínimo de 1,50 m²."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, None)
        self.assertEqual(resultado.area_real_m2, Decimal("0.4900"))
        self.assertEqual(resultado.area_faturavel_m2, Decimal("0.4900"))
        self.assertFalse(resultado.minimo_faturavel_aplicado)

    def test_unidade_m2_variacoes(self):
        """Testa variações de escrita de M²."""
        for unidade in ["M²", "M2", "m²", "m2", "METROQUADRADO", "MQ"]:
            resultado = calcular_area_faturavel(0.70, 0.70, 1, unidade)
            self.assertEqual(resultado.area_faturavel_m2, Decimal("1.5000"), f"Falhou para unidade: {unidade}")
            self.assertTrue(resultado.minimo_faturavel_aplicado, f"Falhou para unidade: {unidade}")

    def test_subtotal_calculo_0_70_x_0_70_preco_120_qtd_1(self):
        """0.70 x 0.70, preço 120, qtd 1 -> subtotal 180.00 (1.50 * 120)."""
        resultado = calcular_area_faturavel(0.70, 0.70, 1, "M²")
        preco = Decimal("120.00")
        subtotal = (resultado.area_faturavel_m2 * preco).quantize(Decimal("0.01"))
        self.assertEqual(subtotal, Decimal("180.00"))

    def test_subtotal_calculo_0_70_x_0_70_preco_120_qtd_2(self):
        """0.70 x 0.70, preço 120, qtd 2 -> subtotal 360.00 (3.00 * 120)."""
        resultado = calcular_area_faturavel(0.70, 0.70, 2, "M²")
        preco = Decimal("120.00")
        subtotal = (resultado.area_faturavel_m2 * preco).quantize(Decimal("0.01"))
        self.assertEqual(subtotal, Decimal("360.00"))

    def test_tipo_retorno_area_faturavel_resultado(self):
        """Verifica se o tipo de retorno é AreaFaturavelResultado."""
        resultado = calcular_area_faturavel(1.0, 1.0, 1, "M²")
        self.assertIsInstance(resultado, AreaFaturavelResultado)
        self.assertIsInstance(resultado.area_real_m2, Decimal)
        self.assertIsInstance(resultado.area_faturavel_m2, Decimal)
        self.assertIsInstance(resultado.minimo_faturavel_aplicado, bool)

    def test_constante_minimo_faturavel(self):
        """Verifica se a constante MINIMO_FATURAVEL_M2 é 1.50."""
        self.assertEqual(MINIMO_FATURAVEL_M2, Decimal("1.50"))


class UnidadeEhM2Test(unittest.TestCase):
    """Testes da função auxiliar _unidade_eh_m2."""

    def test_unidades_m2_true(self):
        for unidade in ["M²", "M2", "m²", "m2", "METROQUADRADO", "MQ", "M² ", " M2"]:
            self.assertTrue(_unidade_eh_m2(unidade), f"Deveria ser True para: {unidade}")

    def test_unidades_nao_m2_false(self):
        for unidade in ["UN", "KIT", "ML", "PAR", "PC", "CX", "KG", "LT", None, ""]:
            self.assertFalse(_unidade_eh_m2(unidade), f"Deveria ser False para: {unidade}")


if __name__ == "__main__":
    unittest.main()