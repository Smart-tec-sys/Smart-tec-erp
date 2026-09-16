"""Contratos não persistidos da expansão multiempresa Fase 5."""

import unittest

from app.auth.models import (
    AuthenticatedTenantContext,
    AuthenticationState,
    UserContext,
    logout_context,
)
from app.technical.catalog import TECHNICAL_CATALOG
from app.tenant.context import LEGACY_UNSCOPED, TenantContext
from app.tenant.onboarding import TenantOnboardingInput, preview_zero_tenant
from app.tenant.portfolio import InMemoryTenantPortfolio
from app.tenant.session import tenant_cache_key, tenant_session_key


class ExpansaoTenantFase5Test(unittest.TestCase):
    def setUp(self):
        self.tenant_a = TenantContext(empresa_id=1)
        self.tenant_b = TenantContext(empresa_id=999999)

    def test_cache_e_sessao_sao_isolados(self):
        self.assertNotEqual(
            tenant_cache_key(self.tenant_a, "servicos"),
            tenant_cache_key(self.tenant_b, "servicos"),
        )
        self.assertEqual(
            tenant_session_key(self.tenant_a, "carrinho"),
            "tenant:1:carrinho",
        )
        self.assertNotEqual(
            tenant_session_key(self.tenant_a, "carrinho"),
            tenant_session_key(self.tenant_b, "carrinho"),
        )
        with self.assertRaises(ValueError):
            tenant_session_key(LEGACY_UNSCOPED, "carrinho")

    def test_contexto_autenticado_vincula_usuario_e_empresa(self):
        user = UserContext(user_id="u1", display_name="Usuário")
        authenticated = AuthenticatedTenantContext(user=user, tenant=self.tenant_a)
        self.assertEqual(authenticated.tenant.empresa_id, 1)
        self.assertEqual(logout_context(authenticated), AuthenticationState.ANONYMOUS)

    def test_usuario_inativo_nao_autentica(self):
        with self.assertRaises(ValueError):
            AuthenticatedTenantContext(
                user=UserContext(user_id="u1", display_name="Inativo", active=False),
                tenant=self.tenant_a,
            )

    def test_onboarding_nasce_zerado_sem_heranca(self):
        preview = preview_zero_tenant(
            TenantOnboardingInput(nome="Empresa B", slug="empresa-b")
        )
        for field in (
            "portfolio", "produtos", "fornecedores", "clientes", "orcamentos",
            "estoque", "custos",
        ):
            self.assertEqual(getattr(preview, field), ())
        self.assertEqual(set(preview.funcoes_tecnicas_globais), set(TECHNICAL_CATALOG))

    def test_portfolio_e_independente_por_empresa_e_vazio_por_padrao(self):
        portfolio = InMemoryTenantPortfolio()
        self.assertEqual(portfolio.list_active(self.tenant_b), ())
        portfolio.activate(self.tenant_a, "ROLO")
        self.assertEqual(portfolio.list_active(self.tenant_a), ("ROLO",))
        self.assertEqual(portfolio.list_active(self.tenant_b), ())
        portfolio.deactivate(self.tenant_a, "ROLO")
        self.assertEqual(portfolio.list_active(self.tenant_a), ())


if __name__ == "__main__":
    unittest.main()
