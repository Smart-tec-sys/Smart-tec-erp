import os
import re
import unicodedata
import csv
from collections import defaultdict
from sqlalchemy import text
from app.database import engine

EXECUTAR = True   # NÃO MUDAR PARA TRUE AINDA

def norm(v):
    v = str(v or "").upper().strip()
    v = unicodedata.normalize("NFKD", v)
    v = "".join(c for c in v if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", v)

CORES = [
    "BRANCO","BEGE","PRETO","CINZA","MARROM","CREME",
    "PRATA","NATURAL","CHOCOLATE","AZUL","VERDE",
    "VERMELHO","MOSTARDA"
]

def cor_nome(nome):
    t = norm(nome)
    for cor in CORES:
        if re.search(rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])", t):
            return cor
    return ""

def familia_nome(nome):
    t = norm(nome)
    t = re.sub(r"^(COM|COMP)\s*-\s*", "", t)

    for cor in CORES:
        t = re.sub(
            rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])",
            " ",
            t
        )

    t = re.sub(r"\(\s*\)", " ", t)
    t = re.sub(r"\s*[-–—]\s*", " ", t)
    return re.sub(r"\s+", " ", t).strip(" -()")


with engine.connect() as conn:

    db = conn.execute(text("SELECT current_database()")).scalar()

    if db != "smarttec_erp_dev":
        raise RuntimeError(f"ABORTADO: banco atual = {db}")

    produtos = list(conn.execute(text("""
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
            fornecedor_padrao_id,
            valor_custo,
            custo_final,
            unidade,
            unidade_venda,
            situacao,
            ativo,
            cor,
            cor_componente,
            variacao_cor
        FROM produtos
        WHERE empresa_id = 1
        ORDER BY id
    """)).mappings())

    deps = defaultdict(int)

    for tabela in (
        "orcamentos_itens",
        "pedidos_itens",
        "compras_itens",
        "estoque_movimentacoes",
        "empresa_equivalencias_tecnicas",
    ):
        for r in conn.execute(text(f"""
            SELECT produto_id, COUNT(*) AS qtd
            FROM {tabela}
            GROUP BY produto_id
        """)).mappings():
            deps[r["produto_id"]] += int(r["qtd"])


grupos = defaultdict(list)

for p in produtos:

    familia = norm(p["familia_tecnica"]) or familia_nome(p["nome"])

    cor = (
        norm(p["cor_componente"])
        or norm(p["variacao_cor"])
        or norm(p["cor"])
        or cor_nome(p["nome"])
    )

    codigo = (
        str(p["codigo_interno"] or "").strip()
        or str(p["codigo_barras"] or "").strip()
        or str(p["codigo"] or "").strip()
    )

    chave = (
        familia,
        cor,
        codigo,
        round(float(p["valor_custo"] or 0), 6),
        norm(p["unidade"]),
        norm(p["unidade_venda"]),
        norm(p["grupo_produto"]),
    )

    if codigo and familia:
        grupos[chave].append(p)


aprovados = []
revisao = []

for chave, itens in grupos.items():

    if len(itens) < 2:
        continue

    # registro que deve sobreviver:
    # 1) vínculos existentes
    # 2) fornecedor relacional
    # 3) família técnica estruturada
    # 4) grupo técnico estruturado
    # 5) menor ID como desempate
    itens = sorted(
        itens,
        key=lambda p: (
            -deps[p["id"]],
            0 if p["fornecedor_padrao_id"] else 1,
            0 if str(p["familia_tecnica"] or "").strip() else 1,
            0 if str(p["grupo_tecnico"] or "").strip() else 1,
            p["id"],
        )
    )

    canonico = itens[0]

    for legado in itens[1:]:

        if deps[legado["id"]] != 0:
            revisao.append((
                legado["id"],
                canonico["id"],
                "LEGADO_COM_DEPENDENCIA",
                legado["nome"],
            ))
            continue

        aprovados.append({
            "legado": legado["id"],
            "canonico": canonico["id"],
            "nome_legado": legado["nome"],
            "nome_canonico": canonico["nome"],
            "familia": chave[0],
            "cor": chave[1],
            "codigo": chave[2],
            "custo": chave[3],
            "unidade": chave[4],
            "unidade_venda": chave[5],
            "grupo": chave[6],
        })


csv_path = "fase7q_plano_estrito.csv"

with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow([
        "legado","canonico","familia","cor","codigo","custo",
        "unidade","unidade_venda","grupo",
        "nome_legado","nome_canonico"
    ])

    for x in aprovados:
        w.writerow([
            x["legado"], x["canonico"], x["familia"], x["cor"],
            x["codigo"], x["custo"], x["unidade"],
            x["unidade_venda"], x["grupo"],
            x["nome_legado"], x["nome_canonico"]
        ])


print("====================================================")
print(" FASE 7Q - PLANO ESTRITO")
print("====================================================")
print("Banco:", db)
print("Produtos:", len(produtos))
print("Duplicados estritos aprovados:", len(aprovados))
print("Retidos por dependência:", len(revisao))
print("Arquivo:", csv_path)

print()
print("=== PRIMEIROS 30 ===")

for x in aprovados[:30]:
    print(
        f'{x["legado"]} -> {x["canonico"]} | '
        f'{x["familia"]} | {x["cor"]} | '
        f'{x["codigo"]} | R$ {x["custo"]:.2f}'
    )


