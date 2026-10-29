from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session
from app.database import get_db
from app.tenant.dependencies import get_current_tenant
from app.tenant.context import TenantContext
from app.schemas.grades_variacoes import GradeCreate, GradeUpdate, ValorCreate, ValorUpdate
from app.services import grades_variacoes as service

router = APIRouter()


def executar(db, function, *args):
    try:
        return function(db, *args)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Nome/valor duplicado ou cadastro com vínculos. Revise os dados.") from exc
    except ProgrammingError as exc:
        db.rollback()
        if getattr(exc.orig, "pgcode", None) == "42P01":
            raise HTTPException(503, "Grades/Variações aguarda aplicação da migration aprovada.") from exc
        raise


@router.get("/")
def listar(db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, service.listar_grades, tenant)


@router.post("/", status_code=201)
def criar(data: GradeCreate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, service.criar_grade, tenant, data)


@router.patch("/{grade_id}")
def atualizar(grade_id: int, data: GradeUpdate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, service.atualizar_grade, tenant, grade_id, data)


@router.delete("/{grade_id}", status_code=204)
def excluir(grade_id: int, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    executar(db, service.excluir_grade, tenant, grade_id)
    return Response(status_code=204)


@router.get("/{grade_id}/valores")
def valores(grade_id: int, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, service.listar_valores, tenant, grade_id)


@router.post("/{grade_id}/valores", status_code=201)
def adicionar_valor(grade_id: int, data: ValorCreate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, service.criar_valor, tenant, grade_id, data)


@router.patch("/{grade_id}/valores/{valor_id}")
def editar_valor(grade_id: int, valor_id: int, data: ValorUpdate, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, service.atualizar_valor, tenant, grade_id, valor_id, data)


@router.delete("/{grade_id}/valores/{valor_id}", status_code=204)
def remover_valor(grade_id: int, valor_id: int, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    executar(db, service.excluir_valor, tenant, grade_id, valor_id)
    return Response(status_code=204)
