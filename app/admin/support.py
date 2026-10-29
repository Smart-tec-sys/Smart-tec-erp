"""Support beta: existing tables only; mutations and audits share one transaction."""
import re
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.admin.dependencies import require_platform_permission
from app.admin.service import PlatformMemberContext

router = APIRouter()
TRANSITIONS = {
    "ABERTO": {"EM_ANALISE"},
    "EM_ANALISE": {"AGUARDANDO_CLIENTE", "EM_CORRECAO"},
    "AGUARDANDO_CLIENTE": {"EM_ANALISE", "EM_CORRECAO"},
    "EM_CORRECAO": {"AGUARDANDO_CLIENTE", "RESOLVIDO"},
    "RESOLVIDO": {"FECHADO"}, "FECHADO": set(),
}
Priority = Literal["BAIXA", "NORMAL", "ALTA", "CRITICA"]
TicketStatus = Literal["ABERTO", "EM_ANALISE", "AGUARDANDO_CLIENTE", "EM_CORRECAO", "RESOLVIDO", "FECHADO"]

class SupportInput(BaseModel):
    class Config:
        extra = "forbid"

class SupportCreate(SupportInput):
    titulo: str = Field(min_length=1, max_length=200)
    descricao: str | None = Field(default=None, max_length=10000)
    prioridade: Priority = "NORMAL"
    usuario_id: int | None = Field(default=None, gt=0)
    responsavel_equipe_id: int | None = Field(default=None, gt=0)
    pagina: str | None = Field(default=None, max_length=200)
    request_id: str | None = Field(default=None, max_length=100)
    navegador: str | None = Field(default=None, max_length=200)
    dispositivo: str | None = Field(default=None, max_length=100)
    versao_frontend: str | None = Field(default=None, max_length=50)
    versao_backend: str | None = Field(default=None, max_length=50)
    erro_codigo: str | None = Field(default=None, max_length=100)
    erro_mensagem: str | None = Field(default=None, max_length=10000)

class SupportUpdate(SupportInput):
    status: TicketStatus | None = None
    prioridade: Priority | None = None
    responsavel_equipe_id: int | None = Field(default=None, gt=0)
    resolucao: str | None = Field(default=None, max_length=10000)

TECHNICAL = ("pagina", "request_id", "navegador", "dispositivo", "versao_frontend", "versao_backend", "erro_codigo", "erro_mensagem")
def safe_text(value):
    if value and re.search(r"traceback|stack\s*trace|(?:^|\n)\s*at\s+\S+\s*\([^)]*:\d+|bearer\s|authorization|password|senha|secret|token|api[_ -]?key|eyJ[\w-]+\.|^\s*[\{\[]", value, re.I):
        return "Detalhes técnicos sensíveis não são exibidos."
    return value

def present(row, member):
    result = dict(row)
    for field in ("titulo", "descricao", "resolucao", *TECHNICAL):
        result[field] = safe_text(result.get(field))
    if not member.has_permission("SUPORTE_LOGS"):
        for field in TECHNICAL:
            result[field] = None
    return result

SELECT = """SELECT c.*, e.nome AS empresa_nome, u.nome AS solicitante_nome,
    ru.nome AS responsavel_nome FROM chamados_suporte_saas c
    JOIN empresas e ON e.id=c.empresa_id LEFT JOIN usuarios u ON u.id=c.usuario_id
    LEFT JOIN plataforma_equipe pe ON pe.id=c.responsavel_equipe_id
    LEFT JOIN usuarios ru ON ru.id=pe.usuario_id"""
def company_exists(db, empresa_id):
    if db.execute(text("SELECT id FROM empresas WHERE id=:id"), {"id": empresa_id}).first() is None:
        raise HTTPException(404, "empresa não encontrada")

