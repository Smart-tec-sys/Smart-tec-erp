from core.plugin_api import FrontPlugin
from modulos.funcionarios import telaFuncionarios


class FuncionariosPlugin(FrontPlugin):
    slug = "funcionarios"
    label = "👔 Funcionários"
    group = "Cadastros"

    def render(self):
        telaFuncionarios()


def get_plugin():
    return FuncionariosPlugin
