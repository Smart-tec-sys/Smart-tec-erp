import unittest

from app.services.romana_teto_calculo_producao import (
    INSTALACAO_DENTRO_VAO,
    INSTALACAO_FORA_VAO,
    STATUS_ALINHADO,
    STATUS_PARCIAL,
    STATUS_REVISAR,
    ROMANA_TETO_PRODUCAO_LIBERADA,
    ROMANA_TETO_V1_STATUS,
    RomanaTetoGeometriaMestre,
    RomanaTetoGrupoEntrada,
    RomanaTetoPecaEntrada,
    calcular_grupo_romana_teto,
)


def geometria_230():
    # Referência explícita para os testes; o motor de teto não a calcula.
    gomo = 228 / 7
    return RomanaTetoGeometriaMestre(
        quantidade_gomos=7,
        posicoes_varetas_cm=tuple(gomo + 2 + indice * gomo for indice in range(6)),
        altura_cm=230,
        origem="REFERENCIA_MATEMATICA_EXPLICITA_NAO_REGRA_TETO",
    )


def calcular(tipo, *alturas):
    return calcular_grupo_romana_teto(
        RomanaTetoGrupoEntrada(
            pecas=tuple(RomanaTetoPecaEntrada(f"P{i + 1}", 120, h) for i, h in enumerate(alturas)),
            tipo_instalacao=tipo,
            geometria_mestre=geometria_230() if max(alturas) == 230 else RomanaTetoGeometriaMestre(
                quantidade_gomos=7,
                posicoes_varetas_cm=tuple((198 / 7) + 2 + i * (198 / 7) for i in range(6)),
                altura_cm=200,
                origem="REFERENCIA_MATEMATICA_EXPLICITA_NAO_REGRA_TETO",
            ),
        )
    )


class RomanaTetoCalculoProducaoTest(unittest.TestCase):
    def test_v1_permanece_diagnostica_e_nao_produtiva(self):
        resultado = calcular(INSTALACAO_FORA_VAO, 230, 140)
        self.assertEqual(resultado.versao_status, ROMANA_TETO_V1_STATUS)
        self.assertEqual(resultado.versao_status, "DIAGNOSTICA")
        self.assertFalse(ROMANA_TETO_PRODUCAO_LIBERADA)
        self.assertFalse(resultado.producao_liberada)

    def test_230_140_fora_do_vao_alinha_integralmente(self):
        resultado = calcular(INSTALACAO_FORA_VAO, 230, 140)
        menor = resultado.pecas[1]
        self.assertEqual(menor.altura_original_cm, 140)
        self.assertEqual(menor.altura_ajustada_cm, 230)
        self.assertEqual(menor.diferenca_acrescentada_cm, 90)
        self.assertEqual(menor.posicoes_varetas_cm, resultado.pecas[0].posicoes_varetas_cm)
        self.assertEqual(menor.quantidade_gomos, 7)
        self.assertEqual(menor.quantidade_varetas, 6)
        self.assertEqual(menor.varetas_com_passadores, (2, 4, 6))
        self.assertEqual(menor.status, STATUS_ALINHADO)

    def test_230_140_dentro_do_vao_preserva_altura(self):
        resultado = calcular(INSTALACAO_DENTRO_VAO, 230, 140)
        menor = resultado.pecas[1]
        self.assertEqual(menor.altura_ajustada_cm, 140)
        self.assertEqual(menor.diferenca_acrescentada_cm, 0)
        self.assertEqual(menor.quantidade_varetas, 4)
        self.assertEqual(menor.quantidade_gomos, 5)
        self.assertEqual(menor.varetas_com_passadores, (2, 4))
        self.assertTrue(all(pos < 140 for pos in menor.posicoes_varetas_cm))
        self.assertGreater(menor.ultimo_gomo_cm, 0)
        self.assertEqual(menor.status, STATUS_PARCIAL)

    def test_demais_grupos_fora_do_vao(self):
        for alturas in ((230, 200), (230, 170), (230, 140), (230, 200, 170, 140)):
            with self.subTest(alturas=alturas):
                resultado = calcular(INSTALACAO_FORA_VAO, *alturas)
                for peca in resultado.pecas[1:]:
                    self.assertEqual(peca.altura_ajustada_cm, 230)
                    self.assertEqual(peca.quantidade_varetas, 6)
                    self.assertEqual(peca.varetas_com_passadores[-1], 6)
                    self.assertEqual(peca.status, STATUS_ALINHADO)

    def test_demais_grupos_dentro_do_vao(self):
        for alturas in ((230, 200), (230, 170), (230, 140), (230, 200, 170, 140)):
            with self.subTest(alturas=alturas):
                resultado = calcular(INSTALACAO_DENTRO_VAO, *alturas)
                for peca in resultado.pecas[1:]:
                    self.assertEqual(peca.altura_ajustada_cm, peca.altura_original_cm)
                    self.assertEqual(peca.quantidade_varetas % 2, 0)
                    self.assertTrue(all(pos < peca.altura_original_cm for pos in peca.posicoes_varetas_cm))
                    self.assertGreater(peca.ultimo_gomo_cm, 0)
                    self.assertIn(peca.status, (STATUS_PARCIAL, STATUS_REVISAR))

    def test_200_200_preserva_as_duas_pecas(self):
        for tipo in (INSTALACAO_FORA_VAO, INSTALACAO_DENTRO_VAO):
            resultado = calcular(tipo, 200, 200)
            self.assertEqual([p.altura_ajustada_cm for p in resultado.pecas], [200, 200])
            self.assertEqual(resultado.pecas[0].posicoes_varetas_cm, resultado.pecas[1].posicoes_varetas_cm)
            self.assertEqual(resultado.status, STATUS_ALINHADO)

    def test_geometria_mestre_invalida_e_rejeitada(self):
        entrada = RomanaTetoGrupoEntrada(
            pecas=(RomanaTetoPecaEntrada("A", 120, 230),),
            tipo_instalacao=INSTALACAO_DENTRO_VAO,
            geometria_mestre=RomanaTetoGeometriaMestre(6, (30, 60, 90, 120, 150), 230, "teste"),
        )
        with self.assertRaises(ValueError):
            calcular_grupo_romana_teto(entrada)

    def test_sem_limite_automatico_de_cinquenta_por_cento(self):
        resultado = calcular(INSTALACAO_DENTRO_VAO, 230, 200)
        menor = resultado.pecas[1]
        self.assertGreater(menor.ultimo_gomo_cm, 0)
        self.assertFalse(any("50%" in alerta for alerta in menor.alertas))


if __name__ == "__main__":
    unittest.main()
