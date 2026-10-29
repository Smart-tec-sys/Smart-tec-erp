from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import financeiro_fluxo_caixa_service as service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant
from decimal import Decimal

router = APIRouter()


class ResumoOut(BaseModel):
    data_inicial: date
    data_final: date
    modo: str
    conta_financeira_id: Optional[int] = None
    saldo_inicial: Decimal
    recebimentos: Decimal
    pagamentos: Decimal
    saldo_realizado: Decimal
    recebimentos_previstos: Decimal
    pagamentos_previstos: Decimal
    saldo_previsto: Decimal
    saldo_inicial_contas_incluido: bool
    atrasados_receber: Decimal
    atrasados_pagar: Decimal


class DiaOut(BaseModel):
    data: date
    saldo_inicial: Decimal
    recebimentos: Decimal
    pagamentos: Decimal
    saldo_dia: Decimal
    recebimentos_previstos: Decimal
    pagamentos_previstos: Decimal
    saldo_previsto: Decimal


class MovimentoOut(BaseModel):
    data: date
    descricao: str
    tipo: str
    natureza: str
    situacao: str
    origem: str
    conta_financeira_id: Optional[int] = None
    conta: str
    valor: Decimal
    titulo_id: int
    baixa_id: Optional[int] = None
    pedido_id: Optional[int] = None
    legado: bool = False


class MovimentosOut(BaseModel):
    total: int
    itens: List[MovimentoOut]


def _filtros(
    data_inicial: Optional[date] = None,
    data_final: Optional[date] = None,
    conta_financeira_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    plano_conta_id: Optional[int] = None,
    origem: Optional[str] = None,
    modo: str = Query("ambos", regex="^(realizado|previsto|ambos)$"),
) -> dict:
    return dict(data_inicial=data_inicial, data_final=data_final, conta_financeira_id=conta_financeira_id,
                centro_custo_id=centro_custo_id, plano_conta_id=plano_conta_id, origem=origem, modo=modo)


def _executar(funcao, *args, **kwargs):
    try:
        return funcao(*args, **kwargs)
    except service.FluxoInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/fluxo-caixa/resumo", response_model=ResumoOut)
def resumo(filtros: dict = Depends(_filtros), db: Session = Depends(get_db),
           tenant: TenantContext = Depends(get_current_tenant)):
    return _executar(service.resumo, db, tenant, **filtros)


@router.get("/fluxo-caixa/diario", response_model=List[DiaOut])
def diario(filtros: dict = Depends(_filtros), db: Session = Depends(get_db),
           tenant: TenantContext = Depends(get_current_tenant)):
    return _executar(service.diario, db, tenant, **filtros)


@router.get("/fluxo-caixa/movimentos", response_model=MovimentosOut)
def movimentos(filtros: dict = Depends(_filtros), limit: int = Query(200, ge=1, le=1000), offset: int = Query(0, ge=0),
               db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return _executar(service.movimentos, db, tenant, limit=limit, offset=offset, **filtros)
