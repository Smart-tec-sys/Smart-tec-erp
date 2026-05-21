# teste.py
import sys
import os

# Garante que o Python encontra os módulos na raiz
sys.path.insert(0, os.path.abspath("."))

print("=== DIAGNÓSTICO SMARTTEC ERP ===\n")

# ===== TESTA BANCO =====
print("📦 Testando conexão com banco...")
try:
    from backend.core.database import conectar, liberar_conexao
    print("✅ backend.database importado OK")
    
    conn = conectar()
    if conn:
        print("✅ Conexão PostgreSQL OK!")
        liberar_conexao(conn)
    else:
        print("❌ Conexão falhou - verifique .env ou credenciais")
except Exception as e:
    print(f"❌ Erro no banco: {e}")

# ===== TESTA MÓDULOS =====
print("\n📦 Testando módulos...")

modulos = [
    "modulos.clientes",
    "modulos.produtos",
    "modulos.dashboard",
    "modulos.financeiro",
    "modulos.orcamentos",
    "modulos.pedidos",
    "modulos.estoque",
    "modulos.vendas",
    "modulos.relatorios",
    "modulos.compras",
    "modulos.notas_fiscal",
    "modulos.simulador",
]

for m in modulos:
    try:
        __import__(m)
        print(f"✅ {m} OK")
    except Exception as e:
        print(f"❌ {m} ERRO: {e}")

# ===== TESTA ARQUIVOS =====
print("\n📁 Verificando arquivos essenciais...")

arquivos = [
    "app.py",
    "backend/database.py",
    "modulos/__init__.py",
    "modulos/clientes.py",
    "modulos/produtos.py",
    "modulos/dashboard.py",
    ".env",
    "assets/logo.png",
]

for arq in arquivos:
    if os.path.exists(arq):
        print(f"✅ {arq} existe")
    else:
        print(f"❌ {arq} NÃO ENCONTRADO")

print("\n=== FIM DO DIAGNÓSTICO ===")
