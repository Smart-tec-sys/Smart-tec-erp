"""Testes unitários da base multiempresa, sem acesso a banco."""

import re
import unittest
from pathlib import Path

from app.technical.catalog import TECHNICAL_CATALOG
from app.tenant.bootstrap import new_tenant_empty_snapshot
from app.tenant.context import LEGACY_UNSCOPED, TenantContext, TenantOrigin
from app.tenant.isolation import (
    TenantAccessError,
    TenantContextRequiredError,
    apply_tenant_filter,
    require_tenant,
    validate_resource_tenant,
)
from app.tenant.prepared_models import TENANT_COLUMN_PLAN
from app.tenant.session import get_tenant_from_session, tenant_cache_key


ROOT = Path(__file__).parents[1]


class _TenantColumn:
    def __eq__(self, value):
        return ("empresa_id", value)


class _TenantModel:
    empresa_id = _TenantColumn()


class _Query:
    def __init__(self):
        self.condition = None

    def filter(self, condition):
        self.condition = condition
        return self


class TenantFase2Test(unittest.TestCase):
    def setUp(self):
        self.context_a = TenantContext(empresa_id=1, user_id="usuario-a")
        self.context_b = TenantContext(empresa_id=2, user_id="usuario-b")

    def test_contexto_exige_identificador_positivo(self):
        self.assertEqual(require_tenant(self.context_a), 1)
        with self.assertRaises(ValueError):
            TenantContext(empresa_id=0)
        with self.assertRaises(ValueError):
            TenantContext(empresa_id=None)

    def test_legacy_unscoped_e_temporario_e_nao_satisfaz_isolamento(self):
        self.assertTrue(LEGACY_UNSCOPED.is_legacy_unscoped)
        with self.assertRaises(TenantContextRequiredError):
            require_tenant(LEGACY_UNSCOPED)

    def test_acesso_cruzado_e_bloqueado_para_recursos_principais(self):
        for resource_type in ("produto", "fornecedor", "cliente", "orcamento"):
            with self.subTest(resource_type=resource_type):
                with self.assertRaises(TenantAccessError):
                    validate_resource_tenant(
                        resource_empresa_id=self.context_b.empresa_id,
                        current_empresa_id=require_tenant(self.context_a),
                    )
        validate_resource_tenant(1, 1)

    def test_recurso_legado_sem_empresa_nao_vaza_em_operacao_isolada(self):
        with self.assertRaises(TenantAccessError):
            validate_resource_tenant(None, require_tenant(self.context_a))

    def test_helper_aplica_filtro_de_empresa(self):
        query = apply_tenant_filter(_Query(), _TenantModel, 7)
        self.assertEqual(query.condition, ("empresa_id", 7))

    def test_sessao_e_cache_novos_nascem_tenant_safe(self):
        context = get_tenant_from_session({"tenant_empresa_id": 8, "tenant_user_id": "u8"})
        self.assertEqual(context.origem, TenantOrigin.SESSION)
        self.assertEqual(tenant_cache_key(context, "produtos", "ativos"),
                         ("tenant", 8, "produtos", "ativos"))
        with self.assertRaises(ValueError):
            tenant_cache_key(LEGACY_UNSCOPED, "produtos")

    def test_novo_tenant_nasce_zerado_mas_enxerga_nucleo_global(self):
        snapshot_a = new_tenant_empty_snapshot(self.context_a)
        snapshot_b = new_tenant_empty_snapshot(self.context_b)
        for snapshot in (snapshot_a, snapshot_b):
            self.assertEqual(snapshot.produtos, ())
            self.assertEqual(snapshot.fornecedores, ())
            self.assertEqual(snapshot.clientes, ())
            self.assertEqual(snapshot.custos, ())
            self.assertEqual(snapshot.estoque, ())
            self.assertEqual(snapshot.portfolio, ())
            self.assertEqual(set(snapshot.funcoes_tecnicas_globais), set(TECHNICAL_CATALOG))

    def test_plano_e_modelos_ativados_mantem_empresa_id_nullable(self):
        self.assertEqual(
            set(TENANT_COLUMN_PLAN),
            {"produtos", "fornecedores", "clientes", "orcamentos"},
        )
        self.assertTrue(all(item["nullable"] for item in TENANT_COLUMN_PLAN.values()))
        legacy_files = (
            "app/models/produto.py", "app/models/fornecedor.py",
            "app/models/cliente.py", "app/models/orcamento.py",
        )
        for relative_path in legacy_files:
            source = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(
                'empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)',
                source,
            )

    def test_empresa_e_portfolio_estao_modelados_sem_populacao(self):
        empresa_source = (ROOT / "app/models/empresa.py").read_text(encoding="utf-8")
        portfolio_source = (ROOT / "app/models/empresa_portfolio.py").read_text(encoding="utf-8")
        for field in (
            "nome", "nome_fantasia", "documento", "status", "slug",
            "configuracoes", "criado_em", "atualizado_em",
        ):
            self.assertRegex(empresa_source, rf"\b{field}\s*=")
        self.assertIn("uq_empresa_portfolio_empresa_modelo", portfolio_source)
        self.assertIn('ForeignKey("empresas.id"', portfolio_source)

    def test_migration_nao_carrega_dados_e_colunas_sao_nullable(self):
        migration = (ROOT / "migrations/20260828_multiempresa_fase2_up.sql").read_text(
            encoding="utf-8"
        )
        sql_without_comments = re.sub(r"--.*", "", migration).upper()
        self.assertNotRegex(sql_without_comments, r"\bINSERT\s+INTO\b")
        self.assertNotRegex(sql_without_comments, r"\bUPDATE\s+\w+\s+SET\b")
        self.assertNotRegex(sql_without_comments, r"\bDELETE\s+FROM\b")
        for table in ("produtos", "fornecedores", "clientes", "orcamentos"):
            self.assertRegex(
                sql_without_comments,
                rf"ALTER TABLE {table.upper()} ADD COLUMN IF NOT EXISTS EMPRESA_ID INTEGER NULL",
            )
        self.assertNotIn("ALTER TABLE ORCAMENTOS_ITENS", sql_without_comments)


if __name__ == "__main__":
    unittest.main()
