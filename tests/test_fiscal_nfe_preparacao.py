"""Pré-validação NF-e: testes sem banco, certificado ou rede."""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.fiscal_nfe_preparacao import (
    analisar_venda_nfe,
    preparar_venda_nfe,
    _valid_document,
)

CNPJ_OK = "11.222.333/0001-81"
CPF_OK = "529.982.247-25"


def sample_pedido():
    return {
        "id": 17, "numero": "VEN-000017", "cliente_id": 8, "total": Decimal("100.00"),
        "desconto": Decimal("0.00"), "total_final": Decimal("100.00"),
        "total_cliente_final": Decimal("150.00"),
        "itens": [
            {"tipo_item": "PRODUTO", "produto_id": 1, "descricao": "Persiana Rolô",
             "quantidade": Decimal("2"), "subtotal": Decimal("50")},
            {"tipo_item": "PRODUTO", "produto_id": 2, "descricao": "Persiana Romana",
             "quantidade": Decimal("1"), "subtotal": Decimal("50")},
        ],
    }


def recipient():
    return {
        "nome": "Cliente fictício", "documento": CPF_OK,
        "cep": "01001000", "logradouro": "Rua Exemplo", "numero": "12",
        "bairro": "Centro", "cidade": "São Paulo", "estado": "SP",
    }


class FiscalTests(unittest.TestCase):
    def test_cpf_cnpj_digitos_verificadores(self):
        self.assertTrue(_valid_document(CPF_OK))
        self.assertTrue(_valid_document(CNPJ_OK))
        self.assertFalse(_valid_document("111.111.111-11"))
        self.assertFalse(_valid_document("00.000.000/0000-00"))

    def test_pedido_consistente_nunca_esta_apto_para_emitir(self):
        result = analisar_venda_nfe(sample_pedido(), {"id": 1, "documento": CNPJ_OK}, recipient())
        self.assertEqual(result["estado"], "NAO_APTO_EMISSAO")
        self.assertFalse(result["transmitido"])
        self.assertTrue(result["simulacao"])
        self.assertFalse(any(p["codigo"].startswith("DIVERGENCIA") for p in result["pendencias"]))
        self.assertIn("CONFIGURACAO_TRIBUTARIA", {p["codigo"] for p in result["pendencias"]})
        self.assertIn("BASE_FATURAMENTO_A_DEFINIR", {p["codigo"] for p in result["pendencias"]})
        self.assertNotIn("valor_parceiro", result["resumo"])
        self.assertNotIn("observacao_interna", result)

    def test_divergencia_dez_reais(self):
        pedido = sample_pedido()
        pedido["itens"][1]["subtotal"] = Decimal("40")
        result = analisar_venda_nfe(pedido, {"id": 1, "documento": CNPJ_OK}, recipient())
        self.assertEqual(result["resumo"]["soma_subtotais"], "90.00")
        self.assertIn("DIVERGENCIA_ITENS", {p["codigo"] for p in result["pendencias"]})

    def test_desconto_nao_concilia(self):
        pedido = sample_pedido()
        pedido["total_final"] = Decimal("90")
        result = analisar_venda_nfe(pedido, {"id": 1, "documento": CNPJ_OK}, recipient())
        self.assertIn("DIVERGENCIA_DESCONTO", {p["codigo"] for p in result["pendencias"]})

    def test_sem_destinatario_bloqueia(self):
        result = analisar_venda_nfe(sample_pedido(), {"id": 1, "documento": CNPJ_OK}, None)
        self.assertIn("DESTINATARIO", {p["codigo"] for p in result["pendencias"]})

    def test_servicos_nao_sao_nfe_de_produtos(self):
        pedido = sample_pedido()
        pedido["itens"][0]["tipo_item"] = "SERVICO"
        result = analisar_venda_nfe(pedido, {"id": 1, "documento": CNPJ_OK}, recipient())
        self.assertIn("SERVICO_NA_NFE", {p["codigo"] for p in result["pendencias"]})

    @patch("app.services.fiscal_nfe_preparacao.pedido_service.obter")
    def test_venda_de_outra_empresa_retorna_nao_encontrada(self, obter):
        obter.return_value = None
        db = Mock()
        result = preparar_venda_nfe(db, 17, SimpleNamespace(empresa_id=2))
        self.assertIsNone(result)
        obter.assert_called_once()
        db.query.assert_not_called()

    @patch("app.services.fiscal_nfe_preparacao.pedido_service.obter")
    def test_destinatario_sempre_consultado_no_tenant(self, obter):
        obter.return_value = sample_pedido()
        empresa = SimpleNamespace(id=7, documento=CNPJ_OK)
        cliente = SimpleNamespace(**recipient())
        db = Mock()
        db.query.return_value.filter.return_value.first.side_effect = [empresa, cliente]
        result = preparar_venda_nfe(db, 17, SimpleNamespace(empresa_id=7))
        self.assertEqual(result["empresa_id"], 7)
        self.assertEqual(result["pedido_id"], 17)
        self.assertEqual(db.query.call_count, 2)
        # Critério do SQLAlchemy fica ligado ao tenant para empresa e cliente.
        for clause_call in db.query.return_value.filter.call_args_list:
            self.assertTrue(clause_call.args)

    def test_dados_malformados_nao_emitem(self):
        pedido = sample_pedido()
        pedido["total"] = "NaN"
        pedido["itens"][0]["subtotal"] = "-10"
        result = analisar_venda_nfe(pedido, {"id": 1, "documento": ""}, recipient())
        codes = {p["codigo"] for p in result["pendencias"]}
        self.assertIn("EMITENTE_CNPJ", codes)
        self.assertIn("TOTAIS_INVALIDOS", codes)
        self.assertIn("SUBTOTAL_INVALIDO", codes)
        self.assertEqual(result["estado"], "NAO_APTO_EMISSAO")


if __name__ == "__main__":
    unittest.main()
