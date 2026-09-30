import sys
sys.path.insert(0, '.')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Get costs for NAPOLES family (JPTEC codes)
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND (nome ILIKE '%napoles%' OR nome ILIKE '%nap%')
        ORDER BY codigo_interno
    """)).mappings()
    print("=== NAPOLES JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')
    
    # Get costs for PIMPOINT family (JPTEC codes)
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND (nome ILIKE '%pimpoint%' OR nome ILIKE '%pimp%')
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== PIMPOINT JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')
    
    # Get costs for ROMA family (JPTEC codes)
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND (nome ILIKE '%roma bk%' OR nome ILIKE '%roma bk,%')
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== ROMA BK JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')
    
    # Get costs for SCREEN 3% JP IMPORTADA
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND nome ILIKE '%screen 3% jp%'
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== SCREEN 3% JP IMPORTADA JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')
    
    # Get costs for SCREEN 1% ONE
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND nome ILIKE '%screen 1% one%'
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== SCREEN 1% ONE JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')
    
    # Get costs for SCREEN 1% ECO IMPORTADA
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND nome ILIKE '%screen 1% eco%'
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== SCREEN 1% ECO IMPORTADA JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')
    
    # Get costs for TJS
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND codigo_interno LIKE 'JPTEC-%'
          AND nome ILIKE '%tjs%'
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== TJS JPTEC costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')

    # Get ACAO codes (021/022/023) for components
    result = conn.execute(text("""
        SELECT id, nome, codigo_interno, valor_custo, cor, cor_componente, variacao_cor, unidade
        FROM produtos 
        WHERE empresa_id = 1 
          AND (codigo_interno LIKE '021%' OR codigo_interno LIKE '022%' OR codigo_interno LIKE '023%')
          AND (nome ILIKE '%comando%' OR nome ILIKE '%corrente%' OR nome ILIKE '%limitador%' OR nome ILIKE '%conector%')
        ORDER BY codigo_interno
    """)).mappings()
    print("\n=== ACAO (021/022/023) component costs ===")
    for r in result:
        print(f'  {r["codigo_interno"]} | {r["nome"]} | custo:{r["valor_custo"]} | cor:{r["cor"] or r["cor_componente"] or r["variacao_cor"]} | unid:{r["unidade"]}')