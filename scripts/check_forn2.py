from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check fabric products specifically
    prods = conn.execute(text('''
        SELECT id, nome, grupo_tecnico, familia_tecnica, material_tecido,
               fornecedor_padrao_id, fornecedores, nome_fornecedor, origem,
               valor_custo, custo_final, largura
        FROM produtos 
        WHERE empresa_id = 1 AND ativo = true
          AND (grupo_tecnico ILIKE '%TECIDO%' OR familia_tecnica ILIKE '%SCREEN%' OR familia_tecnica ILIKE '%BLACKOUT%' OR familia_tecnica ILIKE '%TRANSLUCID%')
        ORDER BY nome
        LIMIT 50
    ''')).mappings().all()
    print('PRODUTOS TECIDOS (amostra):')
    for p in prods:
        print(f'  ID {p["id"]}: {p["nome"][:70]}')
        print(f'    gt={p["grupo_tecnico"]} | ft={p["familia_tecnica"]} | mt={p["material_tecido"]}')
        print(f'    padrao={p["fornecedor_padrao_id"]} | csv={p["fornecedores"]} | nome_forn={p["nome_fornecedor"]} | origem={p["origem"]}')
        print(f'    custo={p["custo_final"]} | largura={p["largura"]}')
        print()