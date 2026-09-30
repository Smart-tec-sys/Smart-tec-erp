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
    migration = Path("migrations/20260905_orcamento_perfil_comercial_up.sql").read_text(encoding="utf-8")
    connection = engine.raw_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT current_database()")
        database = cursor.fetchone()[0]
        print(f"BANCO={database}")
        if database != "smarttec_erp_dev":
            raise RuntimeError("Banco não autorizado; migration abortada")
        cursor.execute(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name='orcamentos' AND column_name='perfil_comercial'"
        )
        existed = bool(cursor.fetchone()[0])
        print(f"COLUNA_ANTES={int(existed)}")
        if not existed:
            cursor.execute(migration)
        connection.commit()
        cursor.execute(
            "SELECT column_default, is_nullable FROM information_schema.columns "
            "WHERE table_name='orcamentos' AND column_name='perfil_comercial'"
        )
        print(f"COLUNA_DEPOIS={cursor.fetchone()}")
        cursor.execute("SELECT perfil_comercial, count(*) FROM orcamentos GROUP BY perfil_comercial")
        print(f"HISTORICO={cursor.fetchall()}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
