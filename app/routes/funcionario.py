from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.funcionario import Funcionario, FuncionarioCreate, FuncionarioUpdate
from app.services.funcionario_service import get_all, get_by_id, create, update, delete
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

router = APIRouter()


@router.get("/", response_model=List[Funcionario])
def listar(db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        funcionarios = get_all(db, tenant)
        if funcionarios is None:
            return []
        return funcionarios

    except Exception as e:
        print(f"Erro na rota listar funcionários: {e}")
        return []


@router.get("/{funcionario_id}", response_model=Funcionario)
def buscar_por_id(funcionario_id: int, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    funcionario = get_by_id(db, funcionario_id, tenant)

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    return funcionario


@router.post("/", response_model=Funcionario)
def criar(data: FuncionarioCreate, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        return create(db, data, tenant)

    except Exception as e:
        print(f"Erro na rota criar funcionário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar funcionário no banco.")


@router.put("/{funcionario_id}", response_model=Funcionario)
def atualizar(funcionario_id: int, data: FuncionarioUpdate, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        funcionario = update(db, funcionario_id, data, tenant)

        if not funcionario:
            raise HTTPException(status_code=404, detail="Funcionário não encontrado")

        return funcionario

    except HTTPException:
        raise

    except Exception as e:
        print(f"Erro na rota atualizar funcionário: {e}")
        raise HTTPException(status_code=500, detail="Erro ao atualizar funcionário no banco.")


@router.delete("/{funcionario_id}")
def deletar(funcionario_id: int, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    funcionario = delete(db, funcionario_id, tenant)

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")

    return {"mensagem": "Funcionário deletado com sucesso"}
