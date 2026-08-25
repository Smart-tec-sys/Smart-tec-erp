from core.plugin_api import FrontPlugin
from modulos.transportadora import telaTransportadoras


class TransportadorasPlugin(FrontPlugin):
    slug = "transportadoras"
    label = "🚚 Transportadoras"
    group = "Cadastros"

    def render(self):
        telaTransportadoras()


def get_plugin():
    return TransportadorasPlugin
