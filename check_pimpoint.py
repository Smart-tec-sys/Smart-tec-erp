import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    families = [
        'PIMPOINT',
        'NAPOLES',
        'PIMPOINT',
    ]
    
    for fam in families:
        result = conn.execute(text('''
            SELECT id, nome, familia_tecnica, grupo_produto, grupo_tecnico, 
                   fornecedor_padrao_id, codigo_interno, codigo_barras, 
                   valor_custo, cor, cor_componente, variacao_cor, unidade
            FROM produtos 
            WHERE empresa_id = 1 
              AND (familia_tecnica ILIKE :fam OR nome ILIKE :fam)
            ORDER BY id
        '''), {'fam': f'%{fam}%'}).mappings()
        
        rows = list(result)
        if rows:
            print(f'\n=== {fam} ===')
            for r in rows:
                print(f'  ID:{r["id"]} | {r["nome"]} | fam_tec:{r["familia_tecnica"]} | grp:{r["grupo_produto"]} | grp_tec:{r["grupo_tecnico"]} | forn:{r["fornecedor_padrao_id"]} | cod_int:{r["codigo_interno"]} | cod_bar:{r["codigo_barras"]} | custo:{r["valor_custo"]} | cor:{r["cor"]} | cor_comp:{r["cor_componente"]} | var_cor:{r["variacao_cor"]} | unid:{r["unidade"]}')
        else:
            print(f'\n=== {fam} === (NAO ENCONTRADO)')