if not EXECUTAR:
    print()
    print("DRY_RUN: nenhuma alteração realizada.")
    raise SystemExit(0)


# =====================================================
# EXECUÇÃO PROTEGIDA
# =====================================================

import json
from datetime import datetime

ids_legados = sorted({int(x["legado"]) for x in aprovados})

if len(ids_legados) != len(aprovados):
    raise RuntimeError("ABORTADO: existem IDs legados repetidos no plano.")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"fase7q_backup_produtos_{timestamp}.json"


with engine.begin() as conn:

    db = conn.execute(
        text("SELECT current_database()")
    ).scalar()

    if db != "smarttec_erp_dev":
        raise RuntimeError(
            f"ABORTADO: banco incorreto = {db}"
        )

    # ---------------------------------------------
    # 1. Captura integral dos registros antes
    # ---------------------------------------------
    registros = list(
        conn.execute(
            text("""
                SELECT *
                FROM produtos
                WHERE empresa_id = 1
                  AND id = ANY(:ids)
                ORDER BY id
            """),
            {"ids": ids_legados},
        ).mappings()
    )

    if len(registros) != len(ids_legados):
        raise RuntimeError(
            f"ABORTADO: esperados {len(ids_legados)} produtos, "
            f"encontrados {len(registros)}."
        )

    # Serialização simples para backup local
    serializaveis = []

    for r in registros:
        item = {}
        for k, v in dict(r).items():
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            else:
                item[k] = v
        serializaveis.append(item)

    with open(
        backup_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            serializaveis,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    # ---------------------------------------------
    # 2. Todos precisam estar ativos
    # ---------------------------------------------
    ativos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
              AND id = ANY(:ids)
              AND ativo = true
        """),
        {"ids": ids_legados},
    ).scalar()

    if ativos != len(ids_legados):
        raise RuntimeError(
            f"ABORTADO: esperados {len(ids_legados)} ativos, "
            f"encontrados {ativos}."
        )

    # ---------------------------------------------
    # 3. Nenhum legado pode possuir dependência
    # ---------------------------------------------
    tabelas = [
        "orcamentos_itens",
        "pedidos_itens",
        "compras_itens",
        "estoque_movimentacoes",
        "empresa_equivalencias_tecnicas",
    ]

    for tabela in tabelas:

        qtd = conn.execute(
            text(f"""
                SELECT COUNT(*)
                FROM {tabela}
                WHERE produto_id = ANY(:ids)
            """),
            {"ids": ids_legados},
        ).scalar()

        if qtd != 0:
            raise RuntimeError(
                f"ABORTADO: {qtd} dependências encontradas "
                f"em {tabela}."
            )

    # ---------------------------------------------
    # 4. Totais de controle antes
    # ---------------------------------------------
    produtos_total_antes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
        """)
    ).scalar()

    ativos_antes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
              AND ativo = true
        """)
    ).scalar()

    equiv_antes = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM empresa_equivalencias_tecnicas
            WHERE empresa_id = 1
        """)
    ).scalar()

    # ---------------------------------------------
    # 5. Inativação
    # ---------------------------------------------
    resultado = conn.execute(
        text("""
            UPDATE produtos
            SET
                ativo = false,
                situacao = 'Inativo',
                status_comercial = 'INATIVO'
            WHERE empresa_id = 1
              AND id = ANY(:ids)
              AND ativo = true
        """),
        {"ids": ids_legados},
    )

    if resultado.rowcount != len(ids_legados):
        raise RuntimeError(
            f"ABORTADO: UPDATE parcial "
            f"{resultado.rowcount}/{len(ids_legados)}."
        )

    # ---------------------------------------------
    # 6. Pós-validação
    # ---------------------------------------------
    ainda_ativos = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
              AND id = ANY(:ids)
              AND ativo = true
        """),
        {"ids": ids_legados},
    ).scalar()

    if ainda_ativos != 0:
        raise RuntimeError(
            f"ABORTADO: {ainda_ativos} legados "
            f"continuaram ativos."
        )

    produtos_total_depois = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
        """)
    ).scalar()

    ativos_depois = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM produtos
            WHERE empresa_id = 1
              AND ativo = true
        """)
    ).scalar()

    equiv_depois = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM empresa_equivalencias_tecnicas
            WHERE empresa_id = 1
        """)
    ).scalar()

    if produtos_total_depois != produtos_total_antes:
        raise RuntimeError(
            "ABORTADO: quantidade total de produtos mudou."
        )

    if ativos_depois != ativos_antes - len(ids_legados):
        raise RuntimeError(
            "ABORTADO: quantidade final de ativos divergiu."
        )

    if equiv_depois != equiv_antes:
        raise RuntimeError(
            "ABORTADO: equivalências técnicas foram alteradas."
        )


print()
print("====================================================")
print(" FASE 7Q - LOTE ESTRITO CONCLUÍDO")
print("====================================================")
print("Produtos inativados:", len(ids_legados))
print("Backup:", backup_path)
print("Total de produtos preservado:", produtos_total_depois)
print("Ativos antes:", ativos_antes)
print("Ativos depois:", ativos_depois)
print("Equivalências preservadas:", equiv_depois)
