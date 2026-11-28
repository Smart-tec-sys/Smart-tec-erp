"""Ações de orçamento com sessão simulada; nenhuma conexão de banco ou rede."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
# Permite validar candidatos em workspace separado antes da aplicação local.
SOURCE = Path(os.environ.get("SMARTTEC_TEST_SOURCE_ROOT", ROOT))
sys.path.insert(0, str(SOURCE))


def _candidate(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    parent, _, attribute = name.rpartition(".")
    setattr(sys.modules[parent], attribute, module)
    return module


# create_engine apenas configura um pool; connect é bloqueado também durante imports.
with patch("sqlalchemy.engine.base.Engine.connect", side_effect=AssertionError("Banco real proibido")):
    import app.models.cliente  # noqa: F401
    import app.services
    import app.routes
    from app.models.orcamento import OrcamentoDB, OrcamentoItemDB, OrcamentoParcelaDB
    from app.models.pedido import PedidoDB
    from app.tenant.context import TenantContext
    from app.tenant.dependencies import get_current_tenant
    from app.schemas.pedido import ConverterOrcamentoInput
    orcamento_service = _candidate("app.services.orcamento_service", "app/services/orcamento_service.py")
    pedido_service = _candidate("app.services.pedido_service", "app/services/pedido_service.py")
    orcamento_route = _candidate("app.routes.orcamento", "app/routes/orcamento.py")
    pedido_route = _candidate("app.routes.pedido", "app/routes/pedido.py")

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


class Query:
    def __init__(self, db, model):
        self.db, self.model, self.criteria = db, model, []

    def options(self, *args):
        return self

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def with_for_update(self):
        self.db.locked.append(self.model)
        return self

    def first(self):
        return next((row for row in self.db.rows.get(self.model, []) if all(
            getattr(row, clause.left.key) == clause.right.value for clause in self.criteria
        )), None)


class FakeSession:
    def __init__(self, source, orders=None):
        self.rows = {OrcamentoDB: [source], PedidoDB: list(orders or [])}
        self.added, self.locked = [], []
        self.commit, self.rollback = Mock(), Mock()

    def query(self, model):
        return Query(self, model)

    def add(self, row):
        self.added.append(row)
        self.rows.setdefault(type(row), []).append(row)

    def flush(self):
        for index, row in enumerate(self.added, 80):
            if row.id is None:
                row.id = index
            if hasattr(row, "criado_em") and row.criado_em is None:
                row.criado_em = datetime(2026, 11, 13)
            for child_index, child in enumerate(getattr(row, "itens", []) + getattr(row, "parcelas_pagamento", []), 100):
                child.id, child.orcamento_id = child_index, row.id


def fixture():
    source = OrcamentoDB(
        id=7, empresa_id=1, numero="1004", cliente_id=5, status="APROVADO",
        perfil_comercial="VAREJO", validade=date(2026, 11, 30),
        total=Decimal("150.25"), desconto=Decimal("2.75"), total_final=Decimal("147.50"),
        total_cliente_final=Decimal("147.50"), observacao="Proposta salva",
        observacao_interna="Apenas equipe", criado_em=datetime(2026, 10, 1),
        atualizado_em=datetime(2026, 10, 2),
        pagamento_modalidade="AVISTA", pagamento_numero_parcelas=1,
        pagamento_intervalo_dias=0, pagamento_primeiro_vencimento=date(2026, 11, 30),
    )
    source.itens = [OrcamentoItemDB(
        id=11, orcamento_id=7, empresa_id=1, tipo_item="PRODUTO", descricao="Cortina sala",
        codigo_interno="C-1", grupo_tecnico="CORTINAS", modelo_tecnico="CORTINA", unidade="UN",
        quantidade=Decimal("2"), largura=Decimal("1.50"), altura=Decimal("2.20"), area=Decimal("3.30"),
        preco_unitario=Decimal("75.1250"), desconto=Decimal("0"), subtotal=Decimal("150.25"),
        observacao_item="Sala", material="Linho", cor="Areia", acionamento="Manual",
        lado_comando="DIREITA", ambiente="Sala", calculo_producao_status="PENDENTE",
        dados_tecnicos={"cortina": {"modeloPrega": "WAVE", "fator": 2.5,
                                   "componentes": [{"produto_id": 4, "quantidade": 10}],
                                   "result": {"custo_total": 40}}},
    ), OrcamentoItemDB(
        id=12, orcamento_id=7, empresa_id=1, tipo_item="SERVICO", servico_id=3,
        descricao="Instalação", unidade="UN", quantidade=Decimal("1"), largura=0, altura=0,
        area=0, preco_unitario=Decimal("0"), desconto=0, subtotal=Decimal("0"),
    )]
    source.parcelas_pagamento = [OrcamentoParcelaDB(
        id=21, orcamento_id=7, empresa_id=1, numero=1, tipo="PARCELA",
        valor=Decimal("147.50"), vencimento=date(2026, 11, 30),
        forma_pagamento_id=8, forma_pagamento_nome="Pix",
        criado_em=datetime(2026, 10, 1), atualizado_em=datetime(2026, 10, 1),
    )]
    return source


class BudgetActionsTests(unittest.TestCase):
    def setUp(self):
        self.connection_block = patch("sqlalchemy.engine.base.Engine.connect", side_effect=AssertionError("Banco real proibido"))
        self.connection_block.start()
        self.addCleanup(self.connection_block.stop)
        self.source, self.tenant = fixture(), TenantContext(empresa_id=1)
        self.db = FakeSession(self.source)

    def test_copy_preserves_snapshot_with_new_identity_and_initial_status(self):
        original_json = deepcopy(self.source.itens[0].dados_tecnicos)
        with patch.object(orcamento_service, "_numero", return_value="1005") as number:
            result = orcamento_service.duplicar(self.db, 7, self.tenant)
        copy = self.db.added[0]
        self.assertEqual((result["numero"], result["status"], result["id"]), ("1005", "EM_ABERTO", 80))
        self.assertEqual((self.source.numero, self.source.status), ("1004", "APROVADO"))
        self.assertEqual(self.db.locked, [OrcamentoDB])
        number.assert_called_once_with(self.db)
        self.db.commit.assert_called_once()
        self.db.rollback.assert_not_called()
        for column in OrcamentoDB.__mapper__.column_attrs:
            if column.key not in {"id", "numero", "status", "criado_em", "atualizado_em"}:
                self.assertEqual(getattr(copy, column.key), getattr(self.source, column.key), column.key)
        self.assertNotEqual(copy.criado_em, self.source.criado_em)
        self.assertEqual(len(copy.itens), 2)
        for cloned, original in zip(copy.itens, self.source.itens):
            for column in OrcamentoItemDB.__mapper__.column_attrs:
                if column.key not in {"id", "orcamento_id"}:
                    self.assertEqual(getattr(cloned, column.key), getattr(original, column.key), column.key)
            self.assertNotEqual(cloned.id, original.id)
            self.assertEqual(cloned.orcamento_id, copy.id)
        for column in OrcamentoParcelaDB.__mapper__.column_attrs:
            if column.key not in {"id", "orcamento_id", "criado_em", "atualizado_em"}:
                self.assertEqual(getattr(copy.parcelas_pagamento[0], column.key), getattr(self.source.parcelas_pagamento[0], column.key), column.key)
        copy.itens[0].dados_tecnicos["cortina"]["componentes"][0]["quantidade"] = 99
        self.assertEqual(self.source.itens[0].dados_tecnicos, original_json)

    def test_copy_missing_or_other_company_creates_nothing(self):
        for oid, tenant in [(999, self.tenant), (7, TenantContext(empresa_id=2))]:
            with patch.object(orcamento_service, "_numero") as number:
                self.assertIsNone(orcamento_service.duplicar(self.db, oid, tenant))
                number.assert_not_called()
        self.assertFalse(self.db.added)
        self.db.commit.assert_not_called()

    def test_existing_number_generator_serializes_and_increments(self):
        db = Mock()
        for current, expected in [(1004, "1005"), (None, "1001")]:
            db.query.return_value.scalar.return_value = current
            self.assertEqual(orcamento_service._numero(db), expected)
        self.assertTrue(all("pg_advisory_xact_lock" in str(call.args[0]) for call in db.execute.call_args_list))

    def test_copy_rejects_cross_company_children(self):
        self.source.itens[0].empresa_id = 2
        with self.assertRaisesRegex(ValueError, "empresa ativa"):
            orcamento_service.duplicar(self.db, 7, self.tenant)
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_copy_rolls_back_if_flush_or_commit_fails(self):
        for operation in ["flush", "commit"]:
            db = FakeSession(fixture())
            setattr(db, operation, Mock(side_effect=RuntimeError("falha simulada")))
            with patch.object(orcamento_service, "_numero", return_value="1005"):
                with self.assertRaisesRegex(RuntimeError, "falha simulada"):
                    orcamento_service.duplicar(db, 7, self.tenant)
            db.rollback.assert_called_once()
            self.assertEqual((self.source.numero, self.source.status), ("1004", "APROVADO"))

    def test_copy_route_requires_tenant_dependency_and_returns_201_or_404(self):
        route = next(route for route in orcamento_route.router.routes if route.path == "/{oid}/duplicar")
        self.assertEqual(route.status_code, 201)
        self.assertIn(get_current_tenant, [dependency.call for dependency in route.dependant.dependencies])
        with patch.object(orcamento_service, "duplicar", return_value=None):
            with self.assertRaises(HTTPException) as error:
                orcamento_route.duplicar(7, self.db, self.tenant)
            self.assertEqual(error.exception.status_code, 404)

    def test_missing_auth_stops_copy_before_service(self):
        with patch.object(orcamento_service, "duplicar") as duplicate:
            with patch("app.tenant.dependencies.get_auth_mode", return_value="authenticated"):
                with self.assertRaises(HTTPException) as error:
                    get_current_tenant(x_empresa_id=1, authorization=None, db=self.db)
        self.assertEqual(error.exception.status_code, 401)
        duplicate.assert_not_called()

    def test_sale_requires_approved_saved_budget_and_company(self):
        self.source.status = "EM_ABERTO"
        with self.assertRaisesRegex(ValueError, "APROVADO"):
            pedido_service.converter_orcamento(self.db, 7, self.tenant)
        self.source.status = "APROVADO"
        with self.assertRaisesRegex(ValueError, "empresa atual"):
            pedido_service.converter_orcamento(self.db, 7, TenantContext(empresa_id=2))
        self.assertFalse(self.db.added)
        self.db.commit.assert_not_called()

    def test_sale_rejects_duplicate_and_locks_budget_snapshot(self):
        self.db.rows[PedidoDB] = [PedidoDB(id=20, empresa_id=1, orcamento_id=7, numero="VEN-000020")]
        with self.assertRaisesRegex(ValueError, "já foi convertido"):
            pedido_service.converter_orcamento(self.db, 7, self.tenant)
        self.assertEqual(self.db.locked, [OrcamentoDB])
        self.assertFalse(self.db.added)

    def test_sale_route_only_maps_known_unique_index_to_409(self):
        for constraint, expected in [("uq_pedidos_orcamento", 409), ("other_constraint", None)]:
            original = SimpleNamespace(diag=SimpleNamespace(constraint_name=constraint))
            failure = IntegrityError("INSERT", {}, original)
            self.db.rollback.reset_mock()
            with patch.object(pedido_service, "converter_orcamento", side_effect=failure):
                with self.assertRaises(HTTPException if expected else IntegrityError) as error:
                    pedido_route.converter_orcamento(7, ConverterOrcamentoInput(), self.db, self.tenant)
            if expected:
                self.assertEqual(error.exception.status_code, expected)
            self.db.rollback.assert_called_once()


class CopyPersistenceTests(unittest.TestCase):
    def test_copy_persists_independent_items_and_installments_in_memory(self):
        # SQLite em memória permite validar relacionamentos ORM sem PostgreSQL.
        import test_cliente_final_revenda_10l29b as fixtures
        setup = fixtures.ClienteFinalTests()
        setup.setUp()
        try:
            db = setup.db
            original = fixture()
            db.add(original)
            db.commit()
            tenant = TenantContext(empresa_id=1)
            before = orcamento_service.obter(db, original.id, tenant)
            with patch.object(orcamento_service, "_numero", return_value="1005"):
                copied = orcamento_service.duplicar(db, original.id, tenant)
            db.expire_all()
            saved = orcamento_service.obter(db, copied["id"], tenant)
            self.assertEqual((saved["numero"], saved["status"]), ("1005", "EM_ABERTO"))
            self.assertNotEqual(saved["id"], before["id"])
            self.assertEqual(len(saved["itens"]), 2)
            self.assertEqual(len(saved["pagamento_parcelas"]), 1)
            for new_item, old_item in zip(saved["itens"], before["itens"]):
                self.assertNotEqual(new_item["id"], old_item["id"])
                self.assertEqual({k: v for k, v in new_item.items() if k != "id"}, {k: v for k, v in old_item.items() if k != "id"})
            self.assertNotEqual(saved["pagamento_parcelas"][0]["id"], before["pagamento_parcelas"][0]["id"])
            self.assertEqual(orcamento_service.obter(db, original.id, tenant), before)
            self.assertIsNone(orcamento_service.obter(db, copied["id"], TenantContext(empresa_id=2)))
        finally:
            setup.tearDown()


if __name__ == "__main__":
    unittest.main()
