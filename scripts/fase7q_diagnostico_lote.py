import os
import re
import unicodedata
from collections import defaultdict

os.environ["DB_NAME"] = "smarttec_erp_dev"

from sqlalchemy import text
from app.database import engine


def norm(v):
    v = str(v or "").upper().strip()
    v = unicodedata.normalize("NFKD", v)
    v = "".join(c for c in v if not unicodedata.combining(c))
    v = re.sub(r"\s+", " ", v)
    return v


CORES = [
    "BRANCO", "BEGE", "PRETO", "CINZA", "MARROM",
    "CREME", "PRATA", "NATURAL", "CHOCOLATE",
    "AZUL", "VERDE", "VERMELHO"
]


def cor_nome(nome):
    t = norm(nome)
    for cor in CORES:
        if re.search(rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])", t):
            return cor
    return ""


def nome_sem_cor(nome):
    t = norm(nome)

    # remove prefixos históricos que não definem família
    t = re.sub(r"^(COM|COMP)\s*-\s*", "", t)

    for cor in CORES:
        t = re.sub(
            rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])",
            " ",
            t
        )

    t = re.sub(r"\(\s*\)", " ", t)
    t = re.sub(r"\s*[-–—]\s*", " ", t)
    t = re.sub(r"\s+", " ", t)

    return t.strip(" -()")


with engine.connect() as conn:

    db = conn.execute(text("SELECT current_database()")).scalar()

    if db != "smarttec_erp_dev":
        raise RuntimeError(
            f"ABORTADO: banco atual = {db!r}"
        )

    produtos = conn.execute(text("""
        SELECT
            id,
            empresa_id,
            nome,
            codigo,
            codigo_interno,
            codigo_barras,
            grupo_produto,
            grupo_tecnico,
            familia_tecnica,
            modelo,
            cor,
            cor_componente,
            variacao_cor,
            varia_cor,
            possui_variacoes,
            fornecedor_padrao_id,
            valor_custo,
            custo_final,
            valor_venda,
            unidade,
            unidade_venda,
            situacao,
            ativo
        FROM produtos
        WHERE empresa_id = 1
        ORDER BY id
    """)).mappings().all()

    deps = {}

    for tabela in [
        "orcamentos_itens",
        "pedidos_itens",
        "compras_itens",
        "estoque_movimentacoes",
        "empresa_equivalencias_tecnicas"
    ]:
        rows = conn.execute(text(f"""
            SELECT produto_id, COUNT(*) qtd
            FROM {tabela}
            GROUP BY produto_id
        """)).mappings()

        for r in rows:
            deps.setdefault(r["produto_id"], 0)
            deps[r["produto_id"]] += r["qtd"]


grupos = defaultdict(list)

for p in produtos:

    familia = (
        norm(p["familia_tecnica"])
        or nome_sem_cor(p["nome"])
    )

    cor = (
        norm(p["cor_componente"])
        or norm(p["variacao_cor"])
        or norm(p["cor"])
        or cor_nome(p["nome"])
    )

    grupos[(familia, cor)].append(p)


auto = []
revisao = []
familias = defaultdict(set)


for (familia, cor), itens in grupos.items():

    if cor:
        familias[familia].add(cor)

    if len(itens) <= 1:
        continue

    # Mesmo código + mesma família + mesma cor
    por_codigo = defaultdict(list)

    for p in itens:
        codigo = (
            str(p["codigo_interno"] or "").strip()
            or str(p["codigo_barras"] or "").strip()
            or str(p["codigo"] or "").strip()
        )

        if codigo:
            por_codigo[codigo].append(p)

    for codigo, duplicados in por_codigo.items():

        if len(duplicados) <= 1:
            continue

        custos = {
            float(p["valor_custo"] or 0)
            for p in duplicados
        }

        if len(custos) == 1:

            ordenados = sorted(
                duplicados,
                key=lambda p: (
                    deps.get(p["id"], 0),
                    0 if float(p["valor_venda"] or 0) == 0 else 1,
                    p["id"]
                )
            )

            canonico = ordenados[0]

            for legado in ordenados[1:]:

                if deps.get(legado["id"], 0) == 0:
                    auto.append({
                        "familia": familia,
                        "cor": cor,
                        "codigo": codigo,
                        "canonico": canonico["id"],
                        "legado": legado["id"],
                        "nome_canonico": canonico["nome"],
                        "nome_legado": legado["nome"],
                        "custo": float(legado["valor_custo"] or 0)
                    })
                else:
                    revisao.append({
                        "motivo": "DUPLICADO_COM_DEPENDENCIA",
                        "familia": familia,
                        "cor": cor,
                        "codigo": codigo,
                        "ids": [p["id"] for p in duplicados]
                    })

        else:
            revisao.append({
                "motivo": "MESMO_CODIGO_CUSTOS_DIFERENTES",
                "familia": familia,
                "cor": cor,
                "codigo": codigo,
                "ids": [p["id"] for p in duplicados]
            })


print()
print("====================================================")
print(" FASE 7Q - DIAGNOSTICO EM LOTE")
print("====================================================")
print(f"Banco: {db}")
print(f"Produtos analisados: {len(produtos)}")
print(f"Famílias com mais de uma cor: {sum(1 for x in familias.values() if len(x) > 1)}")
print(f"Duplicados AUTO_APROVADOS: {len(auto)}")
print(f"Casos para REVISAO_MANUAL: {len(revisao)}")
print()

print("=== AMOSTRA AUTO_APROVADO ===")
for x in auto[:40]:
    print(
        f"{x['legado']} -> {x['canonico']} | "
        f"{x['familia']} | {x['cor']} | {x['codigo']} | "
        f"R$ {x['custo']:.2f}"
    )

print()
print("=== AMOSTRA REVISAO_MANUAL ===")
for x in revisao[:30]:
    print(x)

print()
print("=== FAMILIAS MULTICOR ===")

cont = 0
for familia, cores in sorted(familias.items()):
    if len(cores) > 1:
        print(f"{familia}: {', '.join(sorted(cores))}")
        cont += 1
        if cont >= 60:
            break

print()
print("NENHUMA ALTERACAO FOI REALIZADA.")


