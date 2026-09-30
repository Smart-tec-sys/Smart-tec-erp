import unittest

from app.services.romana_calculo_producao import (
    CATEGORIA_ESPAGUETE_BASE_ROMANA_3MM,
    CATEGORIA_ESPAGUETE_ROMANA_2_5MM,
    CATEGORIA_CORDA_ROMANA_1MM,
    CATEGORIA_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
    CATEGORIA_COMANDO_NORMAL_ROMANA,
    CATEGORIA_COMANDO_REDUCAO_ROMANA,
    CATEGORIA_TAMPA_VARETA_ROMANA,
    CATEGORIA_GUIA_CORDA_ROMANA,
    CORDA_ROMANA_1MM_PRODUTO,
    ID_COMERCIAL_ESPAGUETE_BASE_ROMANA_3MM,
    ID_COMERCIAL_ESPAGUETE_ROMANA_2_5MM,
    ID_COMERCIAL_COMANDO_NORMAL_ROMANA,
    ID_COMERCIAL_COMANDO_REDUCAO_ROMANA,
    IDS_COMERCIAIS_GUIA_CORDA_ROMANA,
    IDS_COMERCIAIS_TAMPA_VARETA_ROMANA,
    TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
    TIPO_CORRENTE_SEM_FIM_PRONTA,
    TIPO_COMANDO_NORMAL,
    TIPO_COMANDO_REDUCAO,
    RomanaCalculoEntrada,
    calcular_quantidade_tampas_varetas,
    calcular_distribuicao_fabricacao_romana,
    calcular_producao_romana,
)


