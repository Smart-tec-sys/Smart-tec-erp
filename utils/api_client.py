import os
import requests

API_URL = os.getenv("SMARTTEC_API_URL", "http://127.0.0.1:8000").rstrip("/")
DEV_TENANT_ID = int(os.getenv("SMARTTEC_DEV_TENANT_ID", "1"))
DEV_TENANT_SLUG = os.getenv("SMARTTEC_DEV_TENANT_SLUG", "smart-tec-persianas")


def _url(path):
    return f"{API_URL}{path}"


def _get_session_state():
    try:
        import streamlit as st
        return st.session_state
    except Exception:
        return {}


def _auth_mode():
    return os.getenv("SMARTTEC_AUTH_MODE", "dev").strip().lower()


def _tenant_headers():
    if _auth_mode() == "dev":
        return {"X-Empresa-ID": str(DEV_TENANT_ID)}
    if _auth_mode() != "authenticated":
        raise RuntimeError("SMARTTEC_AUTH_MODE inválido")

    from app.auth.session import get_access_token, get_active_company_id

    session = _get_session_state()
    token = get_access_token(session)
    empresa_id = get_active_company_id(session)
    if not token:
        raise PermissionError("sessão autenticada ausente")
    if empresa_id is None:
        raise PermissionError("empresa ativa ausente")
    return {
        "Authorization": f"Bearer {token}",
        "X-Empresa-ID": str(empresa_id),
    }


def _authorization_headers():
    from app.auth.session import get_access_token

    token = get_access_token(_get_session_state())
    if not token:
        raise PermissionError("sessão autenticada ausente")
    return {"Authorization": f"Bearer {token}"}


def get_auth_me():
    return requests.get(_url("/auth/me"), headers=_authorization_headers())


# EQUIVALÊNCIAS TÉCNICAS COMERCIAIS
def get_equivalencias_tecnicas():
    return requests.get(_url("/equivalencias-tecnicas/"), headers=_tenant_headers())


def criar_equivalencia_tecnica(dados):
    return requests.post(_url("/equivalencias-tecnicas/"), json=dados, headers=_tenant_headers())


def atualizar_equivalencia_tecnica(equivalence_id, dados):
    return requests.put(
        _url(f"/equivalencias-tecnicas/{equivalence_id}"),
        json=dados,
        headers=_tenant_headers(),
    )


# CLIENTES
def get_clientes():
    return requests.get(_url("/clientes/"), headers=_tenant_headers())


def get_cliente_por_id(id_cliente):
    return requests.get(_url(f"/clientes/{id_cliente}"), headers=_tenant_headers())


def criar_cliente(dados):
    return requests.post(_url("/clientes/"), json=dados, headers=_tenant_headers())


def atualizar_cliente(id_cliente, dados):
    return requests.put(_url(f"/clientes/{id_cliente}"), json=dados, headers=_tenant_headers())


def deletar_cliente(id_cliente):
    return requests.delete(_url(f"/clientes/{id_cliente}"), headers=_tenant_headers())


# FORNECEDORES
def get_fornecedores():
    return requests.get(_url("/fornecedores/"), headers=_tenant_headers())


def get_fornecedor_por_id(id_fornecedor):
    return requests.get(_url(f"/fornecedores/{id_fornecedor}"), headers=_tenant_headers())


def criar_fornecedor(dados):
    return requests.post(_url("/fornecedores/"), json=dados, headers=_tenant_headers())


def atualizar_fornecedor(id_fornecedor, dados):
    return requests.put(_url(f"/fornecedores/{id_fornecedor}"), json=dados, headers=_tenant_headers())


def deletar_fornecedor(id_fornecedor):
    return requests.delete(_url(f"/fornecedores/{id_fornecedor}"), headers=_tenant_headers())


# FUNCIONÁRIOS
def get_funcionarios():
    return requests.get(_url("/funcionarios/"), headers=_tenant_headers())


def get_funcionario_por_id(id_funcionario):
    return requests.get(_url(f"/funcionarios/{id_funcionario}"), headers=_tenant_headers())


def criar_funcionario(dados):
    return requests.post(_url("/funcionarios/"), json=dados, headers=_tenant_headers())


def atualizar_funcionario(id_funcionario, dados):
    return requests.put(_url(f"/funcionarios/{id_funcionario}"), json=dados, headers=_tenant_headers())


def deletar_funcionario(id_funcionario):
    return requests.delete(_url(f"/funcionarios/{id_funcionario}"), headers=_tenant_headers())


# TRANSPORTADORAS
def get_transportadoras():
    return requests.get(_url("/transportadoras/"), headers=_tenant_headers())


def get_transportadora_por_id(id_transportadora):
    return requests.get(_url(f"/transportadoras/{id_transportadora}"), headers=_tenant_headers())


