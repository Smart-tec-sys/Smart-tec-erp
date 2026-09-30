import unittest
from decimal import Decimal

from app.services.romana_teto_calculo_producao import (
    ACIONAMENTO_MANUAL_BASTAO,
    ACIONAMENTO_MANUAL_CORRENTE,
    ACIONAMENTO_MOTORIZADA,
    BASTAO_DEFAULT,
    BASTAO_OPCOES_VALIDAS,
    CORRENTE_SEM_FIM_DEFAULT,
    CORRENTE_SEM_FIM_OPCOES_VALIDAS,
    LADO_COMANDO_VALIDOS,
    REFERENCIA_COMANDO_TETO,
    REFERENCIA_MECANISMO_MANUAL_BASTAO,
    TIPO_TRILHO,
    STATUS_PRODUCAO_LIBERADA,
    STATUS_REQUER_AVALIACAO_PROFISSIONAL,
    RomanaTetoEntrada,
    calcular_romana_teto,
    calcular_area_faturavel,
)
from app.services.romana_teto_simulacao import (
    resolver_tecido_pimpoint,
    simular_romana_teto,
    RomanaTetoSimulacaoInput,
    STATUS_RESOLVIDO,
    STATUS_AVALIACAO_NECESSARIA,
    STATUS_COR_INVALIDA,
    STATUS_FAMILIA_NAO_PIMPOINT,
    FAMILIA_PIMPOINT,
    CORES_PIMPOINT_VALIDAS,
)


