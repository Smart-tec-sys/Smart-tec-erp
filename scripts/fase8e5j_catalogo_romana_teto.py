import os
import re
import unicodedata
from collections import defaultdict
from sqlalchemy import text

os.environ["DB_NAME"] = "smarttec_erp_dev"

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
    "AZUL", "VERDE", "VERMELHO", "MOSTARDA",
    "WHITE", "BLACK", "GREY", "IVORY", "KAIAHK",
    "COCONUT", "BROWN", "RUSTICO", "RÚSTICO",
    "MESCLA", "KAKI", "IMBUIA", "MOGNO", "TABACO",
    "CEREJEIRA", "ALABASTER", "ALUMINIUM", "BISCUIT",
    "FAWN", "PRALINE", "VANILLA", "TRUE WHITE",
    "MIDNIGHT BLUE", "PEACH", "GRAFITE", "ROYAL",
    "AZUL ROYAL", "CARAMELO", "CAFE", "CAFÉ",
    "ALPINO", "NAVY", "ROSE", "ROSA", "LILAS",
    "VERDE ESCURO", "VERDE CLARO", "AMARELO",
    "LARANJA", "VIOLETA", "DOURADO", "COBRE",
    "FUMÊ", "FUME", "AREIA", "PALHA", "TERRA",
    "FERRO", "CHUMBO", "GRAFITE ESCURO", "GRAFITE CLARO",
    "OFF WHITE", "OFF-WHITE", "NEVE", "GELO",
    "PEDRA", "CIMENTO", "CONCRETO", "ARDOISIA",
    "CARVAO", "CARVÃO", "ESPRESSO", "CAFE ESCURO",
    "MEL", "DOURADO CLARO", "BRONZE", "COBRE ESCURO",
    "AZUL MARINHO", "AZUL CELESTE", "AZUL TURQUESA",
    "VERDE MILITAR", "VERDE MUSGO", "VERDE LIMA",
    "VERMELHO ESCURO", "VERMELHO VIVO", "BORDO",
    "VINHO", "MARROM ESCURO", "MARROM CLARO",
    "BEIGE", "BEIGE ESCURO", "BEIGE CLARO",
    "CINZA ESCURO", "CINZA CLARO", "CINZA MEDIO",
    "PRETO FOSCO", "PRETO BRILHANTE",
    "BRANCO NEVE", "BRANCO GELO", "BRANCO PEROLA",
    "PRATA ESCURO", "PRATA CLARO", "DOURADO ESCURO"
]

CORES_EQUIVALENCIAS = {
    "BLACK": "PRETO",
    "WHITE": "BRANCO",
    "GREY": "CINZA",
    "IVORY": "BEGE",
    "BROWN": "MARROM",
    "COCONUT": "MARROM",
    "ALABASTER": "BEGE",
    "ALUMINIUM": "PRATA",
    "BISCUIT": "BEGE",
    "FAWN": "BEGE",
    "PRALINE": "MARROM",
    "VANILLA": "BRANCO",
    "TRUE WHITE": "BRANCO",
    "MIDNIGHT BLUE": "AZUL",
    "GRAFITE": "CINZA",
    "ROYAL": "AZUL",
    "AZUL ROYAL": "AZUL",
    "CARAMELO": "MARROM",
    "CAFE": "MARROM",
    "CAFÉ": "MARROM",
    "ALPINO": "BRANCO",
    "NAVY": "AZUL",
    "ROSE": "ROSA",
    "LILAS": "ROSA",
    "OFF WHITE": "BRANCO",
    "OFF-WHITE": "BRANCO",
    "NEVE": "BRANCO",
    "GELO": "BRANCO",
    "PEDRA": "CINZA",
    "CIMENTO": "CINZA",
    "CONCRETO": "CINZA",
    "ARDOISIA": "CINZA",
    "CARVAO": "PRETO",
    "CARVÃO": "PRETO",
    "ESPRESSO": "MARROM",
    "CAFE ESCURO": "MARROM",
    "MEL": "AMARELO",
    "BRONZE": "MARROM",
    "COBRE ESCURO": "MARROM",
    "AZUL MARINHO": "AZUL",
    "AZUL CELESTE": "AZUL",
    "AZUL TURQUESA": "AZUL",
    "VERDE MILITAR": "VERDE",
    "VERDE MUSGO": "VERDE",
    "VERDE LIMA": "VERDE",
    "VERMELHO ESCURO": "VERMELHO",
    "VERMELHO VIVO": "VERMELHO",
    "BORDO": "VERMELHO",
    "VINHO": "VERMELHO",
    "MARROM ESCURO": "MARROM",
    "MARROM CLARO": "MARROM",
    "BEIGE": "BEGE",
    "BEIGE ESCURO": "BEGE",
    "BEIGE CLARO": "BEGE",
    "CINZA ESCURO": "CINZA",
    "CINZA CLARO": "CINZA",
    "CINZA MEDIO": "CINZA",
    "PRETO FOSCO": "PRETO",
    "PRETO BRILHANTE": "PRETO",
    "BRANCO NEVE": "BRANCO",
    "BRANCO GELO": "BRANCO",
    "BRANCO PEROLA": "BRANCO",
    "PRATA ESCURO": "PRATA",
    "PRATA CLARO": "PRATA",
    "DOURADO ESCURO": "DOURADO",
    "FUME": "CINZA",
    "FUMÊ": "CINZA",
    "AREIA": "BEGE",
    "PALHA": "BEGE",
    "TERRA": "MARROM",
    "FERRO": "CINZA",
    "CHUMBO": "CINZA",
    "GRAFITE ESCURO": "CINZA",
    "GRAFITE CLARO": "CINZA",
}


