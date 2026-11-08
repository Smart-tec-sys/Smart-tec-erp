from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.producao import (
    AtualizarPecaInput,
    AvancarPecaInput,
    ComponenteProducaoInput,
    ConferirPecaInput,
    ConfirmarProducaoInput,
    JustificativaProducaoInput,
)
from app.services import producao_service as service
from app.services.producao_documentos import etiquetas_lote_html, etiqueta_da_peca, ficha_html
from app.tenant.dependencies import get_current_tenant
from app.tenant.context import TenantContext
from app.tenant.isolation import TenantContextRequiredError
from app.settings import producao_v1_habilitada


def exigir_producao_habilitada():
    if not producao_v1_habilitada():
        raise HTTPException(503, "Produção V1 desabilitada. Ativação depende de implantação e validação próprias.")


router = APIRouter(dependencies=[Depends(exigir_producao_habilitada)])
T = TypeVar("T")


def executar(db: Session, acao: Callable[[], T], escrita: bool = False) -> T:
    try:
        resultado = acao()
        if escrita:
            db.commit()
        return resultado
    except LookupError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (PermissionError, TenantContextRequiredError) as exc:
        db.rollback()
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Conflito de produção: peças já vinculadas ou referência inválida. Recarregue a venda.") from exc
    except ProgrammingError as exc:
        db.rollback()
        if getattr(exc.orig, "pgcode", None) == "42P01":
            raise HTTPException(503, "Produção V1 não instalada neste banco. Migration pendente de autorização.") from exc
        raise
    except Exception:
        db.rollback()
        raise


@router.get("/")
def listar(pedido_id: int = Query(gt=0), db: Session = Depends(get_db),
           tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: [service.serializar(db, op) for op in service.listar(db, pedido_id, tenant)])


@router.get("/vendas/{pedido_id}/autorizacao")
def autorizacao(pedido_id: int, db: Session = Depends(get_db),
                tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.obter_autorizacao(db, pedido_id, tenant))


@router.post("/vendas/{pedido_id}/aprovar")
def aprovar(pedido_id: int, db: Session = Depends(get_db),
            tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.aprovar_fabricacao(db, pedido_id, tenant), escrita=True)


@router.post("/vendas/{pedido_id}/liberar-fabricacao")
def liberar_pedido(pedido_id: int, db: Session = Depends(get_db),
                   tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.liberar_pedido_fabricacao(db, pedido_id, tenant), escrita=True)


@router.post("/vendas/{pedido_id}", status_code=201)
def criar(pedido_id: int, data: ConfirmarProducaoInput, db: Session = Depends(get_db),
          tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.criar(db, pedido_id, tenant, data.confirmar_fabricacao)), escrita=True)


@router.get("/catalogo-componentes")
def catalogo_componentes(q: str = Query(default="", max_length=100),
                         db: Session = Depends(get_db),
                         tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.listar_catalogo_componentes(db, tenant, q))


@router.get("/{ordem_id}")
def obter(ordem_id: int, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(db, service.obter(db, ordem_id, tenant)))


@router.post("/{ordem_id}/liberar")
def liberar(ordem_id: int, data: ConfirmarProducaoInput, db: Session = Depends(get_db),
            tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.liberar(db, ordem_id, tenant, data.confirmar_fabricacao)), escrita=True)


@router.patch("/{ordem_id}/pecas/{peca_id}")
def atualizar_peca(ordem_id: int, peca_id: int, data: AtualizarPecaInput,
                   db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.alterar_peca(db, ordem_id, peca_id, tenant, data.model_dump(exclude_unset=True))), escrita=True)


@router.post("/{ordem_id}/pecas/{peca_id}/componentes", status_code=201)
def adicionar_componente(ordem_id: int, peca_id: int, data: ComponenteProducaoInput,
                         db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.adicionar_componente(
            db, ordem_id, peca_id, tenant, data.model_dump(),
        )), escrita=True)


@router.patch("/{ordem_id}/pecas/{peca_id}/componentes/{componente_id}")
def atualizar_componente(ordem_id: int, peca_id: int, componente_id: int,
                         data: ComponenteProducaoInput, db: Session = Depends(get_db),
                         tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.atualizar_componente(
            db, ordem_id, peca_id, componente_id, tenant, data.model_dump(),
        )), escrita=True)


@router.delete("/{ordem_id}/pecas/{peca_id}/componentes/{componente_id}")
def remover_componente(ordem_id: int, peca_id: int, componente_id: int,
                       data: JustificativaProducaoInput, db: Session = Depends(get_db),
                       tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.remover_componente(
            db, ordem_id, peca_id, componente_id, tenant, data.justificativa,
        )), escrita=True)


@router.post("/{ordem_id}/pecas/{peca_id}/conferir")
def conferir_peca(ordem_id: int, peca_id: int, data: ConferirPecaInput,
                  db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.conferir_peca(
            db, ordem_id, peca_id, tenant, data.confirmar_conferencia,
            data.justificativa,
        )), escrita=True)


@router.post("/{ordem_id}/pecas/{peca_id}/status")
def avancar_peca(ordem_id: int, peca_id: int, data: AvancarPecaInput,
                 db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: service.serializar(
        db, service.alterar_peca(db, ordem_id, peca_id, tenant, data.dict())), escrita=True)


@router.get("/{ordem_id}/ficha", response_class=HTMLResponse)
def ficha(ordem_id: int, db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    return executar(db, lambda: ficha_html(db, service.obter(db, ordem_id, tenant)))


@router.get("/{ordem_id}/pecas/{peca_id}/etiqueta", response_class=HTMLResponse)
def etiqueta(ordem_id: int, peca_id: int, db: Session = Depends(get_db),
             tenant: TenantContext = Depends(get_current_tenant)):
    def documento():
        ordem = service.obter(db, ordem_id, tenant)
        service.exigir_autorizacao_fabricacao(db, ordem.pedido_id, tenant)
        if not ordem.liberado_em:
            raise ValueError("Etiqueta de fabricação exige ordem liberada.")
        peca = next((p for p in ordem.pecas if p.id == peca_id), None)
        if peca is None:
            raise LookupError("Peça não encontrada nesta ordem.")
        return etiqueta_da_peca(ordem, peca)
    return executar(db, documento)


@router.get("/{ordem_id}/etiquetas", response_class=HTMLResponse)
def etiquetas_lote(ordem_id: int, db: Session = Depends(get_db),
                   tenant: TenantContext = Depends(get_current_tenant)):
    def documento():
        ordem = service.obter(db, ordem_id, tenant)
        service.exigir_autorizacao_fabricacao(db, ordem.pedido_id, tenant)
        if not ordem.liberado_em:
            raise ValueError("Etiquetas de fabricação exigem ordem liberada.")
        return etiquetas_lote_html(ordem)
    return executar(db, documento)
