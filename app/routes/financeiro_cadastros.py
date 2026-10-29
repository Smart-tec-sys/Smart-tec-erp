from typing import Callable, List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import financeiro_cadastros as s
from app.services import financeiro_cadastros_service as service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

router = APIRouter()


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, service.CadastroNaoEncontrado):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


def _registrar(recurso: str, create_model, update_model, out_model) -> None:
    def listar(
        apenas_ativos: bool = False,
        db: Session = Depends(get_db),
        tenant: TenantContext = Depends(get_current_tenant),
    ):
        return service.listar(db, recurso, tenant, apenas_ativos)

    def obter(
        item_id: int,
        db: Session = Depends(get_db),
        tenant: TenantContext = Depends(get_current_tenant),
    ):
        try:
            return service.obter(db, recurso, item_id, tenant)
        except (service.CadastroNaoEncontrado, service.CadastroConflito) as exc:
            raise _http(exc)

    def criar(
        data: create_model,
        db: Session = Depends(get_db),
        tenant: TenantContext = Depends(get_current_tenant),
    ):
        try:
            return service.criar(db, recurso, tenant, data.dict())
        except (service.CadastroNaoEncontrado, service.CadastroConflito) as exc:
            raise _http(exc)

    def atualizar(
        item_id: int,
        data: update_model,
        db: Session = Depends(get_db),
        tenant: TenantContext = Depends(get_current_tenant),
    ):
        try:
            return service.atualizar(
                db, recurso, item_id, tenant, data.dict(exclude_unset=True)
            )
        except (service.CadastroNaoEncontrado, service.CadastroConflito) as exc:
            raise _http(exc)

    def remover(
        item_id: int,
        db: Session = Depends(get_db),
        tenant: TenantContext = Depends(get_current_tenant),
    ):
        try:
            service.remover(db, recurso, item_id, tenant)
        except (service.CadastroNaoEncontrado, service.CadastroConflito) as exc:
            raise _http(exc)
        return Response(status_code=204)

    base = f"/{recurso}"
    router.add_api_route(base, listar, methods=["GET"], response_model=List[out_model])
    router.add_api_route(base, criar, methods=["POST"], response_model=out_model, status_code=201)
    router.add_api_route(base + "/{item_id}", obter, methods=["GET"], response_model=out_model)
    router.add_api_route(base + "/{item_id}", atualizar, methods=["PATCH"], response_model=out_model)
    router.add_api_route(base + "/{item_id}", remover, methods=["DELETE"], status_code=204)


_registrar("contas-financeiras", s.ContaFinanceiraCreate, s.ContaFinanceiraUpdate, s.ContaFinanceiraOut)
_registrar("formas-pagamento", s.FormaPagamentoCreate, s.FormaPagamentoUpdate, s.FormaPagamentoOut)
_registrar("plano-contas", s.PlanoContaCreate, s.PlanoContaUpdate, s.PlanoContaOut)
_registrar("situacoes", s.SituacaoFinanceiraCreate, s.SituacaoFinanceiraUpdate, s.SituacaoFinanceiraOut)
_registrar("centros-custo", s.CentroCustoCreate, s.CentroCustoUpdate, s.CentroCustoOut)
