"""CRUD HTTP em SQLite isolado; nunca conecta ao PostgreSQL do ERP."""
import csv
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.schemas.grades_variacoes import GradeCreate, GradeUpdate, ValorCreate
from app.services import grades_variacoes as service


class GradesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
        self.Session = sessionmaker(bind=self.engine)
        with self.engine.begin() as db:
            for sql in [
                "CREATE TABLE empresas(id INTEGER PRIMARY KEY)",
                "INSERT INTO empresas VALUES (1),(2)",
                "CREATE TABLE grades_variacoes(id INTEGER PRIMARY KEY,empresa_id INTEGER NOT NULL REFERENCES empresas(id),nome VARCHAR(120) NOT NULL CHECK(trim(nome)<>''),descricao TEXT,ativo BOOLEAN NOT NULL DEFAULT 1,ordem INTEGER NOT NULL DEFAULT 0 CHECK(ordem>=0))",
                "CREATE UNIQUE INDEX uq_grade ON grades_variacoes(empresa_id,lower(trim(nome)))",
                "CREATE TABLE grades_variacoes_valores(id INTEGER PRIMARY KEY,grade_id INTEGER NOT NULL REFERENCES grades_variacoes(id) ON DELETE RESTRICT,valor VARCHAR(150) NOT NULL CHECK(trim(valor)<>''),ativo BOOLEAN NOT NULL DEFAULT 1,ordem INTEGER NOT NULL DEFAULT 0 CHECK(ordem>=0))",
                "CREATE UNIQUE INDEX uq_valor ON grades_variacoes_valores(grade_id,lower(trim(valor)))",
            ]:
                db.execute(text(sql))
        self.tenant = SimpleNamespace(empresa_id=1)
        def get_db():
            with self.Session() as db:
                yield db
        def get_tenant():
            return self.tenant
        # Replace only infrastructure dependencies: real router, schemas and service run.
        database = types.ModuleType("app.database"); database.get_db = get_db
        dependencies = types.ModuleType("app.tenant.dependencies"); dependencies.get_current_tenant = get_tenant
        self.modules = patch.dict(sys.modules, {"app.database": database, "app.tenant.dependencies": dependencies})
        self.modules.start()
        sys.modules.pop("app.routes.grades_variacoes", None)
        from app.routes.grades_variacoes import router
        app = FastAPI(); app.include_router(router, prefix="/grades-variacoes")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.modules.stop()
        sys.modules.pop("app.routes.grades_variacoes", None)
        self.engine.dispose()

    def grade(self, nome="CORES"):
        response=self.client.post("/grades-variacoes/",json={"nome":nome})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()["id"]

    def value(self, grade, valor="BRANCO", ordem=0):
        response=self.client.post(f"/grades-variacoes/{grade}/valores",json={"valor":valor,"ordem":ordem})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()["id"]

    def test_create_list_update_grade(self):
        id=self.grade(" CORES ")
        self.assertEqual(self.client.get("/grades-variacoes/").json()[0]["nome"],"CORES")
        result=self.client.patch(f"/grades-variacoes/{id}",json={"descricao":"Auxiliar","ordem":3,"ativo":False})
        self.assertEqual(result.status_code,200)
        self.assertFalse(result.json()["ativo"])
        self.assertEqual(result.json()["nome"],"CORES")
        self.assertEqual(self.client.patch(f"/grades-variacoes/{id}",json={"ativo":True}).status_code,200)

    def test_duplicate_grade_case_trim(self):
        self.grade()
        self.assertEqual(self.client.post("/grades-variacoes/",json={"nome":" cores "}).status_code,409)

    def test_database_unique_indexes(self):
        from sqlalchemy.exc import IntegrityError
        id=self.grade(); self.value(id)
        for sql in ["INSERT INTO grades_variacoes(empresa_id,nome) VALUES(1,' cores ')",
                    f"INSERT INTO grades_variacoes_valores(grade_id,valor) VALUES({id},' branco ')"]:
            with self.Session() as db, self.assertRaises(IntegrityError):
                db.execute(text(sql))

    def test_same_grade_name_other_company(self):
        self.grade(); self.tenant=SimpleNamespace(empresa_id=2); self.grade()
        self.assertEqual(len(self.client.get("/grades-variacoes/").json()),1)

    def test_cross_tenant_grade_and_values_blocked(self):
        grade=self.grade(); value=self.value(grade)
        self.tenant=SimpleNamespace(empresa_id=2)
        for method,url,data in [
            ("patch",f"/{grade}",{"nome":"Roubo"}),
            ("delete",f"/{grade}",None),
            ("get",f"/{grade}/valores",None),
            ("post",f"/{grade}/valores",{"valor":"X"}),
            ("patch",f"/{grade}/valores/{value}",{"valor":"X"}),
            ("delete",f"/{grade}/valores/{value}",None),
        ]:
            with self.subTest(method=method):
                self.assertEqual(self.client.request(method,"/grades-variacoes"+url,**({"json":data} if data else {})).status_code,404)

    def test_missing_tenant_denied(self):
        self.tenant=SimpleNamespace(empresa_id=None)
        self.assertEqual(self.client.get("/grades-variacoes/").status_code,403)

    def test_value_crud_order_and_omission(self):
        grade=self.grade(); first=self.value(grade,"BRANCO",5); self.value(grade,"PRETO",2)
        rows=self.client.get(f"/grades-variacoes/{grade}/valores").json()
        self.assertEqual([r["valor"] for r in rows],["PRETO","BRANCO"])
        row=self.client.patch(f"/grades-variacoes/{grade}/valores/{first}",json={"ativo":False,"ordem":0}).json()
        self.assertEqual(row["valor"],"BRANCO"); self.assertFalse(row["ativo"])
        self.assertEqual(self.client.patch(f"/grades-variacoes/{grade}/valores/{first}",json={"valor":"GELO","ativo":True}).status_code,200)
        self.assertEqual(self.client.delete(f"/grades-variacoes/{grade}/valores/{first}").status_code,204)

    def test_duplicate_value_and_update(self):
        grade=self.grade(); first=self.value(grade); second=self.value(grade,"PRETO")
        self.assertEqual(self.client.post(f"/grades-variacoes/{grade}/valores",json={"valor":" branco "}).status_code,409)
        self.assertEqual(self.client.patch(f"/grades-variacoes/{grade}/valores/{second}",json={"valor":"BRANCO"}).status_code,409)

    def test_value_wrong_parent(self):
        grade=self.grade(); value=self.value(grade); other=self.grade("TAMANHOS")
        self.assertEqual(self.client.patch(f"/grades-variacoes/{other}/valores/{value}",json={"valor":"X"}).status_code,404)

    def test_delete_grade_restricted_until_empty(self):
        grade=self.grade(); value=self.value(grade)
        self.assertEqual(self.client.delete(f"/grades-variacoes/{grade}").status_code,409)
        self.client.delete(f"/grades-variacoes/{grade}/valores/{value}")
        self.assertEqual(self.client.delete(f"/grades-variacoes/{grade}").status_code,204)

    def test_validation_blank_negative_null_extra(self):
        for payload in [{"nome":" "},{"nome":"X","ordem":-1},{"nome":"X","empresa_id":2}]:
            self.assertEqual(self.client.post("/grades-variacoes/",json=payload).status_code,422)
        grade=self.grade()
        for payload in [{"nome":None},{"ativo":None},{"ordem":None},{"nome":" "}]:
            self.assertEqual(self.client.patch(f"/grades-variacoes/{grade}",json=payload).status_code,422)
        self.assertEqual(self.client.post(f"/grades-variacoes/{grade}/valores",json={"valor":" "}).status_code,422)

    def test_missing_migration_returns_clear_503(self):
        from sqlalchemy.exc import ProgrammingError
        class MissingTable(Exception):
            pgcode = "42P01"
        with patch.object(service, "listar_grades", side_effect=ProgrammingError("SELECT", {}, MissingTable())):
            result = self.client.get("/grades-variacoes/")
        self.assertEqual(result.status_code, 503)
        self.assertIn("aguarda aplicação", result.json()["detail"])

    def test_failed_write_rolls_back(self):
        from sqlalchemy.exc import IntegrityError
        grade = self.grade()
        with patch.object(service, "criar_valor", side_effect=IntegrityError("INSERT", {}, Exception("duplicate"))):
            result = self.client.post(f"/grades-variacoes/{grade}/valores", json={"valor":"BRANCO"})
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.client.get(f"/grades-variacoes/{grade}/valores").json(), [])

    def test_migration_seed_and_scope_static(self):
        root=Path(__file__).resolve().parents[1]
        up=(root/"migrations/20261009_grades_variacoes_up.sql").read_text(encoding="utf-8")
        down=(root/"migrations/20261009_grades_variacoes_down.sql").read_text(encoding="utf-8")
        with (root/"cores_existentes_para_grade.csv").open(encoding="utf-8-sig") as source:
            approved=[r["cor_original"] for r in csv.DictReader(source) if r["status_sugerido"]=="APROVAR"]
        import re
        seed=re.findall(r" \('([^']+)',(\d+)\)",up)
        self.assertEqual([r[0] for r in seed],approved)
        self.assertEqual(len(seed),43)
        self.assertEqual([int(r[1]) for r in seed],list(range(1,44)))
        self.assertIn("lower(btrim(nome))",up); self.assertIn("lower(btrim(valor))",up)
        self.assertNotIn("DROP TABLE public.cores",down)
        self.assertNotIn("CASCADE",down.split("BEGIN;")[1])

if __name__=="__main__": unittest.main()
