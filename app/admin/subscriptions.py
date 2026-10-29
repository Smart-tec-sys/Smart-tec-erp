"""Ciclo manual de assinatura antecipada. Nunca aplica DDL ou agenda tarefas."""
from datetime import date
from decimal import Decimal
from functools import wraps
import json

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.admin.payment_methods import resolve_order_payment_method

EXISTING_PAYMENT_STATUSES = ('PENDENTE', 'PROCESSANDO', 'PAGO', 'ATRASADO', 'ESTORNADO')
LIVE_CONTRACT_STATUSES = ('TRIAL', 'TRIAL_EXPIRADO', 'PENDENTE', 'ATIVA', 'PROXIMA_VENCIMENTO', 'VENCIDA', 'SUSPENSA')


def transaction(operation):
    @wraps(operation)
    def wrapped(db, *args, **kwargs):
        try:
            ready = db.execute(text("""
                SELECT count(*) FROM information_schema.columns
                WHERE table_schema='public' AND
                ((table_name='assinaturas_saas' AND column_name='forma_pagamento_id') OR
                 (table_name='pagamentos_saas' AND column_name IN ('ciclo_inicio','ciclo_fim')))
            """)).scalar_one()
            if ready != 3:
                raise HTTPException(503, "Ciclo de assinaturas indisponível: migration F1 ainda não aplicada.")
            result = operation(db, *args, **kwargs)
            db.commit()
            return result
        except IntegrityError as exc:
            db.rollback()
            constraint = getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None)
            message = ("Já existe cobrança para esta assinatura e ciclo."
                       if constraint == 'uq_pagamentos_saas_assinatura_ciclo'
                       else "Conflito de vínculo comercial. Nenhuma alteração foi confirmada.")
            raise HTTPException(409, message) from exc
        except Exception:
            db.rollback()
            raise
    return wrapped


def _audit(db, member, company_id, action, resource, resource_id, details=None):
    db.execute(text("""
        INSERT INTO auditoria_plataforma(equipe_id,usuario_id,empresa_afetada_id,acao,recurso,recurso_id,detalhes)
        VALUES (:team,:user,:company,:action,:resource,:id,CAST(:details AS JSONB))
    """), dict(team=member.equipe_id, user=member.usuario_id, company=company_id,
               action=action, resource=resource, id=str(resource_id),
               details=json.dumps(details or {},default=str,ensure_ascii=False)))


def _company(db, company_id, require_active=True):
    row = db.execute(text("SELECT id,status FROM empresas WHERE id=:id FOR UPDATE"), {'id':company_id}).mappings().first()
    if not row:
        raise HTTPException(404, "Empresa não encontrada.")
    if require_active and row['status'] != 'ATIVA':
        raise HTTPException(409, "Empresa precisa estar ativa.")
    return row


def _contract(db, contract_id):
    owner = db.execute(text("SELECT empresa_id FROM assinaturas_saas WHERE id=:id"), {'id':contract_id}).scalar()
    if owner is None:
        raise HTTPException(404, "Assinatura não encontrada.")
    _company(db, owner, require_active=False)
    row = db.execute(text("SELECT * FROM assinaturas_saas WHERE id=:id FOR UPDATE"), {'id':contract_id}).mappings().first()
    if not row or row['empresa_id'] != owner:
        raise HTTPException(409, "Vínculo da assinatura foi alterado.")
    return row


def _next(start, period):
    # Reuse the established calendar rule rather than introducing another formula.
    from app.routes.admin import _next_due_date
    return _next_due_date(start, period)


def _period(period):
    value = str(period or '').strip().upper()
    if value not in ('MENSAL','ANUAL'):
        raise HTTPException(400, "Periodicidade deve ser MENSAL ou ANUAL.")
    return value


def _price(value):
    if value is None or not Decimal(str(value)).is_finite() or Decimal(str(value)) <= 0:
        raise HTTPException(400, "Valor contratado deve ser maior que zero.")
    amount = Decimal(str(value))
    if amount > Decimal('9999999999.99') or amount != amount.quantize(Decimal('0.01')):
        raise HTTPException(400, "Valor contratado deve respeitar duas casas decimais e o limite monetário do banco.")
    return amount


