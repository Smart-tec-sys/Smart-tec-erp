"""Upload, prévia e confirmação autenticados da importação de clientes."""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.cliente_importacao import (
    ImportacaoConfiguracao, ImportacaoPrevia, ImportacaoRelatorio, ImportacaoTabela,
)
from app.services import cliente_importacao_service as service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant

router = APIRouter(prefix="/importacao")
logger = logging.getLogger(__name__)


def _entrada(file, configuracao):
    try:
        config = ImportacaoConfiguracao.model_validate_json(configuracao)
    except ValidationError as exc:
        raise HTTPException(422, "Configuração de importação inválida. Confira as colunas e opções selecionadas.") from exc
    content = file.file.read(service.MAX_BYTES + 1)
    if not content or len(content) > service.MAX_BYTES:
        raise HTTPException(422, "Envie um arquivo não vazio de até 5 MB.")
    return content, file.filename or "", config


def _auxiliar(file):
    if file is None:
        return None
    content = file.file.read(service.MAX_BYTES + 1)
    if not content or len(content) > service.MAX_BYTES:
        raise HTTPException(422, "Cada arquivo auxiliar deve ter conteúdo e no máximo 5 MB.")
    return content, file.filename or ""


@router.post("/inspecionar", response_model=ImportacaoTabela)
def inspecionar(file: UploadFile = File(...), configuracao: str = Form("{}"),
                tenant: TenantContext = Depends(get_current_tenant)):
    content, filename, config = _entrada(file, configuracao)
    try:
        return service.inspecionar(content, filename, config, tenant)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/previa", response_model=ImportacaoPrevia)
def previa(file: UploadFile = File(...), configuracao: str = Form(...),
           db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant),
           enderecos_file: UploadFile | None = File(None), contatos_file: UploadFile | None = File(None)):
    content, filename, config = _entrada(file, configuracao)
    enderecos, contatos = _auxiliar(enderecos_file), _auxiliar(contatos_file)
    try:
        return service.previa(db, content, filename, config, tenant, enderecos, contatos)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.warning("Prévia de clientes indisponível; tipo de falha: %s", type(exc).__name__)
        raise HTTPException(503, "Não foi possível conferir os cadastros existentes. Nenhum cliente foi inserido.") from exc


@router.post("/confirmar", response_model=ImportacaoRelatorio)
def confirmar(file: UploadFile = File(...), configuracao: str = Form(...),
              previa_hash: str = Form(...), confirmado: bool = Form(False),
              db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant),
              enderecos_file: UploadFile | None = File(None), contatos_file: UploadFile | None = File(None)):
    content, filename, config = _entrada(file, configuracao)
    enderecos, contatos = _auxiliar(enderecos_file), _auxiliar(contatos_file)
    try:
        return service.confirmar(db, content, filename, config, tenant, previa_hash, confirmado, enderecos, contatos)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.warning("Importação de clientes indisponível; tipo de falha: %s", type(exc).__name__)
        raise HTTPException(503, "Não foi possível concluir a importação. Nenhum cliente foi inserido.") from exc