class RomanaCalculoProducaoTest(unittest.TestCase):
    def test_recomendacao_de_comando_respeita_limite_de_220_cm(self):
        for largura, recomendado in (
            (120, False),
            (220, False),
            (220.1, True),
            (240, True),
        ):
            with self.subTest(largura=largura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(largura, 200, 1)
                )
                self.assertEqual(
                    resultado.tipos_comando_permitidos,
                    (TIPO_COMANDO_NORMAL, TIPO_COMANDO_REDUCAO),
                )
                self.assertEqual(resultado.comando_reducao_recomendado, recomendado)
                self.assertEqual(resultado.tipo_comando, TIPO_COMANDO_NORMAL)
                self.assertEqual(
                    resultado.categoria_comando_selecionado,
                    CATEGORIA_COMANDO_NORMAL_ROMANA,
                )
                self.assertEqual(
                    resultado.id_comercial_comando_selecionado,
                    ID_COMERCIAL_COMANDO_NORMAL_ROMANA,
                )
                self.assertEqual(resultado.quantidade_comando, 1)

    def test_recomendacao_nao_troca_comando_normal_acima_de_220_cm(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(240, 200, 1, tipo_comando=TIPO_COMANDO_NORMAL)
        )

        self.assertTrue(resultado.comando_reducao_recomendado)
        self.assertEqual(resultado.tipo_comando, TIPO_COMANDO_NORMAL)
        self.assertEqual(resultado.id_comercial_comando_selecionado, 273)
        self.assertEqual(resultado.quantidade_comando, 1)

    def test_comando_reducao_continua_selecionavel_em_qualquer_largura(self):
        for largura in (120, 220, 220.1, 240):
            with self.subTest(largura=largura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(
                        largura,
                        200,
                        1,
                        tipo_comando=TIPO_COMANDO_REDUCAO,
                    )
                )
                self.assertEqual(resultado.tipo_comando, TIPO_COMANDO_REDUCAO)
                self.assertEqual(
                    resultado.categoria_comando_selecionado,
                    CATEGORIA_COMANDO_REDUCAO_ROMANA,
                )
                self.assertEqual(
                    resultado.id_comercial_comando_selecionado,
                    ID_COMERCIAL_COMANDO_REDUCAO_ROMANA,
                )
                self.assertEqual(resultado.quantidade_comando, 1)

    def test_comandos_sao_alternativas_e_nunca_somados(self):
        normal = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(240, 200, 1, tipo_comando=TIPO_COMANDO_NORMAL)
        )
        reducao = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(240, 200, 1, tipo_comando=TIPO_COMANDO_REDUCAO)
        )

        self.assertEqual(normal.quantidade_comando, 1)
        self.assertEqual(reducao.quantidade_comando, 1)
        self.assertNotEqual(
            normal.id_comercial_comando_selecionado,
            reducao.id_comercial_comando_selecionado,
        )
        self.assertEqual(normal.categoria_comando_normal, CATEGORIA_COMANDO_NORMAL_ROMANA)
        self.assertEqual(normal.id_comercial_comando_normal, 273)
        self.assertEqual(normal.categoria_comando_reducao, CATEGORIA_COMANDO_REDUCAO_ROMANA)
        self.assertEqual(normal.id_comercial_comando_reducao, 272)

    def test_romana_de_75_cm_permite_corrente_pronta_de_referencia(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 75, 1)
        )

        self.assertEqual(resultado.tipo_corrente, TIPO_CORRENTE_SEM_FIM_PRONTA)
        self.assertEqual(resultado.corrente_pronta_referencia_m, 1.25)
        self.assertEqual(resultado.corrente_pronta_referencia_status, "REFERENCIA_PRONTA")
        self.assertIsNone(resultado.medida_personalizada_m)
        self.assertEqual(resultado.medida_corrente_selecionada_m, 1.25)
        self.assertEqual(resultado.quantidade_correntes, 1)

    def test_romana_de_75_cm_permite_corrente_personalizada_sem_somar_pronta(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(
                120,
                75,
                1,
                tipo_corrente=TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
                medida_personalizada_m=0.80,
            )
        )

        self.assertEqual(
            resultado.tipo_corrente,
            TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
        )
        self.assertEqual(
            resultado.categoria_corrente_personalizada,
            CATEGORIA_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
        )
        self.assertEqual(resultado.corrente_pronta_referencia_m, 1.25)
        self.assertEqual(resultado.medida_personalizada_m, 0.80)
        self.assertEqual(resultado.medida_corrente_selecionada_m, 0.80)
        self.assertNotEqual(
            resultado.medida_corrente_selecionada_m,
            resultado.corrente_pronta_referencia_m + resultado.medida_personalizada_m,
        )
        self.assertEqual(resultado.quantidade_correntes, 1)

    def test_corrente_personalizada_exige_medida_positiva(self):
        for medida in (None, 0, -0.5):
            with self.subTest(medida=medida):
                with self.assertRaises(ValueError):
                    calcular_distribuicao_fabricacao_romana(
                        RomanaCalculoEntrada(
                            120,
                            75,
                            1,
                            tipo_corrente=TIPO_CORRENTE_JUTA_BOLA10_PERSONALIZADA,
                            medida_personalizada_m=medida,
                        )
                    )

    def test_referencias_prontas_continuam_disponiveis_por_altura(self):
        for altura, medida, status in (
            (75, 1.25, "REFERENCIA_PRONTA"),
            (149.99, 1.25, "REFERENCIA_PRONTA"),
            (150, 1.50, "REFERENCIA_PRONTA"),
            (260, 1.50, "REFERENCIA_PRONTA"),
            (260.01, 1.75, "REFERENCIA_INICIAL_SUPERIOR_PROVISORIA"),
        ):
            with self.subTest(altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(120, altura, 1)
                )
                self.assertEqual(resultado.corrente_pronta_referencia_m, medida)
                self.assertEqual(resultado.corrente_pronta_referencia_status, status)

    def test_corda_da_romana_de_120_por_200(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 200, 1)
        )

        self.assertEqual(resultado.categoria_corda_romana_1mm, CATEGORIA_CORDA_ROMANA_1MM)
        self.assertEqual(
            resultado.produto_comercial_corda_romana_1mm,
            CORDA_ROMANA_1MM_PRODUTO,
        )
        self.assertEqual(resultado.produto_comercial_corda_romana_1mm, "PENDENTE")
        self.assertAlmostEqual(
            resultado.posicao_ultima_vareta_cm,
            resultado.posicoes_varetas[-1].posicao_cm,
        )
        self.assertAlmostEqual(
            resultado.corda_por_linha_cm,
            resultado.posicao_ultima_vareta_cm + 5,
        )
        self.assertEqual(resultado.quantidade_cavaletes, 2)
        self.assertAlmostEqual(
            resultado.corda_total_cm,
            resultado.corda_por_linha_cm * 2,
        )
        self.assertAlmostEqual(resultado.corda_total_m, resultado.corda_total_cm / 100)

    def test_corda_total_acompanha_as_faixas_de_cavaletes(self):
        for largura, cavaletes in ((120, 2), (180, 3), (240, 4)):
            with self.subTest(largura=largura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(largura, 200, 1)
                )
                self.assertEqual(resultado.quantidade_cavaletes, cavaletes)
                self.assertAlmostEqual(
                    resultado.corda_por_linha_cm,
                    resultado.posicoes_varetas[-1].posicao_cm + 5,
                )
                self.assertAlmostEqual(
                    resultado.corda_total_cm,
                    resultado.corda_por_linha_cm * cavaletes,
                )
                self.assertAlmostEqual(
                    resultado.corda_total_m,
                    resultado.corda_total_cm / 100,
                )

    def test_geometria_diferente_altera_corda_por_linha(self):
        resultado_200 = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 200, 1)
        )
        resultado_240 = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 240, 1)
        )

        self.assertNotEqual(
            resultado_200.posicao_ultima_vareta_cm,
            resultado_240.posicao_ultima_vareta_cm,
        )
        self.assertNotEqual(
            resultado_200.corda_por_linha_cm,
            resultado_240.corda_por_linha_cm,
        )
        self.assertAlmostEqual(
            resultado_240.corda_por_linha_cm,
            resultado_240.posicoes_varetas[-1].posicao_cm + 5,
        )

    def test_espaguetes_separados_da_romana_de_120_por_200(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 200, 1)
        )

        self.assertEqual(resultado.quantidade_varetas, 6)
        self.assertEqual(resultado.largura_vareta_cm, 118.5)
        self.assertEqual(
            resultado.categoria_espaguete_romana_2_5mm,
            CATEGORIA_ESPAGUETE_ROMANA_2_5MM,
        )
        self.assertEqual(
            resultado.id_comercial_espaguete_romana_2_5mm,
            ID_COMERCIAL_ESPAGUETE_ROMANA_2_5MM,
        )
        self.assertAlmostEqual(resultado.espaguete_romana_2_5_total_cm, 829.5)
        self.assertAlmostEqual(resultado.espaguete_romana_2_5_total_m, 8.295)

        self.assertEqual(resultado.largura_base_cm, 119.0)
        self.assertEqual(
            resultado.categoria_espaguete_base_romana_3mm,
            CATEGORIA_ESPAGUETE_BASE_ROMANA_3MM,
        )
        self.assertEqual(
            resultado.id_comercial_espaguete_base_romana_3mm,
            ID_COMERCIAL_ESPAGUETE_BASE_ROMANA_3MM,
        )
        self.assertAlmostEqual(resultado.espaguete_base_romana_3mm_total_cm, 119.0)
        self.assertAlmostEqual(resultado.espaguete_base_romana_3mm_total_m, 1.19)

    def test_consumo_dos_espaguetes_em_outras_larguras_e_varetas(self):
        casos = (
            (100, 120, 4),
            (200, 240, 6),
            (260, 260, 8),
        )
        for largura, altura, varetas in casos:
            with self.subTest(largura=largura, altura=altura):
                resultado = calcular_distribuicao_fabricacao_romana(
                    RomanaCalculoEntrada(largura, altura, 1)
                )
                largura_vareta = largura - 1.5
                largura_base = largura - 1.0

                self.assertEqual(resultado.quantidade_varetas, varetas)
                self.assertAlmostEqual(resultado.largura_vareta_cm, largura_vareta)
                self.assertAlmostEqual(
                    resultado.espaguete_romana_2_5_total_cm,
                    (varetas + 1) * largura_vareta,
                )
                self.assertAlmostEqual(
                    resultado.espaguete_romana_2_5_total_m,
                    ((varetas + 1) * largura_vareta) / 100,
                )
                self.assertAlmostEqual(resultado.largura_base_cm, largura_base)
                self.assertAlmostEqual(
                    resultado.espaguete_base_romana_3mm_total_cm,
                    largura_base,
                )
                self.assertAlmostEqual(
                    resultado.espaguete_base_romana_3mm_total_m,
                    largura_base / 100,
                )

    def test_duas_tampas_por_vareta(self):
        for varetas, tampas in ((4, 8), (6, 12), (8, 16), (10, 20)):
            with self.subTest(varetas=varetas):
                self.assertEqual(calcular_quantidade_tampas_varetas(varetas), tampas)

    def test_guias_de_corda_sao_alternativas_para_uma_quantidade_tecnica(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 200, 1)
        )
        self.assertEqual(resultado.varetas_com_passadores, (2, 4, 6))
        self.assertEqual(resultado.quantidade_cavaletes, 2)
        self.assertEqual(resultado.quantidade_guias_corda, 3 * 2)
        self.assertEqual(
            resultado.quantidade_guias_corda,
            resultado.quantidade_total_passadores,
        )
        self.assertEqual(resultado.categoria_guia_corda, CATEGORIA_GUIA_CORDA_ROMANA)
        self.assertEqual(resultado.ids_comerciais_guia_corda, (667, 668))
        self.assertEqual(
            resultado.ids_comerciais_guia_corda,
            IDS_COMERCIAIS_GUIA_CORDA_ROMANA,
        )

    def test_tampas_da_romana_de_120_por_200(self):
        resultado = calcular_distribuicao_fabricacao_romana(
            RomanaCalculoEntrada(120, 200, 1)
        )
        self.assertEqual(resultado.quantidade_gomos, 7)
        self.assertEqual(resultado.quantidade_varetas, 6)
        self.assertEqual(resultado.quantidade_tampas_varetas, 12)
        self.assertEqual(resultado.categoria_tampa_vareta, CATEGORIA_TAMPA_VARETA_ROMANA)
        self.assertEqual(
            resultado.ids_comerciais_tampa_vareta,
            (292, 294, 920, 921, 922, 923, 2598),
        )
        self.assertEqual(
            resultado.ids_comerciais_tampa_vareta,
            IDS_COMERCIAIS_TAMPA_VARETA_ROMANA,
        )

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
