"""The company read endpoint exposes existing F1 fields without changing contracts."""
from unittest.mock import MagicMock
from app.routes.admin import admin_empresa_detalhe

def test_company_subscription_history_projection():
    queries=[]
    db=MagicMock()
    def execute(statement,params):
        sql=str(statement);queries.append((sql,params));result=MagicMock()
        result.mappings.return_value.first.return_value={'id':17}
        result.mappings.return_value.all.return_value=[]
        result.mappings.return_value.one.return_value={}
        return result
    db.execute.side_effect=execute
    result=admin_empresa_detalhe(17,db=db,member=MagicMock())
    subscription=[q for q,p in queries if 'FROM assinaturas_saas a' in q][0]
    assert 'a.plano_id' in subscription and 'a.forma_pagamento_id' in subscription
    assert 'fp.nome AS forma_pagamento_nome' in subscription
    payments=[q for q,p in queries if 'FROM pagamentos_saas p' in q and 'p.ciclo_inicio' in q]
    assert len(payments)==2
    assert all('p.ciclo_fim' in q for q in payments)
    assert 'LIMIT 20' in payments[0]
    assert "p.tipo = 'ASSINATURA'" in payments[1] and 'LIMIT' not in payments[1]
    assert all(p=={'empresa_id':17} for q,p in queries)
    assert result['cobrancas_assinatura']==[]

from datetime import date
from sqlalchemy import text
from test_admin_subscriptions_f1 import db, prepare, charge, execute, MEMBER
from app.admin import subscriptions as svc

def isolate_detail_tables(db):
    for table in ('empresa_usuarios','usuarios','plataforma_equipe','pedidos_modulos_saas','notas_fiscais_saas','chamados_suporte_saas','acompanhamentos_comerciais_saas'):
        execute(db,f'CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)')

def test_f2_detail_initial_payment_and_two_cycles(db):
    isolate_detail_tables(db)
    contract=prepare(db)
    first=charge(db,contract,date.today())
    detail=admin_empresa_detalhe(2,member=MEMBER,db=db)
    assert detail['assinatura']['status']=='PENDENTE'
    assert detail['assinatura']['forma_pagamento_nome']=='PIX contratado'
    assert detail['assinatura']['plano_id']==1
    assert detail['modulos']==[]
    bill=detail['cobrancas_assinatura'][0]
    assert bill['ciclo_inicio']==date.today() and bill['status']=='PENDENTE'
    assert bill['forma_pagamento_id']==1
    svc.confirm_payment(db,member=MEMBER,pagamento_id=first)
    detail=admin_empresa_detalhe(2,member=MEMBER,db=db)
    due=detail['assinatura']['data_vencimento']
    assert detail['assinatura']['status']=='ATIVA' and len(detail['modulos'])==1
    next_payment=charge(db,contract)
    assert admin_empresa_detalhe(2,member=MEMBER,db=db)['assinatura']['data_vencimento']==due
    svc.confirm_payment(db,member=MEMBER,pagamento_id=next_payment)
    assert svc.confirm_payment(db,member=MEMBER,pagamento_id=next_payment)['idempotente']
    detail=admin_empresa_detalhe(2,member=MEMBER,db=db)
    assert len(detail['cobrancas_assinatura'])==2
    assert all(p['status']=='PAGO' for p in detail['cobrancas_assinatura'])
    assert detail['assinatura']['data_vencimento']>due

def test_f2_history_not_truncated_by_financial_cards(db):
    isolate_detail_tables(db)
    contract=prepare(db)
    execute(db,"""INSERT INTO pagamentos_saas(empresa_id,assinatura_id,tipo,status,valor,forma_pagamento)
        SELECT 2,:id,'ASSINATURA','CANCELADO',100,'PIX histórico' FROM generate_series(1,23)""",{'id':contract})
    execute(db,"INSERT INTO pagamentos_saas(empresa_id,tipo,status,valor,forma_pagamento) VALUES (3,'MODULO_AVULSO','PAGO',10,'Banco Inter')")
    detail=admin_empresa_detalhe(2,member=MEMBER,db=db)
    assert len(detail['pagamentos'])==20
    assert len(detail['cobrancas_assinatura'])==23
    assert all(p['assinatura_id']==contract for p in detail['cobrancas_assinatura'])
    assert all(p['forma_pagamento_nome']=='PIX histórico' and p['forma_pagamento_id'] is None for p in detail['cobrancas_assinatura'])
