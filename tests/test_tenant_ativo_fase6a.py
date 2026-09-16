"""Isolamento tenant-aware dos módulos persistidos ativados na Fase 6A."""

import unittest

from app.models.funcionario import FuncionarioDB
from app.models.opcao_auxiliar import OpcaoAuxiliarDB
from app.models.transportadora import TransportadoraDB
from app.schemas.funcionario import FuncionarioCreate, FuncionarioUpdate
from app.schemas.opcao_auxiliar import OpcaoAuxiliarCreate
from app.schemas.transportadora import TransportadoraCreate, TransportadoraUpdate
from app.services import funcionario_service, opcao_auxiliar, transportadora_service
from app.tenant.context import LEGACY_UNSCOPED, TenantContext
from app.tenant.isolation import TenantContextRequiredError
from app.tenant.session import tenant_cache_key, tenant_session_key


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


class TenantAtivoFase6ATest(unittest.TestCase):
    def setUp(self):
        self.tenant_a = TenantContext(empresa_id=1)
        self.tenant_b = TenantContext(empresa_id=999999)
        self.funcionario = FuncionarioDB(id=1, nome="Funcionário A", empresa_id=1)
        self.transportadora = TransportadoraDB(
            id=2, nome="Transportadora A", tipo="Pessoa Jurídica", empresa_id=1
        )
        self.opcao = OpcaoAuxiliarDB(
            id=3, categoria="tipo_contato", nome="Comercial", empresa_id=1
        )
        self.db = FakeSession({
            FuncionarioDB: [self.funcionario],
            TransportadoraDB: [self.transportadora],
            OpcaoAuxiliarDB: [self.opcao],
        })

    def test_tenant_1_ve_legado_e_tenant_inexistente_ve_zero(self):
        self.assertEqual(len(funcionario_service.get_all(self.db, self.tenant_a)), 1)
        self.assertEqual(funcionario_service.get_all(self.db, self.tenant_b), [])
        self.assertEqual(len(transportadora_service.get_all(self.db, self.tenant_a)), 1)
        self.assertEqual(transportadora_service.get_all(self.db, self.tenant_b), [])
        self.assertEqual(len(opcao_auxiliar.get_all(self.db, self.tenant_a)), 1)
        self.assertEqual(opcao_auxiliar.get_all(self.db, self.tenant_b), [])

    def test_get_update_delete_cross_tenant_falham(self):
        self.assertIsNone(funcionario_service.get_by_id(self.db, 1, self.tenant_b))
        self.assertIsNone(funcionario_service.update(
            self.db, 1, FuncionarioUpdate(nome="Inválido"), self.tenant_b
        ))
        self.assertIsNone(funcionario_service.delete(self.db, 1, self.tenant_b))
        self.assertIsNone(transportadora_service.get_by_id(self.db, 2, self.tenant_b))
        self.assertFalse(opcao_auxiliar.delete(self.db, 3, self.tenant_b))
        self.assertEqual(self.funcionario.nome, "Funcionário A")

    def test_create_deriva_empresa_do_contexto(self):
        funcionario = funcionario_service.create(
            self.db, FuncionarioCreate(nome="Novo"), self.tenant_b
        )
        transportadora = transportadora_service.create(
            self.db,
            TransportadoraCreate(nome="Nova", tipo="Pessoa Jurídica"),
            self.tenant_b,
        )
        opcao = opcao_auxiliar.create(
            self.db,
            OpcaoAuxiliarCreate(categoria="tipo_contato", nome="Novo"),
            self.tenant_b,
        )
        self.assertEqual(
            (funcionario.empresa_id, transportadora.empresa_id, opcao.empresa_id),
            (999999, 999999, 999999),
        )

    def test_update_preserva_empresa(self):
        funcionario_service.update(
            self.db, 1, FuncionarioUpdate(nome="Atualizado"), self.tenant_a
        )
        transportadora_service.update(
            self.db,
            2,
            TransportadoraUpdate(nome="Atualizada", tipo="Pessoa Jurídica"),
            self.tenant_a,
        )
        opcao_auxiliar.update(
            self.db,
            3,
            OpcaoAuxiliarCreate(categoria="tipo_contato", nome="Atualizado"),
            self.tenant_a,
        )
        self.assertEqual(self.funcionario.empresa_id, 1)
        self.assertEqual(self.transportadora.empresa_id, 1)
        self.assertEqual(self.opcao.empresa_id, 1)

    def test_opcoes_sao_isoladas_por_categoria(self):
        self.assertEqual(
            len(opcao_auxiliar.get_by_categoria(self.db, "tipo_contato", self.tenant_a)), 1
        )
        self.assertEqual(
            opcao_auxiliar.get_by_categoria(self.db, "tipo_contato", self.tenant_b), []
        )

    def test_legacy_unscoped_e_bloqueado(self):
        for service in (funcionario_service, transportadora_service, opcao_auxiliar):
            with self.assertRaises(TenantContextRequiredError):
                service.get_all(self.db, LEGACY_UNSCOPED)

    def test_schemas_publicos_nao_aceitam_troca_de_empresa(self):
        funcionario = FuncionarioCreate(nome="Teste", empresa_id=999999)
        transportadora = TransportadoraCreate(
            nome="Teste", tipo="Pessoa Jurídica", empresa_id=999999
        )
        opcao = OpcaoAuxiliarCreate(
            categoria="tipo_contato", nome="Teste", empresa_id=999999
        )
        self.assertNotIn("empresa_id", funcionario.dict())
        self.assertNotIn("empresa_id", transportadora.dict())
        self.assertNotIn("empresa_id", opcao.dict())

    def test_chaves_comerciais_sao_isoladas(self):
        for namespace in ("funcionarios", "transportadoras", "opcoes_auxiliares"):
            self.assertNotEqual(
                tenant_cache_key(self.tenant_a, namespace),
                tenant_cache_key(self.tenant_b, namespace),
            )
            self.assertNotEqual(
                tenant_session_key(self.tenant_a, namespace),
                tenant_session_key(self.tenant_b, namespace),
            )


if __name__ == "__main__":
    unittest.main()
