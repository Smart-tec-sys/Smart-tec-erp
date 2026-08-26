import os
import requests

API_URL = os.getenv("SMARTTEC_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _url(path):
    return f"{API_URL}{path}"


# CLIENTES
def get_clientes():
    return requests.get(_url("/clientes/"))


def get_cliente_por_id(id_cliente):
    return requests.get(_url(f"/clientes/{id_cliente}"))


def criar_cliente(dados):
    return requests.post(_url("/clientes/"), json=dados)


def atualizar_cliente(id_cliente, dados):
    return requests.put(_url(f"/clientes/{id_cliente}"), json=dados)


def deletar_cliente(id_cliente):
    return requests.delete(_url(f"/clientes/{id_cliente}"))


# FORNECEDORES
def get_fornecedores():
    return requests.get(_url("/fornecedores/"))


def get_fornecedor_por_id(id_fornecedor):
    return requests.get(_url(f"/fornecedores/{id_fornecedor}"))


def criar_fornecedor(dados):
    return requests.post(_url("/fornecedores/"), json=dados)


def atualizar_fornecedor(id_fornecedor, dados):
    return requests.put(_url(f"/fornecedores/{id_fornecedor}"), json=dados)


def deletar_fornecedor(id_fornecedor):
    return requests.delete(_url(f"/fornecedores/{id_fornecedor}"))


# FUNCIONÁRIOS
def get_funcionarios():
    return requests.get(_url("/funcionarios/"))


def get_funcionario_por_id(id_funcionario):
    return requests.get(_url(f"/funcionarios/{id_funcionario}"))


def criar_funcionario(dados):
    return requests.post(_url("/funcionarios/"), json=dados)


def atualizar_funcionario(id_funcionario, dados):
    return requests.put(_url(f"/funcionarios/{id_funcionario}"), json=dados)


def deletar_funcionario(id_funcionario):
    return requests.delete(_url(f"/funcionarios/{id_funcionario}"))


# TRANSPORTADORAS
def get_transportadoras():
    return requests.get(_url("/transportadoras/"))


def get_transportadora_por_id(id_transportadora):
    return requests.get(_url(f"/transportadoras/{id_transportadora}"))


def criar_transportadora(dados):
    return requests.post(_url("/transportadoras/"), json=dados)


def atualizar_transportadora(id_transportadora, dados):
    return requests.put(_url(f"/transportadoras/{id_transportadora}"), json=dados)


def deletar_transportadora(id_transportadora):
    return requests.delete(_url(f"/transportadoras/{id_transportadora}"))


def get_transportadora():
    return get_transportadoras()

# ORÇAMENTOS
def get_orcamentos(): return requests.get(_url("/orcamentos/"))
def get_orcamento_por_id(orcamento_id): return requests.get(_url(f"/orcamentos/{orcamento_id}"))
def criar_orcamento(dados): return requests.post(_url("/orcamentos/"), json=dados)
def atualizar_orcamento(orcamento_id,dados): return requests.put(_url(f"/orcamentos/{orcamento_id}"),json=dados)
def deletar_orcamento(orcamento_id): return requests.delete(_url(f"/orcamentos/{orcamento_id}"))


# OPÇÕES AUXILIARES
def get_opcoes_auxiliares():
    return requests.get(_url("/opcoes-auxiliares/"))


def get_opcoes_auxiliares_por_categoria(categoria):
    return requests.get(_url(f"/opcoes-auxiliares/categoria/{categoria}"))


def criar_opcao_auxiliar(dados):
    return requests.post(_url("/opcoes-auxiliares/"), json=dados)


def atualizar_opcao_auxiliar(id_opcao, dados):
    return requests.put(_url(f"/opcoes-auxiliares/{id_opcao}"), json=dados)


def deletar_opcao_auxiliar(id_opcao):
    return requests.delete(_url(f"/opcoes-auxiliares/{id_opcao}"))


# PRODUTOS
def get_produtos(skip=0, limit=100):
    return requests.get(
        _url("/produtos/"),
        params={"skip": skip, "limit": limit},
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
    return requests.get(_url("/produtos/resumo/"), params=params or {})


def get_produto_por_id(id_produto):
    return requests.get(_url(f"/produtos/{id_produto}"))


def criar_produto(dados):
    return requests.post(_url("/produtos/"), json=dados)


def atualizar_produto(id_produto, dados):
    return requests.put(_url(f"/produtos/{id_produto}"), json=dados)


def deletar_produto(id_produto):
    return requests.delete(_url(f"/produtos/{id_produto}"))


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
