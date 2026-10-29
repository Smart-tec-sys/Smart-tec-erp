from unittest.mock import MagicMock
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.admin.platform_company import get_platform_empresa_id
from app.admin.payment_methods import (list_payment_methods, resolve_order_payment_method, create_payment_method, AdminPaymentMethodCreate)
from app.routes import admin


def db_with(row):
    db = MagicMock()
    db.execute.return_value.mappings.return_value.first.return_value = row
    return db


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("SMARTTEC_PLATFORM_EMPRESA_ID", raising=False)
    monkeypatch.delenv("SMARTTEC_PLATFORM_EMPRESA_SLUG", raising=False)


def test_platform_id(monkeypatch):
    monkeypatch.setenv("SMARTTEC_PLATFORM_EMPRESA_ID", "7")
    db=db_with({"id":7,"status":"ATIVA"})
    assert get_platform_empresa_id(db)==7
    assert db.execute.call_args.args[1]=={"id":7}


@pytest.mark.parametrize("slug", [None, "plataforma"])
def test_platform_slug(monkeypatch, slug):
    if slug: monkeypatch.setenv("SMARTTEC_PLATFORM_EMPRESA_SLUG",slug)
    db=db_with({"id":7,"status":"ATIVA"})
    assert get_platform_empresa_id(db)==7
    assert db.execute.call_args.args[1]=={"slug":slug or "smart-tec-persianas"}


@pytest.mark.parametrize("row", [None, {"id":7,"status":"INATIVA"}])
def test_platform_unavailable(row):
    with pytest.raises(HTTPException) as exc: get_platform_empresa_id(db_with(row))
    assert exc.value.status_code==503


@pytest.mark.parametrize("value", ["abc","0","-1"])
def test_invalid_platform_id(monkeypatch,value):
    monkeypatch.setenv("SMARTTEC_PLATFORM_EMPRESA_ID",value)
    with pytest.raises(HTTPException) as exc: get_platform_empresa_id(MagicMock())
    assert exc.value.status_code==503


def test_get_filters(monkeypatch):
    import app.admin.payment_methods as module
    monkeypatch.setattr(module,"get_platform_empresa_id",lambda db:7)
    db=MagicMock(); db.execute.return_value.mappings.return_value.all.return_value=[]
    assert list_payment_methods(db)==[]
    sql=str(db.execute.call_args.args[0])
    assert "f.empresa_id=:empresa_id" in sql
    assert "f.ativo IS TRUE" in sql
    assert "('RECEBER','AMBOS')" in sql
    assert db.execute.call_args.args[1]=={"empresa_id":7}


@pytest.mark.parametrize("row", [None, {"id":3,"nome":"PIX","ativo":False,"disponivel_para":"RECEBER"}, {"id":3,"nome":"PIX","ativo":True,"disponivel_para":"PAGAR"}])
def test_invalid_method(monkeypatch,row):
    monkeypatch.setattr("app.admin.payment_methods.get_platform_empresa_id",lambda db:7)
    db=db_with(row)
    with pytest.raises(HTTPException) as exc: resolve_order_payment_method(db,3,"ignored")
    assert exc.value.status_code==400
    assert db.execute.call_args.args[1]=={"id":3,"empresa_id":7}


@pytest.mark.parametrize("availability",["RECEBER","AMBOS"])
def test_snapshot(monkeypatch,availability):
    monkeypatch.setattr("app.admin.payment_methods.get_platform_empresa_id",lambda db:7)
    db=db_with({"id":3,"nome":"Banco Inter PIX","ativo":True,"disponivel_para":availability})
    assert resolve_order_payment_method(db,3,"Banco Inter")== (3,"Banco Inter PIX")


def test_legacy():
    db=MagicMock()
    assert resolve_order_payment_method(db,None," banco inter ")== (None,"banco inter")
    db.execute.assert_not_called()


def test_inline_platform(monkeypatch):
    monkeypatch.setattr("app.admin.payment_methods.get_platform_empresa_id",lambda db:7)
    db=MagicMock(); db.execute.return_value.mappings.return_value.one.return_value={"id":3,"nome":"PIX"}
    assert create_payment_method(db,AdminPaymentMethodCreate(nome="PIX",tipo="PIX"))["id"]==3
    params=db.execute.call_args.args[1]
    assert params["empresa_id"]==7 and params["disponivel_para"]=="RECEBER"


@pytest.mark.parametrize("data",[{"disponivel_para":"PAGAR"},{"conta_financeira_id":8},{"ativo":False}])
def test_inline_restrictions(monkeypatch,data):
    monkeypatch.setattr("app.admin.payment_methods.get_platform_empresa_id",lambda db:7)
    with pytest.raises(HTTPException): create_payment_method(MagicMock(),AdminPaymentMethodCreate(nome="PIX",**data))


class RecordingDB:
    def __init__(self, payment_exists=False):
        self.calls=[]; self.payment_exists=payment_exists
    def execute(self,statement,params=None):
        sql=str(statement); self.calls.append((sql,params))
        result=MagicMock()
        if "FROM empresas" in sql:
            result.mappings.return_value.first.return_value={"id":4,"status":"ATIVA"}
        elif "FROM pedidos_modulos_saas pm" in sql:
            result.mappings.return_value.first.return_value={"id":5,"modulo_id":1,"status":"AGUARDANDO_PAGAMENTO","valor":100,"periodicidade":"UNICO","forma_pagamento_id":3,"forma_pagamento":"PIX antigo","modulo_nome":"Módulo"}
        elif "FROM pagamentos_saas" in sql:
            result.mappings.return_value.first.return_value={"id":8,"status":"PENDENTE"} if self.payment_exists else None
            result.scalar.return_value=None
        result.scalar_one.return_value=8
        return result
    def commit(self): pass
    def rollback(self): pass


