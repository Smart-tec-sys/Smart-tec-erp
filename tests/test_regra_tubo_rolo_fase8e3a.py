"""Testes da regra técnica central de seleção de tubo Rolô.

Valida os limiares confirmados em CONFIRMACAO_TECNICA_MANUAL:
- 1,50 -> 32mm (manual)
- 1,80 -> 32mm (manual)
- 1,81 -> 38mm (manual)
- 2,20 -> 38mm (manual)  -- 2,20 NÃO é mais limiar
- 2,50 -> 38mm (manual)
- 2,51 -> 43mm (manual)
- 3,20 -> 43mm (manual)
- 3,21 -> motor obrigatório / sugestão 65mm
- 4,00 -> motor obrigatório / sugestão 65mm
"""

import unittest

from app.technical.rules.rolo import (
    selecionar_tubo_rolo,
    TuboRoloDiametro,
    AcionamentoPermitido,
    MotorObrigatorioErro,
    tubo_para_codigo_tecnico,
    codigo_tecnico_para_tubo,
)


class TestRegraTuboRoloCentral(unittest.TestCase):
    """Testes da regra central de seleção de tubo Rolô."""

    def test_largura_1_50_deve_ser_32mm_manual(self):
        selecao = selecionar_tubo_rolo(1.50, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D32)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)
        self.assertFalse(selecao.requer_confirmacao_vendedor)

    def test_largura_1_80_deve_ser_32mm_manual(self):
        selecao = selecionar_tubo_rolo(1.80, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D32)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)

    def test_largura_1_81_deve_ser_38mm_manual(self):
        selecao = selecionar_tubo_rolo(1.81, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D38)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)

    def test_largura_2_20_deve_ser_38mm_manual(self):
        """2,20 NÃO é mais limiar - deve ser 38mm (limiar antigo era 2,20)."""
        selecao = selecionar_tubo_rolo(2.20, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D38)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)

    def test_largura_2_50_deve_ser_38mm_manual(self):
        selecao = selecionar_tubo_rolo(2.50, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D38)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)

    def test_largura_2_51_deve_ser_43mm_manual(self):
        selecao = selecionar_tubo_rolo(2.51, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D43)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)

    def test_largura_3_20_deve_ser_43mm_manual(self):
        selecao = selecionar_tubo_rolo(3.20, acionamento="manual")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D43)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MANUAL)

    def test_largura_3_21_manual_deve_levantar_motor_obrigatorio(self):
        """Largura > 3,20m com acionamento manual deve lançar MotorObrigatorioErro."""
        with self.assertRaises(MotorObrigatorioErro) as cm:
            selecionar_tubo_rolo(3.21, acionamento="manual")
        erro = cm.exception
        self.assertEqual(erro.largura, 3.21)
        self.assertEqual(erro.diametro_sugerido, TuboRoloDiametro.D65)
        self.assertIn("motorização obrigatória", str(erro).lower())

    def test_largura_4_00_manual_deve_levantar_motor_obrigatorio(self):
        with self.assertRaises(MotorObrigatorioErro) as cm:
            selecionar_tubo_rolo(4.00, acionamento="manual")
        erro = cm.exception
        self.assertEqual(erro.largura, 4.00)
        self.assertEqual(erro.diametro_sugerido, TuboRoloDiametro.D65)

    def test_largura_3_21_motorizado_deve_ser_65mm_com_confirmacao(self):
        """Largura > 3,20m com motorização deve retornar 65mm com confirmação de vendedor."""
        selecao = selecionar_tubo_rolo(3.21, acionamento="motorizado")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D65)
        self.assertEqual(selecao.acionamento_permitido, AcionamentoPermitido.MOTORIZADO)
        self.assertTrue(selecao.requer_confirmacao_vendedor)
        self.assertIsNotNone(selecao.observacao)
        self.assertIn("65mm", selecao.observacao)
        self.assertIn("confirmação do vendedor", selecao.observacao.lower())
        self.assertIn("pé-direito", selecao.observacao.lower())
        self.assertIn("70mm", selecao.observacao)

    def test_largura_4_00_motorizado_deve_ser_65mm_com_confirmacao(self):
        selecao = selecionar_tubo_rolo(4.00, acionamento="motorizado")
        self.assertEqual(selecao.diametro, TuboRoloDiametro.D65)
        self.assertTrue(selecao.requer_confirmacao_vendedor)

    def test_largura_zero_ou_negativa_deve_levantar_erro(self):
        with self.assertRaises(ValueError):
            selecionar_tubo_rolo(0, acionamento="manual")
        with self.assertRaises(ValueError):
            selecionar_tubo_rolo(-1, acionamento="manual")

    def test_tubo_para_codigo_tecnico(self):
        self.assertEqual(tubo_para_codigo_tecnico(TuboRoloDiametro.D32), "TUBO_ROLO_32MM")
        self.assertEqual(tubo_para_codigo_tecnico(TuboRoloDiametro.D38), "TUBO_ROLO_38MM")
        self.assertEqual(tubo_para_codigo_tecnico(TuboRoloDiametro.D43), "TUBO_ROLO_43MM")
        self.assertEqual(tubo_para_codigo_tecnico(TuboRoloDiametro.D65), "TUBO_ROLO_65MM")
        self.assertEqual(tubo_para_codigo_tecnico(TuboRoloDiametro.D70), "TUBO_ROLO_70MM")

    def test_codigo_tecnico_para_tubo(self):
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_ROLO_32MM"), TuboRoloDiametro.D32)
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_ROLO_38MM"), TuboRoloDiametro.D38)
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_ROLO_43MM"), TuboRoloDiametro.D43)
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_ROLO_65MM"), TuboRoloDiametro.D65)
        self.assertEqual(codigo_tecnico_para_tubo("TUBO_ROLO_70MM"), TuboRoloDiametro.D70)
        self.assertIsNone(codigo_tecnico_para_tubo("TUBO_ROLO_99MM"))
        self.assertIsNone(codigo_tecnico_para_tubo("INVALIDO"))