def plan_module_conflicts(db, *, empresa_id, assinatura_id, plano_id):
    """Preflight all modules: no writes and no absorption of independent grants."""
    modules = db.execute(text("""
        SELECT pm.modulo_id FROM plano_modulos_saas pm JOIN modulos_saas m ON m.id=pm.modulo_id
        WHERE pm.plano_id=:plan AND pm.incluido IS TRUE AND m.ativo IS TRUE ORDER BY pm.modulo_id
    """), {'plan':plano_id}).scalars().all()
    decisions = []
    for module_id in modules:
        row = db.execute(text("""
            SELECT * FROM empresa_modulos_saas
            WHERE empresa_id=:company AND modulo_id=:module AND status IN ('ATIVO','PENDENTE','SUSPENSO')
            ORDER BY id DESC FOR UPDATE
        """), {'company':empresa_id,'module':module_id}).mappings().first()
        if row and not (assinatura_id is not None and row['assinatura_id']==assinatura_id and row['origem'] in ('PLANO','TRIAL')):
            raise HTTPException(409, f"Módulo #{module_id} possui vínculo {row['origem']} independente. Decisão comercial explícita necessária.")
        decisions.append((module_id,row))
    return decisions


def activate_plan_modules(db, *, empresa_id, assinatura_id, plano_id, data_fim):
    decisions = plan_module_conflicts(db, empresa_id=empresa_id, assinatura_id=assinatura_id, plano_id=plano_id)
    for module_id,row in decisions:
        if row:
            db.execute(text("""
                UPDATE empresa_modulos_saas SET origem='PLANO',status='ATIVO',data_fim=:end,atualizado_em=NOW()
                WHERE id=:id AND assinatura_id=:contract AND origem IN ('PLANO','TRIAL')
            """), {'id':row['id'],'end':data_fim,'contract':assinatura_id})
        else:
            db.execute(text("""
                INSERT INTO empresa_modulos_saas(empresa_id,modulo_id,assinatura_id,origem,status,data_inicio,data_fim)
                VALUES (:company,:module,:contract,'PLANO','ATIVO',CURRENT_DATE,:end)
            """), {'company':empresa_id,'module':module_id,'contract':assinatura_id,'end':data_fim})


@transaction
def prepare_contract(db, *, member, empresa_id, plano_id, periodicidade, valor, forma_pagamento_id,
                     renovacao_automatica=False, observacoes=None, trial_id=None):
    _company(db, empresa_id)
    plan = db.execute(text("SELECT id,ativo FROM planos_saas WHERE id=:id FOR SHARE"), {'id':plano_id}).mappings().first()
    if not plan or not plan['ativo']:
        raise HTTPException(404, "Plano ativo não encontrado.")
    period = _period(periodicidade)
    price = _price(valor)
    if forma_pagamento_id is None:
        raise HTTPException(400, "Informe a forma de pagamento da plataforma.")
    method_id,_ = resolve_order_payment_method(db,forma_pagamento_id,None)
    live = db.execute(text("""
        SELECT * FROM assinaturas_saas WHERE empresa_id=:company
        AND status IN ('TRIAL','TRIAL_EXPIRADO','PENDENTE','ATIVA','PROXIMA_VENCIMENTO','VENCIDA','SUSPENSA')
        ORDER BY id FOR UPDATE
    """), {'company':empresa_id}).mappings().all()
    trial = None
    if trial_id is not None:
        if len(live)!=1 or live[0]['id']!=trial_id or live[0]['status'] not in ('TRIAL','TRIAL_EXPIRADO'):
            raise HTTPException(409, "Trial informado não está disponível para conversão nesta empresa.")
        trial = live[0]
    elif live:
        raise HTTPException(409, "Empresa já possui assinatura vigente; utilize o contrato existente.")
    plan_module_conflicts(db,empresa_id=empresa_id,assinatura_id=trial_id,plano_id=plano_id)
    params=dict(company=empresa_id,plan=plano_id,period=period,price=price,method=method_id,
                auto=renovacao_automatica,notes=observacoes)
    if trial:
        params['id']=trial_id
        db.execute(text("""
            UPDATE assinaturas_saas SET plano_id=:plan,periodicidade=:period,valor=:price,
              forma_pagamento_id=:method,renovacao_automatica=:auto,observacoes=:notes,atualizado_em=NOW()
            WHERE id=:id
        """),params)
        contract_id=trial_id
        state=trial['status']
    else:
        contract_id=db.execute(text("""
            INSERT INTO assinaturas_saas(empresa_id,plano_id,status,periodicidade,valor,forma_pagamento_id,renovacao_automatica,observacoes)
            VALUES (:company,:plan,'PENDENTE',:period,:price,:method,:auto,:notes) RETURNING id
        """),params).scalar_one()
        state='PENDENTE'
    _audit(db,member,empresa_id,'ASSINATURA_CONTRATO_PREPARADO','assinaturas_saas',contract_id,
           {'plano_id':plano_id,'periodicidade':period,'valor':price,'trial_id':trial_id})
    return {'ok':True,'assinatura_id':contract_id,'status':state}


