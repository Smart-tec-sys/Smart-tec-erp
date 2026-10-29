"""Venda manual e paridade comercial em SQLite isolado, sem banco real."""
from decimal import Decimal
import unittest
from pydantic import ValidationError
from sqlalchemy import text
from app.models.cliente import ClienteDB
from app.models.produto import ProdutoDB
from app.models.pedido import PedidoDB
from app.schemas.pedido import PedidoCreate, PedidoOut
from app.schemas.orcamento import OrcamentoInput
from app.services import pedido_service, orcamento_service
import test_cliente_final_revenda_10l29b as fixtures
from test_pedido_composicao_comercial_10l5b import FIELDS

class NovaVendaTests(unittest.TestCase):
    tearDown = fixtures.ClienteFinalTests.tearDown
    budget = fixtures.ClienteFinalTests.budget

    def setUp(self):
        fixtures.ClienteFinalTests.setUp(self)
        self.db.add(ClienteDB(id=4, empresa_id=1, tipo="Pessoa física", nome="Cliente direto"))
        self.db.add(ClienteDB(id=5, empresa_id=2, tipo="Pessoa física", nome="Outra empresa"))
        self.db.add(ProdutoDB(id=1, empresa_id=1, nome="Produto unitário", valor_custo=50,
                             modelo_tecnico="COMPONENTE", unidade_venda="UN"))
        self.db.add(ProdutoDB(id=2, empresa_id=2, nome="Outro produto", valor_custo=50))
        self.db.add(ProdutoDB(id=3, empresa_id=1, nome="Rolô", valor_custo=50,
                             modelo_tecnico="ROLO", unidade_venda="M²"))
        self.db.execute(text("INSERT INTO representantes VALUES (3,1,NULL,TRUE)"))
        self.db.execute(text("INSERT INTO representantes VALUES (4,2,NULL,TRUE)"))
        self.db.commit()

    def data(self, **values):
        defaults = dict(cliente_id=4, itens=[dict(tipo_item="SERVICO", descricao="Instalação",
                        quantidade=2, preco_unitario=100, subtotal=999999)])
        defaults.update(values)
        return PedidoCreate(**defaults)

    def create(self, **values):
        return pedido_service.criar(self.db, self.data(**values), self.tenant)

    def test_direct_sale(self):
        result = self.create()
        self.assertEqual(result["cliente_id"], 4)
        self.assertIsNone(result["parceiro_id"])
        self.assertEqual(result["status"], "ABERTO")
        self.assertEqual(result["total"], Decimal("200.00"))
        self.assertEqual(result["itens"][0]["subtotal"], Decimal("200.00"))

    def test_direct_with_independent_representative(self):
        result = self.create(representante_id=3)
        self.assertEqual(result["representante_id"], 3)
        self.assertIsNone(result["parceiro_id"])

    def test_partner_without_representative(self):
        result = self.create(cliente_id=None, parceiro_id=1)
        self.assertEqual(result["parceiro_id"], 1)
        self.assertIsNone(result["cliente_id"])
        self.assertIsNone(result["representante_id"])

    def test_partner_with_independent_representative(self):
        self.assertEqual(self.create(cliente_id=None, parceiro_id=1, representante_id=3)["representante_id"], 3)

    def test_partner_final_client(self):
        result = self.create(cliente_id=None, parceiro_id=1, **self.values)
        for key, value in self.values.items():
            self.assertEqual(result[key], value)

    def test_reject_client_and_partner(self):
        with self.assertRaisesRegex(ValueError, "ao mesmo tempo"):
            self.create(parceiro_id=1)
        self.assertEqual(self.db.query(PedidoDB).count(), 0)

    def test_reject_final_client_on_direct(self):
        for key in self.values:
            with self.assertRaisesRegex(ValueError, "só pode ser informado"):
                self.create(**{key: "Cliente final"})

    def test_reject_missing_origin(self):
        with self.assertRaisesRegex(ValueError, "exige cliente"):
            self.create(cliente_id=None)

    def test_reject_no_items(self):
        with self.assertRaises(ValidationError):
            self.data(itens=[])

    def test_reject_foreign_tenant_product(self):
        with self.assertRaisesRegex(ValueError, "empresa ativa"):
            self.create(itens=[dict(tipo_item="PRODUTO", produto_id=2, descricao="Outro produto")])
        self.assertEqual(self.db.query(PedidoDB).count(), 0)

    def test_reject_foreign_tenant_links(self):
        for values in [dict(cliente_id=5), dict(representante_id=4), dict(vendedor_id=999)]:
            with self.assertRaisesRegex(ValueError, "esta empresa"):
                self.create(**values)

    def test_catalog_price_and_subtotal_are_authoritative(self):
        result = self.create(itens=[dict(tipo_item="PRODUTO", produto_id=1, descricao="Produto",
                                        quantidade=2, preco_unitario=1, subtotal=999999)])
        self.assertEqual(result["itens"][0]["preco_unitario"], Decimal("100.0000"))
        self.assertEqual(result["total"], Decimal("200.00"))
        product = self.db.query(ProdutoDB).filter(ProdutoDB.id == 1).one()
        product.valor_custo = 999
        self.db.commit()
        loaded = pedido_service.obter(self.db, result["id"], self.tenant)
        self.assertEqual(loaded["total"], Decimal("200.00"))
        self.assertEqual(loaded["itens"][0]["preco_unitario"], Decimal("100.0000"))

    def test_partner_calculation(self):
        result = self.create(cliente_id=None, parceiro_id=1, percentual_parceiro=10)
        self.assertEqual(result["valor_parceiro"], Decimal("20.00"))
        self.assertEqual(result["total_cliente_final"], Decimal("220.00"))

    def test_reject_partner_percentage_without_partner(self):
        with self.assertRaisesRegex(ValueError, "Selecione o parceiro"):
            self.create(percentual_parceiro=10)

    def test_rt_percentage(self):
        result = self.create(representante_id=3, incluir_rt=True, tipo_rt="PERCENTUAL", percentual_rt=5)
        self.assertEqual(result["valor_rt"], Decimal("10.00"))
        self.assertEqual(result["total_cliente_final"], Decimal("210.00"))

    def test_rt_fixed(self):
        result = self.create(representante_id=3, incluir_rt=True, tipo_rt="VALOR_FIXO", valor_rt=33.33)
        self.assertEqual(result["valor_rt"], Decimal("33.33"))
        self.assertEqual(result["percentual_rt"], 0)

    def test_bank_fee_inside_calculation(self):
        result = self.create(incluir_taxa_bancaria=True, taxa_bancaria_percentual=10)
        self.assertEqual(result["total_cliente_final"], Decimal("222.22"))
        self.assertEqual(result["valor_taxa_bancaria"], Decimal("22.22"))

    def test_discount(self):
        result = self.create(desconto=20)
        self.assertEqual(result["desconto"], Decimal("20.00"))
        self.assertEqual(result["total_final"], Decimal("180.00"))

    def test_numbering_across_manual_and_conversion(self):
        first = self.create()
        budget = self.budget(cliente_id=4, status="APROVADO", itens=[dict(tipo_item="SERVICO", descricao="Serviço", quantidade=1, preco_unitario=50)])
        converted = pedido_service.converter_orcamento(self.db, budget.id, self.tenant)
        last = self.create()
        for result in (first, converted, last):
            self.assertEqual(result["numero"], f"VEN-{result['id']:06d}")
        self.assertEqual(len({result["numero"] for result in (first, converted, last)}), 3)

    def test_tenant_number_and_computed_totals_cannot_be_supplied(self):
        for field, value in [("empresa_id", 2), ("numero", "VEN-999999"), ("total_final", 1), ("total_cliente_final", 1)]:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.data(**{field: value})

    def test_no_budget_or_financial_generation(self):
        result = self.create()
        self.assertIsNone(result["orcamento_id"])
        # A fixture nem possui tabela financeira: criar não depende dela.
        self.assertEqual(self.db.query(PedidoDB).count(), 1)
        with self.assertRaises(ValidationError):
            self.data(orcamento_id=123)

    def test_persist_all_ten_fields_and_freeze_on_read(self):
        result = self.create(cliente_id=None, parceiro_id=1, representante_id=3, percentual_parceiro=10, desconto=20,
                             incluir_rt=True, tipo_rt="PERCENTUAL", percentual_rt=5,
                             incluir_taxa_bancaria=True, taxa_bancaria_percentual=10)
        self.assertEqual(result["total_cliente_final"], Decimal("230.00"))
        self.assertEqual(result["valor_parceiro"], Decimal("18.00"))
        self.assertEqual(result["valor_rt"], Decimal("9.00"))
        self.assertEqual(result["valor_taxa_bancaria"], Decimal("23.00"))
        self.db.expire_all()
        loaded = pedido_service.obter(self.db, result["id"], self.tenant)
        self.assertEqual({key: loaded[key] for key in FIELDS}, {key: result[key] for key in FIELDS})
        PedidoOut.parse_obj(loaded)

    def test_disabled_fields_saved_explicitly(self):
        result = self.create(representante_id=3, valor_rt=99, percentual_rt=20, taxa_bancaria_percentual=20)
        for key in ("valor_rt", "percentual_rt", "valor_parceiro", "valor_taxa_bancaria", "taxa_bancaria_percentual"):
            self.assertEqual(result[key], 0)
        self.assertIs(result["incluir_rt"], False)
        self.assertIs(result["incluir_taxa_bancaria"], False)
        self.assertIsNone(result["tipo_rt"])

    def test_quantity_price_discount_and_nonfinite_validation(self):
        for key, value in [("quantidade", 0), ("quantidade", -1), ("preco_unitario", -1), ("desconto", -1), ("largura", -1), ("preco_unitario", "NaN")]:
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                self.data(itens=[dict(tipo_item="SERVICO", descricao="Serviço", **{key:value})])

    def test_product_measures_validate_catalog_even_if_payload_spoofed(self):
        for width, quantity in [(0, 1), (1, Decimal("1.5"))]:
            with self.assertRaisesRegex(ValueError, "maiores que zero|inteira"):
                self.create(itens=[dict(tipo_item="PRODUTO", produto_id=3, descricao="Rolô",
                              modelo_tecnico="COMPONENTE", largura=width, altura=1, quantidade=quantity)])

    def test_parity_with_budget_for_three_profiles(self):
        for profile in ("VAREJO", "DECORADOR", "CONSUMIDOR_FINAL"):
            with self.subTest(profile=profile):
                data = self.data(cliente_id=None, parceiro_id=1, representante_id=3, perfil_comercial=profile,
                    percentual_parceiro=12.3456, incluir_rt=True, tipo_rt="PERCENTUAL", percentual_rt=5.4321,
                    incluir_taxa_bancaria=True, taxa_bancaria_percentual=7.2, desconto=12.34,
                    itens=[dict(tipo_item="PRODUTO", produto_id=1, descricao="Produto", quantidade=2, desconto=3.21)])
                sale = pedido_service.criar(self.db, data, self.tenant)
                budget = self.budget(**data.dict(exclude={"data_venda", "prazo_entrega", "canal_venda"}))
                budget.numero = profile
                self.db.commit()
                for key in (*FIELDS, "total", "desconto", "total_final"):
                    self.assertEqual(sale[key], getattr(budget, key))

    def test_transaction_rolls_back_after_later_item_failure(self):
        with self.assertRaises(ValueError):
            self.create(itens=[dict(tipo_item="SERVICO", descricao="Válido", preco_unitario=20),
                              dict(tipo_item="PRODUTO", produto_id=2, descricao="Inválido")])
        self.assertEqual(self.db.query(PedidoDB).count(), 0)

if __name__ == "__main__":
    unittest.main()
