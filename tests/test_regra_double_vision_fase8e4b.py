"""Testes da regra técnica central de seleção de tubo Double Vision manual.

Valida os limiares confirmados em CONFIRMACAO_TECNICA_MANUAL:
- 1,50 -> 32mm (permitido)
- 1,80 -> 32mm (permitido)
- 1,81 -> 38mm (permitido)
- 2,20 -> 38mm (permitido)  -- 2,20 NÃO é limiar
- 2,60 -> 38mm (permitido - padrão)
- 2,61 -> 38mm (requer validação tecido/fornecedor)
- 2,80 -> 38mm (somente com compatibilidade explícita)
- 2,81 -> bloqueado
"""

import unittest

from app.technical.rules.double_vision import (
    selecionar_tubo_double_vision,
    TuboDVdiametro,
    EstadoValidacao,
    LarguraInvalidaErro,
    LarguraExcedidaErro,
    tubo_para_codigo_tecnico,
    codigo_tecnico_para_tubo,
    validar_largura_double_vision,
    obter_limites_double_vision,
)


class TestRegraTuboDoubleVisionCentral(unittest.TestCase):
    """Testes da regra central de seleção de tubo Double Vision."""

    def test_largura_1_50_deve_ser_32mm_permitido(self):
        selecao = selecionar_tubo_double_vision(1.50)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D32)
        self.assertEqual(selecao.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao.permitido)
        self.assertFalse(selecao.requer_validacao_tecido_fornecedor)
        self.assertIsNone(selecao.motivo_bloqueio)
        self.assertEqual(selecao.origem, "CONFIRMACAO_TECNICA_MANUAL")

    def test_largura_1_80_deve_ser_32mm_permitido(self):
        selecao = selecionar_tubo_double_vision(1.80)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D32)
        self.assertEqual(selecao.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao.permitido)

    def test_largura_1_81_deve_ser_38mm_permitido(self):
        selecao = selecionar_tubo_double_vision(1.81)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D38)
        self.assertEqual(selecao.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao.permitido)

    def test_largura_2_20_deve_ser_38mm_permitido(self):
        """2,20 NÃO é limiar - deve ser 38mm (limiar antigo era 2,20)."""
        selecao = selecionar_tubo_double_vision(2.20)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D38)
        self.assertEqual(selecao.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao.permitido)

    def test_largura_2_60_deve_ser_38mm_permitido_padrao(self):
        """2,60 é o limite padrão - permitido normalmente."""
        selecao = selecionar_tubo_double_vision(2.60)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D38)
        self.assertEqual(selecao.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao.permitido)
        self.assertFalse(selecao.requer_validacao_tecido_fornecedor)

    def test_largura_2_61_requer_validacao_tecido_fornecedor(self):
        """2,61 excede padrão 2,60 - requer validação explícita."""
        selecao = selecionar_tubo_double_vision(2.61)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D38)
        self.assertEqual(selecao.estado, EstadoValidacao.REQUER_VALIDACAO)
        self.assertFalse(selecao.permitido)
        self.assertTrue(selecao.requer_validacao_tecido_fornecedor)
        self.assertIsNotNone(selecao.motivo_bloqueio)
        self.assertIn("2,60m", selecao.motivo_bloqueio)
        self.assertIn("validação", selecao.motivo_bloqueio.lower())

    def test_largura_2_61_com_validacao_explicita_deve_ser_permitido(self):
        """2,61 com validação explícita de tecido/fornecedor deve ser permitido."""
        selecao = selecionar_tubo_double_vision(2.61, tem_validacao_tecido_fornecedor=True)
        self.assertEqual(selecao.diametro, TuboDVdiametro.D38)
        self.assertEqual(selecao.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao.permitido)
        self.assertTrue(selecao.requer_validacao_tecido_fornecedor)

    def test_largura_2_80_somente_com_validacao_explicita(self):
        """2,80 é o máximo absoluto - só permitido com validação explícita."""
        # Sem validação: requer validação
        selecao_sem = selecionar_tubo_double_vision(2.80)
        self.assertEqual(selecao_sem.estado, EstadoValidacao.REQUER_VALIDACAO)
        self.assertFalse(selecao_sem.permitido)

        # Com validação: permitido
        selecao_com = selecionar_tubo_double_vision(2.80, tem_validacao_tecido_fornecedor=True)
        self.assertEqual(selecao_com.estado, EstadoValidacao.PERMITIDO)
        self.assertTrue(selecao_com.permitido)

    def test_largura_2_81_deve_ser_bloqueado(self):
        """2,81 excede máximo absoluto 2,80 - deve lançar LarguraExcedidaErro."""
        with self.assertRaises(LarguraExcedidaErro) as cm:
            selecionar_tubo_double_vision(2.81)
        erro = cm.exception
        self.assertEqual(erro.largura, 2.81)
        self.assertIn("2,80m", str(erro))
        self.assertIn("não é possível fabricar", str(erro).lower())

    def test_largura_3_00_deve_ser_bloqueado(self):
        with self.assertRaises(LarguraExcedidaErro):
            selecionar_tubo_double_vision(3.00)

    def test_largura_zero_ou_negativa_deve_levantar_erro(self):
        with self.assertRaises(LarguraInvalidaErro):
            selecionar_tubo_double_vision(0)
        with self.assertRaises(LarguraInvalidaErro):
            selecionar_tubo_double_vision(-1)

    def test_limites_tecnicos_retornados_corretamente(self):
        selecao = selecionar_tubo_double_vision(2.00)
        self.assertEqual(selecao.largura_maxima_padrao_m, 2.60)
        self.assertEqual(selecao.largura_maxima_excepcional_m, 2.80)

    def test_tubo_para_codigo_tecnico(self):
        self.assertEqual(tubo_para_codigo_tecnico(TuboDVdiametro.D32), "TUBO_DOUBLE_VISION_32MM")
        self.assertEqual(tubo_para_codigo_tecnico(TuboDVdiametro.D38), "TUBO_DOUBLE_VISION_38MM")

    def test_codigo_tecnico_para_tubo(self):
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_DOUBLE_VISION_32MM"), TuboDVdiametro.D32)
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_DOUBLE_VISION_38MM"), TuboDVdiametro.D38)
        self.assertIsNone(codigo_tecnico_para_tubo("TUBO_DOUBLE_VISION_99MM"))
        self.assertIsNone(codigo_tecnico_para_tubo("INVALIDO"))

    def test_validar_largura_double_vision_permitido(self):
        permitido, motivo = validar_largura_double_vision(1.50)
        self.assertTrue(permitido)
        self.assertIsNone(motivo)

        permitido, motivo = validar_largura_double_vision(2.60)
        self.assertTrue(permitido)
        self.assertIsNone(motivo)

    def test_validar_largura_double_vision_requer_validacao(self):
        permitido, motivo = validar_largura_double_vision(2.61)
        self.assertFalse(permitido)
        self.assertIsNotNone(motivo)
        self.assertIn("validação", motivo.lower())

    def test_validar_largura_double_vision_bloqueado(self):
        permitido, motivo = validar_largura_double_vision(2.81)
        self.assertFalse(permitido)
        self.assertIsNotNone(motivo)
        self.assertIn("2,80m", motivo)

    def test_validar_largura_double_vision_invalida(self):
        permitido, motivo = validar_largura_double_vision(0)
        self.assertFalse(permitido)
        self.assertIsNotNone(motivo)

    def test_obter_limites_double_vision(self):
        limites = obter_limites_double_vision()
        self.assertEqual(limites["limite_tubo_32mm_m"], 1.80)
        self.assertEqual(limites["limite_tubo_38mm_m"], 2.80)
        self.assertEqual(limites["largura_maxima_padrao_m"], 2.60)
        self.assertEqual(limites["largura_maxima_excepcional_m"], 2.80)
        self.assertEqual(limites["largura_maxima_absoluta_m"], 2.80)
        self.assertEqual(limites["requer_validacao_acima_de_m"], 2.60)
        self.assertEqual(limites["origem"], "CONFIRMACAO_TECNICA_MANUAL")


