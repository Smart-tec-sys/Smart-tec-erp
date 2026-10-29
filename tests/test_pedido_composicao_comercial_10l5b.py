"""Composição histórica de pedidos; testes usam apenas SQLite em memória."""
from decimal import Decimal
import unittest
import test_cliente_final_revenda_10l29b as fixtures
from app.models.orcamento import OrcamentoItemDB
from app.schemas.pedido import PedidoOut, PedidoUpdate
from app.services import pedido_service

FIELDS = ("percentual_parceiro", "incluir_rt", "tipo_rt", "percentual_rt", "valor_rt",
          "incluir_taxa_bancaria", "taxa_bancaria_percentual", "valor_parceiro",
          "valor_taxa_bancaria", "total_cliente_final")

class ComposicaoTests(unittest.TestCase):
    setUp = fixtures.ClienteFinalTests.setUp
    tearDown = fixtures.ClienteFinalTests.tearDown
    budget = fixtures.ClienteFinalTests.budget
    sale = fixtures.ClienteFinalTests.sale

    def convert(self, **values):
        budget = self.budget(parceiro_id=1, status="APROVADO")
        budget.itens.append(OrcamentoItemDB(tipo_item="SERVICO", descricao="Instalação",
            quantidade=1, preco_unitario=1000, subtotal=1000, desconto=0))
        budget.total = Decimal("1000.00")
        budget.desconto = Decimal("20.00")
        budget.total_final = Decimal("980.00")
        for key, value in values.items():
            setattr(budget, key, value)
        self.db.commit()
        expected = {key: getattr(budget, key) for key in FIELDS}
        result = pedido_service.converter_orcamento(self.db, budget.id, self.tenant)
        self.db.expire_all()
        persisted = pedido_service.obter(self.db, result["id"], self.tenant)
        for response in (result, persisted):
            self.assertEqual({key: response[key] for key in FIELDS}, expected)
            self.assertEqual(response["total"], Decimal("1000.00"))
            self.assertEqual(response["desconto"], Decimal("20.00"))
            self.assertEqual(response["total_final"], Decimal("980.00"))
            self.assertEqual(response["itens"][0]["subtotal"], Decimal("1000.00"))
            PedidoOut.parse_obj(response)
        return persisted

    def test_conversion_freezes_partner_rt_and_bank_saved_values(self):
        # Montantes salvos deliberadamente diferentes de uma fórmula atual:
        # qualquer recálculo durante a conversão violaria o histórico.
        result = self.convert(percentual_parceiro=Decimal("12.3456"), incluir_rt=True,
            tipo_rt="PERCENTUAL", percentual_rt=Decimal("5.4321"), valor_rt=Decimal("54.32"),
            incluir_taxa_bancaria=True, taxa_bancaria_percentual=Decimal("7.2000"),
            valor_parceiro=Decimal("123.45"), valor_taxa_bancaria=Decimal("89.76"),
            total_cliente_final=Decimal("1247.53"))
        self.assertTrue(result["incluir_rt"])
        self.assertTrue(result["incluir_taxa_bancaria"])

    def test_conversion_preserves_explicit_zero_and_false(self):
        values = {key: Decimal("0") for key in FIELDS}
        values.update(incluir_rt=False, incluir_taxa_bancaria=False, tipo_rt=None,
                      total_cliente_final=Decimal("980.00"))
        result = self.convert(**values)
        self.assertIs(result["incluir_rt"], False)
        self.assertIs(result["incluir_taxa_bancaria"], False)

    def test_historical_null_in_detail_list_and_schemas(self):
        sale = self.sale()
        detail = pedido_service.obter(self.db, sale.id, self.tenant)
        listing = pedido_service.listar(self.db, self.tenant)
        for response in (detail, listing[0]):
            self.assertTrue(all(response[key] is None for key in FIELDS))
            parsed = PedidoOut.parse_obj(response)
            self.assertTrue(all(getattr(parsed, key) is None for key in FIELDS))
        update = PedidoUpdate(**{key: None for key in FIELDS})
        result = pedido_service.atualizar(self.db, sale.id, self.tenant, update)
        self.assertTrue(all(result[key] is None for key in FIELDS))

    def test_patch_preserves_omitted_composition_and_updates_only_provided(self):
        values = {key: Decimal("12.34") for key in FIELDS}
        values.update(incluir_rt=True, incluir_taxa_bancaria=True, tipo_rt="VALOR_FIXO")
        self.db.execute(fixtures.text('INSERT INTO representantes VALUES (3,1,NULL,TRUE)'))
        sale = self.sale(**values)
        sale.representante_id = 3
        self.db.commit()
        expected = {key: getattr(sale, key) for key in FIELDS}
        result = pedido_service.atualizar(self.db, sale.id, self.tenant,
                                          PedidoUpdate(observacao="Alterada"))
        self.assertEqual({key: result[key] for key in FIELDS}, expected)
        result = pedido_service.atualizar(self.db, sale.id, self.tenant,
                                          PedidoUpdate(valor_rt=Decimal("33.21")))
        expected["valor_rt"] = Decimal("33.21")
        self.assertEqual({key: result[key] for key in FIELDS}, expected)
        result = pedido_service.atualizar(self.db, sale.id, self.tenant,
                                          PedidoUpdate(valor_rt=None))
        expected["valor_rt"] = None
        self.assertEqual({key: result[key] for key in FIELDS}, expected)
        self.db.expire_all()
        self.assertEqual({key: getattr(sale, key) for key in FIELDS}, expected)

if __name__ == "__main__":
    unittest.main()
