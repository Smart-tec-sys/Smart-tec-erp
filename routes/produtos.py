from fastapi import APIRouter

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.get("/")
def listar_produtos():
    return []