class TestCompatibilidadeOrcamentos(unittest.TestCase):
    """Testes de compatibilidade com a função tubo_double_vision do orcamentos.py."""

    def test_tubo_double_vision_retorna_string_compativel(self):
        from modulos.orcamentos import tubo_double_vision

        # <= 1,80 -> 32mm
        self.assertEqual(tubo_double_vision("Double Vision", 1.50), "32mm")
        self.assertEqual(tubo_double_vision("Double Vision", 1.80), "32mm")

        # > 1,80 e <= 2,60 -> 38mm
        self.assertEqual(tubo_double_vision("Double Vision", 1.81), "38mm")
        self.assertEqual(tubo_double_vision("Double Vision", 2.20), "38mm")
        self.assertEqual(tubo_double_vision("Double Vision", 2.60), "38mm")

        # > 2,60 sem validação -> ainda retorna 38mm (diâmetro técnico) mas estado interno é pendente
        self.assertEqual(tubo_double_vision("Double Vision", 2.61), "38mm")
        self.assertEqual(tubo_double_vision("Double Vision", 2.80), "38mm")

        # Motorizada
        self.assertEqual(tubo_double_vision("Double Vision Motorizada", 2.00), "41mm")
        self.assertEqual(tubo_double_vision("Double Vision Motorizada", 2.00, tipo_motor="Bateria"), "38mm")

    def test_tubo_double_vision_com_validacao_explicita(self):
        from modulos.orcamentos import tubo_double_vision

        # Com validação explícita, 2,61 a 2,80 retornam 38mm
        self.assertEqual(tubo_double_vision("Double Vision", 2.61, tem_validacao_tecido_fornecedor=True), "38mm")
        self.assertEqual(tubo_double_vision("Double Vision", 2.80, tem_validacao_tecido_fornecedor=True), "38mm")