def criar_transportadora(dados):
    return requests.post(_url("/transportadoras/"), json=dados, headers=_tenant_headers())


def atualizar_transportadora(id_transportadora, dados):
    return requests.put(_url(f"/transportadoras/{id_transportadora}"), json=dados, headers=_tenant_headers())


def deletar_transportadora(id_transportadora):
    return requests.delete(_url(f"/transportadoras/{id_transportadora}"), headers=_tenant_headers())


def get_transportadora():
    return get_transportadoras()

# ORÇAMENTOS
def get_orcamentos(): return requests.get(_url("/orcamentos/"), headers=_tenant_headers())
def get_orcamento_por_id(orcamento_id): return requests.get(_url(f"/orcamentos/{orcamento_id}"), headers=_tenant_headers())
def criar_orcamento(dados): return requests.post(_url("/orcamentos/"), json=dados, headers=_tenant_headers())
def atualizar_orcamento(orcamento_id,dados): return requests.put(_url(f"/orcamentos/{orcamento_id}"),json=dados,headers=_tenant_headers())
def deletar_orcamento(orcamento_id): return requests.delete(_url(f"/orcamentos/{orcamento_id}"),headers=_tenant_headers())


# OPÇÕES AUXILIARES
def get_opcoes_auxiliares():
    return requests.get(_url("/opcoes-auxiliares/"), headers=_tenant_headers())


def get_opcoes_auxiliares_por_categoria(categoria):
    return requests.get(_url(f"/opcoes-auxiliares/categoria/{categoria}"), headers=_tenant_headers())


def criar_opcao_auxiliar(dados):
    return requests.post(_url("/opcoes-auxiliares/"), json=dados, headers=_tenant_headers())


def atualizar_opcao_auxiliar(id_opcao, dados):
    return requests.put(_url(f"/opcoes-auxiliares/{id_opcao}"), json=dados, headers=_tenant_headers())


def deletar_opcao_auxiliar(id_opcao):
    return requests.delete(_url(f"/opcoes-auxiliares/{id_opcao}"), headers=_tenant_headers())


# PRODUTOS
def get_produtos(skip=0, limit=100):
    return requests.get(
        _url("/produtos/"),
        params={"skip": skip, "limit": limit},
        headers=_tenant_headers(),
    )


def get_produtos_todos(lote=500, max_paginas=20):
    todos = []
    skip = 0

    for _ in range(max_paginas):
        resp = get_produtos(skip=skip, limit=lote)

        if resp is None or resp.status_code != 200:
            break

        dados = resp.json()

        if not isinstance(dados, list) or not dados:
            break

        todos.extend(dados)

        if len(dados) < lote:
            break

        skip += lote

    return todos


def get_produtos_resumo(params=None):
    return requests.get(_url("/produtos/resumo/"), params=params or {}, headers=_tenant_headers())


def get_produto_por_id(id_produto):
    return requests.get(_url(f"/produtos/{id_produto}"), headers=_tenant_headers())


def criar_produto(dados):
    return requests.post(_url("/produtos/"), json=dados, headers=_tenant_headers())


def atualizar_produto(id_produto, dados):
    return requests.put(_url(f"/produtos/{id_produto}"), json=dados, headers=_tenant_headers())


def deletar_produto(id_produto):
    return requests.delete(_url(f"/produtos/{id_produto}"), headers=_tenant_headers())


# RECEITAS BASE
def get_receitas_base(params=None):
    return requests.get(_url("/receitas-base/"), params=params or {})


def get_receita_base_por_id(id_receita_base):
    return requests.get(_url(f"/receitas-base/{id_receita_base}"))


def criar_receita_base(dados):
    return requests.post(_url("/receitas-base/"), json=dados)


def atualizar_receita_base(id_receita_base, dados):
    return requests.put(_url(f"/receitas-base/{id_receita_base}"), json=dados)


def deletar_receita_base(id_receita_base):
    return requests.delete(_url(f"/receitas-base/{id_receita_base}"))


def aplicar_receita_base_em_massa(dados):
    return requests.post(_url("/receitas-base/aplicar-em-massa/"), json=dados)


def get_receita_do_produto(id_produto):
    return requests.get(_url(f"/produtos/{id_produto}/receita"))


def aplicar_receita_base_no_produto(id_produto, id_receita_base):
    return requests.post(_url(f"/produtos/{id_produto}/receita-base/{id_receita_base}"))


def remover_receita_base_do_produto(id_produto):
    return requests.delete(_url(f"/produtos/{id_produto}/receita-base"))


# COMPONENTES / BAÚ
def get_componentes_bau(params=None):
    return requests.get(_url("/produtos/componentes-bau/"), params=params or {})


def get_componentes_por_grupo(grupo_tecnico):
    return requests.get(
        _url("/produtos/componentes/"),
        params={"grupo_tecnico": grupo_tecnico},
    )
