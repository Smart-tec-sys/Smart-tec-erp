from core.plugin_api import BackPlugin
from backend.app.routers.clientes import router  # seu router atual


class ClientesBack(BackPlugin):

    def register(self, app):
        app.include_router(router)


def get_plugin():
    return ClientesBack
