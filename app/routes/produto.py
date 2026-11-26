import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.produto import ProdutoCreate, ProdutoUpdate
from app.services.produto_service import (
    create,
    delete,
    get_all,
    get_by_id,
    get_history,
    get_technical_classifications,
    update,
)
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant


from fastapi.encoders import jsonable_encoder
from app.models.empresa import EmpresaDB
import unicodedata
import re

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/classificacoes-tecnicas")
def listar_classificacoes_tecnicas(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    try:
        return get_technical_classifications(db, tenant)
    except Exception as e:
        logger.exception("Falha ao consultar classificações técnicas")
        raise HTTPException(
            status_code=500,
            detail="Erro ao consultar classificações técnicas.",
        ) from e



def _catalogo_rolo_comercial(db, tenant, produtos):
    empresa = db.get(EmpresaDB, tenant.empresa_id)
    if empresa is None:
        return produtos

    cfg = empresa.configuracoes or {}
    mapa = cfg.get("tecidos_rolo_v1", {})
    receitas = cfg.get("receitas_rolo_v1", {})

    # Empresas sem consolidacao mantem o comportamento anterior.
    if not isinstance(mapa, dict) or not mapa:
        return produtos

    def normalizar(valor):
        return "".join(
            c for c in unicodedata.normalize(
                "NFKD", str(valor or "")
            )
            if not unicodedata.combining(c)
        ).upper().strip()

    ids_receitas = {
        str(chave).split(":")[0]
        for chave, receita in receitas.items()
        if isinstance(receita, dict) and receita
    }

    resultado = jsonable_encoder(produtos)

    for p in resultado:
        pid = str(p["id"])
        nome = normalizar(p.get("nome"))
        modelo = normalizar(p.get("modelo_tecnico"))
        tipo = normalizar(p.get("tipo_produto"))

        if tipo in {"COMPONENTE", "INSUMO", "MATERIA PRIMA"}:
            continue

        eh_rolo = (
            modelo == "ROLO"
            or bool(re.match(r"^ROLO\b", nome))
        )

        if not eh_rolo:
            continue

        vinculos = mapa.get(pid, [])

        cores = sorted({
            normalizar(v.get("cor"))
            for v in vinculos
            if isinstance(v, dict) and v.get("cor")
        })

        receita_preservada = (
            pid in ids_receitas
            and (
                bool(re.search(r"\bPICASSO\b", nome))
                or (
                    pid == "84"
                    and bool(re.search(r"SCREEN\s*3\s*%", nome))
                    and "IMPORTAD" in nome
                )
            )
        )

        p["rolo_liberado_comercial"] = (
            bool(cores) or receita_preservada
        )

        if cores:
            p["rolo_cores_disponiveis"] = cores

    return resultado


@router.get("/")
def listar(skip: int=0, limit: int=100, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        produtos = get_all(db, tenant, skip=skip, limit=limit)
        return _catalogo_rolo_comercial(db, tenant, produtos)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produtos no banco: {str(e)}"
        )


@router.get("/{produto_id}")
def buscar_por_id(produto_id: int, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        produto = get_by_id(db, produto_id, tenant)

        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return produto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar produto: {str(e)}"
        )


@router.post("/")
def criar(data: ProdutoCreate, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        return create(db, data, tenant)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar produto no banco: {str(e)}"
        )


@router.put("/{produto_id}")
def atualizar(produto_id: int, data: ProdutoUpdate, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        produto = update(db, produto_id, data, tenant)

        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return produto

    except PermissionError as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Falha ao atualizar produto %s", produto_id)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao atualizar produto; nenhuma alteração foi confirmada."
        ) from e


@router.get("/{produto_id}/historico")
def historico(produto_id: int, db: Session = Depends(get_db),
              tenant: TenantContext = Depends(get_current_tenant)):
    try:
        registros = get_history(db, produto_id, tenant)
        if registros is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        return [{
            "id": item.id,
            "produto_id": item.produto_id,
            "usuario_id": item.usuario_id,
            "criado_em": item.criado_em,
            "alteracoes": item.alteracoes,
        } for item in registros]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Falha ao consultar histórico do produto %s", produto_id)
        raise HTTPException(status_code=500, detail="Erro ao consultar histórico do produto.") from e


@router.delete("/{produto_id}")
def deletar(produto_id: int, db: Session=Depends(get_db), tenant: TenantContext=Depends(get_current_tenant)):
    try:
        sucesso = delete(db, produto_id, tenant)

        if not sucesso:
            raise HTTPException(status_code=404, detail="Produto não encontrado")

        return {"mensagem": "Produto removido com sucesso"}

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao deletar produto: {str(e)}"
        )
