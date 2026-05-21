import streamlit as st

st.set_page_config(
    page_title="SmartTec ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

from modulos.dashboard import telaDashboard
from modulos.clientes import telaClientes
from modulos.fornecedores import telaFornecedores
from modulos.funcionarios import telaFuncionarios
from modulos.transportadoras import telaTransportadoras
from modulos.tipos_contatos import telaTiposContatos
from modulos.tipos_enderecos import telaTiposEnderecos
from modulos.campos_extras import telaCamposExtras
from modulos.importar_xml import telaImportarXML

# ==========================================
# CONTROLE DE NAVEGAÇÃO E SUB-MENUS
# ==========================================
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 'Dashboard'

# Controle para abrir/fechar o sub-menu de configurações de cadastro
if 'abrir_config_cadastros' not in st.session_state:
    st.session_state.abrir_config_cadastros = False


def navegar(pagina):
    st.session_state.pagina_atual = pagina


def toggle_config_cadastros():
    st.session_state.abrir_config_cadastros = not st.session_state.abrir_config_cadastros


# ==========================================
# CAPTURA QUERY PARAMS DO BREADCRUMB (NAVEGAÇÃO POR LINKS)
# ==========================================
params = st.query_params
if params.get("nav"):
    nav_value = params.get("nav")
    st.query_params.clear()
    
    if nav_value == "dashboard":
        st.session_state.pagina_atual = 'Dashboard'
    elif nav_value == "clientes_listar":
        st.session_state.pagina_atual = 'Clientes'
        st.session_state.tela_atual_clientes = 'listar'
    elif nav_value == "fornecedores_listar":
        st.session_state.pagina_atual = 'Fornecedores'
        st.session_state.tela_atual_fornecedores = 'listar'
    elif nav_value == "funcionarios_listar":
        st.session_state.pagina_atual = 'Funcionarios'
        st.session_state.tela_atual_funcionarios = 'listar'
    elif nav_value == "transportadoras_listar":
        st.session_state.pagina_atual = 'Transportadoras'
        st.session_state.tela_atual_transportadoras = 'listar'
    
    st.rerun()

# ==========================================
# SIDEBAR (MENU LATERAL COMPACTO)
# ==========================================
with st.sidebar:
    try:
        st.image("assets/logo.png", use_container_width=True)
    except Exception:
        st.markdown("## 🏭 SmartTec")
        
    st.divider()

    st.button("🏠 Dashboard", on_click=navegar, args=('Dashboard',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Dashboard' else "secondary")

    # --- CADASTROS ---
    abas_cadastros = ['Clientes', 'Fornecedores', 'Funcionarios', 'Transportadoras', 'TiposContatos', 'TiposEnderecos', 'CamposExtras', 'ImpExpClientes', 'ImpExpFornecedores']
    with st.expander("📝 Cadastros", expanded=True if st.session_state.pagina_atual in abas_cadastros else False):
        st.button("👥 Clientes", on_click=navegar, args=('Clientes',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Clientes' else "secondary")
        st.button("🏢 Fornecedores", on_click=navegar, args=('Fornecedores',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Fornecedores' else "secondary")
        st.button("👔 Funcionários", on_click=navegar, args=('Funcionarios',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Funcionarios' else "secondary")
        st.button("🚚 Transportadoras", on_click=navegar, args=('Transportadoras',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Transportadoras' else "secondary")
        
        # SUB-MENU COM A SETINHA (Mostrar/Esconder)
        setinha = "▴" if st.session_state.abrir_config_cadastros else "▾"
        st.button(f"⚙️ Configurações {setinha}", on_click=toggle_config_cadastros, use_container_width=True)
        
                # Só mostra os botões se a setinha estiver aberta
        if st.session_state.abrir_config_cadastros:
            st.button("↳ Tipos de contatos", on_click=navegar, args=('TiposContatos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'TiposContatos' else "secondary")
            st.button("↳ Tipos de endereços", on_click=navegar, args=('TiposEnderecos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'TiposEnderecos' else "secondary")
            st.button("↳ Campos extras", on_click=navegar, args=('CamposExtras',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'CamposExtras' else "secondary")

    # --- PRODUTOS ---
    with st.expander("|||| Produtos", expanded=True if st.session_state.pagina_atual == 'Produtos' else False):
        st.button("📦 Gerenciar Produtos", on_click=navegar, args=('Produtos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Produtos' else "secondary")

    # --- SERVIÇOS ---
    with st.expander("🔧 Serviços", expanded=True if st.session_state.pagina_atual == 'Servicos' else False):
        st.button("📋 Gerenciar Serviços", on_click=navegar, args=('Servicos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Servicos' else "secondary")

    # --- ORÇAMENTOS ---
    with st.expander("📄 Orçamentos", expanded=True if st.session_state.pagina_atual == 'Orcamentos' else False):
        st.button("➕ Novo Orçamento", on_click=navegar, args=('Orcamentos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Orcamentos' else "secondary")

    # --- ORDENS DE SERVIÇO ---
    with st.expander("🛠️ Ordens de serviços", expanded=True if st.session_state.pagina_atual == 'OS' else False):
        st.button("📋 Gerenciar O.S.", on_click=navegar, args=('OS',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'OS' else "secondary")

    # --- VENDAS ---
    with st.expander("🛒 Vendas", expanded=True if st.session_state.pagina_atual == 'Vendas' else False):
        st.button("💰 Gerenciar Vendas", on_click=navegar, args=('Vendas',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Vendas' else "secondary")

    # --- ESTOQUE ---
    with st.expander("📦 Estoque", expanded=True if st.session_state.pagina_atual == 'Estoque' else False):
        st.button("📊 Controle de Estoque", on_click=navegar, args=('Estoque',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Estoque' else "secondary")

    # --- FINANCEIRO ---
    with st.expander("💵 Financeiro", expanded=True if st.session_state.pagina_atual == 'Financeiro' else False):
        st.button("🏦 Fluxo de Caixa", on_click=navegar, args=('Financeiro',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Financeiro' else "secondary")

    # --- FISCAL ---
    with st.expander("🧾 Fiscal", expanded=True if st.session_state.pagina_atual == 'Fiscal' else False):
        st.button("📝 Notas Fiscais", on_click=navegar, args=('Fiscal',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Fiscal' else "secondary")

    # --- CONTRATOS ---
    with st.expander("✍️ Contratos", expanded=True if st.session_state.pagina_atual == 'Contratos' else False):
        st.button("📑 Gerenciar Contratos", on_click=navegar, args=('Contratos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Contratos' else "secondary")

    # --- ATENDIMENTOS ---
    with st.expander("📞 Atendimentos", expanded=True if st.session_state.pagina_atual == 'Atendimentos' else False):
        st.button("🎧 Suporte / SAC", on_click=navegar, args=('Atendimentos',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Atendimentos' else "secondary")

    # --- RELATÓRIOS ---
    with st.expander("📈 Relatórios", expanded=True if st.session_state.pagina_atual == 'Relatorios' else False):
        st.button("📊 Gerar Relatórios", on_click=navegar, args=('Relatorios',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'Relatorios' else "secondary")

    # --- CONFIGURAÇÕES GERAIS ---
    with st.expander("⚙️ Configurações Gerais", expanded=True if st.session_state.pagina_atual == 'ConfiguracoesGerais' else False):
        st.button("🛠️ Ajustes do Sistema", on_click=navegar, args=('ConfiguracoesGerais',), use_container_width=True, type="primary" if st.session_state.pagina_atual == 'ConfiguracoesGerais' else "secondary")

    st.divider()
    st.caption("v1.0.0 © SmartTec 2026")

# ==========================================
# ROTEADOR (CHAMA A TELA CORRESPONDENTE)
# ==========================================
pagina = st.session_state.pagina_atual

if pagina == 'Dashboard':
    telaDashboard()
elif pagina == 'Clientes':
    telaClientes()
elif pagina == 'Fornecedores':
    telaFornecedores()
elif pagina == 'Funcionarios':
    telaFuncionarios()
elif pagina == 'Transportadoras':
    telaTransportadoras()
elif pagina == 'TiposContatos':
    telaTiposContatos()
elif pagina == 'TiposEnderecos': 
    telaTiposEnderecos()
elif pagina == 'CamposExtras':
    telaCamposExtras()
elif pagina == 'ImpNFClientes':
    telaImportarXML()

elif pagina in ['TiposEnderecos', 'CamposExtras', 'ImpExpClientes', 'ImpExpFornecedores']:
    st.title("⚙️ Configurações de Cadastros")
    st.info(f"Módulo de {pagina} em construção.")

elif pagina == 'ConfiguracoesGerais':
    st.title("⚙️ Configurações Gerais")
    st.info("Módulo de ajustes gerais do sistema em construção.")
else:
    st.title(f"🚧 {pagina}")
    st.info(f"A tela {pagina} está na fila de desenvolvimento.")
