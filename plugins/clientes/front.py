from core.plugin_api import FrontPlugin
from modulos.cliente import telaClientes


class ClientesPlugin(FrontPlugin):
    slug = "clientes"
    label = "👥 Clientes"
    group = "Cadastros"

    def render(self):
        telaClientes()


def get_plugin():
    return ClientesPlugin
