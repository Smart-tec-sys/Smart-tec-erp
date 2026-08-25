from core.plugin_api import FrontPlugin
from modulos.fornecedores import telaFornecedores


class FornecedoresPlugin(FrontPlugin):
    slug = "fornecedores"
    label = "🏢 Fornecedores"
    group = "Cadastros"

    def render(self):
        telaFornecedores()


def get_plugin():
    return FornecedoresPlugin
