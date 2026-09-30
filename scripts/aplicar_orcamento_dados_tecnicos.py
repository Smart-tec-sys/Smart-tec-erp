import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DB_NAME = "smarttec_erp_dev"
PGPASS = Path.home() / "AppData/Roaming/postgresql/pgpass.conf"
MIGRATION = Path("migrations/20260926_orcamento_dados_tecnicos_up.sql")


def carregar_pgpass():
    if not PGPASS.exists():
        raise RuntimeError(f"pgpass.conf nao encontrado: {PGPASS}")

    for raw in PGPASS.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()

        if not raw or raw.startswith("#"):
            continue

        parts = raw.split(":", 4)

        if len(parts) != 5:
            continue

        host, port, database, user, password = parts

        if database == DB_NAME:
            os.environ["DB_HOST"] = host
            os.environ["DB_PORT"] = port
            os.environ["DB_NAME"] = database
            os.environ["DB_USER"] = user
            os.environ["DB_PASSWORD"] = password
            return

    raise RuntimeError(
        f"Nenhuma credencial para {DB_NAME} encontrada em {PGPASS}"
    )


def main():
    carregar_pgpass()

    # Importar somente depois de carregar as variaveis.
    from app.database import engine

    if not MIGRATION.exists():
        raise RuntimeError(f"Migration nao encontrada: {MIGRATION}")

    connection = engine.raw_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT current_database()")
        banco = cursor.fetchone()[0]

        print(f"BANCO={banco}")

        if banco != DB_NAME:
            raise RuntimeError(
                f"ABORTADO: banco atual e {banco}, esperado {DB_NAME}"
            )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'orcamentos'
              AND column_name = 'observacao_interna'
            """
        )
        obs_antes = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'orcamentos_itens'
              AND column_name = 'dados_tecnicos'
            """
        )
        dados_antes = cursor.fetchone()[0]

        print(f"OBSERVACAO_INTERNA_ANTES={obs_antes}")
        print(f"DADOS_TECNICOS_ANTES={dados_antes}")

        sql = MIGRATION.read_text(encoding="utf-8")

        for statement in sql.split(";"):
            statement = statement.strip()

            if statement:
                cursor.execute(statement)

        connection.commit()

        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'orcamentos'
              AND column_name = 'observacao_interna'
            """
        )
        obs = cursor.fetchone()

        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'orcamentos_itens'
              AND column_name = 'dados_tecnicos'
            """
        )
        dados = cursor.fetchone()

        if not obs:
            raise RuntimeError("Coluna observacao_interna nao foi criada.")

        if not dados:
            raise RuntimeError("Coluna dados_tecnicos nao foi criada.")

        print(f"OBSERVACAO_INTERNA_TIPO={obs[0]}")
        print(f"DADOS_TECNICOS_TIPO={dados[0]}")

        if dados[0] != "jsonb":
            raise RuntimeError(
                f"dados_tecnicos deveria ser jsonb, encontrado: {dados[0]}"
            )

        print("MIGRATION_EXECUTADA=1")
        print("OK_ORCAMENTO_DADOS_TECNICOS=1")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