class TestCompatibilidadeOrcamentos(unittest.TestCase):
    """Testes de compatibilidade com a função escolher_tubo_rolo do orcamentos.py."""

    def test_escolher_tubo_rolo_retorna_string_compativel(self):
        from modulos.orcamentos import escolher_tubo_rolo

        self.assertEqual(escolher_tubo_rolo(1.50), "32mm")
        self.assertEqual(escolher_tubo_rolo(1.80), "32mm")
        self.assertEqual(escolher_tubo_rolo(1.81), "38mm")
        self.assertEqual(escolher_tubo_rolo(2.20), "38mm")
        self.assertEqual(escolher_tubo_rolo(2.50), "38mm")
        self.assertEqual(escolher_tubo_rolo(2.51), "43mm")
        self.assertEqual(escolher_tubo_rolo(3.20), "43mm")
        self.assertEqual(escolher_tubo_rolo(3.21), "65mm")
        self.assertEqual(escolher_tubo_rolo(4.00), "65mm")
        self.assertEqual(escolher_tubo_rolo(0), "")
        self.assertEqual(escolher_tubo_rolo(None), "")

    def test_kit_por_tubo_rolo_inclui_novos_diametros(self):
        from modulos.orcamentos import kit_por_tubo_rolo

        self.assertEqual(kit_por_tubo_rolo("32mm"), "Kit Comando Ação Premium 32mm")
        self.assertEqual(kit_por_tubo_rolo("38mm"), "Kit Comando Ação Premium 38mm")
        self.assertEqual(kit_por_tubo_rolo("43mm"), "Kit Comando Ação Premium 43mm")
        self.assertEqual(kit_por_tubo_rolo("65mm"), "Kit Comando Ação Premium 65mm")
        self.assertEqual(kit_por_tubo_rolo("70mm"), "Kit Comando Ação Premium 70mm")
        self.assertEqual(kit_por_tubo_rolo(""), "")


class TestCompatibilidadeProdutos(unittest.TestCase):
    """Testes de compatibilidade com chaves_rolo_manual_por_largura do produtos.py."""

    def test_chaves_rolo_manual_por_largura(self):
        from modulos.produtos import chaves_rolo_manual_por_largura

        chaves_base = ["tubo_32", "comando_32", "tubo_38", "comando_38", "tubo_43", "comando_43", "tecido"]

        # <= 1,80: mantém 32, remove 38 e 43
        resultado = chaves_rolo_manual_por_largura(chaves_base, {"largura": 1.50})
        self.assertIn("tubo_32", resultado)
        self.assertIn("comando_32", resultado)
        self.assertNotIn("tubo_38", resultado)
        self.assertNotIn("tubo_43", resultado)

        # 1,81 a 2,50: mantém 38, remove 32 e 43
        resultado = chaves_rolo_manual_por_largura(chaves_base, {"largura": 2.00})
        self.assertIn("tubo_38", resultado)
        self.assertIn("comando_38", resultado)
        self.assertNotIn("tubo_32", resultado)
        self.assertNotIn("tubo_43", resultado)

        # 2,51 a 3,20: mantém 43, remove 32 e 38
        resultado = chaves_rolo_manual_por_largura(chaves_base, {"largura": 2.80})
        self.assertIn("tubo_43", resultado)
        self.assertIn("comando_43", resultado)
        self.assertNotIn("tubo_32", resultado)
        self.assertNotIn("tubo_38", resultado)

        # > 3,20: manual proibido, remove todos
        resultado = chaves_rolo_manual_por_largura(chaves_base, {"largura": 3.50})
        self.assertNotIn("tubo_32", resultado)
        self.assertNotIn("tubo_38", resultado)
        self.assertNotIn("tubo_43", resultado)
        self.assertNotIn("comando_32", resultado)
        self.assertNotIn("comando_38", resultado)
        self.assertNotIn("comando_43", resultado)

        # Sem largura: padrão 32mm
        resultado = chaves_rolo_manual_por_largura(chaves_base, {})
        self.assertIn("tubo_32", resultado)
        self.assertNotIn("tubo_38", resultado)
        self.assertNotIn("tubo_43", resultado)


if __name__ == "__main__":
    unittest.main()