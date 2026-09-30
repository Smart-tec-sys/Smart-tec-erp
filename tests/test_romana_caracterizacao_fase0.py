"""Caracteriza a Romana manual antes do desacoplamento multiempresa.

Registra o comportamento atual, inclusive IDs comerciais ainda expostos pelo
motor. Estes testes não definem a arquitetura futura.
"""

import unittest

from app.services.romana_calculo_producao import (
    RomanaCalculoEntrada,
    calcular_distribuicao_fabricacao_romana,
)


class RomanaCaracterizacaoFase0Test(unittest.TestCase):
    CASOS = {
        180: {
            "primeiro": 27.428571428571427,
            "demais": 25.428571428571427,
            "posicoes": (
                27.428571428571427, 52.857142857142854, 78.28571428571428,
                103.71428571428571, 129.14285714285714, 154.57142857142856,
            ),
            "corda_total_m": 3.1914285714285713,
        },
        200: {
            "primeiro": 30.285714285714285,
            "demais": 28.285714285714285,
            "posicoes": (
                30.285714285714285, 58.57142857142857, 86.85714285714286,
                115.14285714285714, 143.42857142857142, 171.7142857142857,
            ),
            "corda_total_m": 3.534285714285714,
        },
        240: {
            "primeiro": 36.0,
            "demais": 34.0,
            "posicoes": (36.0, 70.0, 104.0, 138.0, 172.0, 206.0),
            "corda_total_m": 4.22,
        },
    }

    def test_geometria_e_componentes_aprovados(self):
        for altura, esperado in self.CASOS.items():
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.quantidade_gomos, 7)
                self.assertEqual(resultado.quantidade_varetas, 6)
                self.assertAlmostEqual(resultado.primeiro_gomo_pronto_cm, esperado["primeiro"])
                self.assertEqual(len(resultado.gomos_intermediarios_prontos_cm), 5)
                for gomo in resultado.gomos_intermediarios_prontos_cm:
                    self.assertAlmostEqual(gomo, esperado["demais"])
                self.assertAlmostEqual(resultado.ultimo_gomo_pronto_cm, esperado["demais"])
                for posicao, valor_esperado in zip(resultado.posicoes_varetas, esperado["posicoes"]):
                    self.assertAlmostEqual(posicao.posicao_cm, valor_esperado)
                self.assertEqual(resultado.varetas_com_passadores, (2, 4, 6))
                self.assertEqual(resultado.quantidade_total_passadores, 6)
                self.assertEqual(resultado.quantidade_tampas_varetas, 12)
                self.assertEqual(resultado.quantidade_cavaletes, 2)
                self.assertAlmostEqual(resultado.corda_total_m, esperado["corda_total_m"])
                self.assertAlmostEqual(resultado.espaguete_romana_2_5_total_m, 8.295)
                self.assertAlmostEqual(resultado.espaguete_base_romana_3mm_total_m, 1.19)

    def test_corrente_comando_e_ids_comerciais_atualmente_expostos(self):
        for altura in self.CASOS:
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.tipo_corrente, "SEM_FIM_PRONTA")
                self.assertEqual(resultado.medida_corrente_selecionada_m, 1.5)
                self.assertEqual(resultado.quantidade_correntes, 1)
                self.assertEqual(resultado.tipo_comando, "NORMAL")
                self.assertFalse(resultado.comando_reducao_recomendado)
                self.assertEqual(resultado.quantidade_comando, 1)
                self.assertEqual(resultado.id_comercial_comando_selecionado, 273)
                self.assertEqual(resultado.id_comercial_espaguete_romana_2_5mm, 660)
                self.assertEqual(resultado.id_comercial_espaguete_base_romana_3mm, 661)
                self.assertEqual(resultado.ids_comerciais_guia_corda, (667, 668))
                self.assertEqual(
                    resultado.ids_comerciais_tampa_vareta,
                    (292, 294, 920, 921, 922, 923, 2598),
                )


if __name__ == "__main__":
    unittest.main()
