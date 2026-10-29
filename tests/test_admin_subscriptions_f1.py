"""Integration tests use PostgreSQL TEMP tables; no public rows or sequences are written."""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import os,re
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.admin import subscriptions as svc
from app.routes.admin import _next_due_date, AdminSubscriptionContractInput, AdminSubscriptionChargeInput

MEMBER=SimpleNamespace(equipe_id=1,usuario_id=1)
TABLES=('empresas','planos_saas','modulos_saas','plano_modulos_saas','contas_financeiras','formas_pagamento','assinaturas_saas','pagamentos_saas','empresa_modulos_saas','auditoria_plataforma')

class TempDB:
    def __init__(self,session):self.session=session
    def execute(self,statement,params=None):
        if 'FROM information_schema.columns' in str(statement):
            return SimpleNamespace(scalar_one=lambda:3)
        return self.session.execute(statement,params or {})
    def commit(self):self.session.commit()
    def rollback(self):self.session.rollback()

@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv('SMARTTEC_PLATFORM_EMPRESA_ID','1')
    engine=create_engine(os.getenv('ADMIN_TEST_DATABASE_URL','postgresql://smarttec_dev@localhost:5432/smarttec_erp_dev'))
    connection=engine.connect()
    session=Session(bind=connection)
    try:
        session.execute(text('SET search_path TO pg_temp,public'))
        for table in TABLES:
            session.execute(text(f'CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)'))
            session.execute(text(f'CREATE TEMP SEQUENCE seq_{table} START 100'))
            session.execute(text(f"ALTER TABLE pg_temp.{table} ALTER COLUMN id SET DEFAULT nextval('pg_temp.seq_{table}')"))
        migration=Path('migrations/20261006_admin_assinaturas_ciclo_f1_up.sql').read_text(encoding='utf-8')
        body=re.sub(r'^\s*(BEGIN|COMMIT);\s*$','',migration,flags=re.M).replace('public.','pg_temp.')
        applied = session.execute(text("""
            SELECT count(*) FROM information_schema.columns WHERE table_schema='public'
              AND ((table_name='assinaturas_saas' AND column_name='forma_pagamento_id')
                   OR (table_name='pagamentos_saas' AND column_name IN ('ciclo_inicio','ciclo_fim')))
        """)).scalar_one()
        if applied == 0:
            session.execute(text(body))
        elif applied == 3:
            # LIKE INCLUDING ALL already copied the columns, CHECKs and indexes.
            # Foreign keys are not copied by LIKE, so add the fixture-only FK.
            session.execute(text("ALTER TABLE pg_temp.assinaturas_saas ADD CONSTRAINT fk_assinaturas_saas_forma_pagamento FOREIGN KEY(forma_pagamento_id) REFERENCES pg_temp.formas_pagamento(id) ON DELETE SET NULL"))
        else:
            raise AssertionError('Schema F1 parcialmente aplicado')
        session.execute(text("INSERT INTO empresas(id,nome,slug) VALUES (1,'Plataforma','plataforma'),(2,'Cliente teste','cliente-teste'),(3,'Outra empresa','outra')"))
        session.execute(text("INSERT INTO planos_saas(id,codigo,nome,produto,periodicidade,valor) VALUES (1,'TEST','Plano teste','ERP','MENSAL',100)"))
        session.execute(text("INSERT INTO modulos_saas(id,codigo,nome,produto) VALUES (1,'TEST','Modulo teste','ERP')"))
        session.execute(text('INSERT INTO plano_modulos_saas(plano_id,modulo_id) VALUES (1,1)'))
        session.execute(text("INSERT INTO formas_pagamento(id,empresa_id,nome,tipo,disponivel_para) VALUES (1,1,'PIX contratado','PIX','RECEBER'),(2,3,'Outra','PIX','RECEBER'),(3,1,'Pagar','PIX','PAGAR')"))
        session.execute(text("INSERT INTO formas_pagamento(id,empresa_id,nome,tipo,disponivel_para,ativo) VALUES (4,1,'Inativa','PIX','RECEBER',FALSE)"))
        session.commit()
        yield TempDB(session)
    finally:
        session.close();connection.close();engine.dispose()


