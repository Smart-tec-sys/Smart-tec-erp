from sqlalchemy import Integer, cast, func, text
from sqlalchemy.orm import Session, joinedload
from app.models.orcamento import OrcamentoDB, OrcamentoItemDB

def _item_dict(i):
    return {"id":i.id,"tipo_item":i.tipo_item,"produto_id":i.produto_id,"descricao":i.descricao,"codigo_interno":i.codigo_interno,"grupo_tecnico":i.grupo_tecnico,"modelo_tecnico":i.modelo_tecnico,"unidade":i.unidade,"quantidade":float(i.quantidade or 0),"largura":float(i.largura or 0),"altura":float(i.altura or 0),"area":float(i.area or 0),"preco_unitario":float(i.preco_unitario or 0),"desconto":float(i.desconto or 0),"subtotal":float(i.subtotal or 0),"observacao_item":i.observacao_item,"material":i.material,"cor":i.cor,"acionamento":i.acionamento,"lado_comando":i.lado_comando,"calculo_producao_status":i.calculo_producao_status}

def _dict(o):
    return {"id":o.id,"numero":o.numero,"cliente_id":o.cliente_id,"cliente_nome":getattr(o.cliente,"nome","") if o.cliente else "","status":o.status,"validade":o.validade,"observacao":o.observacao,"total":float(o.total or 0),"desconto":float(o.desconto or 0),"total_final":float(o.total_final or 0),"criado_em":o.criado_em,"atualizado_em":o.atualizado_em,"itens":[_item_dict(i) for i in o.itens]}

def listar(db:Session):
    q=db.query(OrcamentoDB).options(joinedload(OrcamentoDB.cliente),joinedload(OrcamentoDB.itens)).order_by(OrcamentoDB.id.desc())
    return [_dict(o) for o in q.all()]

def obter(db:Session,oid:int):
    o=db.query(OrcamentoDB).options(joinedload(OrcamentoDB.cliente),joinedload(OrcamentoDB.itens)).filter(OrcamentoDB.id==oid).first()
    return _dict(o) if o else None

def _numero(db):
    db.execute(text("SELECT pg_advisory_xact_lock(2026082601)"))
    atual=db.query(func.max(cast(OrcamentoDB.numero,Integer))).scalar() or 0
    return str(max(int(atual)+1,1001))

def _fill(o,data):
    for c in ["cliente_id","status","validade","observacao","desconto","total","total_final"]: setattr(o,c,getattr(data,c))
    o.itens.clear()
    for item in data.itens: o.itens.append(OrcamentoItemDB(**item.dict()))

def criar(db,data):
    try:
        o=OrcamentoDB(numero=_numero(db)); _fill(o,data); db.add(o); db.commit(); return obter(db,o.id)
    except Exception: db.rollback(); raise

def atualizar(db,oid,data):
    try:
        o=db.query(OrcamentoDB).filter(OrcamentoDB.id==oid).with_for_update().first()
        if not o:return None
        _fill(o,data); db.commit(); return obter(db,o.id)
    except Exception: db.rollback(); raise

def remover(db,oid):
    try:
        o=db.query(OrcamentoDB).filter(OrcamentoDB.id==oid).first()
        if not o:return False
        db.delete(o); db.commit(); return True
    except Exception: db.rollback(); raise
