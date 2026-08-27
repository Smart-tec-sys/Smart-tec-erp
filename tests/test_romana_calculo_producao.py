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
        self.assertEqual(resultado.quantidade_gomos, 7)
        self.assertEqual(resultado.quantidade_varetas, 6)
        self.assertAlmostEqual(resultado.tamanho_gomo_padrao_cm, 198 / 7)
        self.assertAlmostEqual(resultado.primeiro_gomo_pronto_cm, (198 / 7) + 2)
        self.assertEqual(resultado.regra_primeiro_gomo_status, "FORMULA_GERAL_DISTRIBUICAO_IGUAL")
        self.assertEqual(len(resultado.gomos_intermediarios_prontos_cm), 5)
        for gomo in resultado.gomos_intermediarios_prontos_cm:
            self.assertAlmostEqual(gomo, 198 / 7)
        self.assertAlmostEqual(resultado.ultimo_gomo_pronto_cm, 198 / 7)
        self.assertAlmostEqual(resultado.soma_altura_pronta_cm, 200.0)
        self.assertAlmostEqual(resultado.diferenca_altura_pronta_cm, 0.0)
        self.assertEqual(resultado.dobra_cabeceira_cm, 2.5)
        self.assertAlmostEqual(resultado.primeiro_gomo_corte_cm, (198 / 7) + 2.5)
        self.assertEqual(len(resultado.intermediarios_corte_cm), 5)
        for gomo in resultado.intermediarios_corte_cm:
            self.assertAlmostEqual(gomo, (198 / 7) + 0.5)
        self.assertAlmostEqual(resultado.ultimo_gomo_corte_cm, 198 / 7)
        self.assertEqual(resultado.reserva_fita_plastica_cm, 1.5)
        self.assertEqual(resultado.quantidade_dobras_varetas, 6)
        self.assertAlmostEqual(resultado.sobra_total_fabricacao_cm, 7.0)
        self.assertAlmostEqual(resultado.comprimento_total_tecido_cm, 207.0)
        self.assertEqual(resultado.compensacao_aplicada_em, "NENHUMA_DIVISAO_IGUAL")
        self.assertEqual(resultado.status_fabricacao, "DISTRIBUICAO_V2_CALCULADA")

    def test_distribuicao_v2_fecha_todas_as_alturas_de_referencia(self):
        for altura in (120, 150, 180, 200, 220, 260):
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.quantidade_varetas, resultado.quantidade_gomos - 1)
                self.assertEqual(resultado.quantidade_gomos % 2, 1)
                self.assertEqual(resultado.quantidade_varetas % 2, 0)
                self.assertGreater(resultado.primeiro_gomo_pronto_cm, 0)
                self.assertTrue(all(gomo > 0 for gomo in resultado.gomos_intermediarios_prontos_cm))
                self.assertGreater(resultado.ultimo_gomo_pronto_cm, 0)
                self.assertAlmostEqual(resultado.soma_altura_pronta_cm, altura)
                self.assertAlmostEqual(resultado.diferenca_altura_pronta_cm, 0)

    def test_distribuicoes_prioritarias_com_restante_igual(self):
        esperados = (
            (179, 7, (177 / 7) + 2, 177 / 7),
            (180, 7, (178 / 7) + 2, 178 / 7),
            (199, 7, (197 / 7) + 2, 197 / 7),
            (200, 7, (198 / 7) + 2, 198 / 7),
        )
        for altura, gomos, primeiro, demais in esperados:
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.quantidade_gomos, gomos)
                self.assertEqual(resultado.quantidade_varetas, gomos - 1)
                self.assertAlmostEqual(resultado.primeiro_gomo_pronto_cm, primeiro)
                self.assertTrue(
                    all(abs(gomo - demais) < 1e-9 for gomo in resultado.gomos_intermediarios_prontos_cm)
                )
                self.assertAlmostEqual(resultado.ultimo_gomo_pronto_cm, demais)
                self.assertEqual(
                    resultado.regra_primeiro_gomo_status,
                    "FORMULA_GERAL_DISTRIBUICAO_IGUAL",
                )
                self.assertAlmostEqual(resultado.soma_altura_pronta_cm, altura)

    def test_posicoes_das_varetas_nos_casos_confirmados(self):
        esperados = {
            179: tuple((177 / 7) + 2 + i * (177 / 7) for i in range(6)),
            180: tuple((178 / 7) + 2 + i * (178 / 7) for i in range(6)),
            199: tuple((197 / 7) + 2 + i * (197 / 7) for i in range(6)),
            200: tuple((198 / 7) + 2 + i * (198 / 7) for i in range(6)),
        }
        for altura, posicoes_esperadas in esperados.items():
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                posicoes = tuple(item.posicao_cm for item in resultado.posicoes_varetas)
                numeros = tuple(item.vareta for item in resultado.posicoes_varetas)
                self.assertEqual(len(posicoes), len(posicoes_esperadas))
                for posicao, esperada in zip(posicoes, posicoes_esperadas):
                    self.assertAlmostEqual(posicao, esperada)
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
        self.assertEqual(resultado.quantidade_gomos, 7)
        self.assertEqual(resultado.quantidade_varetas, 6)
        self.assertAlmostEqual(resultado.sobra_total_fabricacao_cm, 7.0)
        self.assertAlmostEqual(resultado.comprimento_total_tecido_cm, 187.0)
        self.assertAlmostEqual(resultado.primeiro_gomo_pronto_cm, (178 / 7) + 2)
        self.assertTrue(
            all(abs(gomo - (178 / 7)) < 1e-9 for gomo in resultado.gomos_intermediarios_prontos_cm)
        )
        self.assertAlmostEqual(resultado.ultimo_gomo_pronto_cm, 178 / 7)

    def test_formula_confirmada_de_240_cm(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(200, 240, 1)
        )
        self.assertEqual(resultado.quantidade_gomos, 7)
        self.assertEqual(resultado.ajuste_primeiro_gomo_cm, 2)
        self.assertEqual(resultado.tamanho_gomo_padrao_cm, 34)
        self.assertEqual(resultado.primeiro_gomo_pronto_cm, 36)
        self.assertEqual(resultado.ultimo_gomo_pronto_cm, 34)
        self.assertAlmostEqual(resultado.soma_altura_pronta_cm, 240)

    def test_selecao_sem_limite_inferior_rigido(self):
        resultado_100 = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(200, 100, 1)
        )
        resultado_120 = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(200, 120, 1)
        )
        self.assertEqual(resultado_100.quantidade_gomos, 5)
        self.assertAlmostEqual(resultado_100.tamanho_gomo_padrao_cm, 19.6)
        self.assertAlmostEqual(resultado_100.primeiro_gomo_pronto_cm, 21.6)
        self.assertEqual(resultado_120.quantidade_gomos, 5)
        self.assertAlmostEqual(resultado_120.tamanho_gomo_padrao_cm, 23.6)
        self.assertAlmostEqual(resultado_120.primeiro_gomo_pronto_cm, 25.6)
        self.assertEqual(resultado_120.status_fabricacao, "DISTRIBUICAO_V2_CALCULADA")

    def test_progressao_e_transicoes_por_limite_superior(self):
        esperados = {
            80: 5, 90: 5, 100: 5, 110: 5, 120: 5, 130: 5,
            140: 5, 150: 5, 160: 5, 170: 5,
            180: 7, 190: 7, 200: 7, 210: 7, 220: 7,
            230: 7, 240: 7, 250: 9, 260: 9, 280: 9, 300: 9,
        }
        anterior_por_n = {}
        for altura, quantidade_gomos in esperados.items():
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(200, altura, 1)
                )
                self.assertEqual(resultado.quantidade_gomos, quantidade_gomos)
                anterior = anterior_por_n.get(quantidade_gomos)
                if anterior is not None:
                    self.assertGreater(resultado.tamanho_gomo_padrao_cm, anterior)
                anterior_por_n[quantidade_gomos] = resultado.tamanho_gomo_padrao_cm

        for antes, depois, n_antes, n_depois in (
            (177, 178, 5, 7),
            (247, 248, 7, 9),
            (317, 318, 9, 11),
        ):
            resultado_antes = calcular_distribuicao_fabricacao_romana(
                RomanaCalculoEntrada(200, antes, 1)
            )
            resultado_depois = calcular_distribuicao_fabricacao_romana(
                RomanaCalculoEntrada(200, depois, 1)
            )
            self.assertEqual(resultado_antes.quantidade_gomos, n_antes)
            self.assertEqual(resultado_depois.quantidade_gomos, n_depois)
            self.assertAlmostEqual(resultado_antes.tamanho_gomo_padrao_cm, 35)
            self.assertLess(resultado_depois.tamanho_gomo_padrao_cm, 35)

    def test_passadores_somente_nas_varetas_pares(self):
        for altura in (100, 120, 140, 150, 160, 179, 180, 199, 200,
                       220, 240, 260, 280, 300):
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(200, altura, 1)
                )
                esperadas = tuple(range(2, resultado.quantidade_varetas + 1, 2))
                self.assertEqual(resultado.quantidade_gomos % 2, 1)
                self.assertEqual(resultado.quantidade_varetas % 2, 0)
                self.assertEqual(resultado.varetas_com_passadores, esperadas)
                self.assertEqual(resultado.varetas_com_passadores[-1], resultado.quantidade_varetas)
                self.assertTrue(all(vareta % 2 == 0 for vareta in resultado.varetas_com_passadores))
                self.assertEqual(resultado.quantidade_cavaletes, 3)
                self.assertEqual(resultado.passadores_por_vareta, 3)
                self.assertEqual(
                    resultado.quantidade_total_passadores,
                    len(esperadas) * 3,
                )

    def test_faixas_de_cavaletes_preservadas(self):
        for largura, cavaletes in ((140, 2), (141, 3), (220, 3), (221, 4),
                                   (260, 4), (261, 5), (300, 5)):
            with self.subTest(largura=largura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(largura, 180, 1)
                )
                self.assertEqual(resultado.quantidade_cavaletes, cavaletes)

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
        self.assertGreater(resultado.ultimo_gomo_pronto_cm, 0)
        self.assertAlmostEqual(resultado.soma_altura_pronta_cm, 5)


if __name__ == "__main__":
    unittest.main()
