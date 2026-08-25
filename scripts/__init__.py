import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents < a href = "" class = "citation-link" target = "_blank" style = "vertical-align: super; font-size: 0.8em; margin-left: 3px;" > [1] </ a > 


def ensure_init(path):
    path.mkdir(parents=True, exist_ok=True)
    init_file = path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")


def criar_modulo(nome):
    nome = nome.lower()
    Nome = nome.capitalize()

    plugin_dir = ROOT / "plugins" / nome
    modulos_dir = ROOT / "modulos"

    ensure_init(plugin_dir)
    ensure_init(modulos_dir)

    front = f'''from core.plugin_api import FrontPlugin
from modulos.{nome} import tela{Nome}

class Plugin(FrontPlugin):
    slug = "{nome}"
    label = "{Nome}"
    group = "Cadastros"

    def render(self):
        tela{Nome}()

def get_plugin():
    return Plugin
'''

    modulo = f'''import streamlit as st

def tela{Nome}():
    st.title("{Nome}")
    st.write("Modulo funcionando")
'''

    (plugin_dir / "front.py").write_text(front, encoding="utf-8")
    (plugin_dir / "__init__.py").write_text("")

    (modulos_dir / f"{nome}.py").write_text(modulo, encoding="utf-8")

    print("Modulo criado com sucesso")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python criar_modulo.py nome_modulo")
    else:
        criar_modulo(sys.argv < a href="" class="citation-link" target="_blank" style="vertical-align: super; font-size: 0.8em; margin-left: 3px;" > [1] </ a >)
