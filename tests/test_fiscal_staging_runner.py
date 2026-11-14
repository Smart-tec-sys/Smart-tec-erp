"""Testes da migração protegida com PostgreSQL efêmero de GitHub Actions."""
import os
import unittest

from sqlalchemy import create_engine, text

# scripts/__init__.py do projeto legado não é importável; carregar o arquivo
# do migrador isoladamente, sem executar outros scripts do ERP.
import importlib.util
from pathlib import Path
location = Path(__file__).resolve().parents[1] / "scripts/fiscal/staging_migrate.py"
spec = importlib.util.spec_from_file_location("fiscal_staging_migrate", location)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)
EXPECTED_DATABASE = module.EXPECTED_DATABASE
PreflightError = module.PreflightError
check_database_url = module.check_database_url
run = module.run

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
    raise RuntimeError("O teste exige banco temporário PostgreSQL.")
if "smarttec_fiscal_ci" not in DATABASE_URL:
    raise RuntimeError("O teste recusa URL de banco diferente do CI.")


class FiscalStagingRunnerTests(unittest.TestCase):
    def test_01_bloqueia_producao_e_urls_inesperadas(self):
        for url in (
            "postgresql://x:y@localhost/smarttec_erp_operacional",
            "postgresql://x:y@localhost/smarttec_erp_assinantes",
            "sqlite:///arquivo.db",
            "",
        ):
            with self.subTest(url=url), self.assertRaises(PreflightError):
                check_database_url(url)

    def test_02_exige_confirmacao_antes_de_qualquer_conexao(self):
        with self.assertRaises(PreflightError):
            run("postgresql://x:y@localhost/smarttec_erp_staging", apply=True, confirmed=False)

    def test_03_recusa_banco_ci_que_nao_e_staging(self):
        with self.assertRaises(PreflightError):
            run(DATABASE_URL, apply=True, confirmed=True)

    def test_04_executa_migracao_com_nome_staging_em_db_descartavel(self):
        # CI cria um banco adicional com nome idêntico ao staging, isolado no
        # PostgreSQL de testes — NUNCA usa host do Render.
        ci_url = DATABASE_URL.rsplit("/", 1)[0]
        admin_engine = create_engine(DATABASE_URL)
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("CREATE DATABASE " + EXPECTED_DATABASE))
        admin_engine.dispose()
        test_url = ci_url + "/" + EXPECTED_DATABASE

        eng = create_engine(test_url)
        try:
            with eng.begin() as conn:
                conn.exec_driver_sql("""
                    CREATE TABLE empresas(
                      id INTEGER PRIMARY KEY, nome VARCHAR(100)
                    );
                    CREATE TABLE produtos(
                      id INTEGER PRIMARY KEY, empresa_id INTEGER
                    );
                    CREATE TABLE pedidos(
                      id INTEGER PRIMARY KEY, empresa_id INTEGER
                    );
                    INSERT INTO empresas(id,nome) VALUES (1, 'Empresa TESTE');
                """)
            before = run(test_url)
            self.assertEqual(before["modo"], "PREFLIGHT_SOMENTE_LEITURA")
            self.assertEqual((before["empresas"],before["produtos"],before["pedidos"]), (1,0,0))
            self.assertFalse(before["constraint_produtos"])
            self.assertFalse(before["fiscal_existe"])

            migrated = run(test_url, apply=True, confirmed=True)
            self.assertEqual(migrated["modo"], "APLICADA")
            self.assertTrue(migrated["constraint_produtos"])
            self.assertTrue(migrated["fiscal_existe"])

            repeated = run(test_url, apply=True, confirmed=True)
            self.assertEqual(repeated["modo"], "JA_APLICADA")
            with eng.connect() as conn:
                self.assertEqual(conn.execute(text("SELECT count(*) FROM empresas")).scalar_one(), 1)
                self.assertEqual(conn.execute(text("SELECT count(*) FROM fiscal_produtos")).scalar_one(), 0)

            # O runner não pode adivinhar se staging mudou: falha sem criar registros.
            with eng.begin() as conn:
                conn.execute(text("INSERT INTO produtos(id,empresa_id) VALUES (101,1)"))
            with self.assertRaises(PreflightError):
                run(test_url, apply=True, confirmed=True)
        finally:
            eng.dispose()


if __name__ == "__main__":
    unittest.main()