@transaction
def generate_charge(db, *, member, assinatura_id, ciclo_inicio=None, vencimento=None):
    contract = _contract(db,assinatura_id)
    _company(db, contract['empresa_id'])
    period = _period(contract['periodicidade'])
    price = _price(contract['valor'])
    if contract['status'] not in ('PENDENTE','TRIAL','TRIAL_EXPIRADO','ATIVA','PROXIMA_VENCIMENTO'):
        raise HTTPException(409, "Estado da assinatura não permite gerar cobrança nesta operação.")
    if contract['status'] in ('ATIVA','PROXIMA_VENCIMENTO'):
        start=contract['data_vencimento']
        if start is None or (ciclo_inicio is not None and ciclo_inicio!=start):
            raise HTTPException(409, "Renovação deve iniciar no vencimento atual da assinatura.")
    else:
        if ciclo_inicio is None:
            raise HTTPException(400, "Informe o início do ciclo inicial.")
        start=ciclo_inicio
        if start < date.today():
            raise HTTPException(409, "Não gerar cobertura inicial retroativa nesta operação.")
        if contract['status'] in ('TRIAL','TRIAL_EXPIRADO'):
            if contract['data_fim_trial'] is None or start < contract['data_fim_trial']:
                raise HTTPException(409, "Ciclo comercial não pode antecipar o fim do trial.")
    if vencimento is None or vencimento > start:
        raise HTTPException(400, "Informe vencimento até o início do ciclo para cobrança antecipada.")
    end=_next(start,period)
    plan_module_conflicts(db,empresa_id=contract['empresa_id'],assinatura_id=assinatura_id,plano_id=contract['plano_id'])
    if contract['forma_pagamento_id'] is None:
        raise HTTPException(400, "Contrato não possui forma de pagamento válida.")
    method_id,name=resolve_order_payment_method(db,contract['forma_pagamento_id'],None)
    existing=db.execute(text("""
        SELECT id FROM pagamentos_saas WHERE assinatura_id=:contract AND tipo='ASSINATURA'
        AND status IN ('PENDENTE','PROCESSANDO','PAGO','ATRASADO','ESTORNADO')
        AND (ciclo_inicio IS NULL OR (ciclo_inicio=:start AND ciclo_fim=:end)
             OR (ciclo_inicio<:end AND ciclo_fim>:start)) LIMIT 1
    """), {'contract':assinatura_id,'start':start,'end':end}).scalar()
    if existing:
        raise HTTPException(409, "Já existe cobrança para este ciclo, período sobreposto ou histórico sem ciclo. Revisão administrativa necessária.")
    payment_id=db.execute(text("""
        INSERT INTO pagamentos_saas(empresa_id,assinatura_id,tipo,status,valor,vencimento,ciclo_inicio,ciclo_fim,forma_pagamento_id,forma_pagamento)
        VALUES (:company,:contract,'ASSINATURA','PENDENTE',:price,:due,:start,:end,:method,:name) RETURNING id
    """),dict(company=contract['empresa_id'],contract=assinatura_id,price=price,due=vencimento,start=start,end=end,method=method_id,name=name)).scalar_one()
    _audit(db,member,contract['empresa_id'],'ASSINATURA_COBRANCA_GERADA','pagamentos_saas',payment_id,
           {'assinatura_id':assinatura_id,'ciclo_inicio':start,'ciclo_fim':end,'valor':price})
    return {'ok':True,'pagamento_id':payment_id,'assinatura_id':assinatura_id,'status':'PENDENTE','ciclo_inicio':start,'ciclo_fim':end,'valor':price}


