from fastapi import HTTPException
from sqlalchemy import text
from app.admin.platform_company import get_platform_empresa_id
from app.schemas.financeiro_cadastros import FormaPagamentoCreate


class AdminPaymentMethodCreate(FormaPagamentoCreate):
    disponivel_para: str = "RECEBER"


def list_payment_methods(db):
    empresa_id = get_platform_empresa_id(db)
    return db.execute(text("""
        SELECT f.id, f.nome, f.tipo, f.disponivel_para, f.conta_financeira_id,
               c.nome AS conta_financeira_nome
        FROM formas_pagamento f
        LEFT JOIN contas_financeiras c ON c.id=f.conta_financeira_id AND c.empresa_id=f.empresa_id
        WHERE f.empresa_id=:empresa_id AND f.ativo IS TRUE
          AND f.disponivel_para IN ('RECEBER','AMBOS')
        ORDER BY f.nome, f.id
    """), {"empresa_id": empresa_id}).mappings().all()


def resolve_order_payment_method(db, method_id, legacy_text):
    if method_id is None:
        return None, (legacy_text or "").strip() or None
    empresa_id = get_platform_empresa_id(db)
    method = db.execute(text("""
        SELECT id, nome, ativo, disponivel_para FROM formas_pagamento
        WHERE id=:id AND empresa_id=:empresa_id
    """), {"id": method_id, "empresa_id": empresa_id}).mappings().first()
    if not method or not method["ativo"] or method["disponivel_para"] not in ('RECEBER','AMBOS'):
        raise HTTPException(400, "Forma de pagamento deve estar ativa, disponível para recebimento e pertencer à empresa da plataforma.")
    return method["id"], method["nome"]


def create_payment_method(db, payload):
    empresa_id = get_platform_empresa_id(db)
    if payload.conta_financeira_id is not None or not payload.ativo or payload.disponivel_para not in ('RECEBER','AMBOS'):
        raise HTTPException(400, "Cadastro inline requer forma ativa para RECEBER ou AMBOS, sem conta financeira.")
    return db.execute(text("""
        INSERT INTO formas_pagamento (empresa_id,nome,tipo,disponivel_para,ativo)
        VALUES (:empresa_id,:nome,:tipo,:disponivel_para,TRUE)
        RETURNING id,nome,tipo,disponivel_para,conta_financeira_id
    """), {"empresa_id": empresa_id, "nome": payload.nome, "tipo": payload.tipo,
             "disponivel_para": payload.disponivel_para}).mappings().one()
