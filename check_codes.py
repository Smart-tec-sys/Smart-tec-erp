import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Search for JPTEC codes
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, codigo_barras, fornecedor_padrao_id
        FROM produtos 
        WHERE empresa_id = 1 
          AND (codigo_interno ILIKE 'JPTEC-%' OR codigo_barras ILIKE 'JPTEC-%')
        ORDER BY id
    """)).mappings()
    print("=== JPTEC codes ===")
    for r in result:
        print(f'  ID:{r["id"]} | {r["nome"]} | cod_int:{r["codigo_interno"]} | cod_bar:{r["codigo_barras"]} | forn:{r["fornecedor_padrao_id"]}')
    
    # Search for TECRL codes
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, codigo_barras, fornecedor_padrao_id
        FROM produtos 
        WHERE empresa_id = 1 
          AND (codigo_interno ILIKE 'TECRL%' OR codigo_barras ILIKE 'TECRL%')
        ORDER BY id
    """)).mappings()
    print("\n=== TECRL codes ===")
    for r in result:
        print(f'  ID:{r["id"]} | {r["nome"]} | cod_int:{r["codigo_interno"]} | cod_bar:{r["codigo_barras"]} | forn:{r["fornecedor_padrao_id"]}')
    
    # Search for ACAO or ACAO codes
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, codigo_barras, fornecedor_padrao_id
        FROM produtos 
        WHERE empresa_id = 1 
          AND (codigo_interno ILIKE '%021%' OR codigo_barras ILIKE '%021%' OR
               codigo_interno ILIKE '%022%' OR codigo_barras ILIKE '%022%' OR
               codigo_interno ILIKE '%023%' OR codigo_barras ILIKE '%023%')
        ORDER BY id
    """)).mappings()
    print("\n=== 021/022/023 codes (possible Acao) ===")
    for r in result:
        print(f'  ID:{r["id"]} | {r["nome"]} | cod_int:{r["codigo_interno"]} | cod_bar:{r["codigo_barras"]} | forn:{r["fornecedor_padrao_id"]}')