def cor_nome(nome):
    t = norm(nome)
    cores_ordenadas = sorted(CORES, key=len, reverse=True)
    for cor in cores_ordenadas:
        if re.search(rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])", t):
            return cor
    return ""


CODIGOS_INTERNOS = [
    r"JP\d{1,2}",
    r"SC\d{1,3}",
    r"TEC\d+",
    r"BK\d*",
    r"REF\d+",
    r"COD\d+",
    r"CÓD\d+",
    r"ITEM\d+",
    r"SKU\d+",
    r"MODELO\s*\d+",
    r"MODELO\s*[A-Z]\d*",
]


def remover_codigos_internos(t):
    for padrao in CODIGOS_INTERNOS:
        t = re.sub(padrao, " ", t)
    t = re.sub(r"\b\d{2,}\b", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def extrair_percentual_screen(texto):
    t = norm(texto)
    m = re.search(r"(\d+(?:[.,]\d+)?)%", t)
    if m:
        return m.group(1).replace(",", ".")
    return ""


def remover_ruido_nomenclatura(t):
    ruido = [
        r"\bROLO\b", r"\bROLÔ\b", r"\bROMANA\b", r"\bROMANA\s+TETO\b", r"\bROMANA\s+DE\s+TETO\b",
        r"\bTECIDO\b", r"\bTEC\b", r"\bSC\b", r"\bTECRLSC\b", r"\bTECRLBK\b", r"\bTECRL\b",
        r"\bIMPORTADO\b", r"\bIMPORTADA\b", r"\bCOPIA\b", r"\bCÓPIA\b",
        r"\bLARGURA\b", r"\bMETRAGEM\b",
        r"\b\d+[.,]?\d*\s*[Mm]\b",
        r"\b\d+[.,]?\d*\s*[Mm][Mm]\b",
        r"\bJP\b",
        r"\bTR\b",
    ]
    for r in ruido:
        t = re.sub(r, " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


TERMOS_EXCLUIR_TRANSLUCIDA = [
    "ENTRETELA", "FORRO", "VERTINETT", "VERTICAL", "FITA", "PLASTICA", "PLÁSTICA",
    "ACESSORIO", "ACESSÓRIO", "COMPONENTE", "VOIL", "GAZE", "GASE", "CORTINA", "CORTINAS"
]


def eh_excluido_translucida(nome):
    t = norm(nome)
    for termo in TERMOS_EXCLUIR_TRANSLUCIDA:
        if termo in t:
            return termo
    return None


def excluir_por_regras(produto):
    t = norm(produto["nome"])
    gt = norm(produto["grupo_tecnico"])
    ft = norm(produto["familia_tecnica"])
    mt = norm(produto["material_tecido"])
    grupo = norm(produto["grupo_produto"])
    origem = norm(produto["origem"])

    for termo in ["CORTINA", "CORTINAS", "TECIDO CORTINA", "TECIDOS CORTINAS",
                  "VOIL", "GAZE", "GASE", "LINHO DE CORTINA"]:
        if termo in t or termo in gt or termo in ft or termo in mt or termo in origem:
            return f"CORTINA ({termo})"

    if "LINHO" in t or "LINHO" in mt:
        if not any(k in t for k in ["SCREEN", "BLACKOUT", "BK ", "TRANSLUCID", "ROLO", "ROMANA", "PAINEL", "VERTICAL"]):
            return "LINHO_CORTINA_SEM_EVIDENCIA_PERSIANA"

    if "VERTICAL" in t or "VERTICAL" in gt or "VERTICAL" in ft:
        return "VERTICAL"

    if "DOUBLE VISION" in t or "DOUBLE_VISION" in t or "DOUBLEVISION" in t:
        return "DOUBLE_VISION"

    if "PAINEL" in t:
        if not ("TECIDO" in t or "BASE" in t or "MATERIA" in t):
            return "PAINEL_PRODUTO_FINAL"

    if "ROLO" in t or "ROLÔ" in t:
        if any(k in t for k in ["KIT", "COMPLETO", "MOTORIZADO", "AUTOMATICO", "COMANDO", "ACABADO", "FINAL"]):
            return "ROLO_PRODUTO_FINAL"
        if not ("TECIDO" in t or "BASE" in t or "SCREEN" in t or "BLACKOUT" in t or "BK " in t or "TRANSLUCID" in t):
            return "ROLO_PRODUTO_FINAL_SEM_INDICADOR_TECIDO"

    if "ROMANA" in t:
        if any(k in t for k in ["KIT", "COMPLETO", "MOTORIZADO", "AUTOMATICO", "COMANDO", "ACABADO", "FINAL", "TELHADO", "TETO"]):
            return "ROMANA_PRODUTO_FINAL"

    if "ROMANA TETO" in t or "ROMANA_TETO" in t or "ROMANA DE TETO" in t:
        return "ROMANA_TETO_PRODUTO_FINAL"

    for termo in ["COMPONENTE", "COMANDO", "TRILHO", "CORRENTE", "MOTOR", "BASE", "TAMPA", "SUPORTE", "ACESSORIO", "ACESSÓRIO",
                  "BUCHA", "CANAO", "CANÃO", "BRACKET", "BRACKETS", "FREIO", "EMBREAGEM", "CABO", "FIO", "CORDA", "CORDÃO",
                  "PINO", "ANEL", "ARGOLA", "GANCHO", "PRESILHA", "TRAVA", "FECHO", "BOTO", "BOTÃO", "INTERRUPTOR",
                  "CONTROLE", "REMOTO", "RECEPTOR", "FONTE", "CARREGADOR", "BATERIA", "PILHA"]:
        if termo in t or termo in gt or termo in ft or termo in mt:
            return f"COMPONENTE_ACESSORIO ({termo})"

    if "COMPONENTES" in gt or "ACESSORIOS" in gt or "ACESSÓRIOS" in gt:
        return "GRUPO_COMPONENTES"

    return None


def classificar_familia_tecido(nome, grupo_tecnico, familia_tecnica, material_tecido):
    t = norm(nome)
    gt = norm(grupo_tecnico)
    ft = norm(familia_tecnica)
    mt = norm(material_tecido)

    eh_tecido_persiana = False
    if "TECIDOS_ROLO_ROMANA_PAINEL" in gt:
        eh_tecido_persiana = True
    if "TECIDO" in gt and "CORTINA" not in gt:
        eh_tecido_persiana = True
    if "TECIDO" in ft and "CORTINA" not in ft:
        eh_tecido_persiana = True

    if not eh_tecido_persiana:
        if "SCREEN" in mt or "BLACKOUT" in mt or "BK " in f" {mt} " or "TRANSLUCID" in mt:
            eh_tecido_persiana = True

    if not eh_tecido_persiana:
        return "NAO_TECIDO_PERSIANA"

    if "SCREEN" in t or "SCREEN" in mt or "SCREEN" in ft:
        if "BLACKOUT" in t or "BK" in t.split():
            return "SCREEN_BLACKOUT"
        pct = extrair_percentual_screen(t)
        if pct:
            return f"SCREEN_{pct}"
        return "SCREEN"

    if "BLACKOUT" in t or t.startswith("BK ") or " BK " in f" {t} ":
        if any(k in t for k in ["ROMANA BK", "ROMANA_BK", "ROLO BK", "ROLÔ BK", "VERTICAL BK", "VERTICAL_BK"]):
            return "BLACKOUT_PRODUTO_FINAL"
        return "BLACKOUT"

    for fam in ["NAPOLES", "NÁPOLES", "BRISK", "PRESTIGE", "DENVER", "MADRI", "LUGANO", "VIENA", "SHANTUNG", "PIMPOINT", "SUPERBLACK"]:
        if fam in t:
            if any(k in t for k in ["ROMANA", "ROLO", "ROLÔ", "VERTICAL", "KIT", "COMPLETO", "MOTORIZADO"]):
                return "BLACKOUT_PRODUTO_FINAL"
            return "BLACKOUT"

    excluido = eh_excluido_translucida(nome)
    if excluido:
        return f"EXCLUIDO_TRANSLUCIDA_{excluido}"

    if "TRANSLUCIDO" in t or "TRANSLUCIDA" in t:
        return "TRANSLUCIDA"

    if "TRANSLUCIDO" in mt or "TRANSLUCIDA" in mt:
        return "TRANSLUCIDA"

    for fam in ["AQUARELA", "RAMI", "IMALAIA", "CLASSIC", "CHIFFON"]:
        if fam in t:
            return "TRANSLUCIDA"

    if "NAPOLES" in t and "TRANSLUCID" in t:
        return "TRANSLUCIDA"

    return "OUTRO"


NOMES_COMERCIAIS_VALIDOS = [
    "STANDARD", "OPEN", "ALKENZ", "ALKENS", "NAPOLES", "NÁPOLES",
    "BRISK", "CLASSIC", "AQUARELA", "RAMI", "IMALAIA",
    "PRESTIGE", "DENVER", "MADRI", "LUGANO", "VIENA",
    "SHANTUNG", "PIMPOINT", "SUPERBLACK", "CHIFFON",
    "PREMIUM", "NACIONAL", "ONE", "TJS"
]

TERMOS_NAO_FAMILIA = [
    "SC", "TEC", "TECRLSC", "ROLO", "ROLÔ", "ROMANA", "TETO",
    "IMPORTADO", "IMPORTADA", "COPIA", "CÓPIA",
    "BK", "BLACKOUT", "SCREEN", "TRANSLUCIDA", "TRANSLUCIDO",
    "TR", "VOIL", "GAZE", "GASE", "CORTINA",
    "ENTRETELA", "FORRO", "VERTINETT", "VERTICAL", "FITA",
    "PLASTICA", "PLÁSTICA", "ACESSORIO", "ACESSÓRIO",
    "COMPONENTE", "KIT", "COMPLETO", "MOTORIZADO",
    "AUTOMATICO", "COMANDO", "ACABADO", "FINAL",
    "PAINEL", "BASE", "MATERIA", "LINHO",
    "JP",
]


def limpar_nome_comercial(t, pct=None):
    t = remover_ruido_nomenclatura(t)
    t = remover_codigos_internos(t)

    if pct:
        t = re.sub(rf"SCREEN\s*{pct}%", "", t)
        t = re.sub(rf"SCREEN{pct}%", "", t)
        t = re.sub(rf"\b{pct}%\b", "", t)
        t = re.sub(rf"\b{pct.replace('.', '')}\b", "", t)

    t = re.sub(r"SCREEN", "", t)
    t = re.sub(r"BLACKOUT", "", t)
    t = re.sub(r"\bBK\b", "", t)
    t = re.sub(r"TRANSLUCIDO", "", t)
    t = re.sub(r"TRANSLUCIDA", "", t)

    cores_ordenadas = sorted(CORES, key=len, reverse=True)
    for cor in cores_ordenadas:
        t = re.sub(rf"(?<![A-Z0-9]){cor}(?![A-Z0-9])", " ", t)

    for termo in TERMOS_NAO_FAMILIA:
        t = re.sub(rf"\b{termo}\b", " ", t)

    t = re.sub(r"\s+", " ", t).strip(" -_")
    return t


def extrair_nome_comercial_screen(nome, pct):
    t = norm(nome)
    t = limpar_nome_comercial(t, pct)

    for nome_valido in NOMES_COMERCIAIS_VALIDOS:
        if re.search(rf"\b{nome_valido}\b", t):
            return nome_valido

    return "NOME_COMERCIAL_PENDENTE"


def extrair_nome_comercial_blackout(nome):
    t = norm(nome)
    t = limpar_nome_comercial(t)

    for nome_valido in NOMES_COMERCIAIS_VALIDOS:
        if re.search(rf"\b{nome_valido}\b", t):
            return nome_valido, ""

    return "NOME_COMERCIAL_PENDENTE", ""


def extrair_nome_comercial_translucida(nome):
    t = norm(nome)
    t = limpar_nome_comercial(t)

    for nome_valido in NOMES_COMERCIAIS_VALIDOS:
        if re.search(rf"\b{nome_valido}\b", t):
            return nome_valido, ""

    return "NOME_COMERCIAL_PENDENTE", ""


def resolver_fornecedor(conn, produto):
    if produto.get("fornecedor_padrao_id"):
        f = conn.execute(text("SELECT id, nome FROM fornecedores WHERE id = :id"),
                         {"id": produto["fornecedor_padrao_id"]}).mappings().first()
        if f:
            return f["id"], f["nome"], "fornecedor_padrao_id", "ALTA"

    if produto.get("fornecedores"):
        try:
            ids = [int(x.strip()) for x in produto["fornecedores"].split(",") if x.strip().isdigit()]
            if ids:
                f = conn.execute(text("SELECT id, nome FROM fornecedores WHERE id = :id"),
                                 {"id": ids[0]}).mappings().first()
                if f:
                    return f["id"], f["nome"], "fornecedores_csv", "MEDIA"
        except:
            pass

    if produto.get("nome_fornecedor"):
        nome_forn = norm(produto["nome_fornecedor"])
        f = conn.execute(text("SELECT id, nome FROM fornecedores WHERE upper(nome) = :nome"),
                         {"nome": nome_forn}).mappings().first()
        if f:
            return f["id"], f["nome"], "nome_fornecedor", "MEDIA"

    if produto.get("origem"):
        f = conn.execute(text("SELECT id, nome FROM fornecedores WHERE upper(nome) = :origem"),
                         {"origem": norm(produto["origem"])}).mappings().first()
        if f:
            return f["id"], f["nome"], "origem", "BAIXA"

    return None, "FORNECEDOR_PENDENTE", "nao_resolvido", "SEM_CONFIANCA"


def main():
    with engine.connect() as conn:
        db = conn.execute(text("SELECT current_database()")).scalar()
        print(f"Banco: {db}")

        if db != "smarttec_erp_dev":
            raise RuntimeError(f"ABORTADO: banco atual = {db}")

        produtos = conn.execute(text("""
            SELECT
                id,
                empresa_id,
                nome,
                codigo_interno,
                codigo_barras,
                grupo_produto,
                grupo_tecnico,
                familia_tecnica,
                modelo_tecnico,
                fornecedor_padrao_id,
                valor_custo,
                custo_final,
                unidade,
                unidade_venda,
                unidade_compra,
                situacao,
                ativo,
                cor,
                cor_componente,
                variacao_cor,
                material_tecido,
                descricao,
                origem,
                fornecedores,
                nome_fornecedor,
                largura
            FROM produtos
            WHERE empresa_id = 1
              AND ativo = true
            ORDER BY nome
        """)).mappings().all()

        print(f"Total de candidatos ativos empresa 1: {len(produtos)}")

        stats_excluidos = defaultdict(int)

        familias_dict = defaultdict(lambda: {
            "categoria": None,
            "nome_comercial": None,
            "fornecedor_id": None,
            "fornecedor_nome": None,
            "fornecedor_metodo": None,
            "fornecedor_confianca": None,
            "cores": set(),
            "cores_originais": set(),
            "larguras": set(),
            "custos_atuais": [],
            "custos_historicos": [],
            "fontes": [],
            "qtde_fontes": 0,
            "confianca": "PENDENTE",
            "pendencia": [],
        })

        for p in produtos:
            motivo_exclusao = excluir_por_regras(p)
            if motivo_exclusao:
                for k, v in {
                    "CORTINA": "cortina",
                    "VERTICAL": "vertical",
                    "DOUBLE_VISION": "double_vision",
                    "PAINEL_PRODUTO_FINAL": "painel_final",
                    "ROLO_PRODUTO_FINAL": "rolo_final",
                    "ROMANA_PRODUTO_FINAL": "romana_final",
                    "ROMANA_TETO_PRODUTO_FINAL": "romana_teto_final",
                    "COMPONENTE_ACESSORIO": "componente_acessorio",
                    "GRUPO_COMPONENTES": "grupo_componentes",
                    "LINHO_CORTINA": "linho_sem_evidencia",
                }.items():
                    if k in motivo_exclusao:
                        stats_excluidos[v] += 1
                        break
                else:
                    stats_excluidos["outro"] += 1
                continue

            categoria = classificar_familia_tecido(
                p["nome"],
                p["grupo_tecnico"],
                p["familia_tecnica"],
                p["material_tecido"]
            )

            if categoria.startswith("EXCLUIDO_TRANSLUCIDA"):
                termo = categoria.replace("EXCLUIDO_TRANSLUCIDA_", "")
                stats_excluidos[f"translucida_excluida_{termo.lower()}"] += 1
                continue

            if categoria not in ["SCREEN", "SCREEN_0.5", "SCREEN_1", "SCREEN_3", "SCREEN_5", "SCREEN_10",
                                 "BLACKOUT", "TRANSLUCIDA"]:
                if categoria == "SCREEN_BLACKOUT":
                    stats_excluidos["screen_blackout_produto_final"] += 1
                elif categoria == "BLACKOUT_PRODUTO_FINAL":
                    stats_excluidos["blackout_produto_final"] += 1
                elif categoria == "TRANSLUCIDA_CORTINA":
                    stats_excluidos["translucida_cortina"] += 1
                elif categoria == "NAO_TECIDO_PERSIANA":
                    stats_excluidos["nao_tecido_persiana"] += 1
                else:
                    stats_excluidos["outro"] += 1
                continue

            cat_base = "SCREEN" if categoria.startswith("SCREEN_") else categoria

            cor_raw = (
                norm(p["cor_componente"])
                or norm(p["variacao_cor"])
                or norm(p["cor"])
                or cor_nome(p["nome"])
            )
            cor = CORES_EQUIVALENCIAS.get(cor_raw, cor_raw) if cor_raw else ""
            if cor and cor not in CORES:
                cor = ""

            forn_id, forn_nome, forn_metodo, forn_confianca = resolver_fornecedor(conn, p)

            if cat_base == "SCREEN":
                pct = extrair_percentual_screen(p["nome"])
                nome_comercial = extrair_nome_comercial_screen(p["nome"], pct)
                if pct:
                    cat_display = f"SCREEN {pct}%"
                else:
                    cat_display = "SCREEN"
                    pct = "ND"
            elif cat_base == "BLACKOUT":
                nome_comercial, resto = extrair_nome_comercial_blackout(p["nome"])
                cat_display = "BLACKOUT"
            elif cat_base == "TRANSLUCIDA":
                nome_comercial, resto = extrair_nome_comercial_translucida(p["nome"])
                cat_display = "TRANSLÚCIDA"
            else:
                continue

            if nome_comercial == "NOME_COMERCIAL_PENDENTE":
                pend_nome = "NOME_COMERCIAL_PENDENTE"
            else:
                pend_nome = None

            if forn_id is None:
                pend_forn = "FORNECEDOR_PENDENTE"
            else:
                pend_forn = None

            key = (cat_display, nome_comercial, forn_id if forn_id else "SEM_FORNECEDOR")

            fam = familias_dict[key]
            fam["categoria"] = cat_display
            fam["nome_comercial"] = nome_comercial
            fam["fornecedor_id"] = forn_id
            fam["fornecedor_nome"] = forn_nome
            fam["fornecedor_metodo"] = forn_metodo
            fam["fornecedor_confianca"] = forn_confianca
            if cor:
                fam["cores"].add(cor)
                fam["cores_originais"].add(cor_raw)
            if p.get("largura") and p["largura"] > 0:
                fam["larguras"].add(str(p["largura"]))

            custo_valor = float(p["valor_custo"] or 0)
            custo_final = float(p["custo_final"] or 0)

            if custo_final > 0:
                fam["custos_atuais"].append({
                    "valor": custo_final,
                    "fornecedor": forn_nome,
                    "origem": p.get("origem", ""),
                    "largura": p.get("largura"),
                    "registro_id": p["id"],
                    "tipo": "atual"
                })
            elif custo_valor > 0:
                fam["custos_historicos"].append({
                    "valor": custo_valor,
                    "fornecedor": forn_nome,
                    "origem": p.get("origem", ""),
                    "largura": p.get("largura"),
                    "registro_id": p["id"],
                    "tipo": "historico"
                })

            fam["fontes"].append({
                "id": p["id"],
                "nome": p["nome"],
                "cor": cor_raw,
                "fornecedor": forn_nome,
                "custo": custo_final if custo_final > 0 else custo_valor,
                "origem": p.get("origem", ""),
                "largura": p.get("largura"),
            })
            fam["qtde_fontes"] += 1

            if pend_nome:
                fam["pendencia"].append(pend_nome)
            if pend_forn:
                fam["pendencia"].append(pend_forn)

        for key, fam in familias_dict.items():
            custos_atuais = fam["custos_atuais"]
            custos_historicos = fam["custos_historicos"]

            custos_unicos = set()
            for c in custos_atuais:
                custos_unicos.add(round(c["valor"], 2))

            if len(custos_unicos) == 0:
                if custos_historicos:
                    fam["confianca"] = "CUSTO_HISTORICO"
                else:
                    fam["confianca"] = "SEM_CUSTO"
                    if "SEM_CUSTO" not in fam["pendencia"]:
                        fam["pendencia"].append("SEM_CUSTO")
            elif len(custos_unicos) == 1:
                fam["confianca"] = "CONFIRMADO"
            else:
                fam["confianca"] = "CONFLITO_CUSTO"
                if "CONFLITO_CUSTO" not in fam["pendencia"]:
                    fam["pendencia"].append("CONFLITO_CUSTO")

            fam["pendencia"] = list(set(fam["pendencia"]))

        familias_prontas = []
        familias_pendentes_nome = []
        familias_pendentes_forn = []
        familias_pendentes_custo = []
        familias_pendentes_sem_custo = []
        familias_excluidas_nao_tecido = []

        for key, fam in sorted(familias_dict.items()):
            if fam["confianca"] == "CONFIRMADO" and not fam["pendencia"]:
                familias_prontas.append((key, fam))
            else:
                pendencias = fam["pendencia"]
                if "NOME_COMERCIAL_PENDENTE" in pendencias:
                    familias_pendentes_nome.append((key, fam))
                elif "FORNECEDOR_PENDENTE" in pendencias:
                    familias_pendentes_forn.append((key, fam))
                elif "CONFLITO_CUSTO" in pendencias:
                    familias_pendentes_custo.append((key, fam))
                elif "SEM_CUSTO" in pendencias or "CUSTO_HISTORICO" in pendencias:
                    familias_pendentes_sem_custo.append((key, fam))
                else:
                    familias_pendentes_nome.append((key, fam))

        print("\n" + "=" * 160)
        print(" FASE 8E.5J.4 - LIMPEZA FINAL DE FAMÍLIA + RESOLUÇÃO DE FORNECEDOR")
        print("=" * 160)

        print("\n" + "=" * 160)
        print(" A) PRONTO_PARA_CADASTRO")
        print("=" * 160)
        print(f"{'CATEGORIA':<18} | {'FAMILIA_COMERCIAL':<35} | {'FORNECEDOR':<25} | {'METODO':<20} | {'CONFIANCA':<10} | {'CORES':<30} | {'LARGURAS':<15} | {'CUSTO':<10} | {'QTD':>3}")
        print("-" * 220)

        for key, fam in familias_prontas:
            cat, nome_com, forn_id = key
            forn = fam["fornecedor_nome"][:24] if fam["fornecedor_nome"] else "PENDENTE"
            metodo = fam["fornecedor_metodo"][:19] if fam["fornecedor_metodo"] else ""
            conf_forn = fam["fornecedor_confianca"][:9] if fam["fornecedor_confianca"] else ""
            cores_str = ", ".join(sorted(fam["cores"]))[:29]
            larguras_str = ", ".join(sorted(fam["larguras"]))[:14]
            custo = fam["custos_atuais"][0]["valor"] if fam["custos_atuais"] else 0
            nome_canonica = f"{cat} {nome_com}"[:34]
            qtd = fam["qtde_fontes"]
            print(f"{cat:<18} | {nome_canonica:<35} | {forn:<25} | {metodo:<20} | {conf_forn:<10} | {cores_str:<30} | {larguras_str:<15} | {custo:.2f} | {qtd:>3}")

        print("\n" + "=" * 160)
        print(" B) PENDENTES")
        print("=" * 160)

        def imprimir_pendentes(titulo, lista):
            if not lista:
                return
            print(f"\n--- {titulo} ---")
            print(f"{'CATEGORIA':<18} | {'FAMILIA_COMERCIAL':<35} | {'FORNECEDOR':<25} | {'METODO':<20} | {'CONFIANCA':<10} | {'CORES':<30} | {'LARGURAS':<15} | {'CONFIANCA_CUSTO':<18} | {'PENDENCIA'}")
            print("-" * 220)
            for key, fam in lista:
                cat, nome_com, forn_id = key
                forn = fam["fornecedor_nome"][:24] if fam["fornecedor_nome"] else "PENDENTE"
                metodo = fam["fornecedor_metodo"][:19] if fam["fornecedor_metodo"] else ""
                conf_forn = fam["fornecedor_confianca"][:9] if fam["fornecedor_confianca"] else ""
                cores_str = ", ".join(sorted(fam["cores"]))[:29]
                larguras_str = ", ".join(sorted(fam["larguras"]))[:14]
                conf_custo = fam["confianca"][:17]
                pend = ", ".join(fam["pendencia"])
                nome_canonica = f"{cat} {nome_com}"[:34]
                print(f"{cat:<18} | {nome_canonica:<35} | {forn:<25} | {metodo:<20} | {conf_forn:<10} | {cores_str:<30} | {larguras_str:<15} | {conf_custo:<18} | {pend}")

        imprimir_pendentes("NOME_COMERCIAL_PENDENTE", familias_pendentes_nome)
        imprimir_pendentes("FORNECEDOR_PENDENTE", familias_pendentes_forn)
        imprimir_pendentes("CONFLITO_CUSTO", familias_pendentes_custo)
        imprimir_pendentes("PENDENTE_CUSTO / CUSTO_HISTORICO", familias_pendentes_sem_custo)

        total_screen = sum(1 for k, v in familias_dict.items() if k[0].startswith("SCREEN"))
        total_blackout = sum(1 for k, v in familias_dict.items() if k[0] == "BLACKOUT")
        total_translucida = sum(1 for k, v in familias_dict.items() if k[0] == "TRANSLÚCIDA")
        total_familias = len(familias_dict)
        total_prontas = len(familias_prontas)
        total_pendentes = len(familias_pendentes_nome) + len(familias_pendentes_forn) + len(familias_pendentes_custo) + len(familias_pendentes_sem_custo)
        total_produtos_previstos = sum(len(v["cores"]) for v in familias_dict.values())

        screen_confirmadas = sum(1 for k, v in familias_dict.items() if k[0].startswith("SCREEN") and v["confianca"] == "CONFIRMADO" and not v["pendencia"])
        screen_pendentes = total_screen - screen_confirmadas
        screen_cores = set()
        for k, v in familias_dict.items():
            if k[0].startswith("SCREEN"):
                screen_cores.update(v["cores"])

        blackout_confirmadas = sum(1 for k, v in familias_dict.items() if k[0] == "BLACKOUT" and v["confianca"] == "CONFIRMADO" and not v["pendencia"])
        blackout_pendentes = total_blackout - blackout_confirmadas
        blackout_cores = set()
        for k, v in familias_dict.items():
            if k[0] == "BLACKOUT":
                blackout_cores.update(v["cores"])

        translucida_confirmadas = sum(1 for k, v in familias_dict.items() if k[0] == "TRANSLÚCIDA" and v["confianca"] == "CONFIRMADO" and not v["pendencia"])
        translucida_pendentes = total_translucida - translucida_confirmadas
        translucida_cores = set()
        for k, v in familias_dict.items():
            if k[0] == "TRANSLÚCIDA":
                translucida_cores.update(v["cores"])

        print("\n" + "=" * 160)
        print(" C) RESUMO")
        print("=" * 160)
        print(f"\nSCREEN:")
        print(f"  Famílias comerciais confirmadas: {screen_confirmadas}")
        print(f"  Famílias pendentes:              {screen_pendentes}")
        print(f"  Cores previstas:                 {', '.join(sorted(screen_cores)) if screen_cores else 'NENHUMA'}")

        print(f"\nBLACKOUT:")
        print(f"  Famílias comerciais confirmadas: {blackout_confirmadas}")
        print(f"  Famílias pendentes:              {blackout_pendentes}")
        print(f"  Cores previstas:                 {', '.join(sorted(blackout_cores)) if blackout_cores else 'NENHUMA'}")

        print(f"\nTRANSLÚCIDA:")
        print(f"  Famílias comerciais confirmadas: {translucida_confirmadas}")
        print(f"  Famílias pendentes:              {translucida_pendentes}")
        print(f"  Cores previstas:                 {', '.join(sorted(translucida_cores)) if translucida_cores else 'NENHUMA'}")

        print(f"\nTOTAL:")
        print(f"  Famílias PRONTO_PARA_CADASTRO:   {total_prontas}")
        print(f"  Produtos finais previstos:       {total_produtos_previstos}")
        print(f"  Pendentes NOME_COMERCIAL:        {len(familias_pendentes_nome)}")
        print(f"  Pendentes FORNECEDOR:            {len(familias_pendentes_forn)}")
        print(f"  Pendentes CONFLITO_CUSTO:        {len(familias_pendentes_custo)}")
        print(f"  Pendentes SEM_CUSTO/HISTORICO:   {len(familias_pendentes_sem_custo)}")

        print(f"\nITENS EXCLUÍDOS:")
        for k, v in sorted(stats_excluidos.items()):
            print(f"  {k}: {v}")
        print(f"  TOTAL EXCLUÍDOS: {sum(stats_excluidos.values())}")

        print("\n" + "=" * 160)
        print(" CATÁLOGO LEGADO ROMANA TETO (apenas referência - IDs 542-545, 1192-1195)")
        print("=" * 160)

        legados = conn.execute(text("""
            SELECT
                id, nome, modelo_tecnico, grupo_produto, grupo_tecnico,
                familia_tecnica, cor, cor_componente, variacao_cor,
                valor_custo, custo_final, situacao, ativo
            FROM produtos
            WHERE empresa_id = 1
              AND (modelo_tecnico = 'ROMANA_TETO'
                   OR nome ILIKE '%ROMANA TETO%'
                   OR nome ILIKE '%ROMANA DE TETO%')
            ORDER BY id
        """)).mappings().all()

        print(f"\nRegistros encontrados: {len(legados)}")
        ativos = [p for p in legados if p["ativo"]]
        inativos = [p for p in legados if not p["ativo"]]
        print(f"  Ativos: {len(ativos)}")
        print(f"  Inativos: {len(inativos)}")

        for label, items in [("FORTALEZA ATIVA", ativos), ("FORTALEZA INATIVA", inativos)]:
            if items:
                print(f"\n  {label}:")
                for p in items:
                    cor = norm(p["cor_componente"] or p["variacao_cor"] or p["cor"] or cor_nome(p["nome"]))
                    print(f"    ID {p['id']}: {p['nome']} | Cor: {cor} | Custo: {p['custo_final']:.2f} | Situação: {p['situacao']}")

if __name__ == "__main__":
    main()