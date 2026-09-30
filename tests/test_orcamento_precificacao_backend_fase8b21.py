from types import SimpleNamespace
from decimal import Decimal
import unittest

from pydantic import ValidationError

from app.schemas.orcamento import OrcamentoInput
from app.services.orcamento_service import _preco_produto


class PrecificacaoBackendFase8B21Test(unittest.TestCase):
    def test_tres_perfis_denver(self):
        produto = SimpleNamespace(custo_final=98.71, valor_custo=98.71, valor_venda=999)
        self.assertEqual(_preco_produto(produto, "DECORADOR"), Decimal("148.07"))
        self.assertEqual(_preco_produto(produto, "VAREJO"), Decimal("197.42"))
        self.assertEqual(_preco_produto(produto, "CONSUMIDOR_FINAL"), Decimal("246.78"))

    def test_tres_perfis_custo_2795(self):
        produto = SimpleNamespace(custo_final=27.95, valor_custo=27.95, valor_venda=999)
        self.assertEqual(_preco_produto(produto, "DECORADOR"), Decimal("41.93"))
        self.assertEqual(_preco_produto(produto, "VAREJO"), Decimal("55.90"))
        self.assertEqual(_preco_produto(produto, "CONSUMIDOR_FINAL"), Decimal("69.88"))

    def test_prioridade_e_fallback(self):
        self.assertEqual(_preco_produto(SimpleNamespace(custo_final=30, valor_custo=20, valor_venda=90), "VAREJO"), Decimal("60.00"))
        self.assertEqual(_preco_produto(SimpleNamespace(custo_final=0, valor_custo=20, valor_venda=90), "VAREJO"), Decimal("40.00"))
        self.assertEqual(_preco_produto(SimpleNamespace(custo_final=0, valor_custo=0, valor_venda=90.125), "VAREJO"), Decimal("90.13"))

    def test_perfil_historico_e_validacao(self):
        self.assertEqual(OrcamentoInput(cliente_id=1).perfil_comercial, "VAREJO")
        with self.assertRaises(ValidationError):
            OrcamentoInput(cliente_id=1, perfil_comercial="ATACADO")


if __name__ == "__main__":
    unittest.main()
