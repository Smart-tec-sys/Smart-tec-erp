# Cole isto diretamente no arquivo imp.py pelo VS Code
# Selecione todo o conteúdo (Ctrl+A), delete, e cole isto:

import pandas as pd
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "smarttec_erp"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )


def val(v):
    if pd.isna(v) or v is None:
        return 0.0
    try:
        return float(str(v).strip().replace(".", "").replace(",", "."))
    except:
        return 0.0


def dat(v):
    if pd.isna(v) or v is None:
        return None
    s = str(v).strip()
    for f in ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(s, f)
        except:
            pass
    return None


def stg(v, upper=False):
    if pd.isna(v) or v is None:
        return None
    s = str(v).strip()
    if s.lower() in ["nan", "none", ""]:
        return None
    return s.upper() if upper else s


print("Carregando Excel...")
xls = pd.ExcelFile("dados/compras.xlsx")
print("Abas:", xls.sheet_names)

d0 = pd.read_excel(xls, 0)
d1 = pd.read_excel(xls, 1)
d2 = pd.read_excel(xls, 2)
d3 = pd.read_excel(xls, 3)

print("Conectando banco...")
conn = get_conn()
cur = conn.cursor()
print("Banco OK!")

print("1. Fornecedores...")
for n in d0["Fornecedor"].dropna().unique():
    cur.execute(
        "INSERT INTO fornecedores (nome) VALUES (%s) ON CONFLICT DO NOTHING",
        (str(n).strip().upper(),)
    )
conn.commit()
print("   OK")

print("2. Compras...")
ok = 0
for idx, row in d0.iterrows():
    try:
        num = row.get("Numero da compra") or row.get("N da compra")
        if pd.isna(num):
            continue
        n = int(float(str(num)))
        cur.execute("SELECT id FROM fornecedores WHERE nome=%s",
                    (str(row.get("Fornecedor", "")).strip().upper(),))
        f = cur.fetchone()
        fid = f < a href = "" class = "citation-link" target = "_blank" style = "vertical-align: super; font-size: 0.8em; margin-left: 3px;" > [0] </ a > if f else None
        ch = stg(row.get("Chave NF-e"))
        if ch and len(ch) < 40:
            ch = None
        cur.execute(
            "INSERT INTO compras (numero_compra,numero_nf,chave_nfe,fornecedor_id,"
            "total_produtos,valor_frete,desconto_valor,total_compra,data_emissao,"
            "pagar_frete,transportadora,observacao,status,cadastrado_por,"
            "cadastrado_em,modificado_em) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (numero_compra) DO UPDATE SET "
            "total_compra=EXCLUDED.total_compra",
            (n, stg(row.get("Numero da NF-e")), ch, fid,
             val(row.get("Total dos produtos")), val(row.get("Valor frete")),
             val(row.get("Desconto valor")), val(row.get("Total da compra")),
             dat(row.get("Data de emissao")),
             str(row.get("Pagar frete?", "")).lower() in ["sim", "s"],
             stg(row.get("Transportadora")), stg(row.get("Observacoes")),
             "CONFIRMADA", stg(row.get("Cadastrado por")),
             dat(row.get("Cadastrado em")), dat(row.get("Modificado em"))))
        ok += 1
    except Exception as e:
        if ok < 5:
            print(f"  ERR {idx}: {e}")
conn.commit()
print(f"   OK: {ok}")

print("3. Historico...")
ok = 0
for idx, row in d1.iterrows():
    try:
        cod = row.get("Codigo")
        if pd.isna(cod):
            continue
        cur.execute("SELECT id FROM compras WHERE numero_compra=%s",
                    (int(float(str(cod))),))
        res = cur.fetchone()
        if not res:
            continue
        cur.execute(
            "INSERT INTO compras_historico "
            "(compra_id,data_evento,observacao,situacao,funcionario) "
            "VALUES (%s,%s,%s,%s,%s)",
            (res < a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;" > [0] </ a > , dat(row.get("Data")), stg(row.get("Observacao")),
             stg(row.get("Situacao")) or "Confirmada",
             stg(row.get("Funcionario"))))
        ok += 1
    except:
        pass
conn.commit()
print(f"   OK: {ok}")

print("4. Parcelas...")
ok = 0
ct = {}
for idx, row in d2.iterrows():
    try:
        cod = row.get("Codigo")
        if pd.isna(cod):
            continue
        cur.execute("SELECT id FROM compras WHERE numero_compra=%s",
                    (int(float(str(cod))),))
        res = cur.fetchone()
        if not res:
            continue
        cid = res < a href = "" class = "citation-link" target = "_blank" style = "vertical-align: super; font-size: 0.8em; margin-left: 3px;" > [0] </ a > 
        ct[cid] = ct.get(cid, 0) + 1
        cur.execute(
            "INSERT INTO compras_parcelas "
            "(compra_id,numero_parcela,vencimento,valor_parcela,"
            "forma_pagamento,observacao) VALUES (%s,%s,%s,%s,%s,%s)",
            (cid, ct[cid], dat(row.get("Vencimento")),
             val(row.get("Valor da parcela")),
             stg(row.get("Forma de pagamento")),
             stg(row.get("Observacao"))))
        ok += 1
    except:
        pass
conn.commit()
print(f"   OK: {ok}")

print("5. Itens...")
ok = 0
for idx, row in d3.iterrows():
    try:
        cod = row.get("Codigo")
        if pd.isna(cod):
            continue
        cur.execute("SELECT id FROM compras WHERE numero_compra=%s",
                    (int(float(str(cod))),))
        res = cur.fetchone()
        if not res:
            continue
        prod = stg(row.get("Produto"), upper=True)
        if not prod:
            continue
        cur.execute(
            "INSERT INTO compras_itens "
            "(compra_id,produto_desc,quantidade,unidade,"
            "custo_unitario,custo_total) VALUES (%s,%s,%s,%s,%s,%s)",
            (res < a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;" > [0] </ a > , prod, val(row.get("Quantidade")),
             stg(row.get("Unidade")) or "UN",
             val(row.get("Custo unitario")),
             val(row.get("Custo total"))))
        ok += 1
    except:
        pass
conn.commit()
print(f"   OK: {ok}")

cur.close()
conn.close()
print("CONCLUIDO!")
