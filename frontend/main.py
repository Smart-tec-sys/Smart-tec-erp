# frontend/main.py
import streamlit as st
import requests

# ─── Configuração da página ───────────────────────────────
st.set_page_config(
    page_title="SmartTec ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── URL da API ───────────────────────────────────────────
API_URL = "http://localhost:8000"


# ─── Funções que consomem a API ───────────────────────────
def get_total_clientes():
    try:
        r = requests.get(f"{API_URL}/clientes/contagem", timeout=5)
        return r.json().get("total", 0)
    except:
        return 0


def get_total_pedidos():
    try:
        r = requests.get(f"{API_URL}/pedidos/contagem", timeout=5)
        return r.json().get("total", 0)
    except:
        return 0


def get_faturamento():
    try:
        r = requests.get(f"{API_URL}/vendas/faturamento", timeout=5)
        return r.json().get("total", 0.0)
    except:
        return 0.0


# ─── Navegação ────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"


def go(slug: str):
    st.session_state.page = slug


# ─── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏭 SmartTec")
    st.divider()

    st.button(
        "🏠 Dashboard",
        on_click=go, args=("dashboard",),
        use_container_width=True,
        type="primary" if st.session_state.page == "dashboard" else "secondary"
    )

    with st.expander("📝 Cadastros", expanded=True):
        st.button("👥 Clientes", on_click=go, args=("clientes",), use_container_width=True)
        st.button("🏢 Fornecedores", on_click=go, args=("fornecedores",), use_container_width=True)
        st.button("👔 Funcionários", on_click=go, args=("funcionarios",), use_container_width=True)
        st.button("🚚 Transportadoras", on_click=go, args=("transportadoras",), use_container_width=True)

    with st.expander("📦 Produtos"):
        st.button("📦 Produtos", on_click=go, args=("produtos",), use_container_width=True)

    with st.expander("🛒 Vendas"):
        st.button("💰 Vendas", on_click=go, args=("vendas",), use_container_width=True)

    with st.expander("💵 Financeiro"):
        st.button("🏦 Financeiro", on_click=go, args=("financeiro",), use_container_width=True)

    st.divider()
    st.caption("v1.0.0 © SmartTec 2026")

# ─── Roteador ─────────────────────────────────────────────
page = st.session_state.page

if page == "dashboard":
    st.title("🏠 Dashboard")

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Clientes", get_total_clientes())
    col2.metric("🛒 Pedidos", get_total_pedidos())
    col3.metric("💰 Faturamento", f"R$ {get_faturamento():,.2f}")

    st.divider()
    st.info("Gráficos serão carregados aqui conforme módulos forem ativados.")

elif page == "clientes":
    st.title("👥 Clientes")
    st.info("Módulo de clientes em construção.")

elif page == "produtos":
    st.title("📦 Produtos")
    st.info("Módulo de produtos em construção.")

else:
    st.title(f"🚧 {page.capitalize()}")
    st.info("Este módulo está em construção.")
