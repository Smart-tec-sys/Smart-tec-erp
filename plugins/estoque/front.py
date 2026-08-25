from core.plugin_api import FrontPlugin
from modulos.estoque import telaEstoque

class Plugin(FrontPlugin):
    slug = "estoque"
    label = "📦 Estoque"
    group = "Cadastros"

    def render(self):
        telaEstoque()

def get_plugin():
    return Plugin
