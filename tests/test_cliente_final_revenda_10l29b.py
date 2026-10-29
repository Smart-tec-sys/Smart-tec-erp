"""Persistência ORM em SQLite em memória; nunca usa o banco PostgreSQL real."""
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
from app.models.cliente import ClienteDB
from app.models.produto import ProdutoDB
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB
from app.models.pedido import PedidoDB, PedidoItemDB
from app.schemas.orcamento import OrcamentoInput
from app.schemas.pedido import PedidoUpdate
from app.services import orcamento_service, pedido_service
from app.services.origem_comercial import CLIENTE_FINAL_CAMPOS
from app.tenant.context import TenantContext

@compiles(JSONB, 'sqlite')
def sqlite_jsonb(type_, compiler, **kwargs):
    return 'JSON'

class ClienteFinalTests(unittest.TestCase):
    def setUp(self):
        configure_mappers()
        self.engine = create_engine('sqlite:///:memory:')
        tables = [Base.metadata.tables[name] for name in ['empresas', 'clientes', 'funcionarios', 'produtos', 'orcamentos', 'orcamentos_itens', 'pedidos', 'pedidos_itens']]
        Base.metadata.create_all(self.engine, tables=tables)
        with self.engine.begin() as connection:
            connection.execute(text('CREATE TABLE parceiros_comerciais (id INTEGER PRIMARY KEY, empresa_id INTEGER, ativo BOOLEAN)'))
            connection.execute(text('CREATE TABLE representantes (id INTEGER PRIMARY KEY, empresa_id INTEGER, parceiro_id INTEGER, ativo BOOLEAN)'))
            connection.execute(text('INSERT INTO parceiros_comerciais VALUES (1,1,TRUE)'))
        self.db = Session(self.engine)
        self.tenant = TenantContext(empresa_id=1)
        self.values = dict(zip(CLIENTE_FINAL_CAMPOS, ['Cliente da revenda', '001234', '+55 11 1234', 'final@example.com', 'Rua A, 1']))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def budget(self, **values):
        data = OrcamentoInput(**values)
        budget = OrcamentoDB(empresa_id=1, numero='1004')
        orcamento_service._fill(self.db, budget, data, 1)
        self.db.add(budget)
        self.db.commit()
        self.db.expire_all()
        return budget

    def sale(self, **values):
        values.setdefault('cliente_id', None)
        values.setdefault('parceiro_id', 1)
        sale = PedidoDB(id=2, empresa_id=1, numero='VEN-000002', vendedor_id=10,
                        representante_id=None, total_final=520.33, **values)
        self.db.add(sale)
        self.db.commit()
        return sale

    def test_direct_budget_persists(self):
        budget = self.budget(cliente_id=4)
        self.assertEqual(budget.cliente_id, 4)
        self.assertIsNone(budget.parceiro_id)
        self.assertTrue(all(getattr(budget, key) is None for key in CLIENTE_FINAL_CAMPOS))

    def test_invalid_budgets(self):
        for values, message in [({}, 'Venda direta exige cliente.'),
            ({'cliente_id': 4, 'parceiro_id': 1}, 'Cliente direto e parceiro não podem ser informados ao mesmo tempo.')]:
            with self.assertRaisesRegex(ValueError, message): self.budget(**values)
        for key in CLIENTE_FINAL_CAMPOS:
            with self.assertRaisesRegex(ValueError, 'só pode ser informado'):
                self.budget(cliente_id=4, **{key: 'informado'})

    def test_partner_budget_round_trip(self):
        budget = self.budget(parceiro_id=1, **self.values)
        result = orcamento_service.obter(self.db, budget.id, self.tenant)
        self.assertEqual({key: result[key] for key in CLIENTE_FINAL_CAMPOS}, self.values)
        self.assertIsNone(result['cliente_id'])

    def test_conversion_copies_all_five(self):
        budget = self.budget(parceiro_id=1, status='APROVADO', **self.values)
        budget.itens.append(OrcamentoItemDB(tipo_item='SERVICO', descricao='Instalação', quantidade=1,
                           preco_unitario=520.33, subtotal=520.33, desconto=0))
        budget.total = budget.total_final = 520.33
        self.db.commit()
        result = pedido_service.converter_orcamento(self.db, budget.id, self.tenant)
        self.db.expire_all()
        persisted = pedido_service.obter(self.db, result['id'], self.tenant)
        self.assertEqual({key: persisted[key] for key in CLIENTE_FINAL_CAMPOS}, self.values)
        self.assertEqual(len(persisted['itens']), 1)
        self.assertEqual(float(persisted['total_final']), 520.33)
        self.assertIsNone(persisted['cliente_id'])

    def test_patch_preserves_omitted_and_clears_explicit_null(self):
        sale = self.sale(**self.values)
        pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(observacao='Atualizado'))
        self.db.expire_all()
        self.assertEqual({key: getattr(sale, key) for key in CLIENTE_FINAL_CAMPOS}, self.values)
        pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(cliente_final_telefone=None))
        self.db.expire_all()
        self.assertIsNone(sale.cliente_final_telefone)
        self.assertEqual(sale.cliente_final_nome, self.values['cliente_final_nome'])

    def test_invalid_patch_merged_state(self):
        sale = self.sale()
        with self.assertRaisesRegex(ValueError, 'ao mesmo tempo'):
            pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(cliente_id=4))
        with self.assertRaisesRegex(ValueError, 'Venda direta exige cliente'):
            pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(parceiro_id=None))
        self.assertIsNone(sale.cliente_id)
        self.assertEqual(sale.parceiro_id, 1)

    def test_final_on_direct_sale_rejected(self):
        sale = self.sale(cliente_id=4, parceiro_id=None)
        for key in CLIENTE_FINAL_CAMPOS:
            with self.assertRaisesRegex(ValueError, 'só pode ser informado'):
                pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(**{key: 'texto'}))

    def test_ven2_fixture_remains_valid(self):
        sale = self.sale()
        result = pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate())
        self.assertEqual((result['vendedor_id'], result['parceiro_id'], result['cliente_id'], result['representante_id']), (10, 1, None, None))
        self.assertTrue(all(result[key] is None for key in CLIENTE_FINAL_CAMPOS))
        self.assertEqual(float(result['total_final']), 520.33)

    def test_direct_sale_update_persists(self):
        sale = self.sale(cliente_id=4, parceiro_id=None)
        pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(observacao='Direta'))
        self.db.expire_all()
        self.assertEqual(sale.cliente_id, 4)
        self.assertIsNone(sale.parceiro_id)
        self.assertEqual(sale.observacao, 'Direta')

    def test_partner_sale_update_persists_final(self):
        sale = self.sale()
        result = pedido_service.atualizar(self.db, sale.id, self.tenant, PedidoUpdate(**self.values))
        self.db.expire_all()
        self.assertEqual({key: result[key] for key in CLIENTE_FINAL_CAMPOS}, self.values)
        self.assertIsNone(sale.cliente_id)
        self.assertEqual(sale.parceiro_id, 1)

    def test_tenant_protection(self):
        sale = self.sale()
        self.assertIsNone(pedido_service.atualizar(self.db, sale.id, TenantContext(empresa_id=2), PedidoUpdate(cliente_final_nome='Outro')))
        self.assertIsNone(sale.cliente_final_nome)

if __name__ == '__main__': unittest.main()
