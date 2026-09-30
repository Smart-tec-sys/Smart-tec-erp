"""Contratos de login, sessão e tenant autenticado da Fase 7B."""

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.auth.service import ExternalIdentity
from app.auth.navigation import navigate_in_current_session
from app.auth.session import (
    AUTH_ACCESS_TOKEN_KEY,
    AUTH_ACTIVE_COMPANY_ID_KEY,
    AUTH_REFRESH_TOKEN_KEY,
    AuthSessionData,
    clear_authenticated_session,
    get_active_company_id,
    is_authenticated,
    set_active_company_id,
    set_authenticated_session,
)
from app.auth.supabase_client import SupabaseLoginError, login_with_password
from app.auth.supabase_jwt import SupabaseTokenError
from app.routes.auth import auth_me
from app.tenant.context import TenantContext, TenantOrigin
from app.tenant.dependencies import get_current_tenant
from utils import api_client


class QueryResult:
    def __init__(self, *, one=None, many=None):
        self.one = one
        self.many = list(many or [])

    def filter(self, *_): return self
    def one_or_none(self): return self.one
    def all(self): return self.many


class AuthMeSession:
    def __init__(self, user, links, companies):
        self.user = user
        self.links = links
        self.companies = companies

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "UsuarioDB": return QueryResult(one=self.user)
        if name == "EmpresaUsuarioDB": return QueryResult(many=self.links)
        if name == "EmpresaDB":
            company = next(iter(self.companies.values()), None)
            return QueryResult(one=company)
        raise AssertionError(model)