def execute(db,sql,params=None):
    result=db.execute(text(sql),params or {});db.commit();return result

def prepare(db,**overrides):
    data=dict(member=MEMBER,empresa_id=2,plano_id=1,periodicidade='MENSAL',valor=Decimal('100'),forma_pagamento_id=1,renovacao_automatica=True)
    return svc.prepare_contract(db,**{**data,**overrides})['assinatura_id']

def charge(db,id,start=None):
    return svc.generate_charge(db,member=MEMBER,assinatura_id=id,ciclo_inicio=start,vencimento=date.today())['pagamento_id']

def expect_error(code,operation):
    with pytest.raises(HTTPException) as e:operation()
    assert e.value.status_code==code


def test_pending_no_modules_and_history(db):
    execute(db,"INSERT INTO assinaturas_saas(id,empresa_id,status) VALUES (1,1,'TRIAL')")
    id=prepare(db)
    assert db.execute(text('SELECT status FROM assinaturas_saas WHERE id=:id'),{'id':id}).scalar_one()=='PENDENTE'
    assert db.execute(text('SELECT count(*) FROM empresa_modulos_saas')).scalar_one()==0
    assert db.execute(text('SELECT forma_pagamento_id FROM assinaturas_saas WHERE id=1')).scalar_one() is None
    execute(db,"INSERT INTO pagamentos_saas(empresa_id,tipo,status,valor,forma_pagamento) VALUES (1,'MODULO_AVULSO','PAGO',10,'Banco Inter')")
    assert db.execute(text("SELECT ciclo_inicio FROM pagamentos_saas WHERE tipo='MODULO_AVULSO'")).scalar_one() is None


@pytest.mark.parametrize('method',[None,999,2,3,4])
def test_invalid_forms(db,method):
    expect_error(400,lambda:prepare(db,forma_pagamento_id=method))
    assert db.execute(text('SELECT count(*) FROM assinaturas_saas')).scalar_one()==0


@pytest.mark.parametrize('changes',[{'valor':0},{'periodicidade':'UNICO'}])
def test_invalid_contract(db,changes):expect_error(400,lambda:prepare(db,**changes))


def test_inactive_company_plan_and_live_contract(db):
    execute(db,"UPDATE empresas SET status='INATIVA' WHERE id=2")
    expect_error(409,lambda:prepare(db))
    execute(db,"UPDATE empresas SET status='ATIVA' WHERE id=2")
    execute(db,'UPDATE planos_saas SET ativo=FALSE WHERE id=1')
    expect_error(404,lambda:prepare(db))
    execute(db,'UPDATE planos_saas SET ativo=TRUE WHERE id=1')
    prepare(db);expect_error(409,lambda:prepare(db))


def test_price_and_method_snapshots(db):
    id=prepare(db)
    execute(db,'UPDATE planos_saas SET valor=999 WHERE id=1')
    payment=charge(db,id,date.today())
    execute(db,"UPDATE formas_pagamento SET nome='PIX novo' WHERE id=1")
    row=db.execute(text('SELECT valor,forma_pagamento_id,forma_pagamento FROM pagamentos_saas WHERE id=:id'),{'id':payment}).one()
    assert tuple(row)==(Decimal('100'),1,'PIX contratado')


