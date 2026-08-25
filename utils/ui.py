import streamlit as st


def carregar_css_global():
    st.markdown("""
        <style>
        .erp-header-box {border-top:1px solid #dee2e6;border-bottom:1px solid #dee2e6;padding:18px 4px;margin-bottom:12px;background:transparent;}
        .erp-titulo {font-size:24px;color:#111827;font-weight:500;margin:0;}
        .erp-breadcrumb-text {text-align:right;font-size:13px;color:#6b7280;padding-top:8px;}
        .erp-breadcrumb-text a {color:#4b5563!important;text-decoration:none!important;}
        .erp-breadcrumb-text a:hover {color:#00a65a!important;text-decoration:underline!important;}
        .erp-breadcrumb-current {color:#6b7280;}
        </style>
    """, unsafe_allow_html=True)


def normalizar_modulo_para_url(modulo):
    modulo = str(modulo).strip().lower()
    mapa = {
        "clientes": "clientes",
        "fornecedores": "fornecedores",
        "funcionários": "funcionarios",
        "funcionarios": "funcionarios",
        "transportadoras": "transportadoras",
        "produtos": "produtos",
        "serviços": "servicos",
        "servicos": "servicos",
        "orçamentos": "orcamentos",
        "orcamentos": "orcamentos",
        "vendas": "vendas",
        "ordens de serviços": "ordens_servicos",
        "ordens de servicos": "ordens_servicos",
    }
    return mapa.get(modulo, modulo)


def cabecalho(titulo, modulo, tela_atual, funcao_mudar_tela=None):
    carregar_css_global()
    tela_limpa = str(tela_atual).strip().lower()
    if "cadastrar" in tela_limpa or "adicionar" in tela_limpa:
        nome_filho = "Adicionar"
    elif "editar" in tela_limpa:
        nome_filho = "Editar"
    elif "visualizar" in tela_limpa:
        nome_filho = "Visualizar"
    elif "busca" in tela_limpa:
        nome_filho = "Busca avançada"
    elif "excluir" in tela_limpa:
        nome_filho = "Excluir"
    else:
        nome_filho = "Listar"

    modulo_param = normalizar_modulo_para_url(modulo)
    st.markdown('<div class="erp-header-box">', unsafe_allow_html=True)
    col_titulo, col_breadcrumb = st.columns([1.5, 2.5])
    with col_titulo:
        st.markdown(f'<div class="erp-titulo">{titulo}</div>', unsafe_allow_html=True)
    with col_breadcrumb:
        st.markdown(f"""
            <div class="erp-breadcrumb-text">
                <a href="?go_to=painel" target="_self">🏠 Início</a>
                &nbsp;&gt;&nbsp;
                <a href="?go_to={modulo_param}" target="_self">{modulo}</a>
                &nbsp;&gt;&nbsp;
                <span class="erp-breadcrumb-current">{nome_filho}</span>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
