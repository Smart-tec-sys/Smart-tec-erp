"""Caracteriza o motor Rolô atual sem alterar sua lógica."""

import unittest

from app.services.motor_calculo_produtos import calcular_produto_sob_medida


class RoloCaracterizacaoFase0Test(unittest.TestCase):
    def _catalogo(self, tubo):
        catalogo = {
            "tecido": {"codigo": "TEC", "nome": "Tecido teste", "unidade": "M²", "valor_custo": 10},
            "fita_tubo": {"codigo": "FT", "nome": "Fita tubo", "unidade": "ML", "valor_custo": 1},
            "base": {"codigo": "BAS", "nome": "Base", "unidade": "ML", "valor_custo": 2},
            "fita_base": {"codigo": "FB", "nome": "Fita base", "unidade": "ML", "valor_custo": 1.5},
            "espaguete_base": {"codigo": "ESP", "nome": "Espaguete", "unidade": "ML", "valor_custo": 0.5},
            "corrente": {"codigo": "COR", "nome": "Corrente", "unidade": "ML", "valor_custo": 3},
            "emenda_corrente": {"codigo": "EME", "nome": "Emenda", "unidade": "UN", "valor_custo": 0.25},
            "tampa_base": {"codigo": "TAM", "nome": "Tampa", "unidade": "UN", "valor_custo": 0.75},
        }
        catalogo[tubo] = {"codigo": tubo, "nome": tubo, "unidade": "ML", "valor_custo": 4}
        comando = "comando_32" if tubo == "tubo_32" else "comando_38"
        catalogo[comando] = {"codigo": "CMD", "nome": "Comando", "unidade": "KIT", "valor_custo": 12}
        return catalogo

    def _assert_receita_atual(self, tubo):
        resultado = calcular_produto_sob_medida(
            "Rolô", 2, 2, 2, catalogo=self._catalogo(tubo)
        )
        componentes = {item.categoria: item for item in resultado.componentes}
        self.assertEqual(resultado.alertas, [])
        self.assertEqual(len(componentes), 10)
        self.assertAlmostEqual(componentes["Tecido"].quantidade, 8.8946)
        self.assertAlmostEqual(componentes["Tubo"].quantidade, 3.95)
        self.assertEqual(componentes["Tubo"].codigo, tubo)
        self.assertAlmostEqual(componentes["Fita tubo"].quantidade, 3.95)
        self.assertAlmostEqual(componentes["Perfil/Base"].quantidade, 3.95)
        self.assertAlmostEqual(componentes["Fita base"].quantidade, 3.94)
        self.assertAlmostEqual(componentes["Espaguete base"].quantidade, 3.94)
        self.assertAlmostEqual(componentes["Corrente"].quantidade, 6.0)
        self.assertAlmostEqual(componentes["Emenda corrente"].quantidade, 6.0)
        self.assertAlmostEqual(componentes["Tampa da base"].quantidade, 4.0)
        self.assertAlmostEqual(componentes["Comando"].quantidade, 2.0)
        self.assertAlmostEqual(resultado.custo_total, 170.9755)

    def test_receita_atual_com_tubo_32(self):
        self._assert_receita_atual("tubo_32")

    def test_receita_atual_com_tubo_38(self):
        self._assert_receita_atual("tubo_38")

    def test_motor_prioriza_tubo_32_quando_32_e_38_sao_fornecidos(self):
        catalogo = self._catalogo("tubo_32")
        catalogo.update(self._catalogo("tubo_38"))
        resultado = calcular_produto_sob_medida("Rolô", 2, 2, 1, catalogo=catalogo)
        tubo = next(item for item in resultado.componentes if item.categoria == "Tubo")
        self.assertEqual(tubo.codigo, "tubo_32")


if __name__ == "__main__":
    unittest.main()