class LoginStreamlitFase7BTest(unittest.TestCase):
    def test_dev_permanece_sem_login(self):
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "dev", "SMARTTEC_ENV": "development"}):
            tenant = get_current_tenant(None, None, None, None)
        self.assertEqual(tenant.empresa_id, 1)

    def test_authenticated_sem_bearer_retorna_401(self):
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "authenticated"}):
            with self.assertRaises(HTTPException) as raised:
                get_current_tenant(1, None, None, object())
        self.assertEqual(raised.exception.status_code, 401)

    def test_authenticated_token_invalido_retorna_401(self):
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "authenticated"}), patch(
            "app.tenant.dependencies.verify_supabase_access_token",
            side_effect=SupabaseTokenError("inválido"),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_current_tenant(1, None, "Bearer inválido", object())
        self.assertEqual(raised.exception.status_code, 401)

    def test_vinculo_valido_resolve_empresa_1(self):
        verified = SimpleNamespace(identity=ExternalIdentity("supabase", "subject"))
        resolved = SimpleNamespace(tenant=TenantContext(1, origem=TenantOrigin.AUTHENTICATION))
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "authenticated"}), patch(
            "app.tenant.dependencies.verify_supabase_access_token", return_value=verified
        ), patch("app.tenant.dependencies.resolve_identity_tenant", return_value=resolved):
            tenant = get_current_tenant(1, None, "Bearer válido", object())
        self.assertEqual(tenant.empresa_id, 1)

    def test_empresa_sem_vinculo_retorna_403(self):
        verified = SimpleNamespace(identity=ExternalIdentity("supabase", "subject"))
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "authenticated"}), patch(
            "app.tenant.dependencies.verify_supabase_access_token", return_value=verified
        ), patch(
            "app.tenant.dependencies.resolve_identity_tenant",
            side_effect=PermissionError("sem vínculo"),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_current_tenant(999999, None, "Bearer válido", object())
        self.assertEqual(raised.exception.status_code, 403)

    def test_header_de_teste_nao_contorna_authenticated(self):
        env = {"SMARTTEC_AUTH_MODE": "authenticated", "SMARTTEC_ALLOW_TEST_TENANT_HEADER": "1"}
        with patch.dict(os.environ, env), self.assertRaises(HTTPException) as raised:
            get_current_tenant(999999, None, None, object())
        self.assertEqual(raised.exception.status_code, 401)

    def test_auth_me_retorna_somente_vinculo_ativo(self):
        user = SimpleNamespace(id=1, email="owner@example.com", nome="Owner")
        link = SimpleNamespace(empresa_id=1, papel="OWNER")
        company = SimpleNamespace(id=1, nome="Smart-tec", nome_fantasia="Smart-tec", slug="smart-tec")
        result = auth_me(ExternalIdentity("supabase", "subject"), AuthMeSession(user, [link], {1: company}))
        self.assertEqual([item["id"] for item in result["empresas"]], [1])
        self.assertNotIn("provedor_subject", result["user"])

    def test_auth_me_sem_vinculo_retorna_403(self):
        user = SimpleNamespace(id=1, email="owner@example.com", nome="Owner")
        with self.assertRaises(HTTPException) as raised:
            auth_me(ExternalIdentity("supabase", "subject"), AuthMeSession(user, [], {}))
        self.assertEqual(raised.exception.status_code, 403)

    def test_logout_limpa_tokens_tenant_e_cache_comercial(self):
        session = {"tenant:1:produtos": [1], "cache:tenant:1:clientes": [1]}
        set_authenticated_session(session, AuthSessionData("access", "refresh", "u1", "a@b.com"))
        set_active_company_id(session, 1, slug="empresa-1")
        clear_authenticated_session(session)
        self.assertFalse(is_authenticated(session))
        self.assertNotIn(AUTH_ACTIVE_COMPANY_ID_KEY, session)
        self.assertFalse(any(str(key).startswith(("tenant:", "cache:tenant:")) for key in session))

    def test_navegacao_entre_modulos_preserva_auth_e_empresa(self):
        session = {}
        query_params = {}
        set_authenticated_session(
            session,
            AuthSessionData("access", "refresh", "u1", "owner@example.com"),
        )
        set_active_company_id(session, 1, slug="smart-tec-persianas")

        for destination in ("produtos", "clientes", "fornecedores", "orcamentos"):
            navigate_in_current_session(session, query_params, destination)
            self.assertTrue(is_authenticated(session))
            self.assertEqual(get_active_company_id(session), 1)
            self.assertEqual(query_params["go_to"], destination)
            with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "authenticated"}), patch(
                "utils.api_client._get_session_state", return_value=session
            ):
                self.assertEqual(
                    api_client._tenant_headers()["Authorization"],
                    "Bearer access",
                )

    def test_troca_empresa_limpa_cache_anterior(self):
        session = {AUTH_ACTIVE_COMPANY_ID_KEY: 1, "tenant:1:produtos": [1]}
        set_active_company_id(session, 2, slug="empresa-2")
        self.assertEqual(get_active_company_id(session), 2)
        self.assertNotIn("tenant:1:produtos", session)

    def test_api_client_headers_dev_e_authenticated(self):
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "dev"}):
            self.assertNotIn("Authorization", api_client._tenant_headers())
        session = {
            AUTH_ACCESS_TOKEN_KEY: "access",
            AUTH_REFRESH_TOKEN_KEY: "refresh",
            "auth_user_id": "u1",
            AUTH_ACTIVE_COMPANY_ID_KEY: 1,
        }
        with patch.dict(os.environ, {"SMARTTEC_AUTH_MODE": "authenticated"}), patch(
            "utils.api_client._get_session_state", return_value=session
        ):
            headers = api_client._tenant_headers()
        self.assertEqual(headers["Authorization"], "Bearer access")
        self.assertEqual(headers["X-Empresa-ID"], "1")

    def test_token_nao_aparece_em_repr(self):
        data = AuthSessionData("segredo-access", "segredo-refresh", "u1", "a@b.com")
        self.assertNotIn("segredo-access", repr(data))
        self.assertNotIn("segredo-refresh", repr(data))

    def test_login_nao_armazena_senha_e_normaliza_email(self):
        response = Mock(status_code=200, content=b"{}")
        response.json.return_value = {
            "access_token": "access", "refresh_token": "refresh", "expires_in": 3600,
            "user": {"id": "u1", "email": "owner@example.com"},
        }
        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "public"}), patch(
            "app.auth.supabase_client.requests.post", return_value=response
        ) as post:
            result = login_with_password(" OWNER@EXAMPLE.COM ", "senha-temporaria")
        self.assertEqual(result.email, "owner@example.com")
        self.assertEqual(post.call_args.kwargs["json"]["email"], "owner@example.com")
        self.assertNotIn("senha-temporaria", repr(result))

    def test_nenhum_segredo_hardcoded_nos_arquivos_7b(self):
        paths = [Path("app/auth/supabase_client.py"), Path("app/auth/session.py"), Path("utils/api_client.py")]
        content = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("service_role", content)
        self.assertNotIn("JWT_SECRET", content)


if __name__ == "__main__":
    unittest.main()
