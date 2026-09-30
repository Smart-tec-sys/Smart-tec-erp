import unittest

from app.models.equivalencia_tecnica import EmpresaEquivalenciaTecnicaDB
from app.models.fornecedor import FornecedorDB
from app.models.produto import ProdutoDB
from app.schemas.equivalencia_tecnica import EquivalenciaTecnicaCreate, EquivalenciaTecnicaUpdate
from app.services import equivalencia_tecnica_service as service
from app.tenant.context import LEGACY_UNSCOPED, TenantContext
from app.tenant.isolation import TenantContextRequiredError


def _value(expression):
    return getattr(getattr(expression, "right", None), "value", None)


class FakeQuery:
    def __init__(self, rows): self.rows = list(rows)
    def filter(self, *conditions):
        for condition in conditions:
            key = getattr(getattr(condition, "left", None), "key", None)
            value = _value(condition)
            if key:
                self.rows = [row for row in self.rows if getattr(row, key, None) == value]
        return self
    def order_by(self, *_): return self
    def all(self): return self.rows
    def first(self): return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, mapping): self.mapping = mapping; self.next_id = 100
    def query(self, model): return FakeQuery(self.mapping.setdefault(model, []))
    def add(self, row):
        if row.id is None: row.id = self.next_id; self.next_id += 1
        self.mapping.setdefault(type(row), []).append(row)
    def commit(self): pass
    def refresh(self, _): pass
    def rollback(self): pass


class EquivalenciasTecnicasFase7CTest(unittest.TestCase):
    def setUp(self):
        self.tenant1 = TenantContext(empresa_id=1)
        self.tenant2 = TenantContext(empresa_id=999999)
        self.product1 = ProdutoDB(id=10, empresa_id=1, nome="Produto A")
        self.product2 = ProdutoDB(id=20, empresa_id=999999, nome="Produto B")
        self.supplier1 = FornecedorDB(id=30, empresa_id=1, nome="Fornecedor A", tipo="PJ")
        self.supplier2 = FornecedorDB(id=40, empresa_id=999999, nome="Fornecedor B", tipo="PJ")
        self.row = EmpresaEquivalenciaTecnicaDB(
            id=1, empresa_id=1, funcao_tecnica="TECIDO_ROLO", produto_id=10,
            fornecedor_id=30, prioridade=10, preferencial=True, ativo=True,
            configuracoes_locais={},
        )
        self.db = FakeSession({
            ProdutoDB: [self.product1, self.product2],
            FornecedorDB: [self.supplier1, self.supplier2],
            EmpresaEquivalenciaTecnicaDB: [self.row],
        })

    def test_funcao_valida_e_inexistente(self):
        self.assertTrue(service.is_valid_technical_function("TECIDO_ROLO"))
        self.assertFalse(service.is_valid_technical_function("INVENTADA"))
        with self.assertRaises(ValueError):
            service.list_by_function(self.db, self.tenant1, "INVENTADA")

    def test_criar_deriva_tenant_e_preserva_catalogo(self):
        created = service.create(self.db, self.tenant1, EquivalenciaTecnicaCreate(
            funcao_tecnica="TECIDO_ROLO", produto_id=10, fornecedor_id=30,
            prioridade=2,
        ))
        self.assertEqual(created.empresa_id, 1)
        self.assertEqual(created.prioridade, 2)

    def test_produto_e_fornecedor_cross_tenant_bloqueados(self):
        with self.assertRaises(PermissionError):
            service.create(self.db, self.tenant1, EquivalenciaTecnicaCreate(
                funcao_tecnica="TECIDO_ROLO", produto_id=20,
            ))
        with self.assertRaises(PermissionError):
            service.create(self.db, self.tenant1, EquivalenciaTecnicaCreate(
                funcao_tecnica="TECIDO_ROLO", produto_id=10, fornecedor_id=40,
            ))

    def test_listas_isoladas_por_tenant_e_funcao(self):
        self.assertEqual(service.list_all(self.db, self.tenant2), [])
        self.assertEqual(service.list_by_function(self.db, self.tenant1, "TECIDO_ROLO"), [self.row])

    def test_preferencial_unico(self):
        created = service.create(self.db, self.tenant1, EquivalenciaTecnicaCreate(
            funcao_tecnica="TECIDO_ROLO", produto_id=10, preferencial=True,
        ))
        self.assertFalse(self.row.preferencial)
        self.assertTrue(created.preferencial)

    def test_update_prioridade_status_e_tenant_imutavel(self):
        updated = service.update(self.db, self.tenant1, 1, EquivalenciaTecnicaUpdate(
            prioridade=5, ativo=False,
        ))
        self.assertEqual(updated.prioridade, 5)
        self.assertFalse(updated.ativo)
        self.assertEqual(updated.empresa_id, 1)
        self.assertIsNone(service.update(self.db, self.tenant2, 1, EquivalenciaTecnicaUpdate(prioridade=1)))

    def test_resolver_ordena_e_retorna_dados_comerciais(self):
        result = service.resolve_commercial_candidates(self.db, self.tenant1, "TECIDO_ROLO")
        self.assertEqual(result[0]["produto_nome"], "Produto A")
        self.assertEqual(result[0]["fornecedor_nome"], "Fornecedor A")
        self.assertTrue(result[0]["preferencial"])

    def test_resolver_nao_retorna_equivalencia_inativa(self):
        self.row.ativo = False
        self.assertEqual(
            service.resolve_commercial_candidates(self.db, self.tenant1, "TECIDO_ROLO"),
            [],
        )

    def test_resolver_prioriza_preferencial_e_depois_prioridade(self):
        self.row.preferencial = False
        self.row.prioridade = 1
        preferred = EmpresaEquivalenciaTecnicaDB(
            id=2, empresa_id=1, funcao_tecnica="TECIDO_ROLO", produto_id=10,
            fornecedor_id=30, prioridade=20, preferencial=True, ativo=True,
            configuracoes_locais={},
        )
        self.db.mapping[EmpresaEquivalenciaTecnicaDB].append(preferred)

        result = service.resolve_commercial_candidates(self.db, self.tenant1, "TECIDO_ROLO")

        self.assertTrue(result[0]["preferencial"])
        self.assertEqual(result[0]["prioridade"], 20)
        self.assertEqual(result[1]["prioridade"], 1)

    def test_empresa_sem_catalogo_e_tenant_ficticio_vazios(self):
        self.assertEqual(service.resolve_commercial_candidates(self.db, self.tenant2, "TECIDO_ROLO"), [])

    def test_legacy_unscoped_rejeitado(self):
        with self.assertRaises(TenantContextRequiredError):
            service.list_all(self.db, LEGACY_UNSCOPED)

    def test_nucleo_tecnico_nao_depende_da_camada_comercial(self):
        import app.technical.catalog as catalog_module
        self.assertNotIn("equivalencia_tecnica", " ".join(catalog_module.__dict__))


if __name__ == "__main__":
    unittest.main()