def validate_links(db, empresa_id, data):
    if data.get("usuario_id") is not None:
        valid = db.execute(text("""SELECT eu.id FROM empresa_usuarios eu JOIN usuarios u ON u.id=eu.usuario_id
            WHERE eu.empresa_id=:empresa AND eu.usuario_id=:id AND eu.ativo=TRUE AND u.status='ATIVO'"""), {"empresa": empresa_id, "id": data["usuario_id"]}).first()
        if not valid: raise HTTPException(400, "solicitante não possui vínculo ativo com esta empresa")
    if data.get("responsavel_equipe_id") is not None:
        valid = db.execute(text("""SELECT pe.id FROM plataforma_equipe pe JOIN usuarios u ON u.id=pe.usuario_id
            JOIN plataforma_funcoes f ON f.id=pe.funcao_id
            WHERE pe.id=:id AND pe.status='ATIVO' AND pe.pode_receber_chamados=TRUE
            AND u.status='ATIVO' AND f.ativo=TRUE"""), {"id": data["responsavel_equipe_id"]}).first()
        if not valid: raise HTTPException(400, "responsável indisponível para atendimento de chamados")

def audit(db, member, empresa_id, ticket_id, action, details):
    from app.routes.admin import _audit_admin
    _audit_admin(db, member=member, empresa_id=empresa_id, acao=action,
                 recurso="chamados_suporte_saas", recurso_id=ticket_id, detalhes=details)

@router.get("/empresas/{empresa_id}/chamados")
def list_tickets(empresa_id: int, member: Annotated[PlatformMemberContext, Depends(require_platform_permission("SUPORTE_VER"))], db: Annotated[Session, Depends(get_db)]):
    company_exists(db, empresa_id)
    rows=db.execute(text(SELECT+" WHERE c.empresa_id=:empresa ORDER BY c.id DESC"), {"empresa":empresa_id}).mappings().all()
    return {"items":[present(row,member) for row in rows]}

@router.get("/empresas/{empresa_id}/chamados/opcoes")
def ticket_options(empresa_id: int, member: Annotated[PlatformMemberContext, Depends(require_platform_permission("SUPORTE_ATENDER"))], db: Annotated[Session, Depends(get_db)]):
    company_exists(db, empresa_id)
    users=db.execute(text("""SELECT u.id,u.nome FROM usuarios u JOIN empresa_usuarios eu ON eu.usuario_id=u.id
        WHERE eu.empresa_id=:empresa AND eu.ativo=TRUE AND u.status='ATIVO' ORDER BY u.nome"""), {"empresa":empresa_id}).mappings().all()
    team=db.execute(text("""SELECT pe.id,u.nome FROM plataforma_equipe pe JOIN usuarios u ON u.id=pe.usuario_id
        JOIN plataforma_funcoes f ON f.id=pe.funcao_id WHERE pe.status='ATIVO' AND pe.pode_receber_chamados=TRUE
        AND u.status='ATIVO' AND f.ativo=TRUE ORDER BY u.nome""")).mappings().all()
    return {"solicitantes":[dict(row) for row in users],"responsaveis":[dict(row) for row in team]}

@router.get("/empresas/{empresa_id}/chamados/{chamado_id}")
def get_ticket(empresa_id: int, chamado_id: int, member: Annotated[PlatformMemberContext, Depends(require_platform_permission("SUPORTE_VER"))], db: Annotated[Session, Depends(get_db)]):
    row=db.execute(text(SELECT+" WHERE c.empresa_id=:empresa AND c.id=:id"), {"empresa":empresa_id,"id":chamado_id}).mappings().first()
    if row is None: raise HTTPException(404,"chamado não encontrado nesta empresa")
    return present(row,member)

