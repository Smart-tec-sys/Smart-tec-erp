from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.orcamento import OrcamentoInput,OrcamentoUpdate
from app.services import orcamento_service
router=APIRouter()
@router.get("/")
def listar(db:Session=Depends(get_db)):return orcamento_service.listar(db)
@router.get("/{oid}")
def obter(oid:int,db:Session=Depends(get_db)):
    r=orcamento_service.obter(db,oid)
    if not r:raise HTTPException(404,"Orçamento não encontrado")
    return r
@router.post("/",status_code=201)
def criar(data:OrcamentoInput,db:Session=Depends(get_db)):return orcamento_service.criar(db,data)
@router.put("/{oid}")
def atualizar(oid:int,data:OrcamentoUpdate,db:Session=Depends(get_db)):
    r=orcamento_service.atualizar(db,oid,data)
    if not r:raise HTTPException(404,"Orçamento não encontrado")
    return r
@router.delete("/{oid}",status_code=204)
def remover(oid:int,db:Session=Depends(get_db)):
    if not orcamento_service.remover(db,oid):raise HTTPException(404,"Orçamento não encontrado")