@transaction
def confirm_payment(db, *, member, pagamento_id):
    ref=db.execute(text("SELECT assinatura_id FROM pagamentos_saas WHERE id=:id AND tipo='ASSINATURA'"),{'id':pagamento_id}).scalar()
    if ref is None:
        raise HTTPException(404, "Cobrança de assinatura vinculada não encontrada.")
    contract=_contract(db,ref)
    payment=db.execute(text("SELECT * FROM pagamentos_saas WHERE id=:id FOR UPDATE"),{'id':pagamento_id}).mappings().first()
    if not payment or payment['tipo']!='ASSINATURA' or payment['assinatura_id']!=ref or payment['empresa_id']!=contract['empresa_id']:
        raise HTTPException(409, "Empresa ou vínculo da cobrança incompatível com a assinatura.")
    if payment['status']=='PAGO':
        return {'ok':True,'idempotente':True,'pagamento_id':pagamento_id,'assinatura_id':ref,
                'status':contract['status'],'data_vencimento':contract['data_vencimento']}
    _company(db, contract['empresa_id'])
    if payment['status'] not in ('PENDENTE','PROCESSANDO','ATRASADO'):
        raise HTTPException(409, "Estado da cobrança não permite confirmação.")
    start,end=payment['ciclo_inicio'],payment['ciclo_fim']
    if start is None or end is None or end!=_next(start,_period(contract['periodicidade'])):
        raise HTTPException(409, "Ciclo da cobrança incompleto ou incompatível com o contrato.")
    if contract['status'] not in ('PENDENTE','TRIAL','TRIAL_EXPIRADO','ATIVA','PROXIMA_VENCIMENTO'):
        raise HTTPException(409, "Assinatura requer decisão administrativa antes da confirmação.")
    if end<=date.today():
        raise HTTPException(409, "Ciclo já encerrado; decisão administrativa necessária, sem deslocamento automático de datas.")
    first=contract['data_inicio_assinatura'] is None
    if first:
        if contract['status'] not in ('PENDENTE','TRIAL','TRIAL_EXPIRADO'):
            raise HTTPException(409, "Contrato não está disponível para primeiro pagamento.")
        if contract['status'] in ('TRIAL','TRIAL_EXPIRADO') and (contract['data_fim_trial'] is None or start<contract['data_fim_trial'] or date.today()<contract['data_fim_trial']):
            raise HTTPException(409, "Trial vigente: confirmação comercial disponível somente ao final do período gratuito.")
    elif start!=contract['data_vencimento']:
        raise HTTPException(409, "Ciclo fora de ordem; início deve coincidir com o vencimento atual.")
    previous=db.execute(text("""
        SELECT id FROM pagamentos_saas WHERE assinatura_id=:contract AND tipo='ASSINATURA'
          AND id<>:id AND status IN ('PENDENTE','PROCESSANDO','ATRASADO','ESTORNADO')
          AND (ciclo_inicio IS NULL OR ciclo_inicio<:start) LIMIT 1
    """),{'contract':ref,'id':pagamento_id,'start':start}).scalar()
    if previous:
        raise HTTPException(409, "Existe ciclo anterior não regularizado.")
    plan_module_conflicts(db,empresa_id=contract['empresa_id'],assinatura_id=ref,plano_id=contract['plano_id'])
    db.execute(text("UPDATE pagamentos_saas SET status='PAGO',pago_em=NOW(),atualizado_em=NOW() WHERE id=:id"),{'id':pagamento_id})
    db.execute(text("""
        UPDATE assinaturas_saas SET status='ATIVA',data_inicio_assinatura=COALESCE(data_inicio_assinatura,:start),
          data_vencimento=:end,atualizado_em=NOW() WHERE id=:id
    """),{'id':ref,'start':start,'end':end})
    if first:
        activate_plan_modules(db,empresa_id=contract['empresa_id'],assinatura_id=ref,plano_id=contract['plano_id'],data_fim=end)
    else:
        db.execute(text("""
            UPDATE empresa_modulos_saas SET data_fim=:end,atualizado_em=NOW()
            WHERE empresa_id=:company AND assinatura_id=:contract AND origem='PLANO'
              AND status IN ('ATIVO','PENDENTE')
        """), {'end':end,'company':contract['empresa_id'],'contract':ref})
    _audit(db,member,contract['empresa_id'],'ASSINATURA_PAGAMENTO_CONFIRMADO','pagamentos_saas',pagamento_id,
           {'assinatura_id':ref,'ciclo_inicio':start,'ciclo_fim':end,'primeiro_pagamento':first})
    return {'ok':True,'idempotente':False,'pagamento_id':pagamento_id,'assinatura_id':ref,'status':'ATIVA','data_vencimento':end}
