from pathlib import Path
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(Path(r"C:\Users\valmi\Smart-tec\.env"), override=False)
os.environ["DB_NAME"] = "smarttec_erp_dev"
for entry in Path(r"C:\Users\valmi\AppData\Roaming\postgresql\pgpass.conf").read_text().splitlines():
    host, port, database, user, password = entry.split(":", 4)
    if database == "smarttec_erp_dev":
        os.environ.update(DB_HOST=host, DB_PORT=port, DB_NAME=database, DB_USER=user, DB_PASSWORD=password)
        break

from app.database import engine



def main():
    migration_path = Path("migrations/20260924_agenda_eventos_up.sql")
    migration = migration_path.read_text(encoding="utf-8")

    connection = engine.raw_connection()

    try:
        cursor = connection.cursor()

        # --------------------------------------------------------
        # PROTECAO: SOMENTE DEV
        # --------------------------------------------------------
        cursor.execute("SELECT current_database()")
        database = cursor.fetchone()[0]

        print(f"BANCO={database}")

        if database != "smarttec_erp_dev":
            raise RuntimeError(
                "Banco nao autorizado; migration abortada"
            )

        # --------------------------------------------------------
        # ESTADO ANTES
        # --------------------------------------------------------
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'agenda_eventos'
            )
            """
        )

        existed = bool(cursor.fetchone()[0])

        print(f"TABELA_ANTES={int(existed)}")

        # --------------------------------------------------------
        # MIGRATION
        # --------------------------------------------------------
        if not existed:
            cursor.execute(migration)
            connection.commit()
            print("MIGRATION_EXECUTADA=1")
        else:
            print("MIGRATION_EXECUTADA=0")
            print("MOTIVO=tabela_ja_existia")

        # --------------------------------------------------------
        # VALIDACAO DEPOIS
        # --------------------------------------------------------
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'agenda_eventos'
            )
            """
        )

        exists_after = bool(cursor.fetchone()[0])

        print(f"TABELA_DEPOIS={int(exists_after)}")

        if not exists_after:
            raise RuntimeError(
                "Tabela agenda_eventos nao foi criada"
            )

        cursor.execute(
            """
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'agenda_eventos'
            ORDER BY ordinal_position
            """
        )

        columns = cursor.fetchall()

        print(f"COLUNAS={len(columns)}")

        required = {
            "id",
            "empresa_id",
            "external_uid",
            "titulo",
            "categoria",
            "status",
            "inicio",
            "origem",
            "sincronizacao_status",
            "metadados",
            "created_at",
            "updated_at",
        }

        existing_names = {row[0] for row in columns}

        missing = sorted(required - existing_names)

        if missing:
            raise RuntimeError(
                "Colunas obrigatorias ausentes: "
                + ", ".join(missing)
            )

        cursor.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'agenda_eventos'
            ORDER BY indexname
            """
        )

        indexes = [row[0] for row in cursor.fetchall()]

        print(f"INDICES={len(indexes)}")

        for index_name in indexes:
            print(f"INDEX={index_name}")

        print("OK_AGENDA_EVENTOS=1")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
