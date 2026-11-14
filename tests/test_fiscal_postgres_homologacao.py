"""Homologação real em PostgreSQL efêmero do CI. Nunca conectar ao Render.

O banco usa produtos e empresas fictícios, criados e descartados no próprio job.
"""
import json
import os
import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.models.empresa import EmpresaDB
from app.models.empresa_portfolio import EmpresaPortfolioDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.usuario import UsuarioDB
from app.models.produto import ProdutoDB
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant
from app.routes.fiscal_cadastros import router as fiscal_router
from app.routes.pedido import router as pedidos_router
from app.schemas.fiscal_cadastros import FiscalEmpresaPatch, FiscalProdutoPatch
from app.services import fiscal_cadastros
from app.services.fiscal_nfe_cadastros import conferir_cadastros_fiscais

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
    raise RuntimeError("Este teste exige o PostgreSQL efêmero configurado no GitHub Actions.")


def fiscal_sql(filename):
    from pathlib import Path
    return (Path(__file__).resolve().parent.parent / "migrations" / filename).read_text(encoding="utf-8")


def run_sql(engine, sql, *, expect_fail=False):
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        try:
            cursor.execute(sql)
            raw.commit()
            if expect_fail:
                raise AssertionError("A migração deveria ter sido bloqueada no preflight.")
        except Exception:
            raw.rollback()
            if not expect_fail:
                raise
        finally:
            cursor.close()
    finally:
        raw.close()


class FiscalPostgresHomologacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with cls.engine.connect() as c:
            name = c.execute(text("select current_database()")).scalar_one()
            if name != "smarttec_fiscal_ci":
                raise RuntimeError("Recusado: nome do banco não corresponde ao banco efêmero do CI.")
        Base.metadata.create_all(
            cls.engine,
            tables=[
                EmpresaDB.__table__, EmpresaPortfolioDB.__table__,
                UsuarioDB.__table__, EmpresaUsuarioDB.__table__, ProdutoDB.__table__,
            ],
        )
        # Testar falha segura de staging sem a chave composta.
        with cls.engine.begin() as c:
            c.execute(text("ALTER TABLE produtos DROP CONSTRAINT uq_produtos_id_empresa"))
        run_sql(cls.engine, fiscal_sql("20261114_fiscal_v1_cadastros_up.sql"), expect_fail=True)
        with cls.engine.connect() as c:
            assert c.execute(text("select to_regclass('public.fiscal_produtos')")).scalar_one() is None
        with cls.engine.begin() as c:
            c.execute(text("ALTER TABLE produtos ADD CONSTRAINT uq_produtos_id_empresa UNIQUE (id, empresa_id)"))
        run_sql(cls.engine, fiscal_sql("20261114_fiscal_v1_cadastros_up.sql"))

        with cls.engine.begin() as c:
            for company, cnpj in [(1, "11222333000181"), (2, "19131243000197")]:
                c.execute(text("""
                    INSERT INTO empresas(id,nome,documento,slug,status,configuracoes)
                    VALUES (:id, :name, :doc, :slug, 'ATIVA', CAST(:cfg AS JSON))
                """), {"id": company, "name": f"Empresa fictícia {company}", "doc": cnpj,
                       "slug": f"fiscal-ci-{company}", "cfg": "{}"})
                c.execute(text("INSERT INTO usuarios(id,nome,email,status) VALUES(:id,:name,:email,'ATIVO')"),
                          {"id": company + 1000, "name": "Admin fictício",
                           "email": f"admin-ficticio-{company}@invalid.test"})
                c.execute(text("""
                    INSERT INTO empresa_usuarios(empresa_id,usuario_id,papel,ativo)
                    VALUES(:empresa,:user,'OWNER',true)
                """), {"empresa": company, "user": company + 1000})
            c.execute(text("INSERT INTO produtos(id,empresa_id,nome) VALUES (101,1,'Persiana de teste A'),(202,2,'Persiana de teste B')"))

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_01_migration_criou_pk_e_fk_composta(self):
        with self.engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT conname, contype FROM pg_constraint
                WHERE conrelid='public.fiscal_produtos'::regclass
                AND conname IN ('pk_fiscal_produtos', 'fk_fiscal_produto_tenant', 'ck_fiscal_produto_ncm')
            """)).all()
        self.assertEqual({(r[0], r[1]) for r in rows},
                         {("pk_fiscal_produtos","p"), ("fk_fiscal_produto_tenant","f"), ("ck_fiscal_produto_ncm","c")})

    def test_02_configuracao_empresa_fica_no_tenant(self):
        with Session(self.engine) as db:
            tenant = TenantContext(empresa_id=1, user_id=1001)
            data = FiscalEmpresaPatch(crt="3", uf="SP", cidade="São Paulo", cep="01001000",
                                     municipio_codigo_ibge="3550308", logradouro="Rua Fictícia",
                                     numero="10", bairro="Centro", inscricao_estadual="ISENTO",
                                     serie_nfe=1)
            fiscal_cadastros.atualizar_empresa(db,tenant,data)
            got = fiscal_cadastros.ler_empresa(db,tenant)
            self.assertEqual(got["dados"]["crt"],"3")
            self.assertFalse(got["emissao_habilitada"])
            other=fiscal_cadastros.ler_empresa(db,TenantContext(empresa_id=2,user_id=1002))
            self.assertIsNone(other["dados"]["crt"])

    def test_03_crud_produto_restrito_e_sem_emissao(self):
        with Session(self.engine) as db:
            tenant=TenantContext(empresa_id=1,user_id=1001)
            saved=fiscal_cadastros.atualizar_produto(
                db,tenant,101,FiscalProdutoPatch(ncm="63039200",cfop_padrao_saida="5102",
                  origem_mercadoria="0",cst_icms="00",cst_pis="01",cst_cofins="01",
                  cst_ibs_cbs="000",cclass_trib_ibs_cbs="000001"))
            self.assertEqual(saved["dados"]["ncm"],"63039200")
            self.assertFalse(saved["emissao_habilitada"])
            with self.assertRaises(Exception) as ctx:
                fiscal_cadastros.ler_produto(db,TenantContext(empresa_id=2,user_id=1002),101)
            self.assertEqual(getattr(ctx.exception,"status_code",None),404)

    def test_04_cross_tenant_fk_e_ncm_invalido_bloqueados(self):
        from sqlalchemy.exc import IntegrityError
        with Session(self.engine) as db:
            with self.assertRaises(IntegrityError):
                db.execute(text("INSERT INTO fiscal_produtos(empresa_id,produto_id,ncm) VALUES(1,202,'63039200')"))
                db.commit()
            db.rollback()
            with self.assertRaises(IntegrityError):
                db.execute(text("INSERT INTO fiscal_produtos(empresa_id,produto_id,ncm) VALUES(2,202,'INVALIDO')"))
                db.commit()
            db.rollback()

    def test_05_relatorio_completo_e_ausencia_de_emissao(self):
        sale={"id":5,"numero":"CI-000005","cliente_id":None,
              "total":Decimal("100.00"),"desconto":Decimal("0.00"),
              "total_final":Decimal("100.00"),"total_cliente_final":Decimal("100.00"),
              "itens":[{"tipo_item":"PRODUTO","produto_id":101,"descricao":"Persiana fictícia",
                        "quantidade":1,"subtotal":Decimal("100.00")}]}
        app=FastAPI()
        app.include_router(fiscal_router,prefix="/fiscal/cadastros")
        app.include_router(pedidos_router,prefix="/pedidos")
        context={"tenant":TenantContext(empresa_id=1,user_id=1001)}
        app.dependency_overrides[get_current_tenant] = lambda: context["tenant"]
        def db_fixture():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = db_fixture

        def obter_fake(db,pedido_id,tenant):
            return sale if pedido_id==5 and tenant.empresa_id==1 else None

        with TestClient(app) as client:
            with patch("app.services.fiscal_nfe_preparacao.pedido_service.obter",side_effect=obter_fake):
                r=client.get("/pedidos/5/fiscal/preparacao-nfe")
                self.assertEqual(r.status_code,200,r.text)
                data=r.json()
                self.assertEqual(data["estado"],"NAO_APTO_EMISSAO")
                self.assertFalse(data["transmitido"])
                self.assertEqual(data["cadastros_fiscais"]["total_skus"],1)
                self.assertEqual(data["cadastros_fiscais"]["skus_com_cadastro"],1)
                self.assertIn("SEFAZ_NAO_INTEGRADA",{p["codigo"] for p in data["pendencias"]})
                context["tenant"]=TenantContext(empresa_id=2,user_id=1002)
                forbidden=client.get("/pedidos/5/fiscal/preparacao-nfe")
                self.assertEqual(forbidden.status_code,404)
                x=client.get("/fiscal/cadastros/produtos/101")
                self.assertEqual(x.status_code,404)
        with Session(self.engine) as db:
            r=conferir_cadastros_fiscais(db,sale,
                  db.get(EmpresaDB,1),1)
            self.assertIn("REGRAS_TRIBUTARIAS_NAO_VALIDADAS",{x["codigo"] for x in r[0]})

    def test_06_numero_de_registros_fiscais_inalterado_pelo_diagnostico(self):
        with self.engine.connect() as conn:
            count=conn.execute(text("SELECT count(*) FROM fiscal_produtos")).scalar_one()
        self.assertEqual(count,1)


if __name__=="__main__":
    unittest.main()
