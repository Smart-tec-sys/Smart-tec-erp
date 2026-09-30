import unittest
from unittest.mock import patch

from modulos import orcamentos


class OrcamentoPrecificacaoFase7STest(unittest.TestCase):
    TABELAS = [
        {"nome": "Decorador", "lucro": 50.0, "ordem": 1},
        {"nome": "Varejo", "lucro": 100.0, "ordem": 2},
        {"nome": "Consumidor final", "lucro": 150.0, "ordem": 3},
    ]

    def test_tres_perfis_com_custo_conhecido(self):
        produto = {"custo_final": 27.95, "valor_custo": 27.95, "valor_venda": 999.0}
        with patch.object(orcamentos, "carregar_tabelas_venda_orcamento", return_value=self.TABELAS):
            self.assertEqual(orcamentos.calcular_valor_produto_por_tipo_venda(produto, "Decorador"), 41.93)
            self.assertEqual(orcamentos.calcular_valor_produto_por_tipo_venda(produto, "Varejo"), 55.90)
            self.assertEqual(orcamentos.calcular_valor_produto_por_tipo_venda(produto, "Consumidor final"), 69.88)

    def test_custo_final_tem_prioridade_sobre_valor_custo(self):
        produto = {"custo_final": 30.0, "valor_custo": 20.0, "valor_venda": 90.0}
        with patch.object(orcamentos, "carregar_tabelas_venda_orcamento", return_value=self.TABELAS):
            self.assertEqual(orcamentos.calcular_valor_produto_por_tipo_venda(produto, "Varejo"), 60.0)

    def test_cor_nao_ocupa_detalhes(self):
        self.assertEqual(orcamentos.extrair_detalhe_registro({"cor": "Azul"}), "")
        self.assertEqual(orcamentos.cor_estruturada_produto({"cor_componente": "Azul"}), "Azul")

    def test_troca_sku_preserva_familia_e_usa_cor_estruturada(self):
        atual = {"id": 1, "familia_tecnica": "FAM_TESTE", "varia_cor": True, "cor_componente": "Branco", "ativo": True}
        preto = {"id": 2, "familia_tecnica": "FAM_TESTE", "varia_cor": True, "variacao_cor": "Preto", "ativo": True}
        outra = {"id": 3, "familia_tecnica": "OUTRA", "varia_cor": True, "cor": "Preto", "ativo": True}
        self.assertIs(
            orcamentos.procurar_substituto_mesma_familia_cor_orcamento([outra, preto, atual], atual, "Preto"),
            preto,
        )

    def test_familia_final_multicor_inequivoca_habilita_troca_sem_flag_historica(self):
        branco = {"id": 10, "familia_tecnica": "ROLO_TESTE", "varia_cor": False, "cor": "Branco", "ativo": True}
        bege = {"id": 11, "familia_tecnica": "ROLO_TESTE", "varia_cor": False, "cor": "Bege", "ativo": True}
        produtos = [branco, bege]
        self.assertEqual(orcamentos.opcoes_cor_familia_orcamento(produtos, branco), ["Bege", "Branco"])
        self.assertIs(orcamentos.procurar_substituto_mesma_familia_cor_orcamento(produtos, branco, "Bege"), bege)

    def test_familia_com_cor_duplicada_nao_habilita_troca_ambigua(self):
        atual = {"id": 20, "familia_tecnica": "FAM_AMBIGUA", "varia_cor": False, "cor": "Branco", "ativo": True}
        duplicado = {"id": 21, "familia_tecnica": "FAM_AMBIGUA", "varia_cor": False, "cor": "Branco", "ativo": True}
        preto = {"id": 22, "familia_tecnica": "FAM_AMBIGUA", "varia_cor": False, "cor": "Preto", "ativo": True}
        produtos = [atual, duplicado, preto]
        self.assertEqual(orcamentos.opcoes_cor_familia_orcamento(produtos, atual), [])
        self.assertIsNone(orcamentos.procurar_substituto_mesma_familia_cor_orcamento(produtos, atual, "Preto"))

    def test_flag_historico_nao_contorna_ambiguidade(self):
        atual = {"id": 30, "familia_tecnica": "FAM_AMBIGUA", "varia_cor": True, "cor": "Branco", "ativo": True}
        duplicado = {"id": 31, "familia_tecnica": "FAM_AMBIGUA", "varia_cor": True, "cor": "Branco", "ativo": True}
        preto = {"id": 32, "familia_tecnica": "FAM_AMBIGUA", "varia_cor": True, "cor": "Preto", "ativo": True}
        self.assertIsNone(orcamentos.procurar_substituto_mesma_familia_cor_orcamento([atual, duplicado, preto], atual, "Preto"))

    def test_familias_finais_multicor_habilitam_rolo_romana_e_double_vision(self):
        for modelo in ["Rolô", "Romana", "Double Vision"]:
            branco = {"id": 40, "nome": modelo + " Branco", "modelo_tecnico": modelo, "familia_tecnica": "FAM_" + modelo, "varia_cor": False, "cor": "Branco", "ativo": True, "custo_final": 10}
            preto = {"id": 41, "nome": modelo + " Preto", "modelo_tecnico": modelo, "familia_tecnica": "FAM_" + modelo, "varia_cor": False, "cor": "Preto", "ativo": True, "custo_final": 20}
            produtos = [branco, preto]
            self.assertEqual(orcamentos.opcoes_cor_familia_orcamento(produtos, branco), ["Branco", "Preto"])
            selecionado = orcamentos.procurar_substituto_mesma_familia_cor_orcamento(produtos, branco, "Preto")
            self.assertIs(selecionado, preto)
            with patch.object(orcamentos, "carregar_tabelas_venda_orcamento", return_value=self.TABELAS):
                self.assertEqual(orcamentos.calcular_valor_produto_por_tipo_venda(selecionado, "Varejo"), 40.0)


if __name__ == "__main__":
    unittest.main()
