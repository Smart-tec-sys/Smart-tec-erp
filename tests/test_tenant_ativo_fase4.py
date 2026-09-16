"""Segurança tenant-aware dos quatro módulos ativados na Fase 4."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.models.cliente import ClienteDB
from app.models.fornecedor import FornecedorDB
from app.models.orcamento import OrcamentoDB
from app.models.produto import ProdutoDB
from app.schemas.produto import ProdutoCreate
from app.services import cliente_service, fornecedor_service, orcamento_service, produto_service
from app.technical.catalog import TECHNICAL_CATALOG
from app.tenant.context import LEGACY_UNSCOPED, TenantContext
from app.tenant.dependencies import DEV_TENANT_ID, get_current_tenant
from app.tenant.isolation import TenantContextRequiredError
from app.tenant.session import tenant_cache_key


def _value(expression):
    return getattr(getattr(expression, "right", None), "value", None)


class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *conditions):
        for condition in conditions:
            key = getattr(getattr(condition, "left", None), "key", None)
            value = _value(condition)
            if key:
                self.rows = [row for row in self.rows if getattr(row, key, None) == value]
        return self

    def order_by(self, *_): return self
    def offset(self, value): self.rows = self.rows[value:]; return self
    def limit(self, value): self.rows = self.rows[:value]; return self
    def options(self, *_): return self
    def with_for_update(self): return self
    def all(self): return self.rows
    def first(self): return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, mapping):
        self.mapping = mapping
        self.deleted = []

    def query(self, model): return FakeQuery(self.mapping.setdefault(model, []))
    def add(self, item): self.mapping.setdefault(type(item), []).append(item)
    def delete(self, item): self.deleted.append(item); self.mapping[type(item)].remove(item)
    def commit(self): pass
    def rollback(self): pass
    def refresh(self, _): pass


class TenantAtivoFase4Test(unittest.TestCase):
    def setUp(self):
        self.tenant_a = TenantContext(empresa_id=1)
        self.tenant_b = TenantContext(empresa_id=999999)
        self.produto = ProdutoDB(id=10, nome="Produto A", empresa_id=1)
        self.fornecedor = FornecedorDB(id=20, nome="Fornecedor A", tipo="PJ", empresa_id=1)
        self.cliente = ClienteDB(id=30, nome="Cliente A", tipo="PF", empresa_id=1)
        self.orcamento = OrcamentoDB(id=40, numero="1", cliente_id=30, empresa_id=1)
        self.orcamento.cliente = self.cliente
        self.orcamento.itens = []
        self.db = FakeSession({
            ProdutoDB: [self.produto], FornecedorDB: [self.fornecedor],
            ClienteDB: [self.cliente], OrcamentoDB: [self.orcamento],
        })

    def test_tenant_a_ve_recursos_e_tenant_b_nao(self):
        self.assertEqual(len(produto_service.get_all(self.db, self.tenant_a)), 1)
        self.assertEqual(produto_service.get_all(self.db, self.tenant_b), [])
        self.assertEqual(len(fornecedor_service.get_all(self.db, self.tenant_a)), 1)
        self.assertEqual(fornecedor_service.get_all(self.db, self.tenant_b), [])
        self.assertEqual(len(cliente_service.get_all(self.db, self.tenant_a)), 1)
        self.assertEqual(cliente_service.get_all(self.db, self.tenant_b), [])
        self.assertEqual(len(orcamento_service.listar(self.db, self.tenant_a)), 1)
        self.assertEqual(orcamento_service.listar(self.db, self.tenant_b), [])

    def test_get_by_id_update_e_delete_validam_ownership(self):
        self.assertIsNone(produto_service.get_by_id(self.db, 10, self.tenant_b))
        data = ProdutoCreate(nome="Alterado")
        self.assertIsNone(produto_service.update(self.db, 10, data, self.tenant_b))
        self.assertFalse(produto_service.delete(self.db, 10, self.tenant_b))
        self.assertEqual(self.produto.nome, "Produto A")

    def test_create_deriva_empresa_do_contexto(self):
        created = produto_service.create(self.db, ProdutoCreate(nome="Novo"), self.tenant_b)
        self.assertEqual(created.empresa_id, 999999)

    def test_legacy_unscoped_e_bloqueado(self):
        with self.assertRaises(TenantContextRequiredError):
            produto_service.get_all(self.db, LEGACY_UNSCOPED)

    def test_cache_e_resolucao_dev_incluem_tenant(self):
        self.assertEqual(tenant_cache_key(self.tenant_a, "produtos"), ("tenant", 1, "produtos"))
        with patch.dict(os.environ, {"SMARTTEC_ENV": "development"}, clear=False):
            self.assertEqual(get_current_tenant().empresa_id, DEV_TENANT_ID)

    def test_nucleo_tecnico_permanece_global(self):
        self.assertIn("TECIDO_ROLO", TECHNICAL_CATALOG)
        self.assertNotIn("empresa_id", vars(TECHNICAL_CATALOG["TECIDO_ROLO"]))


if __name__ == "__main__":
    unittest.main()
