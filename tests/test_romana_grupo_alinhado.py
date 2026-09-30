import unittest

from app.services.romana_grupo_alinhado import (
    STATUS_OK,
    STATUS_REVISAR,
    RomanaGrupoAlinhadoEntrada,
    RomanaGrupoPecaEntrada,
    _alertas_ultimo_gomo,
    calcular_grupo_alinhado_romana,
)


def grupo(*alturas):
    return RomanaGrupoAlinhadoEntrada(
        pecas=tuple(
            RomanaGrupoPecaEntrada(f"P{i + 1}", 120, altura, posicao_conjunto=str(i + 1))
            for i, altura in enumerate(alturas)
        )
    )


class RomanaGrupoAlinhadoTest(unittest.TestCase):
    def test_230_e_140(self):
        resultado = calcular_grupo_alinhado_romana(grupo(230, 140))
        mestre, menor = resultado.pecas
        self.assertEqual(resultado.peca_mestre, "P1")
        self.assertEqual(
            [v.posicao_cm for v in menor.posicoes_varetas],
            [p for p in resultado.posicoes_compartilhadas_cm if p < 140],
        )
        self.assertEqual(menor.quantidade_varetas, 4)
        self.assertEqual(menor.quantidade_gomos, 5)
        self.assertEqual(menor.varetas_com_passadores, (2, 4))
        self.assertAlmostEqual(140 - menor.posicoes_varetas[-1].posicao_cm, menor.ultimo_gomo_cm)
        self.assertAlmostEqual(menor.comprimento_total_tecido_cm, 146)
        self.assertEqual(menor.status, STATUS_REVISAR)
        self.assertTrue(mestre.peca_mestre)

    def test_230_e_200(self):
        resultado = calcular_grupo_alinhado_romana(grupo(230, 200))
        menor = resultado.pecas[1]
        self.assertEqual(menor.quantidade_varetas, 6)
        self.assertEqual(menor.varetas_com_passadores, (2, 4, 6))
        self.assertAlmostEqual(menor.comprimento_total_tecido_cm, 207)
        self.assertLess(menor.ultimo_gomo_cm, 3)
        self.assertEqual(menor.status, STATUS_REVISAR)

    def test_varias_menores_usam_a_mesma_mestre(self):
        resultado = calcular_grupo_alinhado_romana(grupo(230, 170, 140))
        self.assertEqual(resultado.peca_mestre, "P1")
        for menor in resultado.pecas[1:]:
            esperadas = [p for p in resultado.posicoes_compartilhadas_cm if p < menor.altura_cm]
            self.assertEqual([v.posicao_cm for v in menor.posicoes_varetas], esperadas)
        self.assertEqual(resultado.pecas[1].quantidade_varetas, 5)
        self.assertEqual(resultado.pecas[1].status, STATUS_REVISAR)

    def test_duas_pecas_iguais_tem_posicoes_iguais(self):
        resultado = calcular_grupo_alinhado_romana(grupo(200, 200))
        posicoes = [tuple(v.posicao_cm for v in p.posicoes_varetas) for p in resultado.pecas]
        self.assertEqual(posicoes[0], posicoes[1])
        self.assertEqual(resultado.status, STATUS_OK)

    def test_grupo_vazio_e_unitario(self):
        with self.assertRaises(ValueError):
            calcular_grupo_alinhado_romana(RomanaGrupoAlinhadoEntrada(pecas=()))
        with self.assertRaises(ValueError):
            calcular_grupo_alinhado_romana(grupo(200))

    def test_dimensoes_invalidas(self):
        with self.assertRaises(ValueError):
            calcular_grupo_alinhado_romana(grupo(230, 0))
        entrada = RomanaGrupoAlinhadoEntrada(
            pecas=(RomanaGrupoPecaEntrada("A", 0, 230), RomanaGrupoPecaEntrada("B", 120, 200))
        )
        with self.assertRaises(ValueError):
            calcular_grupo_alinhado_romana(entrada)

    def test_menor_sem_posicao_compativel(self):
        resultado = calcular_grupo_alinhado_romana(grupo(230, 10))
        menor = resultado.pecas[1]
        self.assertEqual(menor.quantidade_varetas, 0)
        self.assertEqual(menor.status, STATUS_REVISAR)
        self.assertTrue(any("nenhuma posição" in alerta for alerta in menor.alertas))

    def test_ultimo_gomo_nao_positivo(self):
        self.assertTrue(_alertas_ultimo_gomo(0, 30))
        self.assertTrue(_alertas_ultimo_gomo(-1, 30))

    def test_varetas_incompativeis_com_passadores(self):
        resultado = calcular_grupo_alinhado_romana(grupo(230, 170))
        menor = resultado.pecas[1]
        self.assertEqual(menor.quantidade_varetas % 2, 1)
        self.assertNotEqual(menor.varetas_com_passadores[-1], menor.quantidade_varetas)
        self.assertEqual(menor.status, STATUS_REVISAR)


if __name__ == "__main__":
    unittest.main()
