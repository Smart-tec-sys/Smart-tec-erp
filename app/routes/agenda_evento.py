from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.agenda_evento import (
    AgendaEvento,
    AgendaEventoCreate,
    AgendaEventoUpdate,
)
from app.services import agenda_evento_service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant


router = APIRouter()


@router.get("/", response_model=List[AgendaEvento])
def listar(
    inicio_de: datetime | None = None,
    inicio_ate: datetime | None = None,
    status: str | None = None,
    categoria: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    return agenda_evento_service.get_all(
        db=db,
        tenant=tenant,
        inicio_de=inicio_de,
        inicio_ate=inicio_ate,
        status=status,
        categoria=categoria,
        limit=limit,
    )


@router.get("/{evento_id}", response_model=AgendaEvento)
def obter(
    evento_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    evento = agenda_evento_service.get_by_id(db, evento_id, tenant)

    if not evento:
        raise HTTPException(
            status_code=404,
            detail="Evento de agenda nao encontrado.",
        )

    return evento


@router.post("/", response_model=AgendaEvento)
def criar(
    data: AgendaEventoCreate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return agenda_evento_service.create(db, data, tenant)
    except Exception as exc:
        db.rollback()
        print(f"Erro ao criar evento de agenda: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao salvar evento de agenda.",
        )


@router.put("/{evento_id}", response_model=AgendaEvento)
def atualizar(
    evento_id: int,
    data: AgendaEventoUpdate,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        evento = agenda_evento_service.update(
            db,
            evento_id,
            data,
            tenant,
        )

        if not evento:
            raise HTTPException(
                status_code=404,
                detail="Evento de agenda nao encontrado.",
            )

        return evento

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()
        print(f"Erro ao atualizar evento de agenda: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao atualizar evento de agenda.",
        )


@router.delete("/{evento_id}")
def deletar(
    evento_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    evento = agenda_evento_service.delete(
        db,
        evento_id,
        tenant,
    )

    if not evento:
        raise HTTPException(
            status_code=404,
            detail="Evento de agenda nao encontrado.",
        )

    return {"mensagem": "Evento removido com sucesso."}
