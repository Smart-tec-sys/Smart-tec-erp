"""Migração do cofre A1 em PostgreSQL temporário EXCLUSIVO do GitHub Actions."""
import os
import unittest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from app.database import Base
from app.models.empresa import EmpresaDB
from app.models.fiscal_certificado_cofre import FiscalCertificadoCofreDB
from app.services.fiscal_cofre_a1 import proteger_a1
from tests.test_fiscal_cofre_a1 import KmsFakeTemporario

DATABASE_URL=os.environ.get("DATABASE_URL","")
if "smarttec_fiscal_ci" not in DATABASE_URL:
    raise RuntimeError("Teste de migração A1 exige DB descartável smarttec_fiscal_ci")


def sql(name):
    return (Path(__file__).resolve().parents[1]/"migrations"/name).read_text(encoding="utf-8")


class PostgresCofreA1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng=create_engine(DATABASE_URL)
        with cls.eng.connect() as c:
            if c.execute(text("SELECT current_database()")).scalar_one()!="smarttec_fiscal_ci":
                raise RuntimeError("DB não é CI")
        Base.metadata.create_all(cls.eng,tables=[EmpresaDB.__table__])
        # Testes anteriores podem ter criado empresas, reusamos registros sintéticos.
        if not cls.eng.dialect.has_table(cls.eng.connect(),"fiscal_certificados_cofre"):
            with cls.eng.begin() as c:
                c.exec_driver_sql(sql("20261114_fiscal_v1_cofre_a1_up.sql").replace("BEGIN;","").replace("COMMIT;",""))

    @classmethod
    def tearDownClass(cls):
        cls.eng.dispose()

    def test_01_schema_fiscal_sem_coluna_pfx_ou_senha(self):
        with self.eng.connect() as c:
            cols=[r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='fiscal_certificados_cofre'"
            )).all()]
            self.assertIn("conteudo_cifrado",cols)
            self.assertNotIn("pfx",cols)
            self.assertNotIn("senha",cols)
            cons={r[0]:r[1] for r in c.execute(text(
                "SELECT conname,contype FROM pg_constraint "
                "WHERE conrelid='public.fiscal_certificados_cofre'::regclass"
            ))}
            self.assertEqual(cons.get("fiscal_certificados_cofre_pkey"),"p")
            self.assertEqual(cons.get("ck_fiscal_cofre_nonce"),"c")

    def test_02_cifra_persistida_e_isolamento_fk(self):
        kms=KmsFakeTemporario()
        env=proteger_a1(1,b"PFX-DEMO-FAKE",b"senha-fake",kms)
        with self.eng.begin() as c:
            # Garantir dado fictício para FK sem alterar registros de outra empresa.
            c.execute(text(
                "INSERT INTO empresas(id,nome,slug,status,configuracoes) "
                "VALUES(1,'Empresa Teste','cofre-a1-ci','ATIVA','{}') "
                "ON CONFLICT (id) DO NOTHING"
            ))
            c.execute(text("INSERT INTO fiscal_certificados_cofre "
                "(empresa_id,versao,key_id,chave_envelopada,nonce,conteudo_cifrado)"
                " VALUES(:id,1,:key,:wrapped,:nonce,:cipher)"
                " ON CONFLICT (empresa_id) DO UPDATE SET "
                "key_id=EXCLUDED.key_id,chave_envelopada=EXCLUDED.chave_envelopada,"
                "nonce=EXCLUDED.nonce,conteudo_cifrado=EXCLUDED.conteudo_cifrado"),
                dict(id=1,key=env.key_id,wrapped=env.chave_envelopada,
                     nonce=env.nonce,cipher=env.conteudo_cifrado))
        with self.eng.connect() as c:
            row=c.execute(text(
                "SELECT empresa_id,conteudo_cifrado FROM fiscal_certificados_cofre WHERE empresa_id=1"
            )).one()
            self.assertEqual(row[0],1)
            self.assertEqual(bytes(row[1]),env.conteudo_cifrado)
            self.assertNotIn(b"PFX-DEMO-FAKE",bytes(row[1]))

    def test_03_fk_bloqueia_empresa_inexistente(self):
        kms=KmsFakeTemporario()
        env=proteger_a1(999999,b"PFX-FAKE",b"fake",kms)
        with self.assertRaises(IntegrityError):
            with self.eng.begin() as c:
                c.execute(text("INSERT INTO fiscal_certificados_cofre "
                    "(empresa_id,versao,key_id,chave_envelopada,nonce,conteudo_cifrado)"
                    " VALUES(:id,1,:key,:wrapped,:nonce,:cipher)"),
                    dict(id=env.empresa_id,key=env.key_id,wrapped=env.chave_envelopada,
                         nonce=env.nonce,cipher=env.conteudo_cifrado))


if __name__=="__main__":
    unittest.main()
