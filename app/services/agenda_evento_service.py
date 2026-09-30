from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.agenda_evento import AgendaEventoDB
from app.schemas.agenda_evento import AgendaEventoCreate, AgendaEventoUpdate
from app.tenant.context import TenantContext


def get_all(
    db: Session,
    tenant: TenantContext,
    inicio_de: datetime | None = None,
    inicio_ate: datetime | None = None,
    status: str | None = None,
    categoria: str | None = None,
    limit: int = 200,
):
    query = db.query(AgendaEventoDB).filter(
        AgendaEventoDB.empresa_id == tenant.empresa_id
    )

    if inicio_de is not None:
        query = query.filter(AgendaEventoDB.inicio >= inicio_de)

    if inicio_ate is not None:
        query = query.filter(AgendaEventoDB.inicio <= inicio_ate)

    if status:
        query = query.filter(AgendaEventoDB.status == status)

    if categoria:
        query = query.filter(AgendaEventoDB.categoria == categoria)

    return (
        query
        .order_by(AgendaEventoDB.inicio.asc())
        .limit(min(max(limit, 1), 500))
        .all()
    )


def get_by_id(
    db: Session,
    evento_id: int,
    tenant: TenantContext,
):
    return (
        db.query(AgendaEventoDB)
        .filter(
            AgendaEventoDB.id == evento_id,
            AgendaEventoDB.empresa_id == tenant.empresa_id,
        )
        .first()
    )


def get_by_external_uid(
    db: Session,
    external_uid: str,
    tenant: TenantContext,
):
    return (
        db.query(AgendaEventoDB)
        .filter(
            AgendaEventoDB.external_uid == external_uid,
            AgendaEventoDB.empresa_id == tenant.empresa_id,
        )
        .first()
    )


def get_by_origin_ref(
    db: Session,
    origem: str,
    origem_ref: str,
    tenant: TenantContext,
):
    return (
        db.query(AgendaEventoDB)
        .filter(
            AgendaEventoDB.empresa_id == tenant.empresa_id,
            AgendaEventoDB.origem == origem,
            AgendaEventoDB.origem_ref == origem_ref,
        )
        .first()
    )


def create(
    db: Session,
    data: AgendaEventoCreate,
    tenant: TenantContext,
):
    payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()

    external_uid = payload.pop("external_uid", None) or str(uuid4())
    metadados = payload.pop("metadados", {}) or {}

    evento = AgendaEventoDB(
        empresa_id=tenant.empresa_id,
        external_uid=external_uid,
        metadados=metadados,
        **payload,
    )

    db.add(evento)
    db.commit()
    db.refresh(evento)

    return evento


def update(
    db: Session,
    evento_id: int,
    data: AgendaEventoUpdate,
    tenant: TenantContext,
):
    evento = get_by_id(db, evento_id, tenant)

    if not evento:
        return None

    payload = (
        data.model_dump(exclude_unset=True)
        if hasattr(data, "model_dump")
        else data.dict(exclude_unset=True)
    )

    if "metadados" in payload:
        evento.metadados = payload.pop("metadados") or {}

    for key, value in payload.items():
        setattr(evento, key, value)

    db.commit()
    db.refresh(evento)

    return evento


def delete(
    db: Session,
    evento_id: int,
    tenant: TenantContext,
):
    evento = get_by_id(db, evento_id, tenant)

    if not evento:
        return None

    db.delete(evento)
    db.commit()

    return evento
