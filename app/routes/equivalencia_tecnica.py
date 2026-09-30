from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.equivalencia_tecnica import (
    EquivalenciaPreferencialUpdate,
    EquivalenciaStatusUpdate,
    EquivalenciaTecnicaCreate,
    EquivalenciaTecnicaUpdate,
)
from app.services import equivalencia_tecnica_service as service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant


router = APIRouter()


def _execute(operation):
    try:
        return operation()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/")
def listar(db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return _execute(lambda: service.list_all(db, tenant))


@router.get("/funcao/{funcao_tecnica}")
def listar_por_funcao(funcao_tecnica: str, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return _execute(lambda: service.list_by_function(db, tenant, funcao_tecnica))


@router.get("/resolver/{funcao_tecnica}")
def resolver(funcao_tecnica: str, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return _execute(lambda: service.resolve_commercial_candidates(db, tenant, funcao_tecnica))


@router.get("/{equivalence_id}")
def obter(equivalence_id: int, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    row = _execute(lambda: service.get_by_id(db, tenant, equivalence_id))
    if row is None:
        raise HTTPException(status_code=404, detail="equivalência não encontrada")
    return row


@router.post("/")
def criar(data: EquivalenciaTecnicaCreate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return _execute(lambda: service.create(db, tenant, data))


@router.put("/{equivalence_id}")
def editar(equivalence_id: int, data: EquivalenciaTecnicaUpdate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    row = _execute(lambda: service.update(db, tenant, equivalence_id, data))
    if row is None:
        raise HTTPException(status_code=404, detail="equivalência não encontrada")
    return row


@router.patch("/{equivalence_id}/status")
def alterar_status(equivalence_id: int, data: EquivalenciaStatusUpdate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return editar(equivalence_id, EquivalenciaTecnicaUpdate(ativo=data.ativo), db, tenant)


@router.patch("/{equivalence_id}/preferencial")
def alterar_preferencial(equivalence_id: int, data: EquivalenciaPreferencialUpdate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return editar(equivalence_id, EquivalenciaTecnicaUpdate(preferencial=data.preferencial), db, tenant)
