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
        empresa.configuracoes = {"fiscal_nfe": {"crt": "1", "uf": "SP"}}
        db.query.return_value.filter.return_value.first.side_effect = [empresa, cliente]
        db.query.return_value.filter.return_value.all.side_effect = [
            [SimpleNamespace(id=1), SimpleNamespace(id=2)], []
        ]
        result = preparar_venda_nfe(db, 17, SimpleNamespace(empresa_id=7))
        self.assertEqual(result["empresa_id"], 7)
        self.assertEqual(result["pedido_id"], 17)
        self.assertEqual(db.query.call_count, 4)
        self.assertEqual(result["cadastros_fiscais"]["total_skus"], 2)
        self.assertEqual(result["cadastros_fiscais"]["skus_sem_cadastro"], [1, 2])
        self.assertIn("ITEM_NCM", {p["codigo"] for p in result["pendencias"]})
        # Cada consulta SQLAlchemy inclui filtro (tenant para empresa, cliente e produto).
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

    def test_sem_id_valido_nao_consulta_fiscal_produtos(self):
        from app.services.fiscal_nfe_cadastros import conferir_cadastros_fiscais
        pedido = sample_pedido()
        pedido["itens"] = [{"tipo_item": "SERVICO", "produto_id": None}]
        empresa = SimpleNamespace(configuracoes={"fiscal_nfe": {"crt": "1", "uf": "SP"}})
        db = Mock()
        pendencias, resumo = conferir_cadastros_fiscais(db, pedido, empresa, 7)
        self.assertEqual(resumo["total_skus"], 0)
        self.assertEqual(resumo["skus_sem_cadastro"], [])
        db.query.assert_not_called()
        self.assertIn("REGRAS_TRIBUTARIAS_NAO_VALIDADAS",
                      {p["codigo"] for p in pendencias})

    def test_registro_fiscal_de_outro_tenant_ignorado(self):
        from app.services.fiscal_nfe_cadastros import conferir_cadastros_fiscais
        pedido = sample_pedido()
        empresa = SimpleNamespace(configuracoes={"fiscal_nfe": {"crt": "3", "uf": "SP"}})
        db = Mock()
        db.query.return_value.filter.return_value.all.side_effect = [
            [SimpleNamespace(id=1), SimpleNamespace(id=2)],
            [SimpleNamespace(empresa_id=99, produto_id=1), SimpleNamespace(empresa_id=7, produto_id=2,
                 ncm="63039200", cfop_padrao_saida="5102", cest=None, origem_mercadoria="0",
                 cst_icms="00", csosn=None, cst_pis="01", cst_cofins="01",
                 cst_ibs_cbs="000", cclass_trib_ibs_cbs="000001")],
        ]
        pendencias, resumo = conferir_cadastros_fiscais(db, pedido, empresa, 7)
        self.assertEqual(resumo["skus_com_cadastro"], 1)
        self.assertEqual(resumo["skus_sem_cadastro"], [1])
        self.assertTrue(any(p["campo"] == "fiscal.produtos[1].ncm" for p in pendencias))
        self.assertFalse(any(p["campo"] == "fiscal.produtos[2].ncm" for p in pendencias))

    def test_cadastros_completos_ainda_nao_liberam_emissao(self):
        from app.services.fiscal_nfe_cadastros import conferir_cadastros_fiscais
        empresa = SimpleNamespace(configuracoes={"fiscal_nfe": {
            "crt": "3", "inscricao_estadual": "ISENTO", "uf": "SP",
            "municipio_codigo_ibge": "3550308", "cidade": "São Paulo",
            "cep": "01001000", "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "serie_nfe": 1, "ambiente": "HOMOLOGACAO",
        }})
        pedido = sample_pedido()
        db = Mock()
        db.query.return_value.filter.return_value.all.side_effect = [
            [SimpleNamespace(id=1), SimpleNamespace(id=2)],
            [SimpleNamespace(empresa_id=7, produto_id=i,
                 ncm="63039200", cfop_padrao_saida="5102", cest=None, origem_mercadoria="0",
                 cst_icms="00", csosn=None, cst_pis="01", cst_cofins="01",
                 cst_ibs_cbs="000", cclass_trib_ibs_cbs="000001") for i in (1, 2)],
        ]
        pendencias, resumo = conferir_cadastros_fiscais(db, pedido, empresa, 7)
        self.assertEqual(resumo["skus_com_cadastro"], 2)
        self.assertEqual(resumo["skus_sem_cadastro"], [])
        self.assertIn("REGRAS_TRIBUTARIAS_NAO_VALIDADAS",
                      {p["codigo"] for p in pendencias})


if __name__ == "__main__":
    unittest.main()
