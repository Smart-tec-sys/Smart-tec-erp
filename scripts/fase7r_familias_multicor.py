import re
import unicodedata
import csv
from collections import defaultdict
from sqlalchemy import text
from app.database import engine

def norm(v):
    v = str(v or "").upper().strip()
    v = unicodedata.normalize("NFKD", v)
    v = "".join(c for c in v if not unicodedata.combining(c))
    v = re.sub(r"\s+", " ", v)
    return v

CORES = [
    "BRANCO","BEGE","PRETO","CINZA","MARROM","CREME",
    "PRATA","NATURAL","CHOCOLATE","AZUL","VERDE",
    "VERMELHO","MOSTARDA"
]

def detectar_cor(p):
    for campo in ("cor_componente","variacao_cor","cor"):
        valor = norm(p.get(campo))
        if valor:
            return valor

    texto = norm(p["nome"])

    for cor in CORES:
        if re.search(rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])", texto):
            return cor

    return ""

def familia_base(nome):
    t = norm(nome)

    # Prefixos históricos
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

def familia_estruturada(base):
    # Família comercial específica.
    # Não confundir com função técnica universal.
    x = norm(base)
    x = re.sub(r"[^A-Z0-9]+", "_", x)
    x = re.sub(r"_+", "_", x).strip("_")
    return f"FAM_{x}"

with engine.connect() as conn:

    db = conn.execute(
        text("SELECT current_database()")
    ).scalar()

    if db != "smarttec_erp_dev":
        raise RuntimeError(f"ABORTADO: banco = {db}")

    rows = conn.execute(text("""
        SELECT
            id,
            nome,
            grupo_produto,
            grupo_tecnico,
            familia_tecnica,
            varia_cor,
            cor,
            cor_componente,
            variacao_cor,
            fornecedor_padrao_id,
            codigo_interno,
            codigo_barras,
            valor_custo,
            ativo,
            situacao
        FROM produtos
        WHERE empresa_id = 1
          AND ativo = true
          AND COALESCE(grupo_produto,'') <> 'Tecidos'
        ORDER BY id
    """)).mappings()

    produtos = [dict(r) for r in rows]

grupos = defaultdict(list)

for p in produtos:
    base = familia_base(p["nome"])
    cor = detectar_cor(p)

    if not base or not cor:
        continue

    grupos[base].append((p, cor))

aprovados = []
revisao = []

for base, itens in grupos.items():

    cores = sorted({cor for _, cor in itens})

    # Só interessa família realmente multicor
    if len(cores) < 2:
        continue

    familia = familia_estruturada(base)

    # Proteção: mesma família deve ter custos razoavelmente consistentes
    # por SKU/cor; diferenças são permitidas, mas apenas registradas.
    fornecedores = {
        p["fornecedor_padrao_id"]
        for p, _ in itens
        if p["fornecedor_padrao_id"] is not None
    }

    # Se aparecem fornecedores relacionais diferentes,
    # não automatiza.
    if len(fornecedores) > 1:
        revisao.append({
            "familia": base,
            "motivo": "FORNECEDORES_DIFERENTES",
            "ids": [p["id"] for p, _ in itens],
        })
        continue

    for p, cor in itens:
        aprovados.append({
            "id": p["id"],
            "nome": p["nome"],
            "familia_atual": p["familia_tecnica"] or "",
            "familia_nova": familia,
            "cor": cor,
            "varia_cor_atual": bool(p["varia_cor"]),
            "grupo": p["grupo_produto"] or "",
            "grupo_tecnico": p["grupo_tecnico"] or "",
            "fornecedor": p["fornecedor_padrao_id"],
            "codigo": p["codigo_interno"] or p["codigo_barras"] or "",
            "custo": float(p["valor_custo"] or 0),
        })

with open(
    "fase7r_familias_multicor.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    campos = [
        "id","nome","familia_atual","familia_nova","cor",
        "varia_cor_atual","grupo","grupo_tecnico",
        "fornecedor","codigo","custo"
    ]

    w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
    w.writeheader()
    w.writerows(aprovados)

print()
print("===================================================")
print(" FASE 7R - FAMILIAS MULTICOR - DRY RUN")
print("===================================================")
print("Banco:", db)
print("Produtos não-tecido ativos analisados:", len(produtos))
print("Famílias multicor encontradas:",
      sum(1 for x in grupos.values()
          if len({cor for _, cor in x}) >= 2))
print("Produtos prontos para normalização:", len(aprovados))
print("Famílias retidas para revisão:", len(revisao))
print("Arquivo: fase7r_familias_multicor.csv")

print()
print("=== AMOSTRA ===")

for x in aprovados[:60]:
    print(
        f'{x["id"]} | {x["familia_nova"]} | '
        f'{x["cor"]} | {x["nome"]}'
    )

print()
print("=== RETIDOS ===")

for x in revisao[:30]:
    print(x)

print()
print("NENHUMA ALTERACAO FOI REALIZADA.")