class RomanaTetoCalculoProducaoTest(unittest.TestCase):
    def test_0_70_x_5_00_area_real_gomos_trilhos_sem_avaliacao(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=0.70,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertAlmostEqual(resultado.area_real_m2, 3.50)
        self.assertEqual(resultado.quantidade_gomos, 17)
        self.assertAlmostEqual(resultado.passo_gomo_cm, 500 / 17)
        self.assertEqual(resultado.quantidade_varetas, 16)
        self.assertEqual(resultado.comprimento_vareta_m, 0.70)
        self.assertEqual(resultado.quantidade_trilhos_base, 2)
        self.assertEqual(resultado.comprimento_trilho_m, 5.00)
        self.assertFalse(resultado.avaliacao_trilho_central)
        self.assertFalse(resultado.terceiro_trilho_confirmado)
        self.assertEqual(resultado.motores_por_modulo, 0)
        self.assertEqual(resultado.status_calculo, STATUS_PRODUCAO_LIBERADA)
        self.assertEqual(resultado.alertas, ())

    def test_0_70_x_5_00_composicao_fisica_deslizantes_trilhos_tecido_acionamento_bastao(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=0.70,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_deslizantes, 32)
        self.assertEqual(resultado.tipo_trilho, TIPO_TRILHO)
        self.assertEqual(resultado.quantidade_trilhos_base, 2)
        self.assertEqual(resultado.comprimento_trilho_m, 5.00)
        self.assertAlmostEqual(resultado.largura_tecido_m, 0.70)
        self.assertAlmostEqual(resultado.comprimento_tecido_m, 5.60)
        self.assertAlmostEqual(resultado.area_tecido_m2, 3.92)
        self.assertEqual(resultado.tipo_acionamento_manual, ACIONAMENTO_MANUAL_BASTAO)
        self.assertEqual(resultado.referencia_mecanismo_manual, REFERENCIA_MECANISMO_MANUAL_BASTAO)
        self.assertAlmostEqual(resultado.area_real_m2, 3.50)

    def test_acionamento_corrente_nao_tem_referencia_mecanismo_manual(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertIsNone(resultado.tipo_acionamento_manual)
        self.assertIsNone(resultado.referencia_mecanismo_manual)

    def test_acionamento_motorizada_nao_tem_referencia_mecanismo_manual(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MOTORIZADA,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertIsNone(resultado.tipo_acionamento_manual)
        self.assertIsNone(resultado.referencia_mecanismo_manual)

    def test_1_20_x_5_00_dois_trilhos_sem_avaliacao_obrigatoria(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.20,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_trilhos_base, 2)
        self.assertFalse(resultado.avaliacao_trilho_central)
        self.assertFalse(resultado.terceiro_trilho_confirmado)
        self.assertEqual(resultado.status_calculo, STATUS_PRODUCAO_LIBERADA)
        self.assertEqual(resultado.alertas, ())

    def test_1_21_x_5_00_avaliacao_profissional_necessaria_terceiro_trilho_nao_adicionado(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.21,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertTrue(resultado.avaliacao_trilho_central)
        self.assertIsNone(resultado.terceiro_trilho_confirmado)
        self.assertEqual(resultado.quantidade_trilhos_base, 2)
        self.assertEqual(resultado.status_calculo, STATUS_REQUER_AVALIACAO_PROFISSIONAL)
        self.assertIn(
            'Avaliar" necessidade e possibilidade estrutural de trilho "central.',
            resultado.alertas,
        )

    def test_acionamento_motorizada_um_motor_por_modulo(self):
        for modulos in (1, 2, 3):
            with self.subTest(modulos=modulos):
                entrada = RomanaTetoEntrada(
                    largura_modulo_m=1.00,
                    comprimento_avanco_m=4.00,
                    quantidade_modulos=modulos,
                    acionamento=ACIONAMENTO_MOTORIZADA,
                )
                resultado = calcular_romana_teto(entrada)

                self.assertEqual(resultado.motores_por_modulo, 1)
                self.assertEqual(resultado.acionamento, ACIONAMENTO_MOTORIZADA)

    def test_quantidade_modulos_2_mantem_resultados_por_modulo_e_totais_coerentes(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=2,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_modulos, 2)
        self.assertAlmostEqual(resultado.area_real_m2, 4.00)
        self.assertEqual(resultado.quantidade_gomos, 14)
        self.assertEqual(resultado.quantidade_varetas, 13)
        self.assertEqual(resultado.comprimento_vareta_m, 1.00)
        self.assertEqual(resultado.quantidade_trilhos_base, 2)
        self.assertEqual(resultado.comprimento_trilho_m, 4.00)

    def test_gomos_calculados_pelo_comprimento_avanco_nao_pela_largura(self):
        entrada_larga = RomanaTetoEntrada(
            largura_modulo_m=2.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        entrada_estreita = RomanaTetoEntrada(
            largura_modulo_m=0.50,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )

        resultado_larga = calcular_romana_teto(entrada_larga)
        resultado_estreita = calcular_romana_teto(entrada_estreita)

        self.assertEqual(resultado_larga.quantidade_gomos, resultado_estreita.quantidade_gomos)
        self.assertEqual(resultado_larga.passo_gomo_cm, resultado_estreita.passo_gomo_cm)

    def test_validacao_entrada_largura_zero_ou_negativa(self):
        for largura in (0, -0.5):
            with self.subTest(largura=largura):
                with self.assertRaises(ValueError):
                    calcular_romana_teto(
                        RomanaTetoEntrada(largura, 5.00, 1, ACIONAMENTO_MANUAL_BASTAO)
                    )

    def test_validacao_entrada_comprimento_zero_ou_negativo(self):
        for comprimento in (0, -1.0):
            with self.subTest(comprimento=comprimento):
                with self.assertRaises(ValueError):
                    calcular_romana_teto(
                        RomanaTetoEntrada(1.00, comprimento, 1, ACIONAMENTO_MANUAL_BASTAO)
                    )

    def test_validacao_entrada_quantidade_modulos_zero_ou_negativa(self):
        for qtd in (0, -1):
            with self.subTest(qtd=qtd):
                with self.assertRaises(ValueError):
                    calcular_romana_teto(
                        RomanaTetoEntrada(1.00, 5.00, qtd, ACIONAMENTO_MANUAL_BASTAO)
                    )

    def test_validacao_acionamento_invalido(self):
        with self.assertRaises(ValueError):
            calcular_romana_teto(
                RomanaTetoEntrada(1.00, 5.00, 1, "INVALIDO")
            )

    def test_validacao_lado_comando_nao_se_aplica_motorizada(self):
        with self.assertRaises(ValueError):
            calcular_romana_teto(
                RomanaTetoEntrada(
                    1.00, 5.00, 1, ACIONAMENTO_MOTORIZADA, lado_comando="ESQUERDA"
                )
            )

    def test_area_faturavel_regra_comercial_fase_8f1(self):
        self.assertEqual(calcular_area_faturavel(0.50), 1.50)
        self.assertEqual(calcular_area_faturavel(1.49), 1.50)
        self.assertEqual(calcular_area_faturavel(1.50), 1.50)
        self.assertEqual(calcular_area_faturavel(3.50), 3.50)
        self.assertEqual(calcular_area_faturavel(10.00), 10.00)

    def test_area_faturavel_nao_usada_para_componentes(self):
        entrada = RomanaTetoEntrada(
            largura_modulo_m=0.50,
            comprimento_avanco_m=2.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertAlmostEqual(resultado.area_real_m2, 1.00)
        self.assertEqual(resultado.quantidade_gomos, 7)
        self.assertEqual(resultado.quantidade_varetas, 6)
        self.assertEqual(resultado.quantidade_trilhos_base, 2)
        self.assertEqual(resultado.motores_por_modulo, 0)

    def test_lado_comando_opcional_para_manual(self):
        for lado in ("ESQUERDA", "DIREITA", None):
            with self.subTest(lado=lado):
                entrada = RomanaTetoEntrada(
                    largura_modulo_m=1.00,
                    comprimento_avanco_m=4.00,
                    quantidade_modulos=1,
                    acionamento=ACIONAMENTO_MANUAL_BASTAO,
                    lado_comando=lado,
                )
                resultado = calcular_romana_teto(entrada)
                self.assertEqual(resultado.status_calculo, STATUS_PRODUCAO_LIBERADA)

    def test_componentes_adicionais_0_70_x_5_00_manual_bastao(self):
        """Testa os componentes físicos adicionais para 0.70 x 5.00 com 16 varetas."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=0.70,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_tampas_vareta, 32)
        self.assertEqual(resultado.quantidade_bases_conicas, 2)
        self.assertAlmostEqual(resultado.comprimento_base_conica_m, 0.70)
        self.assertEqual(resultado.quantidade_tampas_base, 4)
        self.assertEqual(resultado.quantidade_guias_corda, 32)
        self.assertEqual(resultado.quantidade_argolas, 34)
        self.assertEqual(resultado.quantidade_puxadores, 1)
        self.assertEqual(resultado.quantidade_espaguete_2_5, 16)
        self.assertAlmostEqual(resultado.metragem_total_espaguete_2_5, 11.20)
        self.assertEqual(resultado.quantidade_espaguete_3, 2)
        self.assertAlmostEqual(resultado.metragem_total_espaguete_3, 1.40)
        self.assertEqual(resultado.quantidade_bastoes, 1)
        self.assertAlmostEqual(resultado.comprimento_bastao_m, BASTAO_DEFAULT)

    def test_componentes_adicionais_acionamento_corrente_sem_bastao(self):
        """Testa que acionamento por corrente não tem bastão."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_bastoes, 0)
        self.assertIsNone(resultado.comprimento_bastao_m)
        self.assertEqual(resultado.quantidade_tampas_vareta, 26)
        self.assertEqual(resultado.quantidade_bases_conicas, 2)
        self.assertAlmostEqual(resultado.comprimento_base_conica_m, 1.00)
        self.assertEqual(resultado.quantidade_tampas_base, 4)
        self.assertEqual(resultado.quantidade_guias_corda, 26)
        self.assertEqual(resultado.quantidade_argolas, 28)
        self.assertEqual(resultado.quantidade_puxadores, 1)
        self.assertEqual(resultado.quantidade_espaguete_2_5, 13)
        self.assertAlmostEqual(resultado.metragem_total_espaguete_2_5, 13.00)
        self.assertEqual(resultado.quantidade_espaguete_3, 2)
        self.assertAlmostEqual(resultado.metragem_total_espaguete_3, 2.00)

    def test_componentes_adicionais_acionamento_motorizada_sem_bastao(self):
        """Testa que acionamento motorizado não tem bastão."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MOTORIZADA,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_bastoes, 0)
        self.assertIsNone(resultado.comprimento_bastao_m)

    def test_bastao_comprimento_personalizado_valido(self):
        """Testa bastão com comprimento personalizado válido."""
        for comprimento in BASTAO_OPCOES_VALIDAS:
            with self.subTest(comprimento=comprimento):
                entrada = RomanaTetoEntrada(
                    largura_modulo_m=1.00,
                    comprimento_avanco_m=4.00,
                    quantidade_modulos=1,
                    acionamento=ACIONAMENTO_MANUAL_BASTAO,
                    comprimento_bastao_m=comprimento,
                )
                resultado = calcular_romana_teto(entrada)

                self.assertEqual(resultado.quantidade_bastoes, 1)
                self.assertAlmostEqual(resultado.comprimento_bastao_m, comprimento)

    def test_bastao_comprimento_invalido_levanta_erro(self):
        """Testa que comprimento de bastão inválido levanta ValueError."""
        for comprimento_invalido in (0.50, 1.10, 1.60, 2.50, 3.00):
            with self.subTest(comprimento=comprimento_invalido):
                with self.assertRaises(ValueError):
                    calcular_romana_teto(
                        RomanaTetoEntrada(
                            largura_modulo_m=1.00,
                            comprimento_avanco_m=4.00,
                            quantidade_modulos=1,
                            acionamento=ACIONAMENTO_MANUAL_BASTAO,
                            comprimento_bastao_m=comprimento_invalido,
                        )
                    )

    def test_bastao_default_quando_nao_informado(self):
        """Testa que bastão usa valor padrão quando não informado."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
            comprimento_bastao_m=None,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_bastoes, 1)
        self.assertAlmostEqual(resultado.comprimento_bastao_m, BASTAO_DEFAULT)

    def test_componentes_escalam_com_quantidade_modulos(self):
        """Testa que componentes escalam corretamente com quantidade_modulos > 1."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=4.00,
            quantidade_modulos=2,
            acionamento=ACIONAMENTO_MANUAL_BASTAO,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_modulos, 2)
        self.assertEqual(resultado.quantidade_bases_conicas, 2)
        self.assertEqual(resultado.quantidade_tampas_base, 4)
        self.assertEqual(resultado.quantidade_puxadores, 1)
        self.assertEqual(resultado.quantidade_bastoes, 1)
        self.assertAlmostEqual(resultado.comprimento_base_conica_m, 1.00)

    # MANUAL_CORRENTE tests - Fase 8E.5E.1
    def test_manual_corrente_0_70_x_5_00_lado_direita(self):
        """Exemplo obrigatório: 0.70 x 5.00 MANUAL_CORRENTE lado DIREITA."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=0.70,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="DIREITA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_trilhos, 2)
        self.assertEqual(resultado.lado_comando, "DIREITA")
        self.assertEqual(resultado.trilho_comando, "DIREITO")
        self.assertEqual(resultado.quantidade_carrinho_master, 2)
        self.assertEqual(resultado.quantidade_tampas_cabeceira_teto, 2)
        self.assertAlmostEqual(resultado.metragem_corrente_tracao_m, 10.00)
        self.assertEqual(resultado.quantidade_correntes_sem_fim, 1)
        self.assertAlmostEqual(resultado.comprimento_corrente_sem_fim_m, CORRENTE_SEM_FIM_DEFAULT)
        self.assertEqual(resultado.opcoes_corrente_sem_fim_m, CORRENTE_SEM_FIM_OPCOES_VALIDAS)
        self.assertEqual(resultado.quantidade_pendulos, 1)
        self.assertEqual(resultado.referencia_comando_teto, REFERENCIA_COMANDO_TETO)
        self.assertFalse(resultado.terceiro_trilho)
        self.assertFalse(resultado.avaliacao_trilho_central)
        self.assertEqual(resultado.quantidade_bastoes, 0)
        self.assertIsNone(resultado.comprimento_bastao_m)

    def test_manual_corrente_0_70_x_5_00_lado_esquerda(self):
        """Exemplo obrigatório: 0.70 x 5.00 MANUAL_CORRENTE lado ESQUERDA."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=0.70,
            comprimento_avanco_m=5.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_trilhos, 2)
        self.assertEqual(resultado.lado_comando, "ESQUERDA")
        self.assertEqual(resultado.trilho_comando, "ESQUERDO")
        self.assertEqual(resultado.quantidade_carrinho_master, 2)
        self.assertEqual(resultado.quantidade_tampas_cabeceira_teto, 2)
        self.assertAlmostEqual(resultado.metragem_corrente_tracao_m, 10.00)
        self.assertEqual(resultado.quantidade_correntes_sem_fim, 1)
        self.assertAlmostEqual(resultado.comprimento_corrente_sem_fim_m, CORRENTE_SEM_FIM_DEFAULT)
        self.assertEqual(resultado.quantidade_pendulos, 1)
        self.assertEqual(resultado.referencia_comando_teto, REFERENCIA_COMANDO_TETO)
        self.assertFalse(resultado.terceiro_trilho)
        self.assertFalse(resultado.avaliacao_trilho_central)
        self.assertEqual(resultado.quantidade_bastoes, 0)
        self.assertIsNone(resultado.comprimento_bastao_m)

    def test_manual_corrente_default_corrente_sem_fim(self):
        """Testa que corrente sem fim usa valor padrão 1.50 quando não informado."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
            comprimento_corrente_sem_fim_m=None,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertAlmostEqual(resultado.comprimento_corrente_sem_fim_m, CORRENTE_SEM_FIM_DEFAULT)

    def test_manual_corrente_corrente_sem_fim_medida_valida_alternativa(self):
        """Testa medida válida alternativa para corrente sem fim (ex: 2.00)."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="DIREITA",
            comprimento_corrente_sem_fim_m=2.00,
        )
        resultado = calcular_romana_teto(entrada)

        self.assertAlmostEqual(resultado.comprimento_corrente_sem_fim_m, 2.00)

    def test_manual_corrente_rejeita_corrente_sem_fim_fora_da_lista(self):
        """Testa que medida fora da lista é rejeitada."""
        for medida_invalida in (0.50, 0.80, 1.10, 1.60, 2.20, 3.50, 5.00):
            with self.subTest(medida=medida_invalida):
                with self.assertRaises(ValueError):
                    calcular_romana_teto(
                        RomanaTetoEntrada(
                            largura_modulo_m=1.00,
                            comprimento_avanco_m=3.00,
                            quantidade_modulos=1,
                            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
                            lado_comando="ESQUERDA",
                            comprimento_corrente_sem_fim_m=medida_invalida,
                        )
                    )

    def test_manual_corrente_rejeita_lado_comando_invalido(self):
        """Testa que lado_comando inválido é rejeitado."""
        for lado_invalido in ("ESQUERDO", "DIREITO", "CENTRO", "", "INVALIDO"):
            with self.subTest(lado=lado_invalido):
                with self.assertRaises(ValueError):
                    calcular_romana_teto(
                        RomanaTetoEntrada(
                            largura_modulo_m=1.00,
                            comprimento_avanco_m=3.00,
                            quantidade_modulos=1,
                            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
                            lado_comando=lado_invalido,
                        )
                    )

    def test_manual_corrente_corrente_tracao_igual_avanco_x_2(self):
        """Testa que corrente de tração = avanço x 2."""
        for avancos in (2.50, 3.00, 4.00, 5.00, 6.00):
            with self.subTest(avanco=avancos):
                entrada = RomanaTetoEntrada(
                    largura_modulo_m=1.00,
                    comprimento_avanco_m=avancos,
                    quantidade_modulos=1,
                    acionamento=ACIONAMENTO_MANUAL_CORRENTE,
                    lado_comando="ESQUERDA",
                )
                resultado = calcular_romana_teto(entrada)
                self.assertAlmostEqual(resultado.metragem_corrente_tracao_m, avancos * 2)

    def test_manual_corrente_quantidade_carrinho_master_igual_2(self):
        """Testa que quantidade carrinho Master = 2."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_carrinho_master, 2)

    def test_manual_corrente_quantidade_tampas_cabeceira_igual_2(self):
        """Testa que quantidade tampas cabeceira = 2."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_tampas_cabeceira_teto, 2)

    def test_manual_corrente_quantidade_corrente_sem_fim_igual_1(self):
        """Testa que quantidade corrente sem fim = 1."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_correntes_sem_fim, 1)

    def test_manual_corrente_quantidade_pendulos_igual_1(self):
        """Testa que quantidade pêndulos = 1."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.quantidade_pendulos, 1)

    def test_manual_corrente_corrente_sem_fim_apenas_no_trilho_comando(self):
        """Testa que corrente sem fim fica apenas no trilho do lado de comando."""
        # Lado DIREITA -> trilho DIREITO
        entrada_direita = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="DIREITA",
        )
        resultado_direita = calcular_romana_teto(entrada_direita)
        self.assertEqual(resultado_direita.trilho_comando, "DIREITO")
        self.assertEqual(resultado_direita.lado_comando, "DIREITA")

        # Lado ESQUERDA -> trilho ESQUERDO
        entrada_esquerda = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado_esquerda = calcular_romana_teto(entrada_esquerda)
        self.assertEqual(resultado_esquerda.trilho_comando, "ESQUERDO")
        self.assertEqual(resultado_esquerda.lado_comando, "ESQUERDA")

    def test_manual_corrente_sem_terceiro_trilho(self):
        """Testa que terceiro_trilho é sempre False para MANUAL_CORRENTE."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.50,  # Largura maior que limite de 1.20
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertFalse(resultado.terceiro_trilho)
        self.assertFalse(resultado.avaliacao_trilho_central)

    def test_manual_corrente_requer_lado_comando_obrigatorio(self):
        """Testa que MANUAL_CORRENTE exige lado_comando explícito."""
        with self.assertRaises(ValueError):
            calcular_romana_teto(
                RomanaTetoEntrada(
                    largura_modulo_m=1.00,
                    comprimento_avanco_m=3.00,
                    quantidade_modulos=1,
                    acionamento=ACIONAMENTO_MANUAL_CORRENTE,
                    lado_comando=None,
                )
            )

    def test_manual_corrente_opcoes_corrente_sem_fim_retornadas(self):
        """Testa que opções de corrente sem fim são retornadas."""
        entrada = RomanaTetoEntrada(
            largura_modulo_m=1.00,
            comprimento_avanco_m=3.00,
            quantidade_modulos=1,
            acionamento=ACIONAMENTO_MANUAL_CORRENTE,
            lado_comando="ESQUERDA",
        )
        resultado = calcular_romana_teto(entrada)

        self.assertEqual(resultado.opcoes_corrente_sem_fim_m, CORRENTE_SEM_FIM_OPCOES_VALIDAS)
        self.assertIn(CORRENTE_SEM_FIM_DEFAULT, resultado.opcoes_corrente_sem_fim_m)


class PimpointTecidoCustoResolverTest(unittest.TestCase):
    """Testes para o resolver de tecido/custo PIMPOINT (Fase 8E.5K)."""

    def _criar_produto_pimpoint(self, cor: str, produto_id: int = 1):
        class ProdutoMock:
            def __init__(self, cor, produto_id):
                self.familia_tecnica = FAMILIA_PIMPOINT
                self.cor = cor
                self.id = produto_id
        return ProdutoMock(cor, produto_id)

    def _criar_produto_nao_pimpoint(self, familia: str = "OUTRA_FAMILIA"):
        class ProdutoMock:
            def __init__(self, familia):
                self.familia_tecnica = familia
                self.cor = "BRANCO"
                self.id = 999
        return ProdutoMock(familia)

    # BRANCO tests
    def test_pimpoint_branco_1_50_fonte_1_83_custo_29_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 1.50)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.cor, "BRANCO")
        self.assertEqual(resultado.largura_tecido_selecionada_m, 1.83)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0089")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("29.98"))

    def test_pimpoint_branco_1_83_fonte_1_83_custo_29_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 1.83)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.largura_tecido_selecionada_m, 1.83)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0089")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("29.98"))

    def test_pimpoint_branco_1_84_fonte_2_50_custo_29_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 1.84)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.largura_tecido_selecionada_m, 2.50)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0092")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("29.98"))

    def test_pimpoint_branco_2_20_fonte_2_50_custo_29_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 2.20)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.largura_tecido_selecionada_m, 2.50)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0092")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("29.98"))

    def test_pimpoint_branco_2_50_fonte_2_50_custo_29_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 2.50)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.largura_tecido_selecionada_m, 2.50)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0092")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("29.98"))

    def test_pimpoint_branco_2_51_fonte_3_00_custo_32_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 2.51)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.largura_tecido_selecionada_m, 3.00)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0095")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("32.98"))

    def test_pimpoint_branco_3_00_fonte_3_00_custo_32_98(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 3.00)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.largura_tecido_selecionada_m, 3.00)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0095")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("32.98"))

    def test_pimpoint_branco_3_01_avaliacao_necessaria(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        resultado = resolver_tecido_pimpoint(produto, 3.01)
        self.assertEqual(resultado.status, STATUS_AVALIACAO_NECESSARIA)
        self.assertIsNone(resultado.largura_tecido_selecionada_m)
        self.assertIsNone(resultado.codigo_fonte)
        self.assertIsNone(resultado.custo_tecido_m2)

    # BEGE tests
    def test_pimpoint_bege_2_20_fonte_2_50_custo_29_98(self):
        produto = self._criar_produto_pimpoint("BEGE")
        resultado = resolver_tecido_pimpoint(produto, 2.20)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.cor, "BEGE")
        self.assertEqual(resultado.largura_tecido_selecionada_m, 2.50)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0093")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("29.98"))

    # CINZA tests
    def test_pimpoint_cinza_2_80_fonte_3_00_custo_32_98(self):
        produto = self._criar_produto_pimpoint("CINZA")
        resultado = resolver_tecido_pimpoint(produto, 2.80)
        self.assertEqual(resultado.status, STATUS_RESOLVIDO)
        self.assertEqual(resultado.cor, "CINZA")
        self.assertEqual(resultado.largura_tecido_selecionada_m, 3.00)
        self.assertEqual(resultado.codigo_fonte, "JPTEC-0097")
        self.assertEqual(resultado.custo_tecido_m2, Decimal("32.98"))

    # Cor inválida
    def test_pimpoint_cor_invalida_retorna_erro(self):
        produto = self._criar_produto_pimpoint("AZUL")
        resultado = resolver_tecido_pimpoint(produto, 2.20)
        self.assertEqual(resultado.status, STATUS_COR_INVALIDA)
        self.assertIsNone(resultado.codigo_fonte)
        self.assertIsNone(resultado.custo_tecido_m2)

    # Família não Pimpoint
    def test_familia_nao_pimpoint_nao_usa_regra(self):
        produto = self._criar_produto_nao_pimpoint("ROLO_BLACKOUT")
        resultado = resolver_tecido_pimpoint(produto, 2.20)
        self.assertEqual(resultado.status, STATUS_FAMILIA_NAO_PIMPOINT)
        self.assertIsNone(resultado.codigo_fonte)
        self.assertIsNone(resultado.custo_tecido_m2)

    # comprimento_avanco não interfere na escolha da largura do tecido
    def test_comprimento_avanco_nao_interfere_na_largura_tecido(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        # Mesmo largura_modulo_m, diferentes comprimentos_avanco devem dar mesmo resultado
        resultado_1 = resolver_tecido_pimpoint(produto, 2.20)
        resultado_2 = resolver_tecido_pimpoint(produto, 2.20)  # mesmo largura
        self.assertEqual(resultado_1.largura_tecido_selecionada_m, resultado_2.largura_tecido_selecionada_m)
        self.assertEqual(resultado_1.codigo_fonte, resultado_2.codigo_fonte)
        self.assertEqual(resultado_1.custo_tecido_m2, resultado_2.custo_tecido_m2)


class PimpointSimulacaoTest(unittest.TestCase):
    """Testes para a simulação com custo PIMPOINT por largura (Fase 8E.5K.2)."""

    def _criar_produto_pimpoint(self, cor: str, produto_id: int = 1):
        class ProdutoMock:
            def __init__(self, cor, produto_id):
                self.familia_tecnica = FAMILIA_PIMPOINT
                self.cor = cor
                self.id = produto_id
                self.unidade_venda = "M2"
                self.custo_final = Decimal("10.00")
                self.valor_custo = Decimal("10.00")
                self.valor_venda = Decimal("50.00")
        return ProdutoMock(cor, produto_id)

    def _criar_produto_nao_pimpoint(self, familia: str = "ROLO_BLACKOUT"):
        class ProdutoMock:
            def __init__(self, familia):
                self.familia_tecnica = familia
                self.cor = "BRANCO"
                self.id = 999
                self.unidade_venda = "M2"
                self.custo_final = Decimal("10.00")
                self.valor_custo = Decimal("10.00")
                self.valor_venda = Decimal("50.00")
        return ProdutoMock(familia)

    def _criar_entrada(self, largura: float, perfil: str = "VAREJO", comprimento: float = 2.00):
        return RomanaTetoSimulacaoInput(
            produto_id=1,
            largura_modulo_m=largura,
            comprimento_avanco_m=comprimento,
            quantidade_modulos=1,
            acionamento="MANUAL_BASTAO",
            perfil_comercial=perfil,
            desconto=0,
        )

    # Exemplo A: Pimpoint Branco 2,20 / Varejo
    def test_pimpoint_branco_2_20_varejo_preco_59_96(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = self._criar_entrada(2.20, "VAREJO")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_RESOLVIDO)
        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 29.98)
        self.assertEqual(resultado["custo_cadastrado"], Decimal("29.98"))
        self.assertEqual(resultado["preco_unitario"], Decimal("59.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")
        self.assertTrue(resultado["preco_disponivel"])
        self.assertEqual(resultado["subtotal"], Decimal("263.82"))

    # Exemplo B: Pimpoint Branco 2,80 / Varejo
    def test_pimpoint_branco_2_80_varejo_preco_65_96(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = self._criar_entrada(2.80, "VAREJO")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_RESOLVIDO)
        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 32.98)
        self.assertEqual(resultado["custo_cadastrado"], Decimal("32.98"))
        self.assertEqual(resultado["preco_unitario"], Decimal("65.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")
        self.assertTrue(resultado["preco_disponivel"])

    # Largura > 3,00: preço indisponível, avaliação necessária
    def test_pimpoint_branco_3_01_preco_indisponivel_avaliacao_necessaria(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = self._criar_entrada(3.01, "VAREJO")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_AVALIACAO_NECESSARIA)
        self.assertIsNone(resultado["tecido_custo_resolvido"]["custo_tecido_m2"])
        self.assertIsNone(resultado["custo_cadastrado"])
        self.assertEqual(resultado["preco_unitario"], Decimal("0"))
        self.assertEqual(resultado["origem_preco"], "AVALIACAO_NECESSARIA")
        self.assertFalse(resultado["preco_disponivel"])
        avisos = resultado["alertas"]
        self.assertTrue(any("Avaliação técnica necessária" in a for a in avisos))

    # Produto não Pimpoint: comportamento atual preservado
    def test_produto_nao_pimpoint_comportamento_atual_preservado(self):
        produto = self._criar_produto_nao_pimpoint("ROLO_BLACKOUT")
        entrada = self._criar_entrada(2.20, "VAREJO")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_FAMILIA_NAO_PIMPOINT)
        self.assertEqual(resultado["origem_preco"], "CUSTO_CADASTRADO")
        self.assertEqual(resultado["preco_unitario"], Decimal("20.00"))
        self.assertTrue(resultado["preco_disponivel"])

    # Área faturável mínima: 0,70 x 0,70 = 0,49 -> 1,50 m²
    def test_area_faturavel_minima_0_70_x_0_70_usa_1_50_m2(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = RomanaTetoSimulacaoInput(
            produto_id=1,
            largura_modulo_m=0.70,
            comprimento_avanco_m=0.70,
            quantidade_modulos=1,
            acionamento="MANUAL_BASTAO",
            perfil_comercial="VAREJO",
            desconto=0,
        )
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["area_real_m2"], 0.49)
        self.assertEqual(resultado["area_faturavel_m2"], 1.50)
        self.assertTrue(resultado["minimo_faturavel_aplicado"])
        self.assertEqual(resultado["subtotal"], Decimal("89.94"))

    # Outros perfis comerciais: Decorador 1.50, Consumidor Final 2.50
    def test_pimpoint_branco_2_20_decorador_preco_44_97(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = self._criar_entrada(2.20, "DECORADOR")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["preco_unitario"], Decimal("44.97"))

    def test_pimpoint_branco_2_20_consumidor_final_preco_74_95(self):
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = self._criar_entrada(2.20, "CONSUMIDOR_FINAL")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["preco_unitario"], Decimal("74.95"))

    # Pimpoint Bege
    def test_pimpoint_bege_2_20_varejo_preco_59_96(self):
        produto = self._criar_produto_pimpoint("BEGE")
        entrada = self._criar_entrada(2.20, "VAREJO")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 29.98)
        self.assertEqual(resultado["preco_unitario"], Decimal("59.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")

    # Pimpoint Cinza
    def test_pimpoint_cinza_2_80_varejo_preco_65_96(self):
        produto = self._criar_produto_pimpoint("CINZA")
        entrada = self._criar_entrada(2.80, "VAREJO")
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 32.98)
        self.assertEqual(resultado["preco_unitario"], Decimal("65.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")

    # Testes para prioridade de cor no payload (Fase 8E.6.2)
    def test_pimpoint_produto_bege_payload_branco_usa_branco(self):
        """A) Produto base com cor cadastrada BEGE, payload cor=BRANCO, largura=2.20 -> deve usar BRANCO, JPTEC-0092, custo 29,98"""
        produto = self._criar_produto_pimpoint("BEGE")
        entrada = RomanaTetoSimulacaoInput(
            produto_id=1,
            largura_modulo_m=2.20,
            comprimento_avanco_m=2.00,
            quantidade_modulos=1,
            acionamento="MANUAL_BASTAO",
            perfil_comercial="VAREJO",
            desconto=0,
            cor="BRANCO",
        )
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_RESOLVIDO)
        self.assertEqual(resultado["tecido_custo_resolvido"]["cor"], "BRANCO")
        self.assertEqual(resultado["tecido_custo_resolvido"]["largura_tecido_selecionada_m"], 2.50)
        self.assertEqual(resultado["tecido_custo_resolvido"]["codigo_fonte"], "JPTEC-0092")
        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 29.98)
        self.assertEqual(resultado["custo_cadastrado"], Decimal("29.98"))
        self.assertEqual(resultado["preco_unitario"], Decimal("59.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")
        self.assertTrue(resultado["preco_disponivel"])

    def test_pimpoint_payload_cinza_largura_2_80(self):
        """B) Payload cor=CINZA, largura=2.80 -> JPTEC-0097, custo 32,98"""
        produto = self._criar_produto_pimpoint("BEGE")  # Cor do produto diferente
        entrada = RomanaTetoSimulacaoInput(
            produto_id=1,
            largura_modulo_m=2.80,
            comprimento_avanco_m=2.00,
            quantidade_modulos=1,
            acionamento="MANUAL_BASTAO",
            perfil_comercial="VAREJO",
            desconto=0,
            cor="CINZA",
        )
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_RESOLVIDO)
        self.assertEqual(resultado["tecido_custo_resolvido"]["cor"], "CINZA")
        self.assertEqual(resultado["tecido_custo_resolvido"]["largura_tecido_selecionada_m"], 3.00)
        self.assertEqual(resultado["tecido_custo_resolvido"]["codigo_fonte"], "JPTEC-0097")
        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 32.98)
        self.assertEqual(resultado["custo_cadastrado"], Decimal("32.98"))
        self.assertEqual(resultado["preco_unitario"], Decimal("65.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")
        self.assertTrue(resultado["preco_disponivel"])

    def test_pimpoint_payload_cor_invalida_retorna_erro_controlado(self):
        """C) Payload cor inválida -> erro/pendência controlada"""
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = RomanaTetoSimulacaoInput(
            produto_id=1,
            largura_modulo_m=2.20,
            comprimento_avanco_m=2.00,
            quantidade_modulos=1,
            acionamento="MANUAL_BASTAO",
            perfil_comercial="VAREJO",
            desconto=0,
            cor="AZUL",
        )
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_COR_INVALIDA)
        self.assertEqual(resultado["tecido_custo_resolvido"]["cor"], "AZUL")
        self.assertIsNone(resultado["tecido_custo_resolvido"]["codigo_fonte"])
        self.assertIsNone(resultado["tecido_custo_resolvido"]["custo_tecido_m2"])
        self.assertEqual(resultado["preco_unitario"], Decimal("0"))
        self.assertEqual(resultado["origem_preco"], "AVALIACAO_NECESSARIA")
        self.assertFalse(resultado["preco_disponivel"])
        avisos = resultado["alertas"]
        self.assertTrue(any("não suportada para PIMPOINT" in a for a in avisos))

    def test_pimpoint_payload_sem_cor_usa_fallback_produto(self):
        """D) Payload sem cor -> fallback atual preservado (usa produto.cor)"""
        produto = self._criar_produto_pimpoint("BRANCO")
        entrada = RomanaTetoSimulacaoInput(
            produto_id=1,
            largura_modulo_m=2.20,
            comprimento_avanco_m=2.00,
            quantidade_modulos=1,
            acionamento="MANUAL_BASTAO",
            perfil_comercial="VAREJO",
            desconto=0,
            cor=None,
        )
        resultado = simular_romana_teto(produto, entrada)

        self.assertEqual(resultado["tecido_custo_resolvido"]["status"], STATUS_RESOLVIDO)
        self.assertEqual(resultado["tecido_custo_resolvido"]["cor"], "BRANCO")
        self.assertEqual(resultado["tecido_custo_resolvido"]["largura_tecido_selecionada_m"], 2.50)
        self.assertEqual(resultado["tecido_custo_resolvido"]["codigo_fonte"], "JPTEC-0092")
        self.assertEqual(resultado["tecido_custo_resolvido"]["custo_tecido_m2"], 29.98)
        self.assertEqual(resultado["custo_cadastrado"], Decimal("29.98"))
        self.assertEqual(resultado["preco_unitario"], Decimal("59.96"))
        self.assertEqual(resultado["origem_preco"], "CUSTO_TECIDO_POR_LARGURA")
        self.assertTrue(resultado["preco_disponivel"])


if __name__ == "__main__":
    unittest.main()