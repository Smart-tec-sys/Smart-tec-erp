"""Support integration uses TEMP tables and TEMP sequences only, never public rows."""
import os
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
import asyncio, json
from pydantic import ValidationError
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from app.admin import support as svc
from app.admin.dependencies import get_current_platform_member
from app.database import get_db

MEMBER=SimpleNamespace(equipe_id=1,usuario_id=1,has_permission=lambda permission:True)
@pytest.fixture
def db():
    engine=create_engine(os.getenv('ADMIN_TEST_DATABASE_URL','postgresql://smarttec_dev@localhost:5432/smarttec_erp_dev'))
    connection=engine.connect();session=Session(bind=connection)
    try:
        session.execute(text('SET search_path TO pg_temp,public'))
        for table in ['empresas','usuarios','empresa_usuarios','plataforma_funcoes','plataforma_equipe','chamados_suporte_saas','auditoria_plataforma']:
            session.execute(text(f'CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)'))
            session.execute(text(f'CREATE TEMP SEQUENCE support_seq_{table} OWNED BY pg_temp.{table}.id'))
            session.execute(text(f"ALTER TABLE pg_temp.{table} ALTER COLUMN id SET DEFAULT nextval('pg_temp.support_seq_{table}')"))
        session.execute(text("INSERT INTO empresas(id,nome,slug) VALUES(1,'Cliente teste','support-test'),(2,'Outra','support-other')"))
        session.execute(text("INSERT INTO usuarios(id,nome,email) VALUES(1,'Agente','agent@example.invalid'),(2,'Solicitante','user@example.invalid')"))
        session.execute(text("INSERT INTO empresa_usuarios(empresa_id,usuario_id,papel) VALUES(1,2,'ADMIN')"))
        session.execute(text("INSERT INTO plataforma_funcoes(id,codigo,nome,nivel) VALUES(1,'SUPORTE_TEST','Suporte',1)"))
        session.execute(text("INSERT INTO plataforma_equipe(id,usuario_id,funcao_id,pode_receber_chamados) VALUES(1,1,1,TRUE)"))
        session.commit();yield session
    finally:
        session.close();connection.close();engine.dispose()

def create(db,**kwargs):return svc.create_ticket(1,svc.SupportCreate(titulo='Chamado teste',**kwargs),MEMBER,db)
def update(db,ticket,**kwargs):return svc.update_ticket(1,ticket['id'],svc.SupportUpdate(**kwargs),MEMBER,db)
def expect_error(code,call):
    with pytest.raises(Exception) as exc:call()
    assert exc.value.status_code==code

def test_create_code_list_detail_and_audit(db):
    one=create(db,usuario_id=2,responsavel_equipe_id=1);two=create(db,prioridade='CRITICA')
    assert one['status']=='ABERTO' and one['codigo']=='SUP-000001'
    assert two['codigo']=='SUP-000002'
    assert one['solicitante_nome']=='Solicitante' and one['responsavel_nome']=='Agente'
    assert [t['id'] for t in svc.list_tickets(1,MEMBER,db)['items']]==[two['id'],one['id']]
    assert db.execute(text("SELECT count(*) FROM auditoria_plataforma WHERE acao='CHAMADO_CRIADO'")).scalar_one()==2
    assert svc.ticket_options(1,MEMBER,db)['responsaveis']==[{'id':1,'nome':'Agente'}]

@pytest.mark.parametrize('priority',['BAIXA','NORMAL','ALTA','CRITICA'])
def test_priorities(db,priority):assert create(db,prioridade=priority)['prioridade']==priority

def test_invalid_priority_and_title(db):
    with pytest.raises(ValidationError):svc.SupportCreate(titulo='Teste',prioridade='URGENTE')
    with pytest.raises(ValidationError):svc.SupportUpdate(prioridade='URGENTE')
    expect_error(422,lambda:svc.create_ticket(1,svc.SupportCreate(titulo='  '),MEMBER,db))

