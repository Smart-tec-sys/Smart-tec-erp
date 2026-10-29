import unittest
from app.schemas.pedido import PedidoUpdate
from app.services import pedido_service
import test_pedido_criacao_manual_10l6 as fixtures

class RegraRTTests(unittest.TestCase):
    setUp = fixtures.NovaVendaTests.setUp
    tearDown = fixtures.NovaVendaTests.tearDown
    data = fixtures.NovaVendaTests.data
    create = fixtures.NovaVendaTests.create

    def test_without_representative_without_rt(self):
        result = self.create()
        self.assertFalse(result['incluir_rt'])
        self.assertEqual(result['valor_rt'], 0)

    def test_without_representative_rejects_active_or_residual_rt(self):
        for values in [dict(incluir_rt=True, tipo_rt='PERCENTUAL', percentual_rt=5),
                       dict(valor_rt=10), dict(percentual_rt=5)]:
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, 'representante'):
                self.create(**values)

    def test_representative_percentage(self):
        result = self.create(representante_id=3, incluir_rt=True, tipo_rt='PERCENTUAL', percentual_rt=5)
        self.assertEqual(result['valor_rt'], 10)

    def test_representative_fixed(self):
        result = self.create(representante_id=3, incluir_rt=True, tipo_rt='VALOR_FIXO', valor_rt=33)
        self.assertEqual(result['valor_rt'], 33)

    def test_patch_cannot_remove_representative_with_rt(self):
        result = self.create(representante_id=3, incluir_rt=True, tipo_rt='PERCENTUAL', percentual_rt=5)
        with self.assertRaisesRegex(ValueError, 'representante'):
            pedido_service.atualizar(self.db, result['id'], self.tenant, PedidoUpdate(representante_id=None))
        self.db.rollback()
        loaded = pedido_service.obter(self.db, result['id'], self.tenant)
        self.assertEqual(loaded['representante_id'], 3)
        self.assertEqual(loaded['valor_rt'], 10)

    def test_patch_cannot_activate_rt_without_representative(self):
        result = self.create()
        with self.assertRaisesRegex(ValueError, 'representante'):
            pedido_service.atualizar(self.db, result['id'], self.tenant, PedidoUpdate(incluir_rt=True))
        self.db.rollback()

    def test_remove_representative_without_rt(self):
        result = self.create(representante_id=3)
        updated = pedido_service.atualizar(self.db, result['id'], self.tenant, PedidoUpdate(representante_id=None))
        self.assertIsNone(updated['representante_id'])

if __name__ == '__main__': unittest.main()
