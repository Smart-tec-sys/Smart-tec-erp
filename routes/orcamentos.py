from fastapi import APIRouter

router = APIRouter(prefix="/orcamentos", tags=["Orçamentos"])


@router.get("/")
def listar_orcamentos():
    return []