@pytest.mark.parametrize('period',['MENSAL','ANUAL'])
def test_initial_idempotency_and_renewal(db,period):
    id=prepare(db,periodicidade=period)
    first=charge(db,id,date.today())
    before=db.execute(text('SELECT count(*) FROM empresa_modulos_saas')).scalar_one();assert before==0
    result=svc.confirm_payment(db,member=MEMBER,pagamento_id=first)
    expected=_next_due_date(date.today(),period);assert result['data_vencimento']==expected
    assert db.execute(text('SELECT count(*) FROM empresa_modulos_saas')).scalar_one()==1
    audit_count=db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()
    repeat=svc.confirm_payment(db,member=MEMBER,pagamento_id=first)
    assert repeat['idempotente'] and repeat['data_vencimento']==expected
    assert db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()==audit_count
    renewal=charge(db,id)
    assert db.execute(text('SELECT data_vencimento FROM assinaturas_saas WHERE id=:id'),{'id':id}).scalar_one()==expected
    result=svc.confirm_payment(db,member=MEMBER,pagamento_id=renewal)
    assert result['assinatura_id']==id and result['data_vencimento']==_next_due_date(expected,period)


def test_duplicate_cancelled_replacement_and_estorno(db):
    id=prepare(db);pay=charge(db,id,date.today())
    expect_error(409,lambda:charge(db,id,date.today()))
    execute(db,"UPDATE pagamentos_saas SET status='CANCELADO' WHERE id=:id",{'id':pay})
    replacement=charge(db,id,date.today());assert replacement!=pay
    execute(db,"UPDATE pagamentos_saas SET status='ESTORNADO' WHERE id=:id",{'id':replacement})
    expect_error(409,lambda:charge(db,id,date.today()))


@pytest.mark.parametrize('origin',['AVULSO','CORTESIA','PLANO','TRIAL'])
def test_independent_modules_not_absorbed(db,origin):
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status,valor) VALUES (2,1,:origin,'ATIVO',33)",{'origin':origin})
    expect_error(409,lambda:prepare(db))
    assert tuple(db.execute(text('SELECT origem,valor FROM empresa_modulos_saas')).one())==(origin,Decimal('33'))
    assert db.execute(text('SELECT count(*) FROM assinaturas_saas')).scalar_one()==0


def test_conflict_before_activation_rollback(db):
    id=prepare(db);pay=charge(db,id,date.today())
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status) VALUES (2,1,'AVULSO','ATIVO')")
    expect_error(409,lambda:svc.confirm_payment(db,member=MEMBER,pagamento_id=pay))
    assert db.execute(text('SELECT status FROM pagamentos_saas WHERE id=:id'),{'id':pay}).scalar_one()=='PENDENTE'
    assert db.execute(text('SELECT status FROM assinaturas_saas WHERE id=:id'),{'id':id}).scalar_one()=='PENDENTE'


def test_trial_same_contract_dates_preserved(db):
    yesterday=date.today()-timedelta(days=1)
    execute(db,"INSERT INTO assinaturas_saas(id,empresa_id,status,data_inicio_trial,data_fim_trial) VALUES (1,2,'TRIAL',:start,:end)",{'start':yesterday-timedelta(days=7),'end':yesterday})
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,assinatura_id,origem,status) VALUES (2,1,1,'TRIAL','ATIVO')")
    assert prepare(db,trial_id=1)==1
    assert db.execute(text('SELECT status FROM assinaturas_saas WHERE id=1')).scalar_one()=='TRIAL'
    pay=charge(db,1,date.today());svc.confirm_payment(db,member=MEMBER,pagamento_id=pay)
    row=db.execute(text('SELECT status,data_inicio_trial,data_fim_trial FROM assinaturas_saas WHERE id=1')).one()
    assert tuple(row)==('ATIVA',yesterday-timedelta(days=7),yesterday)
    assert db.execute(text('SELECT origem FROM empresa_modulos_saas')).scalar_one()=='PLANO'


def test_trial_not_ended(db):
    tomorrow=date.today()+timedelta(days=1)
    execute(db,"INSERT INTO assinaturas_saas(id,empresa_id,status,data_inicio_trial,data_fim_trial) VALUES (1,2,'TRIAL',:start,:end)",{'start':date.today(),'end':tomorrow})
    prepare(db,trial_id=1);pay=charge(db,1,tomorrow)
    expect_error(409,lambda:svc.confirm_payment(db,member=MEMBER,pagamento_id=pay))


