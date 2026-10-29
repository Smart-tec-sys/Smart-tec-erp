"""Direct module administration tests use PostgreSQL TEMP tables only."""
from datetime import date, timedelta
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from app.routes import admin
from test_admin_subscriptions_f1 import db, execute

MEMBER = SimpleNamespace(equipe_id=1,usuario_id=1,has_permission=lambda permission: True)

def grant(db, **overrides):
    payload = admin.AdminModuleActivateInput(**{'origem':'CORTESIA','periodicidade':'CORTESIA',**overrides})
    return admin.admin_ativar_modulo(2,1,payload,MEMBER,db)

@pytest.mark.parametrize('origin',['AVULSO','PLANO','TRIAL'])
def test_direct_activation_requires_courtesy(db,origin):
    with pytest.raises(HTTPException) as exc: grant(db,origem=origin)
    assert exc.value.status_code==409
    assert db.execute(text('SELECT count(*) FROM empresa_modulos_saas')).scalar_one()==0
    assert db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()==0

@pytest.mark.parametrize('status',['ATIVO','PENDENTE','SUSPENSO'])
@pytest.mark.parametrize('origin',['AVULSO','CORTESIA','PLANO','TRIAL'])
def test_courtesy_never_overwrites_existing_link(db,status,origin):
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status,data_inicio,valor) VALUES (2,1,:origin,:status,CURRENT_DATE,42)",{'origin':origin,'status':status})
    before=db.execute(text('SELECT to_jsonb(em) FROM empresa_modulos_saas em')).scalar_one()
    with pytest.raises(HTTPException) as exc: grant(db)
    assert exc.value.status_code==409
    assert db.execute(text('SELECT to_jsonb(em) FROM empresa_modulos_saas em')).scalar_one()==before
    assert db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()==0

@pytest.mark.parametrize('end',[None,date.today()+timedelta(days=30)])
def test_courtesy_can_be_granted_without_commercial_value(db,end):
    result=grant(db,data_fim=end,observacoes='Cortesia de teste')
    assert result['origem']=='CORTESIA' and result['status']=='ATIVO'
    row=db.execute(text('SELECT origem,periodicidade,valor,data_inicio,data_fim,observacoes FROM empresa_modulos_saas')).one()
    assert tuple(row)==('CORTESIA','CORTESIA',None,date.today(),end,'Cortesia de teste')

@pytest.mark.parametrize('status',['CANCELADO','EXPIRADO'])
def test_ended_link_does_not_prevent_new_courtesy(db,status):
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status,data_inicio) VALUES (2,1,'AVULSO',:status,CURRENT_DATE)",{'status':status})
    grant(db)
    assert db.execute(text('SELECT count(*) FROM empresa_modulos_saas')).scalar_one()==2
    assert db.execute(text("SELECT status FROM empresa_modulos_saas WHERE origem='AVULSO'")).scalar_one()==status

@pytest.mark.parametrize('origin',['PLANO','TRIAL'])
def test_linked_module_cannot_be_cancelled_in_isolation(db,origin):
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status,data_inicio) VALUES (2,1,:origin,'ATIVO',CURRENT_DATE)",{'origin':origin})
    with pytest.raises(HTTPException) as exc: admin.admin_cancelar_modulo(2,1,MEMBER,db)
    assert exc.value.status_code==409
    assert db.execute(text('SELECT status FROM empresa_modulos_saas')).scalar_one()=='ATIVO'
    assert db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()==0

@pytest.mark.parametrize('origin',['AVULSO','CORTESIA'])
def test_independent_module_can_be_cancelled(db,origin):
    execute(db,"INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,origem,status,data_inicio) VALUES (2,1,:origin,'ATIVO',CURRENT_DATE)",{'origin':origin})
    assert admin.admin_cancelar_modulo(2,1,MEMBER,db)['status']=='CANCELADO'
    assert db.execute(text('SELECT status FROM empresa_modulos_saas')).scalar_one()=='CANCELADO'

@pytest.mark.parametrize('changes',[{'valor':10},{'periodicidade':'MENSAL'},{'data_fim':date.today()-timedelta(days=1)}])
def test_courtesy_rejects_commercial_or_invalid_dates(db,changes):
    with pytest.raises(HTTPException) as exc: grant(db,**changes)
    assert exc.value.status_code==400
    assert db.execute(text('SELECT count(*) FROM empresa_modulos_saas')).scalar_one()==0

def test_courtesy_requires_additional_permission(db):
    member=SimpleNamespace(equipe_id=1,usuario_id=1,has_permission=lambda permission:False)
    with pytest.raises(HTTPException) as exc: admin.admin_ativar_modulo(2,1,admin.AdminModuleActivateInput(origem='CORTESIA'),member,db)
    assert exc.value.status_code==403
