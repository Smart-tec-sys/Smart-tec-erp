import unittest

from app.services.romana_calculo_producao import (
    RomanaCalculoEntrada,
    calcular_distribuicao_fabricacao_romana,
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

    def test_distribuicao_v2_de_200_cm(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 200, 1)
        )
        self.assertEqual(resultado.quantidade_gomos, 8)
        self.assertEqual(resultado.quantidade_varetas, 7)
        self.assertEqual(resultado.tamanho_gomo_padrao_cm, 25.0)
        self.assertAlmostEqual(resultado.primeiro_gomo_pronto_cm, 27.0)
        self.assertEqual(len(resultado.gomos_intermediarios_prontos_cm), 6)
        for gomo in resultado.gomos_intermediarios_prontos_cm:
            self.assertAlmostEqual(gomo, 25.0)
        self.assertAlmostEqual(resultado.ultimo_gomo_pronto_cm, 23.0)
        self.assertAlmostEqual(resultado.soma_altura_pronta_cm, 200.0)
        self.assertAlmostEqual(resultado.diferenca_altura_pronta_cm, 0.0)
        self.assertEqual(resultado.dobra_cabeceira_cm, 2.5)
        self.assertAlmostEqual(resultado.primeiro_gomo_corte_cm, 27.5)
        self.assertEqual(len(resultado.intermediarios_corte_cm), 6)
        for gomo in resultado.intermediarios_corte_cm:
            self.assertAlmostEqual(gomo, 25.5)
        self.assertAlmostEqual(resultado.ultimo_gomo_corte_cm, 23.0)
        self.assertEqual(resultado.reserva_fita_plastica_cm, 1.5)
        self.assertEqual(resultado.quantidade_dobras_varetas, 7)
        self.assertAlmostEqual(resultado.sobra_total_fabricacao_cm, 7.5)
        self.assertAlmostEqual(resultado.comprimento_total_tecido_cm, 207.5)
        self.assertEqual(resultado.compensacao_aplicada_em, "ULTIMO")
        self.assertEqual(resultado.status_fabricacao, "DISTRIBUICAO_V2_CALCULADA")

    def test_distribuicao_v2_fecha_todas_as_alturas_de_referencia(self):
        for altura in (120, 150, 180, 200, 220, 260):
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.quantidade_varetas, resultado.quantidade_gomos - 1)
                self.assertEqual(resultado.quantidade_gomos % 2, 0)
                self.assertEqual(resultado.quantidade_varetas % 2, 1)
                self.assertGreater(resultado.primeiro_gomo_pronto_cm, 0)
                self.assertTrue(all(gomo > 0 for gomo in resultado.gomos_intermediarios_prontos_cm))
                self.assertGreater(resultado.ultimo_gomo_pronto_cm, 0)
                self.assertAlmostEqual(resultado.soma_altura_pronta_cm, altura)
                self.assertAlmostEqual(resultado.diferenca_altura_pronta_cm, 0)

    def test_compensacao_dinamica_confirmada(self):
        esperados = (
            (179, 6, 29, 34, 29, "PRIMEIRO"),
            (180, 6, 29, 35, 29, "PRIMEIRO"),
            (199, 8, 25, 27, 22, "ULTIMO"),
            (200, 8, 25, 27, 23, "ULTIMO"),
        )
        for altura, gomos, padrao, primeiro, ultimo, compensacao in esperados:
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.quantidade_gomos, gomos)
                self.assertEqual(resultado.quantidade_varetas, gomos - 1)
                self.assertEqual(resultado.tamanho_gomo_padrao_cm, padrao)
                self.assertEqual(resultado.primeiro_gomo_pronto_cm, primeiro)
                self.assertTrue(
                    all(gomo == padrao for gomo in resultado.gomos_intermediarios_prontos_cm)
                )
                self.assertEqual(resultado.ultimo_gomo_pronto_cm, ultimo)
                self.assertEqual(resultado.compensacao_aplicada_em, compensacao)
                self.assertEqual(resultado.status_fabricacao, "DISTRIBUICAO_V2_CALCULADA")
                self.assertAlmostEqual(resultado.soma_altura_pronta_cm, altura)

    def test_posicoes_das_varetas_nos_casos_confirmados(self):
        esperados = {
            179: (34, 63, 92, 121, 150),
            180: (35, 64, 93, 122, 151),
            199: (27, 52, 77, 102, 127, 152, 177),
            200: (27, 52, 77, 102, 127, 152, 177),
        }
        for altura, posicoes_esperadas in esperados.items():
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                posicoes = tuple(item.posicao_cm for item in resultado.posicoes_varetas)
                numeros = tuple(item.vareta for item in resultado.posicoes_varetas)
                self.assertEqual(posicoes, posicoes_esperadas)
                self.assertEqual(numeros, tuple(range(1, resultado.quantidade_varetas + 1)))
                self.assertEqual(len(posicoes), resultado.quantidade_varetas)
                self.assertTrue(all(a < b for a, b in zip(posicoes, posicoes[1:])))
                self.assertLess(posicoes[-1], resultado.altura_pronta_cm)
                self.assertAlmostEqual(
                    resultado.altura_pronta_cm - posicoes[-1],
                    resultado.ultimo_gomo_pronto_cm,
                )

    def test_posicoes_das_varetas_em_casos_gerais(self):
        for altura in (100, 120, 140, 150, 160, 220, 240, 260, 280, 300):
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                posicoes = [item.posicao_cm for item in resultado.posicoes_varetas]
                self.assertEqual(len(posicoes), resultado.quantidade_varetas)
                self.assertTrue(all(a < b for a, b in zip(posicoes, posicoes[1:])))
                self.assertLess(posicoes[-1], altura)
                self.assertAlmostEqual(altura - posicoes[-1], resultado.ultimo_gomo_pronto_cm)

    def test_formula_corte_tecido_e_dobras_por_vareta(self):
        for altura in (100, 120, 140, 150, 160, 179, 180, 199, 200,
                       220, 240, 260, 280, 300):
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                sobra_esperada = 2.5 + (resultado.quantidade_varetas * 0.5) + 1.5
                self.assertEqual(
                    resultado.quantidade_dobras_varetas,
                    resultado.quantidade_varetas,
                )
                self.assertEqual(
                    1 + len(resultado.intermediarios_corte_cm),
                    resultado.quantidade_varetas,
                )
                self.assertAlmostEqual(resultado.sobra_total_fabricacao_cm, sobra_esperada)
                self.assertAlmostEqual(
                    resultado.comprimento_total_tecido_cm,
                    altura + sobra_esperada,
                )

    def test_corte_de_180_cm(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 180, 1)
        )
        self.assertEqual(resultado.quantidade_gomos, 6)
        self.assertEqual(resultado.quantidade_varetas, 5)
        self.assertAlmostEqual(resultado.sobra_total_fabricacao_cm, 6.5)
        self.assertAlmostEqual(resultado.comprimento_total_tecido_cm, 186.5)

    def test_bloqueios_tambem_valem_para_fabricacao_v2(self):
        with self.assertRaises(ValueError):
            calcular_distribuicao_fabricacao_romana(
                RomanaCalculoEntrada(100, 120, 1, tipo="ROMANA_TETO")
            )
        with self.assertRaises(ValueError):
            calcular_distribuicao_fabricacao_romana(
                RomanaCalculoEntrada(100, 120, 1, acionamento="MOTORIZADO")
            )

    def test_distribuicao_inviavel_solicita_revisao(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(100, 5, 1)
        )
        self.assertLessEqual(resultado.ultimo_gomo_pronto_cm, 0)
        self.assertEqual(resultado.status_fabricacao, "REVISAR_DISTRIBUICAO")
        self.assertTrue(resultado.alertas)


if __name__ == "__main__":
    unittest.main()