def test_incomplete_and_out_of_order_cycles(db):
    id=prepare(db)
    expect_error(400,lambda:charge(db,id))
    pay=charge(db,id,date.today());svc.confirm_payment(db,member=MEMBER,pagamento_id=pay)
    start=_next_due_date(_next_due_date(date.today(),'MENSAL'),'MENSAL')
    execute(db,"INSERT INTO pagamentos_saas(empresa_id,assinatura_id,tipo,status,valor,ciclo_inicio,ciclo_fim) VALUES (2,:id,'ASSINATURA','PENDENTE',100,:start,:end)",{'id':id,'start':start,'end':_next_due_date(start,'MENSAL')})
    later=db.execute(text('SELECT max(id) FROM pagamentos_saas')).scalar_one()
    expect_error(409,lambda:svc.confirm_payment(db,member=MEMBER,pagamento_id=later))


def test_partial_cycle_database_check_and_unique_index(db):
    id=prepare(db);pay=charge(db,id,date.today())
    with pytest.raises(IntegrityError):
        db.execute(text("INSERT INTO pagamentos_saas(empresa_id,assinatura_id,tipo,status,valor,ciclo_inicio) VALUES (2,:id,'ASSINATURA','PENDENTE',100,:start)"),{'id':id,'start':date.today()})
    db.rollback()
    with pytest.raises(IntegrityError):
        db.execute(text("INSERT INTO pagamentos_saas(empresa_id,assinatura_id,tipo,status,valor,ciclo_inicio,ciclo_fim) SELECT empresa_id,assinatura_id,tipo,status,valor,ciclo_inicio,ciclo_fim FROM pagamentos_saas WHERE id=:id"),{'id':pay})
    db.rollback()


@pytest.mark.parametrize('start,period,expected',[(date(2026,1,31),'MENSAL',date(2026,2,28)),(date(2024,1,31),'MENSAL',date(2024,2,29)),(date(2024,2,29),'ANUAL',date(2025,2,28)),(date(2026,12,31),'MENSAL',date(2027,1,31))])
def test_calendar_rule(start,period,expected):assert _next_due_date(start,period)==expected


def test_integrity_error_friendly():
    db=MagicMock()
    db.execute.return_value.scalar_one.return_value=3
    error=IntegrityError('INSERT',{},SimpleNamespace(diag=SimpleNamespace(constraint_name='uq_pagamentos_saas_assinatura_ciclo')))
    @svc.transaction
    def operation(db):raise error
    expect_error(409,lambda:operation(db));db.rollback.assert_called_once();db.commit.assert_not_called()


def test_schema_not_applied_returns_503():
    db=MagicMock();db.execute.return_value.scalar_one.return_value=0
    expect_error(503,lambda:svc.prepare_contract(db,member=MEMBER,empresa_id=2,plano_id=1,periodicidade='MENSAL',valor=100,forma_pagamento_id=1))


def test_inputs_validate_incomplete_values():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):AdminSubscriptionChargeInput()
    with pytest.raises(ValidationError):AdminSubscriptionContractInput(plano_id=1,periodicidade='MENSAL',valor=0,forma_pagamento_id=1)


def test_renewal_preserves_extra_cortesia_avulso(db):
    id=prepare(db);pay=charge(db,id,date.today());svc.confirm_payment(db,member=MEMBER,pagamento_id=pay)
    for module,origin in [(2,'AVULSO'),(3,'CORTESIA')]:
        execute(db,"INSERT INTO modulos_saas(id,codigo,nome,produto) VALUES (:id,:code,'Extra','ERP')",{'id':module,'code':str(module)})
        execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status,data_fim,valor) VALUES (2,:module,:origin,'ATIVO',:end,33)",{'module':module,'origin':origin,'end':date.today()+timedelta(days=10)})
    before=db.execute(text("SELECT to_jsonb(m) FROM empresa_modulos_saas m WHERE origem<>'PLANO' ORDER BY id")).all()
    renewal=charge(db,id);svc.confirm_payment(db,member=MEMBER,pagamento_id=renewal)
    assert db.execute(text("SELECT to_jsonb(m) FROM empresa_modulos_saas m WHERE origem<>'PLANO' ORDER BY id")).all()==before


