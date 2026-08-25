from sqlalchemy import text
from app.database import Base, engine

# Importando os modelos explicitamente
from app.models.cliente import ClienteDB
from app.models.fornecedor import FornecedorDB
from app.models.funcionario import FuncionarioDB
print("--- Iniciando Sincronizacao no banco smart_tec_erp ---")

try:
    # 1. Conecta e limpa o banco antigo (Dropa as tabelas se elas existirem)
    with engine.connect() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS fornecedores CASCADE;"))
        conexao.execute(text("DROP TABLE IF EXISTS clientes CASCADE;"))
        conexao.commit()
    print("Tabelas antigas removidas com sucesso!")

    # 2. Criação Geral via Metadata do Base
    Base.metadata.create_all(bind=engine)
    print("Nova tabela 'clientes' criada com sucesso no banco atual!")

    # 3. Força-bruta de segurança: Garante que a tabela do FornecedorDB seja criada!
    FornecedorDB.__table__.create(bind=engine, checkfirst=True)
    print("Nova tabela 'fornecedores' criada com sucesso no banco atual!")
    
    FuncionarioDB.__table__.create(bind=engine, checkfirst=True)
    print("Nova tabela 'funcionarios' criada com sucesso no banco atual!")

    print("--- Sincronização concluída com sucesso total! ---")

except Exception as e:
    print(f"Erro ao conectar ou sincronizar o banco de dados: {e}")
