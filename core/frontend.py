import sys
import pathlib
import importlib
import streamlit as st

# ✅ CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="SmartTec ERP", layout="wide")

# ───────────── RAIZ ─────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

# ───────────── API ─────────────
try:
    from Services.API import total, faturamento
except ImportError:

    def total(x): return 0

    def faturamento(): return 0


# ───────────── FUNÇÃO CABEÇALHO (CORRIGIDA) ─────────────
def cabecalho(titulo, modulo, tela_atual, slug_modulo=None):
    import streamlit as st

    c1, c2 = st.columns([1, 1])

    with c1:
        st.title(titulo)

    with c2:
        b1, sep1, b2, sep2, b3 = st.columns([1, 0.2, 1, 0.2, 1])

        with b1:
            if st.button("🏠 Início"):
                st.session_state.page = "dashboard"
                st.rerun()

        with sep1:
            st.write(">")

        with b2:
            if st.button(modulo):
                st.session_state.page = slug_modulo
                st.session_state[f"tela_atual_{slug_modulo}"] = "listar"
                st.rerun()

        with sep2:
            st.write(">")

        with b3:
            st.markdown(f"**{tela_atual}**")


# ───────────── PLUGINS ─────────────
def load_plugins():
    plugs = {}
    plugins_dir = ROOT / "plugins"

    if not plugins_dir.exists():
        return plugs

    for item in plugins_dir.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            nome = item.name
            try:
                m = importlib.import_module(f"plugins.{nome}.front")

                if not hasattr(m, "get_plugin"):
                    continue

                plugin_class = m.get_plugin()
                if plugin_class is None:
                    continue

                plugin = plugin_class()

                if not hasattr(plugin, "slug") or not hasattr(plugin, "label"):
                    continue

                plugs[plugin.slug] = plugin

            except Exception:
                pass

    return plugs


PLUGS = load_plugins()

# ───────────── ESTADO ─────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"


def go(p):
    st.session_state.page = p


page = st.session_state.page

# ───────────── QUERY PARAMS (BREADCRUMB FUNCIONANDO) ─────────────
params = st.query_params

if "nav" in params:
    nav = params["nav"]
    st.query_params.clear()

    if nav == "dashboard":
        st.session_state.page = "dashboard"

    elif nav.endswith("_listar"):
        modulo = nav.replace("_listar", "")
        st.session_state.page = modulo
        st.session_state[f"tela_{modulo}"] = "listar"

    st.rerun()

# ───────────── CSS ─────────────
st.markdown("""
<style>
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 2rem !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# ───────────── SIDEBAR ─────────────
with st.sidebar:
    st.markdown("## 🏭 SmartTec")
    st.caption("Sistema de Gestão")

    st.divider()

    def menu_btn(slug, label):
        st.button(
            label,
            on_click=go,
            args=(slug,),
            use_container_width=True,
            type="primary" if page == slug else "secondary"
        )

    # Dashboard
    menu_btn("dashboard", "🏠 Dashboard")

    st.divider()

    # Cadastros
    with st.expander("🗂️ Cadastros", expanded=page in ["clientes", "fornecedores", "funcionarios", "transportadoras"]):
        if "clientes" in PLUGS:
            menu_btn("clientes", "👥 Clientes")
        if "fornecedores" in PLUGS:
            menu_btn("fornecedores", "🏢 Fornecedores")
        if "funcionarios" in PLUGS:
            menu_btn("funcionarios", "👔 Funcionários")
        if "transportadoras" in PLUGS:
            menu_btn("transportadoras", "🚚 Transportadoras")

    # Produtos
    with st.expander("📦 Produtos"):
        if "produtos" in PLUGS:
            menu_btn("produtos", "📦 Produtos")

    # Estoque
    with st.expander("📦 Estoque"):
        if "estoque" in PLUGS:
            menu_btn("estoque", "📦 Estoque")

    # Financeiro
    with st.expander("💰 Financeiro"):
        if "financeiro" in PLUGS:
            menu_btn("financeiro", "💰 Financeiro")

    st.divider()
    st.caption("v1.0.0 © SmartTec")

# ───────────── PÁGINAS ─────────────
if page == "dashboard":
    st.markdown("## 📊 Dashboard")
    st.caption("Visão geral do sistema")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Clientes", total("clientes"))
    c2.metric("Pedidos", total("pedidos"))
    c3.metric("Faturamento", f"R$ {faturamento():,.2f}")
    c4.metric("Produtos", total("produtos"))

    st.divider()

    st.subheader("Visão geral")
    st.info("Gráficos e indicadores serão exibidos aqui.")

else:
    if page in PLUGS:
        PLUGS[page].render()
    else:
        st.error("Página não encontrada.")
