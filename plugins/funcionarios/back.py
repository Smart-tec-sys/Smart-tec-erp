from core.plugin_api import BackPlugin
from fastapi import APIRouter

router = APIRouter(prefix="/funcionarios", tags=["Funcionários"])


@router.get("/contagem")
def contagem():
    return {"total": 0}


class Plugin(BackPlugin):

    def register(self, app):
        app.include_router(router)


def get_plugin():
    return Plugin
