import streamlit as st
from pathlib import Path

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    layout="wide",
    page_title="SmartTec ERP"
)

from app.auth.streamlit_ui import (
    initialize_authentication_gate,
    render_authenticated_identity_bar,
)
from app.auth.navigation import navigate_in_current_session

initialize_authentication_gate()

from modulos.cliente import telaCliente
from modulos.fornecedor import telaFornecedor
from modulos.funcionario import telaFuncionario
from modulos.transportadora import telaTransportadora
from modulos.opcao_auxiliar import telaOpcaoAuxiliar
from modulos.produtos import telaProdutos
from modulos.produto_opcoes_auxiliares import telaProdutoOpcoesAuxiliares
from modulos.produtos_valores_venda import telaProdutosValoresVenda
from modulos.produtos_etiquetas import telaProdutosEtiquetas
from modulos.equivalencias_tecnicas import telaEquivalenciasTecnicas
try:
    from modulos.servicos import telaServicos
except Exception as erro_import_servicos:
    ERRO_IMPORT_SERVICOS = erro_import_servicos

    def telaServicos(erro=ERRO_IMPORT_SERVICOS):
        st.error("Não consegui carregar o módulo Serviços.")
        st.exception(erro)

try:
    from modulos.orcamentos import telaOrcamentos
except Exception as erro_import_orcamentos:
    ERRO_IMPORT_ORCAMENTOS = erro_import_orcamentos

    def telaOrcamentos(erro=ERRO_IMPORT_ORCAMENTOS):
        st.error("Não consegui carregar o módulo Orçamentos.")
        st.exception(erro)


