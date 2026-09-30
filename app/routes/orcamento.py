from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.orcamento import OrcamentoInput, OrcamentoUpdate, RomanaTetoSimulacaoInput
from app.services import orcamento_service
from app.tenant.context import TenantContext
from app.tenant.dependencies import get_current_tenant
from app.services.romana_simulacao import RomanaSimulacaoInput
from app.services.romana_teto_simulacao import RomanaTetoSimulacaoInput, simular_romana_teto
from app.services.rolo_simulacao import RoloSimulacaoInput
from app.services.double_vision_simulacao import DoubleVisionSimulacaoInput

from app.services.cortina_simulacao import CortinaSimulacaoInput, simular_cortina
router = APIRouter()


@router.post('/simulacao-romana')
def simular_romana_item(data: RomanaSimulacaoInput,
                        db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    from app.models.produto import ProdutoDB
    from app.tenant.isolation import require_tenant
    from app.services.romana_simulacao import simular_romana
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == data.produto_id, ProdutoDB.empresa_id == require_tenant(tenant)).first()
    if produto is None:
        raise HTTPException(404, 'Produto não encontrado para a empresa ativa')
    try:
        return simular_romana(produto, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/simulacao-rolo')
def simular_rolo_item(data: RoloSimulacaoInput,
                      db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    from app.models.produto import ProdutoDB
    from app.tenant.isolation import require_tenant
    from app.services.rolo_simulacao import simular_rolo
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == data.produto_id, ProdutoDB.empresa_id == require_tenant(tenant)).first()
    if produto is None:
        raise HTTPException(404, 'Produto não encontrado para a empresa ativa')
    try:
        return simular_rolo(produto, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/simulacao-double-vision')
def simular_double_vision_item(data: DoubleVisionSimulacaoInput,
                                db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    from app.models.produto import ProdutoDB
    from app.tenant.isolation import require_tenant
    from app.services.double_vision_simulacao import simular_double_vision
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == data.produto_id, ProdutoDB.empresa_id == require_tenant(tenant)).first()
    if produto is None:
        raise HTTPException(404, 'Produto não encontrado para a empresa ativa')
    try:
        return simular_double_vision(produto, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/simulacao-romana-teto')
def simular_romana_teto_item(data: RomanaTetoSimulacaoInput,
                              db: Session = Depends(get_db), tenant: TenantContext = Depends(get_current_tenant)):
    from app.models.produto import ProdutoDB
    from app.tenant.isolation import require_tenant
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == data.produto_id, ProdutoDB.empresa_id == require_tenant(tenant)).first()
    if produto is None:
        raise HTTPException(404, 'Produto não encontrado para a empresa ativa')
    try:
        return simular_romana_teto(produto, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@router.post("/simulacao-cortina")
def simular_cortina_endpoint(
    data: CortinaSimulacaoInput,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_current_tenant),
):
    from app.models.produto import ProdutoDB
    from app.tenant.isolation import require_tenant

    produto = (
        db.query(ProdutoDB)
        .filter(
            ProdutoDB.id == data.produto_id,
            ProdutoDB.empresa_id == require_tenant(tenant),
        )
        .first()
    )

    if produto is None:
        raise HTTPException(
            404,
            "Produto n?o encontrado para a empresa ativa",
        )

    try:
        return simular_cortina(produto, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/")
def listar(db:Session=Depends(get_db),tenant:TenantContext=Depends(get_current_tenant)):return orcamento_service.listar(db,tenant)
@router.get("/{oid}")
def obter(oid:int,db:Session=Depends(get_db),tenant:TenantContext=Depends(get_current_tenant)):
    r=orcamento_service.obter(db,oid,tenant)
    if not r:raise HTTPException(404,"Orçamento não encontrado")
    return r
@router.post("/",status_code=201)
def criar(data:OrcamentoInput,db:Session=Depends(get_db),tenant:TenantContext=Depends(get_current_tenant)):
    try:return orcamento_service.criar(db,data,tenant)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
@router.put("/{oid}")
def atualizar(oid:int,data:OrcamentoUpdate,db:Session=Depends(get_db),tenant:TenantContext=Depends(get_current_tenant)):
    try:r=orcamento_service.atualizar(db,oid,data,tenant)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    if not r:raise HTTPException(404,"Orçamento não encontrado")
    return r
@router.delete("/{oid}",status_code=204)
def remover(oid:int,db:Session=Depends(get_db),tenant:TenantContext=Depends(get_current_tenant)):
    if not orcamento_service.remover(db,oid,tenant):raise HTTPException(404,"Orçamento não encontrado")
