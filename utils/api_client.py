import requests

BASE_URL = "http://127.0.0.1:8000"


# ==========================================
# CLIENTES
# ==========================================
def get_clientes():
    return requests.get(f"{BASE_URL}/clientes/")


def criar_cliente(dados_cliente: dict):
    return requests.post(f"{BASE_URL}/clientes/", json=dados_cliente)


def atualizar_cliente(cliente_id: int, dados_cliente: dict):
    return requests.put(f"{BASE_URL}/clientes/{cliente_id}", json=dados_cliente)


def deletar_cliente(cliente_id: int):
    return requests.delete(f"{BASE_URL}/clientes/{cliente_id}")


# ==========================================
# PRODUTOS
# ==========================================
def get_produtos():
    return requests.get(f"{BASE_URL}/produtos/")


# ==========================================
# FORNECEDORES
# ==========================================
def get_fornecedores():
    return requests.get(f"{BASE_URL}/fornecedores/")


def criar_fornecedor(dados_fornecedor: dict):
    return requests.post(f"{BASE_URL}/fornecedores/", json=dados_fornecedor)


def atualizar_fornecedor(fornecedor_id: int, dados_fornecedor: dict):
    return requests.put(f"{BASE_URL}/fornecedores/{fornecedor_id}", json=dados_fornecedor)


def deletar_fornecedor(fornecedor_id: int):
    return requests.delete(f"{BASE_URL}/fornecedores/{fornecedor_id}")


# ==========================================
# FUNCIONÁRIOS
# ==========================================
def get_funcionarios():
    return requests.get(f"{BASE_URL}/funcionarios/")


def criar_funcionario(dados_funcionario: dict):
    return requests.post(f"{BASE_URL}/funcionarios/", json=dados_funcionario)


def atualizar_funcionario(funcionario_id: int, dados_funcionario: dict):
    return requests.put(f"{BASE_URL}/funcionarios/{funcionario_id}", json=dados_funcionario)


def deletar_funcionario(funcionario_id: int):
    return requests.delete(f"{BASE_URL}/funcionarios/{funcionario_id}")
