import os

os.makedirs('backend', exist_ok=True)
os.makedirs('dados', exist_ok=True)

codigo = open('backend/importer_compras.py', 'w', encoding='utf-8')

codigo.write("""import pandas as pd
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST','localhost'),
        port=int(os.getenv('DB_PORT',5432)),
        dbname=os.getenv('DB_NAME','smarttec_erp'),
        user=os.getenv('DB_USER','postgres'),
        password=os.getenv('DB_PASSWORD','')
    )

def lv(v):
    if pd.isna(v) or v is None: return 0.0
    try: return float(str(v).strip().replace('.','').replace(',','.'))
    except: return 0.0

def ld(v):
    if pd.isna(v) or v is None: return None
    s = str(v).strip()
    for f in ['%d/%m/%Y %H:%M:%S','%d/%m/%Y','%Y-%m-%d %H:%M:%S','%Y-%m-%d']:
        try: return datetime.strptime(s, f)
        except: continue
    return None

def ls(v, u=False):
    if pd.isna(v) or v is None: return None
    s = str(v).strip()
    if s.lower() in ['nan','none','']: return None
    return s.upper() if u else s

def sn(v):
    if pd.isna(v) or v is None: return False
    return str(v).strip().lower() in ['sim','s','1','true']

def gf(nome, cur):
    if not nome or pd.isna(nome): return None
    cur.execute('SELECT id FROM fornecedores WHERE nome=%s',(str(nome).strip().upper(),))
    r = cur.fetchone()
    return r<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[0]</a> if r else None

def s1(df, conn):
    print('1. Fornecedores...')
    ok = 0
    with conn.cursor() as c:
        for n in df['Fornecedor'].dropna().unique():
            n = str(n).strip().upper()
            if not n: continue
            try:
                c.execute('INSERT INTO fornecedores (nome) VALUES (%s) ON CONFLICT DO NOTHING',(n,))
                ok += 1
            except: pass
    conn.commit()
    print('   OK:', ok)

def s2(df, conn):
    print('2. Compras...')
    ok = e = 0
    with conn.cursor() as c:
        for i, row in df.iterrows():
            try:
                num = row.get('Numero da compra') or row.get('N da compra')
                if pd.isna(num): continue
                n = int(float(str(num)))
                fid = gf(row.get('Fornecedor'), c)
                ch = ls(row.get('Chave NF-e'))
                if ch and len(ch) < 40: ch = None
                c.execute('INSERT INTO compras (numero_compra,numero_nf,chave_nfe,fornecedor_id,total_produtos,valor_frete,desconto_valor,total_compra,data_emissao,pagar_frete,transportadora,observacao,status,cadastrado_por,cadastrado_em,modificado_em) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (numero_compra) DO UPDATE SET total_compra=EXCLUDED.total_compra',
                    (n,ls(row.get('Numero da NF-e')),ch,fid,lv(row.get('Total dos produtos')),lv(row.get('Valor frete')),lv(row.get('Desconto valor')),lv(row.get('Total da compra')),ld(row.get('Data de emissao')),sn(row.get('Pagar frete?')),ls(row.get('Transportadora')),ls(row.get('Observacoes')),'CONFIRMADA',ls(row.get('Cadastrado por')),ld(row.get('Cadastrado em')),ld(row.get('Modificado em'))))
                ok += 1
            except Exception as ex:
                e += 1
                if e<=3: print('  ERR',i,ex)
    conn.commit()
    print('   OK:',ok,'Erros:',e)

def s3(df, conn):
    print('3. Historico...')
    ok = 0
    with conn.cursor() as c:
        for i, row in df.iterrows():
            try:
                cod = row.get('Codigo')
                if pd.isna(cod): continue
                c.execute('SELECT id FROM compras WHERE numero_compra=%s',(int(float(str(cod))),))
                r = c.fetchone()
                if not r: continue
                c.execute('INSERT INTO compras_historico (compra_id,data_evento,observacao,situacao,funcionario) VALUES (%s,%s,%s,%s,%s)',
                    (r<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[0]</a>,ld(row.get('Data')),ls(row.get('Observacao')),ls(row.get('Situacao')) or 'Confirmada',ls(row.get('Funcionario'))))
                ok += 1
            except: pass
    conn.commit()
    print('   OK:', ok)

def s4(df, conn):
    print('4. Parcelas...')
    ok = 0
    ct = {}
    with conn.cursor() as c:
        for i, row in df.iterrows():
            try:
                cod = row.get('Codigo')
                if pd.isna(cod): continue
                c.execute('SELECT id FROM compras WHERE numero_compra=%s',(int(float(str(cod))),))
                r = c.fetchone()
                if not r: continue
                cid = r<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[0]</a>
                ct[cid] = ct.get(cid,0)+1
                c.execute('INSERT INTO compras_parcelas (compra_id,numero_parcela,vencimento,valor_parcela,forma_pagamento,observacao) VALUES (%s,%s,%s,%s,%s,%s)',
                    (cid,ct[cid],ld(row.get('Vencimento')),lv(row.get('Valor da parcela')),ls(row.get('Forma de pagamento')),ls(row.get('Observacao'))))
                ok += 1
            except: pass
    conn.commit()
    print('   OK:', ok)

def s5(df, conn):
    print('5. Itens...')
    ok = 0
    with conn.cursor() as c:
        for i, row in df.iterrows():
            try:
                cod = row.get('Codigo')
                if pd.isna(cod): continue
                c.execute('SELECT id FROM compras WHERE numero_compra=%s',(int(float(str(cod))),))
                r = c.fetchone()
                if not r: continue
                prod = ls(row.get('Produto'),u=True)
                if not prod: continue
                c.execute('INSERT INTO compras_itens (compra_id,produto_desc,quantidade,unidade,custo_unitario,custo_total) VALUES (%s,%s,%s,%s,%s,%s)',
                    (r<a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;">[0]</a>,prod,lv(row.get('Quantidade')),ls(row.get('Unidade')) or 'UN',lv(row.get('Custo unitario')),lv(row.get('Custo total'))))
                ok += 1
            except: pass
    conn.commit()
    print('   OK:', ok)

def main():
    arq = 'dados/compras.xlsx'
    print('='*40)
    print('SMARTTEC ERP - Importacao')
    print('='*40)
    try:
        xls = pd.ExcelFile(arq)
        print('Abas:', xls.sheet_names)
        d0 = pd.read_excel(xls, 0)
        d1 = pd.read_excel(xls, 1)
        d2 = pd.read_excel(xls, 2)
        d3 = pd.read_excel(xls, 3)
    except Exception as ex:
        print('ERRO Excel:', ex)
        return
    try:
        conn = get_conn()
        print('Banco OK')
    except Exception as ex:
        print('ERRO Banco:', ex)
        return
    try:
        s1(d0,conn); s2(d0,conn); s3(d1,conn); s4(d2,conn); s5(d3,conn)
        print('CONCLUIDO!')
    except Exception as ex:
        conn.rollback()
        print('ERRO:', ex)
        import traceback; traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
""")

codigo.close()
print('ARQUIVO CRIADO COM SUCESSO!')