@pytest.mark.parametrize("exists",[False,True])
def test_payment_propagation(exists):
    db=RecordingDB(exists)
    member=SimpleNamespace(has_permission=lambda p:True,equipe_id=1,usuario_id=1)
    admin.admin_alterar_status_pedido_modulo(4,5,admin.AdminModuleOrderStatusInput(status="PAGO"),member,db)
    writes=[(sql,params) for sql,params in db.calls if "INSERT INTO pagamentos_saas" in sql or "UPDATE pagamentos_saas" in sql]
    assert writes
    for sql,params in writes:
        assert params["forma_pagamento_id"]==3
        assert params["forma_pagamento"]=="PIX antigo"
        assert "forma_pagamento_id" in sql
        assert "COALESCE(\n                                :forma_pagamento_id" not in sql


def test_read_queries_current_name_and_legacy():
    # Check both actual detail queries include a LEFT JOIN and historical fallback.
    import inspect
    source=inspect.getsource(admin.admin_empresa_detalhe)
    assert "COALESCE(fp.nome,pm.forma_pagamento) AS forma_pagamento_nome" in source
    assert "COALESCE(fp.nome,p.forma_pagamento) AS forma_pagamento_nome" in source
    assert source.count("LEFT JOIN formas_pagamento")==4


def test_endpoint_permissions():
    for route in admin.router.routes:
        if route.path=="/formas-pagamento":
            assert route.dependant.dependencies


@pytest.mark.parametrize("method_id", [3,None])
def test_order_creation_records_id_and_snapshot(monkeypatch,method_id):
    db=MagicMock()
    def execute(statement,params=None):
        sql=str(statement); result=MagicMock()
        result.scalar.return_value=None
        result.scalar_one.return_value=5
        if "FROM empresas" in sql: result.mappings.return_value.first.return_value={"id":4,"status":"ATIVA"}
        elif "FROM modulos_saas" in sql: result.mappings.return_value.first.return_value={"id":1,"codigo":"M","nome":"Módulo","ativo":True}
        return result
    db.execute.side_effect=execute
    monkeypatch.setattr(admin,"resolve_order_payment_method",lambda db,id,legacy:(id,"PIX cadastrado" if id else legacy))
    member=SimpleNamespace(has_permission=lambda p:True,equipe_id=1,usuario_id=1)
    admin.admin_criar_pedido_modulo(4,admin.AdminModuleOrderCreateInput(modulo_id=1,valor=100,periodicidade="UNICO",forma_pagamento_id=method_id,forma_pagamento="banco inter"),member,db)
    writes=[call for call in db.execute.call_args_list if "INSERT INTO pedidos_modulos_saas" in str(call.args[0])]
    assert len(writes)==1
    assert writes[0].args[1]["forma_pagamento_id"]==method_id
    assert writes[0].args[1]["forma_pagamento"]==("PIX cadastrado" if method_id else "banco inter")
    db.commit.assert_called_once()


@pytest.fixture
def payment_sql_db(monkeypatch):
    from sqlalchemy import create_engine,text
    from sqlalchemy.orm import Session
    engine=create_engine("sqlite:///:memory:")
    with Session(engine) as db:
        db.execute(text("CREATE TABLE formas_pagamento (id INTEGER PRIMARY KEY,empresa_id INTEGER,nome TEXT,tipo TEXT,disponivel_para TEXT,ativo BOOLEAN,conta_financeira_id INTEGER)"))
        db.execute(text("CREATE TABLE contas_financeiras (id INTEGER PRIMARY KEY,empresa_id INTEGER,nome TEXT)"))
        for id,owner,active,available in [(1,7,True,'RECEBER'),(2,7,True,'AMBOS'),(3,7,False,'RECEBER'),(4,7,True,'PAGAR'),(5,8,True,'RECEBER')]:
            db.execute(text("INSERT INTO formas_pagamento VALUES (:id,:owner,'PIX','PIX',:available,:active,NULL)"),dict(id=id,owner=owner,active=active,available=available))
        monkeypatch.setattr("app.admin.payment_methods.get_platform_empresa_id",lambda db:7)
        yield db
    engine.dispose()


def test_real_sql_platform_active_receiving_filter(payment_sql_db):
    assert {row['id'] for row in list_payment_methods(payment_sql_db)}=={1,2}


def test_real_sql_other_company_rejected(payment_sql_db):
    with pytest.raises(HTTPException) as exc: resolve_order_payment_method(payment_sql_db,5,None)
    assert exc.value.status_code==400


def test_real_sql_inline_and_snapshot(payment_sql_db):
    created=create_payment_method(payment_sql_db,AdminPaymentMethodCreate(nome="Novo PIX",tipo="PIX"))
    assert resolve_order_payment_method(payment_sql_db,created['id'],None)==(created['id'],'Novo PIX')
