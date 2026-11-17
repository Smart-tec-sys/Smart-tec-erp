"""CRUD fiscal conservador, sempre com tenant e sem certificado digital."""
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.empresa import EmpresaDB
from app.models.empresa_usuario import EmpresaUsuarioDB
from app.models.produto import ProdutoDB
from app.models.fiscal_produto import FiscalProdutoDB
from app.schemas.fiscal_cadastros import FiscalEmpresaDados, FiscalEmpresaPatch, FiscalProdutoDados, FiscalProdutoPatch
from app.tenant.isolation import require_tenant

FISCAL_PRODUTO_CAMPOS = tuple(FiscalProdutoDados.model_fields)


def exigir_admin(db: Session, tenant) -> None:
    empresa_id = require_tenant(tenant)
    user_id = getattr(tenant, "user_id", None)
    if not isinstance(user_id, int) or user_id <= 0:
        raise HTTPException(status_code=403, detail="Configuração fiscal exige usuário administrador autenticado.")
    vinculo = db.query(EmpresaUsuarioDB).filter(
        EmpresaUsuarioDB.empresa_id == empresa_id,
        EmpresaUsuarioDB.usuario_id == user_id,
        EmpresaUsuarioDB.ativo.is_(True),
        EmpresaUsuarioDB.papel.in_(("OWNER", "ADMIN")),
    ).first()
    if vinculo is None:
        raise HTTPException(status_code=403, detail="Permissão de administrador necessária para configuração fiscal.")


def _empresa(db: Session, tenant, *, bloquear=False):
    q = db.query(EmpresaDB).filter(EmpresaDB.id == require_tenant(tenant), EmpresaDB.status == "ATIVA")
    empresa = (q.with_for_update() if bloquear else q).first()
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa ativa não encontrada.")
    return empresa


def _produto(db: Session, tenant, produto_id: int, *, bloquear=False):
    q = db.query(ProdutoDB).filter(
        ProdutoDB.id == produto_id, ProdutoDB.empresa_id == require_tenant(tenant)
    )
    produto = (q.with_for_update() if bloquear else q).first()
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado para a empresa ativa.")
    return produto


def _config_empresa(empresa) -> FiscalEmpresaDados:
    configuracoes = empresa.configuracoes if isinstance(empresa.configuracoes, dict) else {}
    fiscal = configuracoes.get("fiscal_nfe")
    fiscal = fiscal if isinstance(fiscal, dict) else {}
    # Não copiar campos inesperados, em especial segredos legados.
    safe = {key: fiscal[key] for key in FiscalEmpresaDados.model_fields if key in fiscal}
    return FiscalEmpresaDados.model_validate(safe)


def ler_empresa(db, tenant):
    empresa = _empresa(db, tenant)
    return {"empresa_id": empresa.id, "documento": empresa.documento,
            "dados": _config_empresa(empresa).model_dump(), "emissao_habilitada": False}


def atualizar_empresa(db, tenant, dados: FiscalEmpresaPatch):
    exigir_admin(db, tenant)
    empresa = _empresa(db, tenant, bloquear=True)
    atual = _config_empresa(empresa).model_dump()
    atual.update(dados.model_dump(exclude_unset=True))
    validado = FiscalEmpresaDados.model_validate(atual)
    configuracoes = dict(empresa.configuracoes or {})
    configuracoes["fiscal_nfe"] = validado.model_dump(exclude_none=True)
    empresa.configuracoes = configuracoes
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Não foi possível salvar configuração fiscal.") from exc
    return {"empresa_id": empresa.id, "documento": empresa.documento,
            "dados": validado.model_dump(), "emissao_habilitada": False}


def _dados_produto(registro) -> FiscalProdutoDados:
    if registro is None:
        return FiscalProdutoDados()
    return FiscalProdutoDados.model_validate({campo: getattr(registro, campo) for campo in FISCAL_PRODUTO_CAMPOS})


def ler_produto(db, tenant, produto_id: int):
    _produto(db, tenant, produto_id)
    registro = db.query(FiscalProdutoDB).filter(
        FiscalProdutoDB.empresa_id == require_tenant(tenant),
        FiscalProdutoDB.produto_id == produto_id,
    ).first()
    return {"empresa_id": require_tenant(tenant), "produto_id": produto_id,
            "configurado": registro is not None, "dados": _dados_produto(registro).model_dump(),
            "emissao_habilitada": False}


def atualizar_produto(db, tenant, produto_id: int, dados: FiscalProdutoPatch):
    exigir_admin(db, tenant)
    _produto(db, tenant, produto_id, bloquear=True)  # Trava SKU antes de criar/atualizar.
    registro = db.query(FiscalProdutoDB).filter(
        FiscalProdutoDB.empresa_id == require_tenant(tenant),
        FiscalProdutoDB.produto_id == produto_id,
    ).first()
    atual = _dados_produto(registro).model_dump()
    atual.update(dados.model_dump(exclude_unset=True))
    validado = FiscalProdutoDados.model_validate(atual)
    if registro is None:
        registro = FiscalProdutoDB(empresa_id=require_tenant(tenant), produto_id=produto_id)
        db.add(registro)
    for campo in FISCAL_PRODUTO_CAMPOS:
        setattr(registro, campo, getattr(validado, campo))
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Não foi possível salvar dados fiscais do produto.") from exc
    return {"empresa_id": require_tenant(tenant), "produto_id": produto_id,
            "configurado": True, "dados": validado.model_dump(), "emissao_habilitada": False}
