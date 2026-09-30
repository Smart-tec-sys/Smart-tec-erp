from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    forn = conn.execute(text('SELECT id, nome FROM fornecedores WHERE empresa_id = 1 ORDER BY id')).mappings().all()
    print('FORNECEDORES:')
    for f in forn:
        print(f'  {f["id"]}: {f["nome"]}')
    print()
    prods = conn.execute(text('''
        SELECT id, nome, fornecedor_padrao_id, fornecedores, nome_fornecedor, origem
        FROM produtos 
        WHERE empresa_id = 1 AND ativo = true
        ORDER BY nome
        LIMIT 30
    ''')).mappings().all()
    print('PRODUTOS (amostra):')
    for p in prods:
        print(f'  ID {p["id"]}: {p["nome"][:60]} | padrao={p["fornecedor_padrao_id"]} | csv={str(p["fornecedores"])[:30]} | nome_forn={str(p["nome_fornecedor"])[:30]} | origem={str(p["origem"])[:30]}')