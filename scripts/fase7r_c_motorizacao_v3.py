import re
import unicodedata
from collections import defaultdict, Counter
from sqlalchemy import text
from app.database import engine

def norm(v):
    v = str(v or "").upper().strip()
    v = unicodedata.normalize("NFKD", v)
    v = "".join(c for c in v if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", v)

def tipo_motor(nome):
    t = norm(nome)

    # Sensores
    if any(x in t for x in [
        "SENSOR DE VENTO",
        "SENSOR DE VENTOS",
        "SENSOR SOL",
        "SENSOR DE SOL",
        "SENSOR CHUVA",
        "SENSOR DE CHUVA",
    ]):
        return "SENSOR"

    # Botoeira
    if "BOTOEIRA" in t:
        return "BOTOEIRA"

    # Fonte / carregador
    if (
        t.startswith("FONTE ")
        or " CARREGADOR " in f" {t} "
        or t.startswith("CARREGADOR ")
    ):
        # Motor vendido com carregador continua sendo conjunto de motor
        if t.startswith("MOTOR "):
            return "MOTOR"
        return "FONTE_CARREGADOR"

    # Motor + receptor + controle
    if (
        t.startswith("MOTOR ")
        and "RECEPTOR" in t
        and "CONTROLE" in t
    ):
        return "MOTOR_COM_RECEPTOR_CONTROLE"

    # Receptor + controle
    if (
        "RECEPTOR" in t
        and "CONTROLE" in t
        and not t.startswith("MOTOR ")
    ):
        return "RECEPTOR_COM_CONTROLE"

    # Motor puro/principal
    if (
        t.startswith("MOTOR ")
        or t.startswith("MOTOR-")
        or t.startswith("MOTOR RF ")
        or t.startswith("MOTOR TUBULAR ")
        or t.startswith("MOTOR CORTINA ")
    ):
        return "MOTOR"

    # Receptor puro
    if (
        t.startswith("RECEPTOR ")
        or t.startswith("RECEPTOR-")
        or t.startswith("MAQUINA RECEPTOR ")
        or t.startswith("MÁQUINA RECEPTOR ")
    ):
        return "RECEPTOR"

    # Controle puro
    if (
        t.startswith("CONTROLE ")
        or t.startswith("CONTROLE-")
        or " CONTROLE REMOTO " in f" {t} "
    ):
        return "CONTROLE"

    # Acessórios/compatibilidades
    if any(x in t for x in [
        "P/ MOTOR",
        "PARA MOTOR",
        "MOTORIZADA",
        "MOTORIZADO",
        "TRILHO",
        "CORREIA",
        "PONTEIRA",
        "GRAPA",
        "SUPORTE MOTOR",
        "CONECTOR",
        "ADAPTADOR",
        "ACESSORIO",
        "ACESSÓRIO",
    ]):
        return "ACESSORIO_MOTORIZACAO"

    return None
def canais(nome):
    t = norm(nome)
    m = re.search(r"(\d+)\s*\(?CANAIS?\)?", t)
    return m.group(1) if m else ""

def familia_base(nome):
    t = norm(nome)

    # remove atributos que não definem a família comercial
    t = re.sub(r"\b110V\b|\b220V\b|\bBIVOLT\b", " ", t)
    t = re.sub(r"\b\d+(?:[.,]\d+)?\s*N(?:M)?\b", " ", t)
    t = re.sub(r"\b\d+\s*\(?CANAIS?\)?", " ", t)

    t = re.sub(r"\s+", " ", t).strip(" -()")
    return t


def torque(nome):
    t = norm(nome)
    m = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*N(?:M)?\b", t)
    return m.group(1).replace(",", ".") if m else ""


def tensao(nome):
    t = norm(nome)

    if "BIVOLT" in t:
        return "BIVOLT"
    if "BATERIA" in t:
        return "BATERIA"
    if "220V" in t or "220 V" in t or "230V" in t or "230 V" in t:
        return "220V"
    if "110V" in t or "110 V" in t or "120V" in t or "120 V" in t:
        return "110V"

    return ""


def canais(nome):
    t = norm(nome)
    m = re.search(r"(\d+)\s*\(?CANAIS?\)?", t)
    if not m:
        m = re.search(r"(\d+)\s*\(?CANAL\)?", t)
    return m.group(1) if m else ""

with engine.connect() as conn:

    db = conn.execute(text("SELECT current_database()")).scalar()

    if db != "smarttec_erp_dev":
        raise RuntimeError(f"ABORTADO: banco = {db}")

    rows = conn.execute(text("""
        SELECT
            id,
            nome,
            grupo_produto,
            grupo_tecnico,
            familia_tecnica,
            modelo,
            tipo_produto,
            observacoes,
            fornecedor_padrao_id,
            codigo,
            codigo_interno,
            codigo_barras,
            valor_custo,
            custo_final,
            unidade,
            unidade_venda,
            situacao,
            ativo
        FROM produtos
        WHERE empresa_id = 1
          AND ativo = true
        ORDER BY id
    """)).mappings()

    produtos = [dict(r) for r in rows]

candidatos = []

for p in produtos:
    texto = " ".join([
        str(p.get("nome") or ""),
        str(p.get("grupo_produto") or ""),
        str(p.get("grupo_tecnico") or ""),
        str(p.get("familia_tecnica") or ""),
        str(p.get("modelo") or ""),
        str(p.get("tipo_produto") or ""),
        str(p.get("observacoes") or ""),
    ])

    t = norm(texto)

    if not any(x in t for x in [
        "MOTOR",
        "CONTROLE",
        "RECEPTOR",
        "BOTOEIRA",
        "MOTORIZ",
        "AUTOMAC",
        "CARREGADOR"
    ]):
        continue

    candidatos.append(p)

tipos = Counter()
grupos = Counter()
familias = defaultdict(list)
revisao = []

for p in candidatos:

    tp = tipo_motor(p["nome"])

    if not tp:
        revisao.append({
            "id": p["id"],
            "nome": p["nome"],
            "motivo": "TIPO_INDEFINIDO"
        })
        continue

    tipos[tp] += 1
    grupos[norm(p["grupo_produto"])] += 1

    fam = familia_base(p["nome"])

    familias[(tp, fam)].append({
        "id": p["id"],
        "nome": p["nome"],
        "torque": torque(p["nome"]),
        "tensao": tensao(p["nome"]),
        "canais": canais(p["nome"]),
        "fornecedor": p["fornecedor_padrao_id"],
        "codigo": (
            p["codigo_interno"]
            or p["codigo_barras"]
            or p["codigo"]
            or ""
        ),
        "custo": float(p["valor_custo"] or 0),
    })

auto = []
manual = []

for chave, itens in familias.items():

   if len(itens) == 1:
    # Singleton não é automaticamente aprovado.
    # Só entra em AUTO quando sua classe é inequívoca.
    tp = chave[0]

    if tp in [
    "MOTOR",
    "CONTROLE",
    "RECEPTOR",
    "RECEPTOR_COM_CONTROLE",
    "MOTOR_COM_RECEPTOR_CONTROLE",
    "BOTOEIRA",
    "SENSOR",
    "FONTE_CARREGADOR",
]:
        auto.append((chave, itens))
    else:
        manual.append({
            "familia": chave,
            "motivo": "ACESSORIO_OU_IDENTIDADE_INSUFICIENTE",
            "ids": [x["id"] for x in itens],
        })

    continue

    specs = {
        (
            x["torque"],
            x["tensao"],
            x["canais"],
            x["fornecedor"]
        )
        for x in itens
    }

    codigos = {
        str(x["codigo"])
        for x in itens
        if str(x["codigo"]).strip()
    }

    if len(specs) == 1:
        auto.append((chave, itens))
    else:
        manual.append({
            "familia": chave,
            "motivo": "ESPECIFICACOES_DIVERGENTES",
            "ids": [x["id"] for x in itens],
            "specs": list(specs),
            "codigos": sorted(codigos)
        })

print()
print("===================================================")
print(" FASE 7R-C - MOTORIZACAO - DRY RUN")
print("===================================================")
print("Banco:", db)
print("Produtos ativos analisados:", len(produtos))
print("Candidatos motorizacao:", len(candidatos))
print("Familias candidatas:", len(familias))
print("Familias AUTO_APROVADO:", len(auto))
print("Familias REVISAO_MANUAL:", len(manual) + len(revisao))
print()

print("=== DISTRIBUICAO POR TIPO ===")
for k,v in tipos.most_common():
    print(k, v)

print()
print("=== GRUPOS HISTORICOS ===")
for k,v in grupos.most_common():
    print(k or "<VAZIO>", v)

print()
print("=== AMOSTRA AUTO_APROVADO ===")
for (tp,fam), itens in auto[:40]:
    print(tp, "|", fam, "|", [x["id"] for x in itens])

print()
print("=== AMOSTRA REVISAO ===")
for x in manual[:30]:
    print(x)

for x in revisao[:20]:
    print(x)

print()
print("NENHUMA ALTERACAO FOI REALIZADA.")

