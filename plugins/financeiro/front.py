from core.plugin_api import FrontPlugin
from modulos.financeiro import telaFinanceiro

class Plugin(FrontPlugin):
    slug = "financeiro"
    label = "📦 Financeiro"
    group = "Cadastros"

    def render(self):
        telaFinanceiro()

def get_plugin():
    return Plugin
