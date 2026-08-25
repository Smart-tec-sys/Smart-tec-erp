import time
import html
import pandas as pd
import streamlit as st

from utils.ui import cabecalho
from utils.api_client import (
    get_clientes,
    criar_cliente,
    atualizar_cliente,
    deletar_cliente,
)


# =========================================================
# CSS DO MÓDULO CLIENTES
# =========================================================
def carregar_css_clientes():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 4.6rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            max-width: 100% !important;
            width: 100% !important;
        }


        div[data-testid="stButton"] button p {
            margin: 0 !important;
            padding: 0 !important;
            white-space: nowrap !important;
            line-height: 1 !important;
        }

        div[data-testid="stButton"] button {
            min-height: 40px !important;
            height: 40px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }

        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
            color: white !important;
        }

        div[data-testid="stButton"] button[kind="primary"]:hover {
            background-color: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: white !important;
        }

        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #161616 !important;
            border-color: #161616 !important;
            color: white !important;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background-color: #2a2a2a !important;
            border-color: #2a2a2a !important;
            color: white !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            min-height: 40px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            background-color: #ffffff !important;
            border: 1px solid #cfcfcf !important;
            color: #111111 !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input::placeholder,
        textarea::placeholder {
            color: #7a7a7a !important;
            opacity: 1 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 40px !important;
            height: 40px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            background-color: #ffffff !important;
            border: 1px solid #cfcfcf !important;
            box-shadow: none !important;
            outline: none !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 40px !important;
            height: 40px !important;
            align-items: center !important;
            background-color: #ffffff !important;
            box-shadow: none !important;
        }

        div[data-testid="stPopover"] button {
            min-height: 40px !important;
            height: 40px !important;
            width: 100% !important;
            background-color: #161616 !important;
            border: 1px solid #161616 !important;
            color: #ffffff !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }

        div[data-testid="stPopover"] button:hover,
        div[data-testid="stPopover"] button:focus,
        div[data-testid="stPopover"] button:active {
            background-color: #2a2a2a !important;
            border-color: #2a2a2a !important;
            color: #ffffff !important;
            box-shadow: none !important;
            outline: none !important;
        }

        .erp-form-card {
            border: 1px solid #d9dee3;
            background: #ffffff;
            border-radius: 4px;
            margin-bottom: 18px;
            overflow: hidden;
        }

        .erp-form-title {
            background: #f8f9fa;
            border-bottom: 1px solid #d9dee3;
            padding: 12px 16px;
            font-size: 19px;
            font-weight: 500;
            color: #111827;
        }

        .erp-section-content {
            padding: 16px;
        }

        .erp-yellow-info {
            background-color: #fff3cd;
            border: 1px solid #ffe69c;
            color: #856404;
            padding: 11px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin-bottom: 8px;
        }

        .erp-soft-info {
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            color: #64748b;
            padding: 14px;
            border-radius: 6px;
            font-size: 13px;
            margin-bottom: 12px;
        }

        /* Refinamento do formulário de cadastro/edição */
        .erp-form-page-title {
            font-size: 24px;
            font-weight: 500;
            color: #111827;
            margin: 8px 0 18px 0;
        }

        .erp-form-card {
            border: 1px solid #d9dee3;
            background: #ffffff;
            border-radius: 4px;
            margin-bottom: 18px;
            overflow: hidden;
            box-shadow: none;
        }

        .erp-form-title {
            background: #f8f9fa;
            border-bottom: 1px solid #d9dee3;
            padding: 12px 16px;
            font-size: 19px;
            font-weight: 500;
            color: #111827;
        }

        .erp-section-content {
            padding: 16px 16px 6px 16px;
        }

        .erp-form-hint {
            color: #64748b;
            font-size: 12px;
            margin-top: -4px;
            margin-bottom: 8px;
        }

        .erp-form-footer {
            background: #ffffff;
            border-top: 1px solid #e5e7eb;
            padding: 14px 0 8px 0;
            margin-top: 4px;
        }

        .erp-placeholder-photo {
            width: 180px;
            height: 145px;
            background: linear-gradient(180deg, #e5e7eb, #f3f4f6);
            border: 1px solid #cbd5e1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 46px;
            margin-bottom: 10px;
        }


        /* Seções compactas do formulário */
        .erp-section-title-clean {
            background: #ffffff;
            border: 1px solid #d9dee3;
            border-radius: 4px;
            padding: 12px 16px;
            font-size: 19px;
            font-weight: 500;
            color: #111827;
            margin-top: 14px;
            margin-bottom: 14px;
        }

        .erp-section-title-clean:first-child {
            margin-top: 0;
        }

        .erp-form-page-title {
            font-size: 24px;
            font-weight: 500;
            color: #111827;
            margin: 6px 0 18px 0;
        }

        .erp-form-hint {
            color: #64748b;
            font-size: 12px;
            margin-top: 2px;
            margin-bottom: 10px;
        }

        .erp-soft-info {
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            color: #64748b;
            padding: 12px 14px;
            border-radius: 6px;
            font-size: 13px;
            margin: 8px 0 12px 0;
        }

        .erp-yellow-info {
            background-color: #fff3cd;
            border: 1px solid #ffe69c;
            color: #856404;
            padding: 11px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin: 8px 0 12px 0;
        }

        .erp-placeholder-photo {
            width: 150px;
            height: 125px;
            background: linear-gradient(180deg, #e5e7eb, #f3f4f6);
            border: 1px solid #cbd5e1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 42px;
            margin-bottom: 8px;
        }

        .erp-visual-button-dark {
            display: inline-flex;
            align-items: center;
            height: 38px;
            padding: 0 14px;
            background: #161616;
            color: #ffffff;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
        }

        .erp-visual-button-light {
            display: inline-flex;
            align-items: center;
            height: 38px;
            padding: 0 14px;
            background: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
        }

        .erp-form-footer-spacer {
            height: 10px;
            border-top: 1px solid #e5e7eb;
            margin-top: 18px;
            margin-bottom: 8px;
        }

        /* Botões finais do formulário */
        div[data-testid="stFormSubmitButton"] {
            width: 100% !important;
        }

        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            min-height: 38px !important;
            height: 38px !important;
            padding: 0 18px !important;
            border-radius: 5px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            white-space: nowrap !important;
            line-height: 1 !important;
            box-shadow: none !important;
        }

        div[data-testid="stFormSubmitButton"] p {
            margin: 0 !important;
            padding: 0 !important;
            white-space: nowrap !important;
            line-height: 1 !important;
        }

        /* Botão principal: Cadastrar / Salvar */
        div[data-testid="stFormSubmitButton"] button[data-testid*="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #2563eb !important;
            background-color: #2563eb !important;
            border: 1px solid #2563eb !important;
            color: #ffffff !important;
        }

        div[data-testid="stFormSubmitButton"] button[data-testid*="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #1d4ed8 !important;
            background-color: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: #ffffff !important;
        }

        /* Botão secundário: Cancelar / Voltar */
        div[data-testid="stFormSubmitButton"] button[data-testid*="secondary"],
        div[data-testid="stFormSubmitButton"] button[kind="secondary"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #374151 !important;
        }

        div[data-testid="stFormSubmitButton"] button[data-testid*="secondary"]:hover,
        div[data-testid="stFormSubmitButton"] button[kind="secondary"]:hover {
            background: #f9fafb !important;
            background-color: #f9fafb !important;
            border-color: #9ca3af !important;
            color: #111827 !important;
        }

        /* Botão cancelar explicitamente neutro, caso o Streamlit mude o data-testid */
        .erp-cancelar-form + div button,
        .erp-cancelar-form + div div button {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #374151 !important;
        }

        .erp-cancelar-form + div button:hover,
        .erp-cancelar-form + div div button:hover {
            background: #f9fafb !important;
            background-color: #f9fafb !important;
            border-color: #9ca3af !important;
            color: #111827 !important;
        }


        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def texto_seguro(valor):
    if valor is None:
        return ""
    return html.escape(str(valor))


def valor_str(cliente, campo):
    valor = cliente.get(campo, "")
    if valor is None:
        return ""
    return str(valor)


def cliente_ativo(valor):
    valor = str(valor).strip().lower()
    return valor in ["ativo", "true", "1", "sim", "active"]


def buscar_clientes_api():
    try:
        resp = get_clientes()

        if resp is not None and resp.status_code == 200:
            return resp.json()

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar clientes. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


def buscar_cliente_por_id(id_cliente):
    clientes = buscar_clientes_api()

    for cliente in clientes:
        if int(cliente.get("id", 0)) == int(id_cliente):
            return cliente

    return {}


def montar_payload_cliente(
    tipo,
    situacao,
    nome,
    email,
    telefone_comercial,
    telefone_celular,
    documento,
    site,
    vendedor_responsavel,
    cep,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
    limite_credito,
    permitir_exceder,
    observacoes,
):
    return {
        "tipo": str(tipo),
        "situacao": str(situacao),
        "nome": str(nome).strip(),
        "email": str(email).strip() if str(email).strip() else None,
        "telefone_comercial": str(telefone_comercial).strip() if str(telefone_comercial).strip() else None,
        "telefone_celular": str(telefone_celular).strip() if str(telefone_celular).strip() else None,
        "documento": str(documento).strip() if str(documento).strip() else None,
        "site": str(site).strip() if str(site).strip() else None,
        "vendedor_responsavel": str(vendedor_responsavel).strip() if str(vendedor_responsavel).strip() else None,
        "cep": str(cep).strip() if str(cep).strip() else None,
        "logradouro": str(logradouro).strip() if str(logradouro).strip() else None,
        "numero": str(numero).strip() if str(numero).strip() else None,
        "complemento": str(complemento).strip() if str(complemento).strip() else None,
        "bairro": str(bairro).strip() if str(bairro).strip() else None,
        "cidade": str(cidade).strip() if str(cidade).strip() else None,
        "estado": str(estado).strip() if str(estado).strip() else None,
        "limite_credito": float(limite_credito or 0),
        "permitir_exceder": bool(permitir_exceder),
        "observacoes": str(observacoes).strip() if str(observacoes).strip() else None,
    }


def menu_mais_acoes(opcoes):
    acao_escolhida = None

    with st.popover("Ações +", use_container_width=True):
        for opcao in opcoes:
            if st.button(opcao, use_container_width=True, key=f"acao_cliente_{opcao}"):
                acao_escolhida = opcao

    return acao_escolhida


# =========================================================
# TABELA
# =========================================================
def renderizar_tabela_clientes(df, mudar_tela):
    """
    Tabela 100% nativa do Streamlit.
    Sem components.html, sem iframe, sem HTML com onclick.
    """
    st.markdown(
        """
        <style>
        .erp-list-header {
            font-weight: 700;
            font-size: 14px;
            color: #111827;
            background: #ffffff;
            border-top: 1px solid #d9dee3;
            border-bottom: 1px solid #d9dee3;
            padding: 10px 6px;
            min-height: 42px;
        }

        .erp-list-cell {
            font-size: 13px;
            color: #111827;
            padding: 8px 6px;
            min-height: 52px;
            border-bottom: 1px solid #d9dee3;
            display: flex;
            align-items: center;
        }

        .erp-list-cell-alt {
            background: #f3f4f6;
        }

        .erp-list-name {
            display: block;
            font-size: 13px;
            font-weight: 500;
            line-height: 1.1;
        }

        .erp-list-small {
            display: block;
            font-size: 10px;
            font-style: italic;
            color: #111827;
            margin-top: 4px;
        }

        .erp-status-ok {
            color: #00a65a;
            font-size: 22px;
            font-weight: 800;
            justify-content: center;
        }

        .erp-status-no {
            color: #ff0019;
            font-size: 22px;
            font-weight: 800;
            justify-content: center;
        }

        .erp-action-links {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            min-height: 52px;
            border-bottom: 1px solid #d9dee3;
        }

        .erp-action-link {
            width: 30px;
            height: 30px;
            min-width: 30px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            text-decoration: none !important;
            font-size: 15px;
            font-weight: 800;
            box-sizing: border-box;
            transition: 0.15s ease-in-out;
        }

        .erp-action-view {
            background: #ffffff;
            color: #111827 !important;
            border: 1px solid #d1d5db;
        }

        .erp-action-view:hover {
            background: #f8fafc;
            border-color: #94a3b8;
        }

        .erp-action-edit {
            background: #2f855a;
            color: #ffffff !important;
            border: 1px solid #276749;
        }

        .erp-action-edit:hover {
            background: #276749;
            border-color: #1f5a3d;
            color: #ffffff !important;
        }

        .erp-action-delete {
            background: #ef4444;
            color: #ffffff !important;
            border: 1px solid #dc2626;
        }

        .erp-action-delete:hover {
            background: #dc2626;
            border-color: #b91c1c;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Cabeçalho
    h0, h1, h2, h3, h4, h5, h6 = st.columns([0.45, 3.2, 1.45, 1.65, 1.05, 0.75, 1.15])

    with h0:
        st.markdown('<div class="erp-list-header">☐</div>', unsafe_allow_html=True)
    with h1:
        st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
    with h2:
        st.markdown('<div class="erp-list-header">Documento</div>', unsafe_allow_html=True)
    with h3:
        st.markdown('<div class="erp-list-header">Telefone</div>', unsafe_allow_html=True)
    with h4:
        st.markdown('<div class="erp-list-header">Cidade/UF</div>', unsafe_allow_html=True)
    with h5:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Situação</div>', unsafe_allow_html=True)
    with h6:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

    # Linhas
    for index, row in df.reset_index(drop=True).iterrows():
        cliente_id = int(row.get("id", 0))

        nome = texto_seguro(row.get("nome", ""))
        tipo = texto_seguro(row.get("tipo", ""))
        email = texto_seguro(row.get("email", ""))
        documento = texto_seguro(row.get("documento", ""))

        telefone = row.get("telefone_celular", "") or row.get("telefone_comercial", "")
        telefone = texto_seguro(telefone)

        cidade = texto_seguro(row.get("cidade", ""))
        estado = texto_seguro(row.get("estado", ""))
        cidade_uf = f"{cidade}/{estado}" if cidade and estado else cidade or estado

        ativo = cliente_ativo(row.get("situacao", "Ativo"))
        status = "✓" if ativo else "×"
        status_class = "erp-status-ok" if ativo else "erp-status-no"

        cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

        c0, c1, c2, c3, c4, c5, c6 = st.columns([0.45, 3.2, 1.45, 1.65, 1.05, 0.75, 1.15])

        with c0:
            st.markdown(f'<div class="{cell_class}">☐</div>', unsafe_allow_html=True)

        with c1:
            subtitulo = ""
            if tipo or email:
                subtitulo = f'<span class="erp-list-small">({tipo} {email})</span>'

            st.markdown(
                f'<div class="{cell_class}"><span><span class="erp-list-name">{nome}</span>{subtitulo}</span></div>',
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(f'<div class="{cell_class}">{documento}</div>', unsafe_allow_html=True)

        with c3:
            st.markdown(f'<div class="{cell_class}">{telefone}</div>', unsafe_allow_html=True)

        with c4:
            st.markdown(f'<div class="{cell_class}">{cidade_uf}</div>', unsafe_allow_html=True)

        with c5:
            st.markdown(f'<div class="{cell_class} {status_class}">{status}</div>', unsafe_allow_html=True)

        with c6:
            st.markdown(
                f"""
                <div class="erp-action-links">
                    <a class="erp-action-link erp-action-view" href="?go_to=clientes&acao_cliente=visualizar&id_cliente={cliente_id}" target="_self" title="Visualizar">🔍</a>
                    <a class="erp-action-link erp-action-edit" href="?go_to=clientes&acao_cliente=editar&id_cliente={cliente_id}" target="_self" title="Editar">✎</a>
                    <a class="erp-action-link erp-action-delete" href="?go_to=clientes&acao_cliente=excluir&id_cliente={cliente_id}&nome_cliente={texto_seguro(row.get("nome", ""))}" target="_self" title="Excluir">×</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def renderizar_confirmacao_exclusao(mudar_tela):
    """Exibe confirmação de exclusão com visual parecido com ERP comercial."""
    cliente_id = st.session_state.get("confirmar_exclusao_cliente")
    cliente_nome = st.session_state.get("confirmar_exclusao_cliente_nome", "")

    if not cliente_id:
        return

    nome_exibicao = texto_seguro(cliente_nome) if cliente_nome else f"ID {cliente_id}"

    st.markdown(
        f"""
        <style>
        .erp-delete-overlay {{
            background: rgba(17, 24, 39, 0.22);
            border-radius: 4px;
            padding: 18px;
            margin: 12px 0 16px 0;
        }}

        .erp-delete-modal {{
            max-width: 620px;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            box-shadow: 0 12px 35px rgba(0,0,0,0.22);
            overflow: hidden;
        }}

        .erp-delete-body {{
            text-align: center;
            padding: 28px 22px 24px 22px;
        }}

        .erp-delete-icon {{
            color: #ff0019;
            font-size: 58px;
            line-height: 1;
            font-weight: 900;
            margin-bottom: 16px;
        }}

        .erp-delete-message {{
            font-size: 18px;
            color: #333333;
            line-height: 1.4;
            margin-bottom: 6px;
        }}

        .erp-delete-name {{
            font-size: 18px;
            color: #111827;
            font-weight: 800;
            text-transform: uppercase;
        }}

        .erp-delete-footer {{
            border-top: 1px solid #e5e7eb;
            padding: 12px 16px;
            background: #ffffff;
        }}
        </style>

        <div class="erp-delete-overlay">
            <div class="erp-delete-modal">
                <div class="erp-delete-body">
                    <div class="erp-delete-icon">▥</div>
                    <div class="erp-delete-message">
                        Deseja remover o cliente <span class="erp-delete-name">{nome_exibicao}</span>?
                    </div>
                </div>
                <div class="erp-delete-footer"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_espaco, col_nao, col_sim = st.columns([7.4, 1.1, 1.1])

    with col_nao:
        if st.button("Não", key="cancelar_exclusao_cliente", use_container_width=True):
            st.session_state.confirmar_exclusao_cliente = None
            st.session_state.confirmar_exclusao_cliente_nome = ""
            st.rerun()

    with col_sim:
        if st.button("Sim", type="primary", key="confirmar_exclusao_cliente_btn", use_container_width=True):
            try:
                resp = deletar_cliente(cliente_id)

                if resp is not None and resp.status_code in [200, 204]:
                    st.toast("✅ Cliente excluído com sucesso!")
                    st.session_state.confirmar_exclusao_cliente = None
                    st.session_state.confirmar_exclusao_cliente_nome = ""
                    mudar_tela("listar")
                    st.rerun()
                else:
                    status = resp.status_code if resp is not None else "sem resposta"
                    st.error(f"Não foi possível excluir este cliente. Status: {status}")

            except Exception as erro:
                st.error(f"Erro ao excluir cliente: {erro}")


def telaCliente():
    carregar_css_clientes()

    if "tela_clientes" not in st.session_state:
        st.session_state.tela_clientes = "listar"
    if "id_cliente_editar" not in st.session_state:
        st.session_state.id_cliente_editar = None
    if "clientes_filtros_avancados" not in st.session_state:
        st.session_state.clientes_filtros_avancados = {}

    if "confirmar_exclusao_cliente" not in st.session_state:
        st.session_state.confirmar_exclusao_cliente = None

    if "confirmar_exclusao_cliente_nome" not in st.session_state:
        st.session_state.confirmar_exclusao_cliente_nome = ""

    def mudar_tela(tela, id_cliente=None):
        st.query_params.clear()
        st.session_state.tela_clientes = tela
        st.session_state.id_cliente_editar = id_cliente

    params = st.query_params
    if "acao_cliente" in params and "id_cliente" in params:
        acao = params["acao_cliente"]
        id_param = params["id_cliente"]

        if isinstance(acao, (list, tuple)):
            acao = acao[0]

        if isinstance(id_param, (list, tuple)):
            id_param = id_param[0]

        id_alvo = int(id_param)
        st.query_params.clear()

        if acao == "visualizar":
            mudar_tela("visualizar", id_alvo)
            st.rerun()
        elif acao == "editar":
            mudar_tela("editar", id_alvo)
            st.rerun()
        elif acao == "excluir":
            nome_param = params.get("nome_cliente", "")

            if isinstance(nome_param, (list, tuple)):
                nome_param = nome_param[0]

            st.session_state.confirmar_exclusao_cliente = id_alvo
            st.session_state.confirmar_exclusao_cliente_nome = str(nome_param)
            mudar_tela("listar")
            st.rerun()

    tela_atual = st.session_state.tela_clientes
    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
        "busca": "Busca Avançada",
    }.get(tela_atual, "Listar")

    cabecalho(titulo="👥 Clientes", modulo="Clientes", tela_atual=tela_nome)

    # =====================================================
    # LISTAGEM
    # =====================================================
    if tela_atual == "listar":
        col_add, col_more, col_view, col_space, col_search, col_btn, col_advanced = st.columns(
            [1.25, 1.70, 0.35, 1.10, 2.35, 0.35, 1.35]
        )

        with col_add:
            if st.button("Adicionar +", type="primary", use_container_width=True):
                mudar_tela("adicionar")
                st.rerun()

        with col_more:
            acao_extra = menu_mais_acoes([
                "Importar planilha",
                "Importar notas fiscais",
                "Exportar clientes",
                "Exportar e-mails",
                "Excluir selecionados",
            ])

        with col_view:
            st.button("☷", use_container_width=True)

        with col_space:
            st.markdown("")

        with col_search:
            busca_texto = st.text_input("Buscar por nome", placeholder="Buscar por nome", label_visibility="collapsed")

        with col_btn:
            st.button("🔍", use_container_width=True)

        with col_advanced:
            if st.button("🔍 Avançado", use_container_width=True):
                mudar_tela("busca")
                st.rerun()

        if acao_extra:
            st.info(f"Ação selecionada: {acao_extra}. Vamos implementar essa função em uma próxima etapa.")

        clientes = buscar_clientes_api()
        if not clientes:
            st.info("Nenhum cliente cadastrado no banco de dados ainda. Clique em '+ Adicionar' para cadastrar o primeiro!")
            return

        df = pd.DataFrame(clientes).fillna("")

        if busca_texto and "nome" in df.columns:
            df = df[df["nome"].astype(str).str.lower().str.contains(busca_texto.lower(), na=False)]

        filtros = st.session_state.clientes_filtros_avancados
        if filtros:
            if filtros.get("tipo") and filtros["tipo"] != "Todos" and "tipo" in df.columns:
                df = df[df["tipo"].astype(str) == filtros["tipo"]]
            if filtros.get("nome") and "nome" in df.columns:
                termo = filtros["nome"].lower()
                df = df[df["nome"].astype(str).str.lower().str.contains(termo, na=False)]
            if filtros.get("documento") and "documento" in df.columns:
                termo = filtros["documento"].lower()
                df = df[df["documento"].astype(str).str.lower().str.contains(termo, na=False)]
            if filtros.get("telefone") and "telefone_celular" in df.columns:
                termo = filtros["telefone"].lower()
                df = df[
                    df["telefone_celular"].astype(str).str.lower().str.contains(termo, na=False)
                    | df["telefone_comercial"].astype(str).str.lower().str.contains(termo, na=False)
                ]
            if filtros.get("email") and "email" in df.columns:
                termo = filtros["email"].lower()
                df = df[df["email"].astype(str).str.lower().str.contains(termo, na=False)]
            if filtros.get("cidade") and "cidade" in df.columns:
                termo = filtros["cidade"].lower()
                df = df[df["cidade"].astype(str).str.lower().str.contains(termo, na=False)]
            if filtros.get("estado") and "estado" in df.columns:
                termo = filtros["estado"].lower()
                df = df[df["estado"].astype(str).str.lower().str.contains(termo, na=False)]
            if filtros.get("situacao") and filtros["situacao"] != "Todos" and "situacao" in df.columns:
                df = df[df["situacao"].astype(str) == filtros["situacao"]]

        if df.empty:
            st.warning("Nenhum cliente encontrado com os filtros aplicados.")
            return

        renderizar_confirmacao_exclusao(mudar_tela)

        renderizar_tabela_clientes(df, mudar_tela)

    # =====================================================
    # BUSCA AVANÇADA
    # =====================================================
    elif tela_atual == "busca":
        col_add, col_more, col_view, col_space, col_search, col_btn, col_advanced = st.columns(
            [1.25, 1.70, 0.35, 1.10, 2.35, 0.35, 1.35]
        )

        with col_add:
            if st.button("Adicionar +", type="primary", use_container_width=True):
                mudar_tela("adicionar")
                st.rerun()

        with col_more:
            acao_extra_busca = menu_mais_acoes(["Exportar clientes", "Exportar e-mails"])

        with col_view:
            st.button("☷", use_container_width=True)

        with col_space:
            st.markdown("")

        with col_search:
            st.text_input("Buscar por nome", placeholder="Buscar por nome", label_visibility="collapsed")

        with col_btn:
            st.button("🔍", use_container_width=True)

        with col_advanced:
            if st.button("⬅️ Listar", use_container_width=True):
                mudar_tela("listar")
                st.rerun()

        if acao_extra_busca:
            st.info(f"Ação selecionada: {acao_extra_busca}. Vamos implementar essa função em uma próxima etapa.")

        st.markdown('<div class="erp-form-card"><div class="erp-form-title">🔍 Filtros Avançados de Clientes</div><div class="erp-section-content">', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([1.7, 1.0, 2.3, 1.7])
        with col1:
            tipo = st.selectbox("Tipo", ["Todos", "Física", "Jurídica"])
        with col2:
            codigo = st.text_input("Código")
        with col3:
            nome = st.text_input("Nome")
        with col4:
            documento = st.text_input("CPF/CNPJ")

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            telefone = st.text_input("Telefone/Celular")
        with col6:
            email = st.text_input("E-mail")
        with col7:
            cidade = st.text_input("Cidade")
        with col8:
            estado = st.text_input("Estado")

        col9, col10, col11, col12 = st.columns(4)
        with col9:
            vendedor = st.selectbox("Vendedor / Responsável", ["Todos", "Valmir Barbosa"])
        with col10:
            situacao = st.selectbox("Situação", ["Todos", "Ativo", "Inativo", "Bloqueado"])

        st.markdown("</div></div>", unsafe_allow_html=True)

        c_buscar, c_limpar, _ = st.columns([1.0, 1.0, 8.0])
        with c_buscar:
            buscar = st.button("✔ Buscar", type="primary", use_container_width=True)
        with c_limpar:
            limpar = st.button("✖ Limpar", use_container_width=True)

        if buscar:
            st.session_state.clientes_filtros_avancados = {
                "tipo": tipo,
                "codigo": codigo,
                "nome": nome,
                "documento": documento,
                "telefone": telefone,
                "email": email,
                "cidade": cidade,
                "estado": estado,
                "vendedor": vendedor,
                "situacao": situacao,
            }
            mudar_tela("listar")
            st.rerun()

        if limpar:
            st.session_state.clientes_filtros_avancados = {}
            mudar_tela("listar")
            st.rerun()

    # =====================================================
    # ADICIONAR / EDITAR / VISUALIZAR
    # =====================================================
    elif tela_atual in ["adicionar", "editar", "visualizar"]:
        modo = tela_atual
        is_visualizar = modo == "visualizar"
        cliente_atual = {}

        if modo in ["editar", "visualizar"]:
            cliente_atual = buscar_cliente_por_id(st.session_state.id_cliente_editar)
            if not cliente_atual:
                st.error("Cliente não encontrado.")
                if st.button("⬅️ Voltar"):
                    mudar_tela("listar")
                    st.rerun()
                return

        titulo_tela = {"adicionar": "Adicionar cliente", "editar": "Editar cliente", "visualizar": "Visualizar cliente"}.get(modo, "Cliente")
        st.markdown(
            f'<div class="erp-form-page-title">{titulo_tela}</div>',
            unsafe_allow_html=True,
        )

        with st.form("form_cliente"):
            st.markdown('<div class="erp-section-title-clean">✍️ Dados gerais</div>', unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                opcoes_tipo = ["Selecione", "Física", "Jurídica"]
                valor_tipo = valor_str(cliente_atual, "tipo") or "Selecione"
                index_tipo = opcoes_tipo.index(valor_tipo) if valor_tipo in opcoes_tipo else 0
                tipo = st.selectbox("Tipo de cliente*", opcoes_tipo, index=index_tipo, disabled=is_visualizar)
            with col2:
                opcoes_situacao = ["Ativo", "Inativo", "Bloqueado"]
                valor_situacao = valor_str(cliente_atual, "situacao") or "Ativo"
                index_situacao = opcoes_situacao.index(valor_situacao) if valor_situacao in opcoes_situacao else 0
                situacao = st.selectbox("Situação", opcoes_situacao, index=index_situacao, disabled=is_visualizar)
            with col3:
                nome = st.text_input("Nome*", value=valor_str(cliente_atual, "nome"), disabled=is_visualizar)
            with col4:
                documento = st.text_input("CPF / CNPJ", value=valor_str(cliente_atual, "documento"), disabled=is_visualizar)

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                email = st.text_input("E-mail", value=valor_str(cliente_atual, "email"), disabled=is_visualizar)
            with col6:
                telefone_comercial = st.text_input("Telefone comercial", value=valor_str(cliente_atual, "telefone_comercial"), disabled=is_visualizar)
            with col7:
                telefone_celular = st.text_input("Telefone celular", value=valor_str(cliente_atual, "telefone_celular"), disabled=is_visualizar)
            with col8:
                site = st.text_input("Site", value=valor_str(cliente_atual, "site"), disabled=is_visualizar)

            col9, col10, col11, col12 = st.columns(4)
            with col9:
                vendedor_responsavel = st.text_input("Vendedor / Responsável", value=valor_str(cliente_atual, "vendedor_responsavel") or "Valmir Barbosa", disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">📍 Endereço</div>', unsafe_allow_html=True)

            col13, col14, col15, col16 = st.columns([1.1, 2.8, 1.0, 1.8])
            with col13:
                cep = st.text_input("CEP", value=valor_str(cliente_atual, "cep"), disabled=is_visualizar)
            with col14:
                logradouro = st.text_input("Logradouro", value=valor_str(cliente_atual, "logradouro"), disabled=is_visualizar)
            with col15:
                numero = st.text_input("Número", value=valor_str(cliente_atual, "numero"), disabled=is_visualizar)
            with col16:
                complemento = st.text_input("Complemento", value=valor_str(cliente_atual, "complemento"), disabled=is_visualizar)

            col17, col18, col19 = st.columns([2.0, 2.0, 0.9])
            with col17:
                bairro = st.text_input("Bairro", value=valor_str(cliente_atual, "bairro"), disabled=is_visualizar)
            with col18:
                cidade = st.text_input("Cidade", value=valor_str(cliente_atual, "cidade"), disabled=is_visualizar)
            with col19:
                estado = st.text_input("Estado", value=valor_str(cliente_atual, "estado"), disabled=is_visualizar, max_chars=2)

            st.markdown('<div class="erp-section-title-clean">📣 Contatos</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-soft-info">Estrutura visual preparada para múltiplos contatos. Vamos ligar em tabela própria depois para não quebrar o banco atual.</div>', unsafe_allow_html=True)
            if not is_visualizar:
                st.markdown(
                    '<div class="erp-visual-button-light">➕ Inserir novo contato</div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="erp-section-title-clean">💰 Financeiro</div>', unsafe_allow_html=True)
            col20, col21, col22 = st.columns([1.5, 1.5, 5.0])
            with col20:
                limite_credito = st.number_input("Limite de crédito", min_value=0.0, value=float(cliente_atual.get("limite_credito", 0) or 0), step=100.0, disabled=is_visualizar)
            with col21:
                permitir_exceder = st.checkbox("Permitir exceder", value=bool(cliente_atual.get("permitir_exceder", False)), disabled=is_visualizar)
            st.caption("Para não limitar o crédito do cliente, deixe o limite zerado.")

            st.markdown('<div class="erp-section-title-clean">📷 Foto</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-yellow-info">Insira uma imagem JPG, PNG ou GIF de até 5MB. Upload real será ligado quando criarmos armazenamento de arquivos.</div>', unsafe_allow_html=True)

            col_foto_preview, col_foto_info = st.columns([1.4, 5.6])

            with col_foto_preview:
                st.markdown('<div class="erp-placeholder-photo">👤</div>', unsafe_allow_html=True)

            with col_foto_info:
                st.markdown('<div class="erp-form-hint">A foto ficará vinculada ao cadastro do cliente em etapa futura.</div>', unsafe_allow_html=True)

                if not is_visualizar:
                    st.markdown(
                        '<div class="erp-visual-button-dark">📁 Selecione uma foto</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div class="erp-section-title-clean">📎 Anexos</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-yellow-info">Utilize este espaço para anexar arquivos e documentos. Tamanho máximo 5MB. Será ligado em etapa própria.</div>', unsafe_allow_html=True)

            st.markdown(
                '<div class="erp-soft-info">Nenhum arquivo anexado ainda. Em uma próxima etapa criaremos uma tabela própria para documentos do cliente.</div>',
                unsafe_allow_html=True,
            )

            if not is_visualizar:
                st.markdown(
                    '<div class="erp-visual-button-dark">📁 Selecionar arquivo</div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="erp-section-title-clean">✍️ Observações</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-form-hint">Use este campo para informações importantes sobre atendimento, condições comerciais ou particularidades do cliente.</div>', unsafe_allow_html=True)
            observacoes = st.text_area(
                "Observações",
                value=valor_str(cliente_atual, "observacoes"),
                height=120,
                label_visibility="collapsed",
                disabled=is_visualizar,
                placeholder="Digite aqui observações importantes sobre o cliente.",
            )

            st.markdown('<div class="erp-form-footer-spacer"></div>', unsafe_allow_html=True)

            # Botões finais alinhados à direita, com mais espaço para o texto
            _, col_salvar, col_cancelar = st.columns([7.0, 1.4, 1.4])

            with col_salvar:
                texto_botao = "Cadastrar" if modo == "adicionar" else "Salvar" if modo == "editar" else "Visualizar"
                salvar = st.form_submit_button(texto_botao, type="primary", disabled=is_visualizar, use_container_width=True)

            with col_cancelar:
                st.markdown('<span class="erp-cancelar-form"></span>', unsafe_allow_html=True)
                cancelar = st.form_submit_button("Voltar" if is_visualizar else "Cancelar", type="secondary", use_container_width=True)

            if salvar and not is_visualizar:
                if not str(nome).strip():
                    st.error("⚠️ O campo Nome é obrigatório.")
                    return
                if tipo == "Selecione":
                    st.error("⚠️ Selecione o tipo de cliente.")
                    return

                payload_cliente = montar_payload_cliente(
                    tipo=tipo,
                    situacao=situacao,
                    nome=nome,
                    email=email,
                    telefone_comercial=telefone_comercial,
                    telefone_celular=telefone_celular,
                    documento=documento,
                    site=site,
                    vendedor_responsavel=vendedor_responsavel,
                    cep=cep,
                    logradouro=logradouro,
                    numero=numero,
                    complemento=complemento,
                    bairro=bairro,
                    cidade=cidade,
                    estado=estado,
                    limite_credito=limite_credito,
                    permitir_exceder=permitir_exceder,
                    observacoes=observacoes,
                )

                with st.spinner("Enviando dados para o servidor..."):
                    if modo == "adicionar":
                        resposta = criar_cliente(payload_cliente)
                    else:
                        resposta = atualizar_cliente(st.session_state.id_cliente_editar, payload_cliente)

                if resposta is not None and resposta.status_code in [200, 201, 204]:
                    st.success("✅ Cliente salvo com sucesso!")
                    time.sleep(0.4)
                    mudar_tela("listar")
                    st.rerun()
                else:
                    status = resposta.status_code if resposta is not None else "sem resposta"
                    st.error(f"🔴 Erro ao salvar cliente. Status: {status}")
                    try:
                        st.caption(resposta.text)
                    except Exception:
                        pass

            if cancelar:
                mudar_tela("listar")
                st.rerun()