# =========================================================
# CSS GLOBAL DO APP
# =========================================================
def carregar_estilo_global():
    css = """
<style>
:root {
    --erp-bg: #f3f4f6;
    --erp-surface: #ffffff;
    --erp-border: #d6d6d6;
    --erp-text: #111111;
    --erp-muted: #6b7280;
    --erp-topbar: #0f0f10;
    --erp-topbar-hover: #252526;
    --erp-primary: #ff0019;
    --erp-primary-hover: #d10015;
    --erp-menu: #161616;
    --erp-menu-hover: #2b2b2b;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--erp-bg) !important;
}

.block-container {
    padding-top: 4.5rem !important;
    padding-left: 1.1rem !important;
    padding-right: 1.1rem !important;
    max-width: 100% !important;
    width: 100% !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #f5f6f8 !important;
    border-right: 1px solid var(--erp-border);
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 4.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

.sidebar-logo-box {
    width: 100%;
    min-height: 130px;
    background: var(--erp-surface);
    border: 1px dashed #c5c5c5;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--erp-muted);
    font-size: 13px;
    text-align: center;
    margin-bottom: 18px;
    padding: 14px;
}

.sidebar-section-title {
    font-weight: 700;
    color: var(--erp-text);
    font-size: 14px;
    margin-top: 8px;
    margin-bottom: 10px;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background-color: var(--erp-menu) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    min-height: 42px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
    background-color: var(--erp-menu-hover) !important;
    color: white !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
    background-color: var(--erp-primary) !important;
    color: white !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: var(--erp-primary-hover) !important;
    color: white !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="secondary"] {
    background: transparent !important;
    color: #374151 !important;
    border: none !important;
    min-height: 32px !important;
    height: 32px !important;
    justify-content: flex-start !important;
    padding: 7px 8px 7px 16px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="secondary"]:hover {
    background: #ffffff !important;
    color: #111827 !important;
}

/* Menu lateral estilo GestãoClick */
section[data-testid="stSidebar"] details {
    border-bottom: 1px solid #dddddd !important;
    padding: 0 !important;
    margin: 0 !important;
}

section[data-testid="stSidebar"] summary {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #111827 !important;
    padding: 10px 6px !important;
    cursor: pointer !important;
}

section[data-testid="stSidebar"] details div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* Topbar fixa */
.erp-topbar-fixed {
    position: fixed;
    top: 0;
    left: 0 !important;
    right: 0 !important;
    width: 100vw !important;
    height: 58px;
    z-index: 999999;
    background: var(--erp-topbar);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 26px;
    box-sizing: border-box;
    border-bottom: 1px solid #222;
}

.erp-topbar-left,
.erp-topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
}

.erp-brand {
    display: flex;
    align-items: baseline;
    gap: 7px;
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.6px;
    line-height: 1;
    white-space: nowrap;
    margin-right: 10px;
}

.erp-brand .brand-red {
    color: var(--erp-primary);
}

.erp-brand .brand-small {
    color: #ffffff;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2.2px;
    text-transform: uppercase;
    opacity: 0.8;
}

.erp-topbar-link,
.erp-topbar-icon,
.erp-user-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-decoration: none !important;
    color: #ffffff !important;
    height: 34px;
    min-width: 34px;
    padding: 0 10px;
    border-radius: 6px;
    background: transparent;
    font-size: 16px;
    position: relative;
    box-sizing: border-box;
    cursor: pointer;
}

.erp-topbar-link:hover,
.erp-topbar-icon:hover {
    background: var(--erp-topbar-hover);
    color: #ffffff !important;
}

.erp-user-chip {
    background: #ffffff;
    color: #111111 !important;
    font-size: 13px;
    font-weight: 800;
    min-width: 36px;
}

.erp-user-chip:hover {
    background: #f3f4f6;
    color: #111111 !important;
}

.erp-badge {
    position: absolute;
    top: 2px;
    right: 2px;
    background: var(--erp-primary);
    color: #ffffff;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    font-size: 10px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


# =========================================================
# BARRA SUPERIOR
# =========================================================
def render_topbar():
    topbar = (
        '<div class="erp-topbar-fixed">'
        '<div class="erp-topbar-left">'
        '<div class="erp-brand">'
        '<span>Smart-<span class="brand-red">tec</span></span>'
        '<span class="brand-small">Sistemas</span>'
        '</div>'
        '<span class="erp-topbar-link" title="Menu">☰</span>'
        '</div>'
        '<div class="erp-topbar-right">'
        '<span class="erp-topbar-link" title="Painel">▦</span>'
        '<span class="erp-topbar-icon" title="Atalhos">✦</span>'
        '<span class="erp-topbar-icon" title="Documentos">⌑</span>'
        '<span class="erp-topbar-icon" title="Notificações">🔔<span class="erp-badge">1</span></span>'
        '<span class="erp-user-chip" title="Usuário">VB</span>'
        '</div>'
        '</div>'
    )
    st.markdown(topbar, unsafe_allow_html=True)


# =========================================================
# ESTADO INICIAL
# =========================================================
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Painel"

# =========================================================
# NAVEGAÇÃO POR QUERY PARAMS
# =========================================================
params = st.query_params

if "go_to" in params:
    destino = params.get("go_to", "painel")
    acao = params.get("acao", "listar")

    if isinstance(destino, (list, tuple)):
        destino = destino[0]

    if isinstance(acao, (list, tuple)):
        acao = acao[0]

    if destino == "painel":
        st.session_state.pagina_atual = "Painel"

    elif destino == "clientes":
        st.session_state.pagina_atual = "Clientes"

        if "acao_cliente" in params and "id_cliente" in params:
            acao_cliente = params["acao_cliente"]
            id_cliente = params["id_cliente"]

            if isinstance(acao_cliente, (list, tuple)):
                acao_cliente = acao_cliente[0]

            if isinstance(id_cliente, (list, tuple)):
                id_cliente = id_cliente[0]

            id_cliente = int(id_cliente)

            if acao_cliente == "visualizar":
                st.session_state.tela_clientes = "visualizar"
                st.session_state.id_cliente_editar = id_cliente

            elif acao_cliente == "editar":
                st.session_state.tela_clientes = "editar"
                st.session_state.id_cliente_editar = id_cliente

            elif acao_cliente == "excluir":
                nome_cliente = params.get("nome_cliente", "")

                if isinstance(nome_cliente, (list, tuple)):
                    nome_cliente = nome_cliente[0]

                st.session_state.tela_clientes = "listar"
                st.session_state.confirmar_exclusao_cliente = id_cliente
                st.session_state.confirmar_exclusao_cliente_nome = str(nome_cliente)

        else:
            st.session_state.tela_clientes = (
                acao if acao in ["listar", "busca", "adicionar", "editar", "visualizar"] else "listar"
            )

    elif destino == "fornecedores":
        st.session_state.pagina_atual = "Fornecedores"

        if "acao_fornecedor" in params and "id_fornecedor" in params:
            acao_fornecedor = params["acao_fornecedor"]
            id_fornecedor = params["id_fornecedor"]

            if isinstance(acao_fornecedor, (list, tuple)):
                acao_fornecedor = acao_fornecedor[0]

            if isinstance(id_fornecedor, (list, tuple)):
                id_fornecedor = id_fornecedor[0]

            id_fornecedor = int(id_fornecedor)

            if acao_fornecedor == "visualizar":
                st.session_state.tela_fornecedores = "visualizar"
                st.session_state.id_fornecedor_editar = id_fornecedor

            elif acao_fornecedor == "editar":
                st.session_state.tela_fornecedores = "editar"
                st.session_state.id_fornecedor_editar = id_fornecedor

            elif acao_fornecedor == "excluir":
                nome_fornecedor = params.get("nome_fornecedor", "")

                if isinstance(nome_fornecedor, (list, tuple)):
                    nome_fornecedor = nome_fornecedor[0]

                st.session_state.tela_fornecedores = "listar"
                st.session_state.confirmar_exclusao_fornecedor = id_fornecedor
                st.session_state.confirmar_exclusao_fornecedor_nome = str(nome_fornecedor)

        else:
            st.session_state.tela_fornecedores = (
                acao if acao in ["listar", "busca", "adicionar", "editar", "visualizar"] else "listar"
            )

    elif destino == "funcionarios":
        st.session_state.pagina_atual = "Funcionários"

        if "acao_funcionario" in params and "id_funcionario" in params:
            acao_funcionario = params["acao_funcionario"]
            id_funcionario = params["id_funcionario"]

            if isinstance(acao_funcionario, (list, tuple)):
                acao_funcionario = acao_funcionario[0]

            if isinstance(id_funcionario, (list, tuple)):
                id_funcionario = id_funcionario[0]

            id_funcionario = int(id_funcionario)

            if acao_funcionario == "visualizar":
                st.session_state.tela_atual_funcionarios = "visualizar"
                st.session_state.id_funcionario_editar = id_funcionario

            elif acao_funcionario == "editar":
                st.session_state.tela_atual_funcionarios = "editar"
                st.session_state.id_funcionario_editar = id_funcionario

            elif acao_funcionario == "excluir":
                nome_funcionario = params.get("nome_funcionario", "")

                if isinstance(nome_funcionario, (list, tuple)):
                    nome_funcionario = nome_funcionario[0]

                st.session_state.tela_atual_funcionarios = "listar"
                st.session_state.confirmar_exclusao_funcionario = id_funcionario
                st.session_state.confirmar_exclusao_funcionario_nome = str(nome_funcionario)

        else:
            st.session_state.tela_atual_funcionarios = (
                acao if acao in ["listar", "busca", "adicionar", "editar", "visualizar"] else "listar"
            )

    elif destino == "transportadoras":
        st.session_state.pagina_atual = "Transportadoras"

        if "acao_transportadora" in params and "id_transportadora" in params:
            acao_transportadora = params["acao_transportadora"]
            id_transportadora = params["id_transportadora"]

            if isinstance(acao_transportadora, (list, tuple)):
                acao_transportadora = acao_transportadora[0]

            if isinstance(id_transportadora, (list, tuple)):
                id_transportadora = id_transportadora[0]

            id_transportadora = int(id_transportadora)

            if acao_transportadora == "visualizar":
                st.session_state.tela_atual_transportadoras = "visualizar"
                st.session_state.id_transportadora_editar = id_transportadora

            elif acao_transportadora == "editar":
                st.session_state.tela_atual_transportadoras = "editar"
                st.session_state.id_transportadora_editar = id_transportadora

            elif acao_transportadora == "excluir":
                nome_transportadora = params.get("nome_transportadora", "")

                if isinstance(nome_transportadora, (list, tuple)):
                    nome_transportadora = nome_transportadora[0]

                st.session_state.tela_atual_transportadoras = "listar"
                st.session_state.confirmar_exclusao_transportadora = id_transportadora
                st.session_state.confirmar_exclusao_transportadora_nome = str(nome_transportadora)

        else:
            st.session_state.tela_atual_transportadoras = (
                acao if acao in ["listar", "busca", "adicionar", "editar", "visualizar"] else "listar"
            )

    elif destino == "opcoes_auxiliares":
        st.session_state.pagina_atual = "Opções Auxiliares"

        categoria = params.get("categoria", "tipo_contato")
        acao_opcao = params.get("acao_opcao", "listar")

        if isinstance(categoria, (list, tuple)):
            categoria = categoria[0]

        if isinstance(acao_opcao, (list, tuple)):
            acao_opcao = acao_opcao[0]

        st.session_state.categoria_opcoes = categoria

        if "acao_opcao" in params and "id_opcao" in params:
            id_opcao = params["id_opcao"]

            if isinstance(id_opcao, (list, tuple)):
                id_opcao = id_opcao[0]

            id_opcao = int(id_opcao)

            if acao_opcao == "visualizar":
                st.session_state.tela_atual_opcoes = "visualizar"
                st.session_state.id_opcao_editar = id_opcao

            elif acao_opcao == "editar":
                st.session_state.tela_atual_opcoes = "editar"
                st.session_state.id_opcao_editar = id_opcao

            elif acao_opcao == "excluir":
                nome_opcao = params.get("nome_opcao", "")

                if isinstance(nome_opcao, (list, tuple)):
                    nome_opcao = nome_opcao[0]

                st.session_state.tela_atual_opcoes = "listar"
                st.session_state.confirmar_exclusao_opcao = id_opcao
                st.session_state.confirmar_exclusao_opcao_nome = str(nome_opcao)

        else:
            st.session_state.tela_atual_opcoes = (
                acao_opcao if acao_opcao in ["listar", "adicionar", "editar", "visualizar"] else "listar"
            )
            st.session_state.id_opcao_editar = None

    elif destino == "produtos":
        # Não force "listar" em toda atualização, senão os botões do módulo Produtos piscam e voltam.
        pagina_anterior = st.session_state.get("pagina_atual")
        st.session_state.pagina_atual = "Produtos"

        if pagina_anterior != "Produtos":
            st.session_state.tela_produtos = "listar"
            st.session_state.id_produto_editar = None

        if "tela_produtos" not in st.session_state:
            st.session_state.tela_produtos = "listar"

        if "id_produto_editar" not in st.session_state:
            st.session_state.id_produto_editar = None

    elif destino == "servicos":
        pagina_anterior = st.session_state.get("pagina_atual")
        st.session_state.pagina_atual = "Serviços"

        if pagina_anterior != "Serviços":
            st.session_state.tela_servicos = "listar"
            st.session_state.id_servico_editar = None

        if "tela_servicos" not in st.session_state:
            st.session_state.tela_servicos = "listar"

        if "id_servico_editar" not in st.session_state:
            st.session_state.id_servico_editar = None

        acao_servico = params.get("acao_servico")
        id_servico = params.get("id_servico")

        if isinstance(acao_servico, (list, tuple)):
            acao_servico = acao_servico[0]
        if isinstance(id_servico, (list, tuple)):
            id_servico = id_servico[0]

        if acao_servico in ["visualizar", "editar"] and id_servico:
            st.session_state.tela_servicos = acao_servico
            st.session_state.id_servico_editar = int(id_servico)
        elif acao_servico == "excluir" and id_servico:
            nome_servico = params.get("nome_servico", "")
            if isinstance(nome_servico, (list, tuple)):
                nome_servico = nome_servico[0]
            st.session_state.tela_servicos = "listar"
            st.session_state.confirmar_exclusao_servico = int(id_servico)
            st.session_state.confirmar_exclusao_servico_nome = str(nome_servico)

    elif destino == "orcamentos":
        pagina_anterior = st.session_state.get("pagina_atual")
        st.session_state.pagina_atual = "Orçamentos"

        if pagina_anterior != "Orçamentos":
            st.session_state.tela_orcamentos = "listar"
            st.session_state.id_orcamento_editar = None

        if "tela_orcamentos" not in st.session_state:
            st.session_state.tela_orcamentos = "listar"

        if "id_orcamento_editar" not in st.session_state:
            st.session_state.id_orcamento_editar = None

    elif destino == "produtos_valores":
        st.session_state.pagina_atual = "Valores de venda"

    elif destino == "produtos_ajustar_valores":
        st.session_state.pagina_atual = "Ajustar valores em massa"
        st.session_state.tela_produtos = "listar"
        st.session_state.acao_mais_produtos = "ajustar_valores"

    elif destino == "produtos_etiquetas":
        st.session_state.pagina_atual = "Etiquetas"

    elif destino == "produtos_opcoes":
        st.session_state.pagina_atual = "Opções auxiliares de produtos"

        categoria_produto = params.get("categoria", "grupo_produto")
        if isinstance(categoria_produto, (list, tuple)):
            categoria_produto = categoria_produto[0]

        st.session_state.categoria_produto_opcoes = categoria_produto

        # IMPORTANTE:
        # Não forçar tela_produto_opcoes = "listar" aqui.
        # Isso evita o problema da tela "piscar" e voltar quando clicar em Adicionar/Editar.
        if "tela_produto_opcoes" not in st.session_state:
            st.session_state.tela_produto_opcoes = "listar"

        if "id_produto_opcao_editar" not in st.session_state:
            st.session_state.id_produto_opcao_editar = None

    elif destino == "equivalencias_tecnicas":
        st.session_state.pagina_atual = "Equivalências técnicas"

    # IMPORTANTE:
    # Não limpar query params com rerun automático aqui.
    # Isso corta cliques de formulário e faz botões piscarem.


# =========================================================
# FUNÇÕES DO MENU LATERAL
# =========================================================
def ir_para_clientes():
    st.query_params.clear()
    st.session_state.pagina_atual = "Clientes"
    st.session_state.tela_clientes = "listar"
    st.session_state.id_cliente_editar = None


def ir_para_fornecedores():
    st.query_params.clear()
    st.session_state.pagina_atual = "Fornecedores"
    st.session_state.tela_fornecedores = "listar"
    st.session_state.id_fornecedor_editar = None


def ir_para_funcionarios():
    st.query_params.clear()
    st.session_state.pagina_atual = "Funcionários"
    st.session_state.tela_atual_funcionarios = "listar"
    st.session_state.id_funcionario_editar = None


def ir_para_transportadoras():
    st.query_params.clear()
    st.session_state.pagina_atual = "Transportadoras"
    st.session_state.tela_atual_transportadoras = "listar"
    st.session_state.id_transportadora_editar = None


def ir_para_opcoes_auxiliares():
    st.query_params.clear()
    st.session_state.pagina_atual = "Opções Auxiliares"
    st.session_state.tela_atual_opcoes = "listar"
    st.session_state.categoria_opcoes = "tipo_contato"
    st.session_state.id_opcao_editar = None


def ir_para_tipos_contatos():
    st.query_params.clear()
    st.session_state.pagina_atual = "Opções Auxiliares"
    st.session_state.tela_atual_opcoes = "listar"
    st.session_state.categoria_opcoes = "tipo_contato"
    st.session_state.id_opcao_editar = None


def ir_para_tipos_enderecos():
    st.query_params.clear()
    st.session_state.pagina_atual = "Opções Auxiliares"
    st.session_state.tela_atual_opcoes = "listar"
    st.session_state.categoria_opcoes = "tipo_endereco"
    st.session_state.id_opcao_editar = None


def ir_para_campos_extras():
    st.query_params.clear()
    st.session_state.pagina_atual = "Opções Auxiliares"
    st.session_state.tela_atual_opcoes = "listar"
    st.session_state.categoria_opcoes = "campo_extra"
    st.session_state.id_opcao_editar = None


def ir_para_produtos():
    st.query_params.clear()
    st.session_state.pagina_atual = "Produtos"
    st.session_state.tela_produtos = "listar"
    st.session_state.id_produto_editar = None


def ir_para_ajustar_valores_produtos():
    st.query_params.clear()
    st.session_state.pagina_atual = "Ajustar valores em massa"
    st.session_state.tela_produtos = "listar"
    st.session_state.acao_mais_produtos = "ajustar_valores"
    st.session_state.id_produto_editar = None


def ir_para_servicos():
    st.query_params.clear()
    st.session_state.pagina_atual = "Serviços"
    st.session_state.tela_servicos = "listar"
    st.session_state.id_servico_editar = None


def ir_para_orcamentos():
    st.query_params.clear()
    st.session_state.pagina_atual = "Orçamentos"
    st.session_state.tela_orcamentos = "listar"
    st.session_state.id_orcamento_editar = None


# =========================================================
# RENDERIZAÇÃO PRINCIPAL
# =========================================================
carregar_estilo_global()
render_topbar()
render_authenticated_identity_bar()


# =========================================================
# MENU LATERAL
# =========================================================
def item_menu_link(label, destino, ativo=False, extra_params=""):
    """
    Link pequeno no estilo GestãoClick para evitar botões grandes na lateral.
    """
    key_suffix = extra_params.replace("&", "_").replace("=", "_") or "root"
    st.button(
        label,
        key=f"nav_{destino}_{key_suffix}",
        type="primary" if ativo else "secondary",
        use_container_width=True,
        on_click=navigate_in_current_session,
        args=(st.session_state, st.query_params, destino, extra_params),
    )


with st.sidebar:
    logo_path = Path("assets/logo_empresa.png")

    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.markdown(
            """
            <div class="sidebar-logo-box">
                Logo da empresa<br>
                250 x 140 px
            </div>
            """,
            unsafe_allow_html=True,
        )

    item_menu_link(
        "▦ Painel",
        "painel",
        ativo=st.session_state.pagina_atual == "Painel",
    )

    paginas_cadastros = [
        "Clientes",
        "Fornecedores",
        "Funcionários",
        "Transportadoras",
        "Opções Auxiliares",
    ]

    paginas_produtos = [
        "Produtos",
        "Valores de venda",
        "Ajustar valores em massa",
        "Etiquetas",
        "Opções auxiliares de produtos",
        "Equivalências técnicas",
    ]

    # ─────────────────────────────────────────
    # CADASTROS estilo menu recolhível
    # ─────────────────────────────────────────
    with st.expander(
        "▤ Cadastros",
        expanded=st.session_state.pagina_atual in paginas_cadastros,
    ):
        item_menu_link(
            "👥 Clientes",
            "clientes",
            ativo=st.session_state.pagina_atual == "Clientes",
        )

        item_menu_link(
            "📦 Fornecedores",
            "fornecedores",
            ativo=st.session_state.pagina_atual == "Fornecedores",
        )

        item_menu_link(
            "🧑‍💼 Funcionários",
            "funcionarios",
            ativo=st.session_state.pagina_atual == "Funcionários",
        )

        item_menu_link(
            "🚚 Transportadoras",
            "transportadoras",
            ativo=st.session_state.pagina_atual == "Transportadoras",
        )

        item_menu_link(
            "⚙️ Opções auxiliares",
            "opcoes_auxiliares",
            ativo=st.session_state.pagina_atual == "Opções Auxiliares",
            extra_params="&categoria=tipo_contato",
        )

        if st.session_state.pagina_atual == "Opções Auxiliares":
            categoria_atual = st.session_state.get("categoria_opcoes", "tipo_contato")

            st.markdown(
                '<div style="padding-left:18px;margin-top:4px;margin-bottom:6px;">',
                unsafe_allow_html=True,
            )

            item_menu_link(
                "📣 Tipos de contatos",
                "opcoes_auxiliares",
                ativo=categoria_atual == "tipo_contato",
                extra_params="&categoria=tipo_contato",
            )

            item_menu_link(
                "📍 Tipos de endereços",
                "opcoes_auxiliares",
                ativo=categoria_atual == "tipo_endereco",
                extra_params="&categoria=tipo_endereco",
            )

            item_menu_link(
                "📋 Campos extras",
                "opcoes_auxiliares",
                ativo=categoria_atual == "campo_extra",
                extra_params="&categoria=campo_extra",
            )

            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # PRODUTOS estilo menu recolhível
    # ─────────────────────────────────────────
    with st.expander(
        "▥ Produtos",
        expanded=st.session_state.pagina_atual in paginas_produtos,
    ):
        item_menu_link(
            "📦 Gerenciar produtos",
            "produtos",
            ativo=st.session_state.pagina_atual == "Produtos",
        )

        item_menu_link(
            "💲 Valores de venda",
            "produtos_valores",
            ativo=st.session_state.pagina_atual == "Valores de venda",
        )

        item_menu_link(
            "💹 Ajustar valores em massa",
            "produtos_ajustar_valores",
            ativo=st.session_state.pagina_atual == "Ajustar valores em massa",
        )

        item_menu_link(
            "🏷️ Etiquetas",
            "produtos_etiquetas",
            ativo=st.session_state.pagina_atual == "Etiquetas",
        )

        item_menu_link(
            "⚙️ Opções auxiliares",
            "produtos_opcoes",
            ativo=st.session_state.pagina_atual == "Opções auxiliares de produtos",
            extra_params="&categoria=grupo_produto",
        )

        item_menu_link(
            "🔗 Equivalências técnicas",
            "equivalencias_tecnicas",
            ativo=st.session_state.pagina_atual == "Equivalências técnicas",
        )

    # ─────────────────────────────────────────
    # PRÓXIMOS MÓDULOS, já no mesmo padrão visual
    # ─────────────────────────────────────────
    with st.expander("🔧 Serviços", expanded=st.session_state.pagina_atual == "Serviços"):
        item_menu_link(
            "🔧 Gerenciar serviços",
            "servicos",
            ativo=st.session_state.pagina_atual == "Serviços",
        )
        item_menu_link(
            "⚙️ Opções auxiliares",
            "opcoes_auxiliares",
            ativo=False,
            extra_params="&categoria=servicos",
        )

    with st.expander(
        "📝 Orçamentos",
        expanded=st.session_state.pagina_atual == "Orçamentos",
    ):
        item_menu_link(
            "📋 Gerenciar orçamentos",
            "orcamentos",
            ativo=st.session_state.pagina_atual == "Orçamentos",
        )

    with st.expander("🛒 Vendas", expanded=False):
        st.markdown(
            '<div style="padding:7px 8px 7px 16px;font-size:14px;color:#6b7280;">Módulo será desenvolvido depois.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("🧾 Ordens de serviços", expanded=False):
        st.markdown(
            '<div style="padding:7px 8px 7px 16px;font-size:14px;color:#6b7280;">Módulo será desenvolvido depois.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("📦 Estoque", expanded=False):
        st.markdown(
            '<div style="padding:7px 8px 7px 16px;font-size:14px;color:#6b7280;">Módulo será desenvolvido depois.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("💰 Financeiro", expanded=False):
        st.markdown(
            '<div style="padding:7px 8px 7px 16px;font-size:14px;color:#6b7280;">Módulo será desenvolvido depois.</div>',
            unsafe_allow_html=True,
        )

# =========================================================
# CORPO PRINCIPAL
# =========================================================
if st.session_state.pagina_atual == "Painel":
    st.title("📊 Painel Indicador")

    col1, col2, col3 = st.columns(3)

    col1.metric("Clientes Ativos", "128")
    col2.metric("Pedidos Feitos", "42")
    col3.metric("Faturamento", "R$ 58.320,00")

elif st.session_state.pagina_atual == "Clientes":
    telaCliente()

elif st.session_state.pagina_atual == "Fornecedores":
    telaFornecedor()

elif st.session_state.pagina_atual == "Funcionários":
    telaFuncionario()

elif st.session_state.pagina_atual == "Transportadoras":
    telaTransportadora()

elif st.session_state.pagina_atual == "Opções Auxiliares":
    telaOpcaoAuxiliar()

elif st.session_state.pagina_atual == "Produtos":
    telaProdutos()

elif st.session_state.pagina_atual == "Valores de venda":
    telaProdutosValoresVenda()

elif st.session_state.pagina_atual == "Ajustar valores em massa":
    st.session_state.tela_produtos = "listar"
    st.session_state.acao_mais_produtos = "ajustar_valores"
    telaProdutos()

elif st.session_state.pagina_atual == "Etiquetas":
    telaProdutosEtiquetas()

elif st.session_state.pagina_atual == "Opções auxiliares de produtos":
    telaProdutoOpcoesAuxiliares()

elif st.session_state.pagina_atual == "Equivalências técnicas":
    telaEquivalenciasTecnicas()

elif st.session_state.pagina_atual == "Serviços":
    telaServicos()

elif st.session_state.pagina_atual == "Orçamentos":
    telaOrcamentos()

else:
    st.title(f"👥 Área de {st.session_state.pagina_atual}")
    st.info("Módulo em desenvolvimento.")