class TestReceitaDoubleVision(unittest.TestCase):
    """Testes da receita Double Vision."""

    def test_receita_sem_bando_inclui_barra_niveladora(self):
        from modulos.orcamentos import montar_receita_double_vision

        receita = montar_receita_double_vision(1.50, 2.00, 1, modelo="Double Vision", com_bando=False)
        componentes = {item["componente"] for item in receita}
        self.assertIn("Barra Estabilizadora Double Vision", componentes)
        self.assertNotIn("Bandô Double Vision", componentes)

    def test_receita_com_bando_inclui_bando_e_tampas(self):
        from modulos.orcamentos import montar_receita_double_vision

        receita = montar_receita_double_vision(1.50, 2.00, 1, modelo="Double Vision", com_bando=True)
        componentes = {item["componente"] for item in receita}
        self.assertIn("Bandô Double Vision", componentes)
        self.assertIn("Tampa Bandô Double Vision", componentes)
        self.assertNotIn("Barra Estabilizadora Double Vision", componentes)

    def test_receita_sempre_inclui_tubo_correto(self):
        from modulos.orcamentos import montar_receita_double_vision

        # 1,50 -> 32mm
        receita = montar_receita_double_vision(1.50, 2.00, 1, modelo="Double Vision")
        tubos = [item for item in receita if item["grupo"] == "Tubos"]
        self.assertEqual(len(tubos), 1)
        self.assertIn("32mm", tubos[0]["componente"])

        # 2,00 -> 38mm
        receita = montar_receita_double_vision(2.00, 2.00, 1, modelo="Double Vision")
        tubos = [item for item in receita if item["grupo"] == "Tubos"]
        self.assertIn("38mm", tubos[0]["componente"])

    def test_receita_inclui_componentes_obrigatorios(self):
        from modulos.orcamentos import montar_receita_double_vision

        receita = montar_receita_double_vision(1.50, 2.00, 1, modelo="Double Vision")
        componentes = {item["componente"] for item in receita}

        # Componentes obrigatórios da receita Double Vision manual
        self.assertIn("Tecido Double Vision", componentes)
        self.assertIn("Barra Estabilizadora Double Vision", componentes)
        self.assertIn("Eixo Base Double Vision", componentes)
        self.assertIn("Base Cunha Double Vision", componentes)
        self.assertIn("Tampa Redonda do Eixo Double Vision", componentes)
        self.assertIn("Tampa Base Double Vision", componentes)
        self.assertIn("CLIPS E SUPORTES - GRAPA 40MM BRANCA - IMPORTADA", componentes)
        self.assertIn("Espaguete 2,5mm", componentes)
        self.assertIn("Fita Plástica 1,5mm", componentes)

    def test_receita_nao_usa_regras_rolo(self):
        """Verifica que a receita Double Vision não reutiliza fórmula de Rolô."""
        from modulos.orcamentos import montar_receita_double_vision

        receita = montar_receita_double_vision(1.50, 2.00, 1, modelo="Double Vision")
        componentes = {item["componente"] for item in receita}

        # Não deve ter componentes de Rolô
        self.assertNotIn("Tubo Rolô", componentes)
        self.assertNotIn("Kit Comando Rolô", " ".join(componentes))
        self.assertNotIn("Corrente Rolô", " ".join(componentes))


if __name__ == "__main__":
    unittest.main()