@router.post("/empresas/{empresa_id}/chamados", status_code=201)
def create_ticket(empresa_id: int, payload: SupportCreate, member: Annotated[PlatformMemberContext, Depends(require_platform_permission("SUPORTE_ATENDER"))], db: Annotated[Session, Depends(get_db)]):
    data=payload.dict()
    data["titulo"]=data["titulo"].strip()
    if not data["titulo"]: raise HTTPException(422,"título obrigatório")
    try:
        company_exists(db,empresa_id)
        validate_links(db,empresa_id,data)
        fields=list(data)
        sql="""WITH allocated AS (SELECT nextval(pg_get_serial_sequence('chamados_suporte_saas','id')) AS id)
            INSERT INTO chamados_suporte_saas (id,codigo,empresa_id,status,"""+",".join(fields)+""" )
            SELECT id,'SUP-' || lpad(id::text,GREATEST(6,length(id::text)),'0'),:empresa,'ABERTO',"""+",".join(":"+field for field in fields)+" FROM allocated RETURNING id"
        ticket_id=db.execute(text(sql),{**data,"empresa":empresa_id}).scalar_one()
        audit(db,member,empresa_id,ticket_id,"CHAMADO_CRIADO",{"status":"ABERTO","prioridade":data["prioridade"],"responsavel_equipe_id":data["responsavel_equipe_id"]})
        result=get_ticket(empresa_id,ticket_id,member,db)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise

@router.post("/empresas/{empresa_id}/chamados/{chamado_id}/atendimento")
def update_ticket(empresa_id: int, chamado_id: int, payload: SupportUpdate, member: Annotated[PlatformMemberContext, Depends(require_platform_permission("SUPORTE_ATENDER"))], db: Annotated[Session, Depends(get_db)]):
    data=payload.dict(exclude_unset=True)
    try:
        old=db.execute(text("SELECT * FROM chamados_suporte_saas WHERE id=:id AND empresa_id=:empresa FOR UPDATE"), {"id":chamado_id,"empresa":empresa_id}).mappings().first()
        if old is None: raise HTTPException(404,"chamado não encontrado nesta empresa")
        if old["status"]=="FECHADO": raise HTTPException(409,"chamado fechado é terminal")
        if "status" in data and data["status"] not in TRANSITIONS[old["status"]]: raise HTTPException(409,"transição de suporte não permitida")
        if "prioridade" in data and data["prioridade"] is None: raise HTTPException(422,"prioridade obrigatória")
        if "resolucao" in data and data.get("status")!="RESOLVIDO": raise HTTPException(422,"resolução deve acompanhar a conclusão do chamado")
        if data.get("status") in {"RESOLVIDO","FECHADO"} and not member.has_permission("SUPORTE_ENCERRAR"):
            raise HTTPException(403,"permissão para encerrar suporte insuficiente")
        if data.get("status")=="RESOLVIDO":
            data["resolucao"]=(data.get("resolucao") or "").strip()
            if not data["resolucao"]: raise HTTPException(422,"resolução obrigatória")
        validate_links(db,empresa_id,data)
        changes={key:value for key,value in data.items() if old[key]!=value}
        if not changes:
            result=get_ticket(empresa_id,chamado_id,member,db)
            db.commit()
            return result
        assignments=[key+"=:"+key for key in changes]+["atualizado_em=NOW()"]
        if data.get("status")=="RESOLVIDO": assignments.append("resolvido_em=NOW()")
        db.execute(text("UPDATE chamados_suporte_saas SET "+",".join(assignments)+" WHERE id=:id AND empresa_id=:empresa"),{**changes,"id":chamado_id,"empresa":empresa_id})
        details={key:{"anterior":old[key],"novo":changes.get(key,old[key])} for key in ("status","prioridade","responsavel_equipe_id")}
        if data.get("status") in {"RESOLVIDO","FECHADO"}:
            details["resolucao"]=safe_text(changes.get("resolucao",old["resolucao"]))
        for field,action in [("status","CHAMADO_STATUS_ALTERADO"),("prioridade","CHAMADO_PRIORIDADE_ALTERADA"),("responsavel_equipe_id","CHAMADO_RESPONSAVEL_ALTERADO")]:
            if field in changes: audit(db,member,empresa_id,chamado_id,action,details)
        if changes.get("status") in {"RESOLVIDO","FECHADO"}: audit(db,member,empresa_id,chamado_id,"CHAMADO_"+changes["status"],details)
        result=get_ticket(empresa_id,chamado_id,member,db)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
