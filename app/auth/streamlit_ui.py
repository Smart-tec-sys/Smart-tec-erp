"""Gate de autenticação e seleção de empresa do Streamlit."""

import os

import streamlit as st

from app.auth.session import (
    AUTH_COMPANIES_KEY,
    AUTH_EMAIL_KEY,
    AuthSessionData,
    clear_authenticated_session,
    get_active_company_id,
    is_authenticated,
    set_active_company_id,
    set_authenticated_session,
)
from app.auth.supabase_client import (
    SupabaseClientConfigurationError,
    SupabaseLoginError,
    login_with_password,
)
from app.tenant.session import initialize_development_tenant_session
from utils.api_client import get_auth_me


def _auth_mode() -> str:
    mode = os.getenv("SMARTTEC_AUTH_MODE", "dev").strip().lower()
    if mode not in {"dev", "authenticated"}:
        raise RuntimeError("SMARTTEC_AUTH_MODE inválido")
    return mode


def _load_authorized_companies() -> list[dict]:
    response = get_auth_me()
    if response.status_code != 200:
        raise PermissionError("Usuário sem vínculo empresarial ativo")
    payload = response.json()
    companies = list(payload.get("empresas") or [])
    if not companies:
        raise PermissionError("Usuário sem vínculo empresarial ativo")
    st.session_state[AUTH_COMPANIES_KEY] = companies
    return companies


def _select_company(companies: list[dict]) -> bool:
    if len(companies) == 1:
        company = companies[0]
        set_active_company_id(st.session_state, int(company["id"]), slug=company.get("slug"))
        return True

    ids = [int(company["id"]) for company in companies]
    labels = {
        int(company["id"]): company.get("nome_fantasia") or company.get("nome") or str(company["id"])
        for company in companies
    }
    selected = st.selectbox("Empresa", ids, format_func=lambda value: labels[value])
    if st.button("Acessar empresa", type="primary", use_container_width=True):
        company = next(item for item in companies if int(item["id"]) == selected)
        set_active_company_id(st.session_state, selected, slug=company.get("slug"))
        st.rerun()
    return False


def initialize_authentication_gate() -> None:
    if _auth_mode() == "dev":
        initialize_development_tenant_session(st.session_state)
        return

    if not is_authenticated(st.session_state):
        st.title("Smart-tec Sistemas")
        st.caption("Entre para acessar o ERP")
        with st.form("smarttec_login", clear_on_submit=True):
            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if submit:
            try:
                auth = login_with_password(email, password)
                set_authenticated_session(st.session_state, AuthSessionData(
                    access_token=auth.access_token,
                    refresh_token=auth.refresh_token,
                    user_id=auth.user_id,
                    email=auth.email,
                    expires_at=auth.expires_at,
                ))
                companies = _load_authorized_companies()
                if _select_company(companies):
                    st.rerun()
            except (SupabaseLoginError, SupabaseClientConfigurationError, PermissionError) as exc:
                clear_authenticated_session(st.session_state)
                st.error(str(exc))
        st.stop()

    companies = list(st.session_state.get(AUTH_COMPANIES_KEY) or [])
    if not companies:
        try:
            companies = _load_authorized_companies()
        except PermissionError as exc:
            clear_authenticated_session(st.session_state)
            st.error(str(exc))
            st.stop()
    if get_active_company_id(st.session_state) is None and not _select_company(companies):
        st.stop()


def render_authenticated_identity_bar() -> None:
    if _auth_mode() != "authenticated":
        return
    empresa_id = get_active_company_id(st.session_state)
    companies = list(st.session_state.get(AUTH_COMPANIES_KEY) or [])
    company = next((item for item in companies if int(item["id"]) == empresa_id), {})
    label = company.get("nome_fantasia") or company.get("nome") or f"Empresa {empresa_id}"
    col_info, col_company, col_logout = st.columns([6, 2, 1])
    with col_info:
        st.caption(f"{st.session_state.get(AUTH_EMAIL_KEY, '')} · {label}")
    with col_company:
        if len(companies) > 1:
            ids = [int(item["id"]) for item in companies]
            labels = {
                int(item["id"]): item.get("nome_fantasia") or item.get("nome") or str(item["id"])
                for item in companies
            }
            selected = st.selectbox(
                "Empresa ativa",
                ids,
                index=ids.index(empresa_id),
                format_func=lambda value: labels[value],
                label_visibility="collapsed",
                key="auth_company_switch",
            )
            if selected != empresa_id:
                company = next(item for item in companies if int(item["id"]) == selected)
                set_active_company_id(st.session_state, selected, slug=company.get("slug"))
                st.rerun()
    with col_logout:
        if st.button("Sair", key="auth_logout", use_container_width=True):
            clear_authenticated_session(st.session_state)
            st.rerun()
