from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.contabilidade import (
    DocumentoContabilInput,
    FecharCompetenciaInput,
    MarcarObrigacaoPagaInput,
    ObrigacaoContabilInput,
)
from app.services import contabilidade_service
from app.tenant.dependencies import (
    TenantContext,
    get_current_tenant,
)


router = APIRouter()


@router.get("/resumo")
def resumo(
    competencia: str = Query(...),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.resumo(
            db,
            tenant,
            competencia,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/documentos")
def listar_documentos(
    competencia: str = Query(...),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.listar_documentos(
            db,
            tenant,
            competencia,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/documentos")
def criar_documento(
    data: DocumentoContabilInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.criar_documento(
            db,
            tenant,
            data,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get("/obrigacoes")
def listar_obrigacoes(
    competencia: str = Query(...),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.listar_obrigacoes(
            db,
            tenant,
            competencia,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/obrigacoes")
def criar_obrigacao(
    data: ObrigacaoContabilInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.criar_obrigacao(
            db,
            tenant,
            data,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/obrigacoes/{obrigacao_id}/gerar-conta-pagar")
def gerar_conta_pagar(
    obrigacao_id: int,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.gerar_conta_pagar(
            db,
            tenant,
            obrigacao_id,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/obrigacoes/{obrigacao_id}/marcar-paga")
def marcar_paga(
    obrigacao_id: int,
    data: MarcarObrigacaoPagaInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.marcar_paga(
            db,
            tenant,
            obrigacao_id,
            data.pagamento,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/fechamentos/{competencia}/fechar")
def fechar_competencia(
    competencia: str,
    data: FecharCompetenciaInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return contabilidade_service.fechar_competencia(
            db,
            tenant,
            competencia,
            data.observacao,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc