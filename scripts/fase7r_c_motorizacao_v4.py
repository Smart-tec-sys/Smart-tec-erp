import re
import unicodedata
from collections import defaultdict, Counter
import json
from pathlib import Path
from sqlalchemy import text
from app.database import engine

def norm(v):
    v = str(v or "").upper().strip()
    v = unicodedata.normalize("NFKD", v)
    v = "".join(c for c in v if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", v)


    t = norm(nome)
def tipo_motor(nome):
    t = norm(nome)

    # Itens que nunca devem ser classificados automaticamente
    if any(x in t for x in [
        "CONECTOR",
        "CABO",
        "CORREIA",
        "TRILHO",
        "PONTEIRA",
        "GRAPA",
        "SUPORTE",
        "ADAPTADOR",
        "ACESSORIO",
        "ACESSÓRIO",
        "P/ MOTOR",
        "PARA MOTOR",
    ]):
        return "ACESSORIO_MOTORIZACAO"

    if any(x in t for x in [
        "SENSOR DE VENTO",
        "SENSOR DE VENTOS",
        "SENSOR DE SOL",
        "SENSOR SOL",
        "SENSOR DE CHUVA",
        "SENSOR CHUVA",
    ]):
        return "SENSOR"

    if "BOTOEIRA" in t:
        return "BOTOEIRA"

    motor_principal = bool(
        re.match(r"^(?:MOTOR\b|(?:MOTP|MOTV|APMOTV) - MOTOR\b|\d+(?:[.,]\d+)?N\b.*\bMOTOR\b)", t)
    )

    # Motor + receptor + controle
    if (
        motor_principal
        and "RECEPTOR" in t
        and "CONTROLE" in t
        and "SEM CONTROLE" not in t
    ):
        return "MOTOR_COM_RECEPTOR_CONTROLE"

    # Motor principal
    if motor_principal:
        return "MOTOR"

    # Receptor + controle sem ser motor
    if "RECEPTOR" in t and "CONTROLE" in t and "SEM CONTROLE" not in t:
        return "RECEPTOR_COM_CONTROLE"

    if (
        t.startswith("RECEPTOR ")
        or t.startswith("MAQUINA RECEPTOR ")
        or t.startswith("MÁQUINA RECEPTOR ")
        or re.match(r"^\d+(?:[.,]\d+)?N\b.*\bMAQUINA RECEPTOR\b", t)
    ):
        return "RECEPTOR"

    if t.startswith("CONTROLE ") or ("AC123" in t and re.search(r"\b\d+\s*CANAIS?\b", t)):
        return "CONTROLE"

    if (
        t.startswith("FONTE ")
        or t.startswith("CARREGADOR ")
    ):
        return "FONTE_CARREGADOR"

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

diag_7rb = sorted(Path(r"C:\Users\valmi\Smart-tec-backups").glob(
    "fase7r_b_*/fase7r_b_diagnostico_completo.json"
))
if not diag_7rb:
    raise RuntimeError("ABORTADO: diagnóstico da 7R-B não localizado")
dados_7rb = json.loads(diag_7rb[-1].read_text(encoding="utf-8"))
protegidos_7rb = {
    int(p["id"])
    for f in dados_7rb["familias"]
    if f["status"] == "REVISAO_MANUAL"
    for p in f["produtos"]
}
if len(protegidos_7rb) != 1346:
    raise RuntimeError(f"ABORTADO: protegidos 7R-B={len(protegidos_7rb)}; esperado=1346")

protegidos_7ra = {
    57, 567, 568, 89, 90, 91, 636, 92, 93, 94, 95, 639, 96, 97, 98, 99,
    100, 652, 653, 654, 655, 656, 257, 258, 267, 832, 263, 264, 265, 845,
    846, 266, 268, 269, 848, 849, 850, 270, 271, 852, 292, 294, 920, 921,
    922, 923, 298, 927, 2654, 2659, 2664, 2668, 2672, 299, 300, 301, 302,
    303, 928, 929, 930, 931, 932, 317, 558, 945, 2280, 2281, 2282, 2283,
    2284, 465, 466, 467, 468, 469, 1113, 1114, 1115, 1116, 1117, 470, 471,
    472, 473, 474, 1118, 1119, 1120, 1121, 1122, 616, 617, 618, 2629,
    2705, 2707,
}
protegidos = protegidos_7ra | protegidos_7rb

candidatos = []

for p in produtos:
    if p["id"] in protegidos:
        continue
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
    tp = chave[0]

    if len(itens) == 1:
        # Singleton não é automaticamente aprovado.
        # Só entra em AUTO quando sua classe é inequívoca.
        nome_item = norm(itens[0]["nome"])
        modelo_claro = bool(
            re.search(r"\b(?:AC|DC|DD|DM|DT|EM|FC|FD|FT|TR|RE)\d+[A-Z0-9/.-]*", chave[1])
            or any(x in chave[1] for x in ["BLACK PIANO", "MILANO", "SOFTPLUS LSN"])
        )
        conflito_textual = (
            (("110V" in nome_item or "120V" in nome_item)
             and ("220V" in nome_item or "230V" in nome_item)
             and "BIVOLT" not in nome_item)
            or nome_item.count("MOTP - MOTOR") > 1
            or nome_item.count("MOTV - MOTOR") > 1
        )
        identidade_minima = modelo_claro and not conflito_textual
        if tp in [
            "MOTOR",
            "CONTROLE",
            "RECEPTOR",
            "MOTOR_COM_RECEPTOR_CONTROLE",
            "RECEPTOR_COM_CONTROLE",
            "BOTOEIRA",
            "SENSOR",
            "FONTE_CARREGADOR",
        ] and identidade_minima:
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
print("IDs protegidos 7R-A:", len(protegidos_7ra))
print("IDs protegidos 7R-B:", len(protegidos_7rb))
print("Candidatos motorizacao:", len(candidatos))
print("Familias candidatas:", len(familias))
print("Familias AUTO_APROVADO:", len(auto))
print("Produtos AUTO_APROVADO:", sum(len(itens) for _, itens in auto))
print("Familias REVISAO_MANUAL:", len(manual) + len(revisao))
print("Produtos REVISAO_MANUAL:", len(candidatos) - sum(len(itens) for _, itens in auto))
print("DUPLICADO_CONFIRMADO:", 0)
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
