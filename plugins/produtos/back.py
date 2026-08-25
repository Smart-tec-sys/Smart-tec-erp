from core.plugin_api import BackPlugin
from fastapi import APIRouter

router = APIRouter(prefix="/produtos", tags=["Produtos"])

@router.get("/")
def listar():
    return []

class Plugin(BackPlugin):
    def register(self, app):
        app.include_router(router)

def get_plugin():
    return Plugin
