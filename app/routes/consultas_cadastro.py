from fastapi import APIRouter, Depends, HTTPException

from app.schemas.consultas_cadastro import (
    ConsultaCEPInput,
    ConsultaCadastroResponse,
    ConsultaCNPJInput,
)
from app.services import consultas_cadastro_service
from app.services.consultas_cadastro_adapters import ConsultaCadastroError
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant


router = APIRouter()


@router.post(
    "/cnpj",
    response_model=ConsultaCadastroResponse,
    response_model_exclude_none=True,
)
def consultar_cnpj(
    data: ConsultaCNPJInput,
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return consultas_cadastro_service.consultar_cnpj(
            data.documento, enriquecer_contatos=data.enriquecer_contatos
        )
    except ConsultaCadastroError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/cep",
    response_model=ConsultaCadastroResponse,
    response_model_exclude_none=True,
)
def consultar_cep(
    data: ConsultaCEPInput,
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return consultas_cadastro_service.consultar_cep(data.cep)
    except ConsultaCadastroError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