@pytest.mark.parametrize('source,target',[(s,t) for s,targets in svc.TRANSITIONS.items() for t in targets])
def test_allowed_transitions(db,source,target):
    t=create(db)
    db.execute(text("UPDATE chamados_suporte_saas SET status=:status,resolucao='Anterior',resolvido_em=CASE WHEN :status='RESOLVIDO' THEN NOW() ELSE NULL END WHERE id=:id"),{'id':t['id'],'status':source});db.commit()
    result=update(db,t,status=target,**({'resolucao':'Corrigido com sucesso'} if target=='RESOLVIDO' else {}))
    assert result['status']==target
    if target in ['RESOLVIDO','FECHADO']:assert result['resolvido_em'] and result['resolucao']

@pytest.mark.parametrize('source,target',[(s,t) for s in svc.TRANSITIONS for t in svc.TRANSITIONS if t not in svc.TRANSITIONS[s]])
def test_invalid_transitions(db,source,target):
    t=create(db);db.execute(text('UPDATE chamados_suporte_saas SET status=:status WHERE id=:id'),{'status':source,'id':t['id']});db.commit()
    expect_error(409,lambda:update(db,t,status=target))
    assert svc.get_ticket(1,t['id'],MEMBER,db)['status']==source

def test_assignment_priority_and_audit(db):
    t=create(db);result=update(db,t,responsavel_equipe_id=1,prioridade='ALTA')
    assert result['responsavel_equipe_id']==1 and result['prioridade']=='ALTA'
    actions=set(db.execute(text('SELECT acao FROM auditoria_plataforma')).scalars())
    assert {'CHAMADO_RESPONSAVEL_ALTERADO','CHAMADO_PRIORIDADE_ALTERADA'}<=actions
    assert update(db,t,responsavel_equipe_id=None)['responsavel_equipe_id'] is None

@pytest.mark.parametrize('changes',[{'responsavel_equipe_id':999},{'usuario_id':999},{'usuario_id':1}])
def test_invalid_links(db,changes):
    expect_error(400,lambda:create(db,**changes))
    assert db.execute(text('SELECT count(*) FROM chamados_suporte_saas')).scalar_one()==0

def test_ineligible_team_and_tenant(db):
    t=create(db)
    db.execute(text('UPDATE plataforma_equipe SET pode_receber_chamados=FALSE'));db.commit()
    expect_error(400,lambda:update(db,t,responsavel_equipe_id=1))
    expect_error(404,lambda:svc.get_ticket(2,t['id'],MEMBER,db))
    expect_error(404,lambda:svc.update_ticket(2,t['id'],svc.SupportUpdate(prioridade='ALTA'),MEMBER,db))
    assert svc.list_tickets(2,MEMBER,db)['items']==[]

def test_resolution_close_permissions_and_history(db):
    t=create(db)
    for status in ['EM_ANALISE','EM_CORRECAO']:update(db,t,status=status)
    expect_error(422,lambda:update(db,t,status='RESOLVIDO',resolucao=' '))
    limited=SimpleNamespace(has_permission=lambda p:p!='SUPORTE_ENCERRAR')
    expect_error(403,lambda:svc.update_ticket(1,t['id'],svc.SupportUpdate(status='RESOLVIDO',resolucao='OK'),limited,db))
    resolved=update(db,t,status='RESOLVIDO',resolucao='Corrigido')
    closed=update(db,t,status='FECHADO')
    assert closed['resolvido_em']==resolved['resolvido_em'] and closed['resolucao']=='Corrigido'
    expect_error(409,lambda:update(db,t,prioridade='BAIXA'))
    actions=set(db.execute(text('SELECT acao FROM auditoria_plataforma')).scalars())
    assert {'CHAMADO_RESOLVIDO','CHAMADO_FECHADO','CHAMADO_STATUS_ALTERADO'}<=actions

def test_rollback_on_audit_failure(db,monkeypatch):
    def fail(*args,**kwargs):raise RuntimeError('simulated audit failure')
    monkeypatch.setattr(svc,'audit',fail)
    with pytest.raises(RuntimeError):create(db)
    assert db.execute(text('SELECT count(*) FROM chamados_suporte_saas')).scalar_one()==0

def test_security_and_logs_permission(db):
    t=create(db,erro_mensagem='Authorization: Bearer secret',pagina='/teste')
    assert 'secret' not in t['erro_mensagem']
    limited=SimpleNamespace(has_permission=lambda p:p!='SUPORTE_LOGS')
    result=svc.get_ticket(1,t['id'],limited,db)
    assert result['pagina'] is None and result['erro_mensagem'] is None

def request(app, method, path, body=None):
    messages=[]
    async def receive():return {"type":"http.request","body":json.dumps(body or {}).encode(),"more_body":False}
    async def send(message):messages.append(message)
    scope={"type":"http","asgi":{"version":"3.0"},"method":method,"scheme":"http","path":path,"raw_path":path.encode(),"query_string":b"","headers":[(b"content-type",b"application/json")],"client":("test",123),"server":("test",80),"root_path":"","http_version":"1.1"}
    asyncio.run(app(scope,receive,send))
    code=next(m['status'] for m in messages if m['type']=='http.response.start')
    data=json.loads(b''.join(m.get('body',b'') for m in messages if m['type']=='http.response.body'))
    return code,data

def test_route_permissions(db):
    app=FastAPI();app.include_router(svc.router,prefix='/admin')
    limited=SimpleNamespace(has_permission=lambda p:False)
    app.dependency_overrides[get_current_platform_member]=lambda:limited
    app.dependency_overrides[get_db]=lambda:db
    for method,path,body in [('GET','/admin/empresas/1/chamados',None),('POST','/admin/empresas/1/chamados',{'titulo':'Teste'}),('GET','/admin/empresas/1/chamados/opcoes',None)]:
        assert request(app,method,path,body)[0]==403

def test_endpoints(db):
    app=FastAPI();app.include_router(svc.router,prefix='/admin')
    app.dependency_overrides[get_current_platform_member]=lambda:MEMBER
    app.dependency_overrides[get_db]=lambda:db
    code,ticket=request(app,'POST','/admin/empresas/1/chamados',{'titulo':'Teste HTTP','usuario_id':2})
    assert code==201 and ticket['status']=='ABERTO'
    assert request(app,'GET',f"/admin/empresas/1/chamados/{ticket['id']}")[0]==200
    assert request(app,'POST',f"/admin/empresas/1/chamados/{ticket['id']}/atendimento",{'status':'EM_ANALISE'})[0]==200
    assert request(app,'POST',f"/admin/empresas/1/chamados/{ticket['id']}/atendimento",{'status':'FECHADO'})[0]==409
    assert request(app,'POST','/admin/empresas/1/chamados',{'titulo':'Teste','prioridade':'INVALIDA'})[0]==422


def test_update_audit_failure_rolls_back(db,monkeypatch):
    ticket=create(db)
    def fail(*args,**kwargs):raise RuntimeError('simulated failure')
    monkeypatch.setattr(svc,'audit',fail)
    with pytest.raises(RuntimeError):update(db,ticket,status='EM_ANALISE',prioridade='ALTA')
    result=svc.get_ticket(1,ticket['id'],MEMBER,db)
    assert result['status']=='ABERTO' and result['prioridade']=='NORMAL'
    assert db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()==1

def test_audit_resolution_is_safe_and_close_preserves_it(db):
    ticket=create(db)
    for status in ['EM_ANALISE','EM_CORRECAO']:update(db,ticket,status=status)
    update(db,ticket,status='RESOLVIDO',resolucao='token=secret')
    update(db,ticket,status='FECHADO')
    rows=db.execute(text("SELECT detalhes FROM auditoria_plataforma WHERE acao IN ('CHAMADO_RESOLVIDO','CHAMADO_FECHADO')")).scalars().all()
    assert len(rows)==2
    for row in rows:
        assert 'secret' not in str(row) and row['resolucao']=='Detalhes técnicos sensíveis não são exibidos.'
        assert {'status','prioridade','responsavel_equipe_id'}<=row.keys()

def test_noop_preserves_data_and_extra_fields_rejected(db):
    ticket=create(db)
    assert update(db,ticket,prioridade='NORMAL')['atualizado_em']==ticket['atualizado_em']
    assert db.execute(text('SELECT count(*) FROM auditoria_plataforma')).scalar_one()==1
    with pytest.raises(ValidationError):svc.SupportCreate(titulo='Teste',status='FECHADO')
    assert svc.safe_text('Error: failed\n at handler (app.js:2:1)')!='Error: failed\n at handler (app.js:2:1)'
