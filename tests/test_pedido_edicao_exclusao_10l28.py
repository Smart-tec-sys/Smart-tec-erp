import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from decimal import Decimal
from pydantic import ValidationError
from app.models.cliente import ClienteDB
from app.models.produto import ProdutoDB
from app.services import pedido_service as service
from app.schemas.pedido import PedidoUpdate
from sqlalchemy.orm import configure_mappers


class PedidoTests(unittest.TestCase):
    def setUp(self):
        configure_mappers()
        self.db = MagicMock()
        self.tenant = SimpleNamespace(empresa_id=1)
        self.order = SimpleNamespace(id=2, numero='VEN-000002', empresa_id=1,
            vendedor_id=10, parceiro_id=1, representante_id=None, cliente_id=None,
            total_final=Decimal('520.33'), itens=[object()], orcamento_id=1004)

    def test_update_preserves_commercial_links_items_totals(self):
        item = self.order.itens[0]
        with patch.object(service, '_pedido_para_alteracao', return_value=self.order), patch.object(service, '_pedido_dict', return_value={'id': 2}):
            service.atualizar(self.db, 2, self.tenant, PedidoUpdate(observacao='Teste'))
        self.assertEqual(self.order.observacao, 'Teste')
        self.assertEqual((self.order.vendedor_id, self.order.parceiro_id, self.order.representante_id), (10, 1, None))
        self.assertEqual(self.order.total_final, Decimal('520.33'))
        self.assertIs(self.order.itens[0], item)
        self.assertEqual(self.order.orcamento_id, 1004)

    def test_unknown_fields_forbidden(self):
        for field in ['itens', 'total_final', 'empresa_id', 'orcamento_id']:
            with self.assertRaises(ValidationError): PedidoUpdate(**{field: 1})

    def test_foreign_tenant_link_rejected(self):
        self.db.execute.return_value.first.return_value = None
        for field in ['cliente_id', 'vendedor_id', 'parceiro_id', 'representante_id']:
            with patch.object(service, '_pedido_para_alteracao', return_value=self.order):
                with self.assertRaises(ValueError): service.atualizar(self.db, 2, self.tenant, PedidoUpdate(**{field: 9}))
        self.db.commit.assert_not_called()

    def test_null_removes_only_requested_link(self):
        with patch.object(service, '_pedido_para_alteracao', return_value=self.order), patch.object(service, '_pedido_dict', return_value={}):
            service.atualizar(self.db, 2, self.tenant, PedidoUpdate(parceiro_id=None, cliente_id=4))
        self.assertIsNone(self.order.parceiro_id)
        self.assertEqual(self.order.vendedor_id, 10)

    def test_invalid_status_profile(self):
        for data in [PedidoUpdate(status='INVALIDO'), PedidoUpdate(perfil_comercial=None)]:
            with patch.object(service, '_pedido_para_alteracao', return_value=self.order):
                with self.assertRaises(ValueError): service.atualizar(self.db, 2, self.tenant, data)

    def test_tenant_filter_and_lock(self):
        service._pedido_para_alteracao(self.db, 2, self.tenant)
        filters = self.db.query.return_value.filter.call_args.args
        self.assertIn('pedidos.empresa_id', str(filters[1]))
        self.assertEqual(filters[1].right.value, 1)
        self.db.query.return_value.filter.return_value.with_for_update.assert_called_once()

    def test_missing_update_delete(self):
        with patch.object(service, '_pedido_para_alteracao', return_value=None):
            self.assertIsNone(service.atualizar(self.db, 2, self.tenant, PedidoUpdate()))
            self.assertFalse(service.remover(self.db, 2, self.tenant))
        self.db.delete.assert_not_called()

    def test_origin_blocks_reconversion(self):
        with patch.object(service, '_pedido_para_alteracao', return_value=self.order), patch.object(service, '_verificar_vinculos_exclusao'):
            with self.assertRaisesRegex(ValueError, 'segunda conversão'): service.remover(self.db, 2, self.tenant)
        self.db.delete.assert_not_called()

    def test_safe_delete(self):
        self.order.orcamento_id = None
        with patch.object(service, '_pedido_para_alteracao', return_value=self.order), patch.object(service, '_verificar_vinculos_exclusao'):
            self.assertTrue(service.remover(self.db, 2, self.tenant))
        self.db.delete.assert_called_once_with(self.order)
        self.db.commit.assert_called_once()

    def test_financial_and_operational_links_block(self):
        for table in ['financeiro', 'representantes_rt', 'ordens_servico']:
            inspector = MagicMock()
            inspector.get_schema_names.return_value = ['public']
            inspector.get_table_names.return_value = [table]
            inspector.get_columns.return_value = [{'name': 'pedido_id'}]
            inspector.get_foreign_keys.return_value = []
            self.db.get_bind.return_value.dialect.identifier_preparer.quote.side_effect = lambda value: value
            self.db.execute.return_value.first.return_value = (1,)
            with patch('sqlalchemy.inspect', return_value=inspector), patch.object(service, '_pedido_para_alteracao', return_value=self.order):
                with self.assertRaisesRegex(ValueError, 'vinculado'): service.remover(self.db, 2, self.tenant)
            self.db.delete.assert_not_called()


if __name__ == '__main__': unittest.main()