def test_late_failure_rolls_back_all_updates(db,monkeypatch):
    id=prepare(db);pay=charge(db,id,date.today())
    def fail(*args,**kwargs):raise RuntimeError('Falha técnica após updates')
    monkeypatch.setattr(svc,'activate_plan_modules',fail)
    with pytest.raises(RuntimeError):svc.confirm_payment(db,member=MEMBER,pagamento_id=pay)
    assert db.execute(text('SELECT status FROM pagamentos_saas WHERE id=:id'),{'id':pay}).scalar_one()=='PENDENTE'
    assert db.execute(text('SELECT data_vencimento FROM assinaturas_saas WHERE id=:id'),{'id':id}).scalar_one() is None


def test_same_paid_payment_idempotent_even_if_company_inactive(db):
    id=prepare(db);pay=charge(db,id,date.today());svc.confirm_payment(db,member=MEMBER,pagamento_id=pay)
    execute(db,"UPDATE empresas SET status='INATIVA' WHERE id=2")
    assert svc.confirm_payment(db,member=MEMBER,pagamento_id=pay)['idempotente']


def test_concurrent_database_unique_cycle():
    import threading,uuid
    from concurrent.futures import ThreadPoolExecutor
    schema='test_admin_f1_'+uuid.uuid4().hex
    engine=create_engine(os.getenv('ADMIN_TEST_DATABASE_URL','postgresql://smarttec_dev@localhost:5432/smarttec_erp_dev'))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {schema}'))
            connection.execute(text(f'CREATE TABLE {schema}.pagamentos_saas (assinatura_id INTEGER,ciclo_inicio DATE,ciclo_fim DATE,tipo TEXT,status TEXT)'))
            connection.execute(text(f"CREATE UNIQUE INDEX uq_pagamentos_saas_assinatura_ciclo ON {schema}.pagamentos_saas(assinatura_id,ciclo_inicio,ciclo_fim) WHERE tipo='ASSINATURA' AND status IN ('PENDENTE','PROCESSANDO','PAGO','ATRASADO','ESTORNADO')"))
        barrier=threading.Barrier(2)
        def attempt():
            with engine.connect() as connection:
                barrier.wait(timeout=5)
                try:
                    connection.execute(text(f"INSERT INTO {schema}.pagamentos_saas VALUES (1,'2026-10-05','2026-11-05','ASSINATURA','PENDENTE')"))
                    connection.commit();return 'created'
                except IntegrityError:
                    connection.rollback();return 'duplicate'
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(attempt) for _ in range(2)]
            assert sorted(f.result(timeout=10) for f in futures)==['created','duplicate']
    finally:
        assert schema.startswith('test_admin_f1_') and len(schema)==46
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        engine.dispose()


def test_previous_open_cycle_blocks_confirmation(db):
    id=prepare(db);pay=charge(db,id,date.today())
    execute(db,"INSERT INTO pagamentos_saas(empresa_id,assinatura_id,tipo,status,valor,ciclo_inicio,ciclo_fim) VALUES (2,:id,'ASSINATURA','PENDENTE',100,:start,:end)",{'id':id,'start':date.today()-timedelta(days=30),'end':date.today()})
    expect_error(409,lambda:svc.confirm_payment(db,member=MEMBER,pagamento_id=pay))
    assert db.execute(text('SELECT status FROM pagamentos_saas WHERE id=:id'),{'id':pay}).scalar_one()=='PENDENTE'


@pytest.mark.parametrize('value',[Decimal('0.001'),Decimal('10000000000')])
def test_money_not_silently_rounded(db,value):expect_error(400,lambda:prepare(db,valor=value))
