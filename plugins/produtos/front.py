from core.plugin_api import FrontPlugin
from modulos.produtos import telaProdutos

class Plugin(FrontPlugin):
    slug = "produtos"
    label = "📦 Produtos"
    group = "Cadastros"

    def render(self):
        telaProdutos()

def get_plugin():
    return Plugin
