import html
import pandas as pd
import streamlit as st

from utils.ui import cabecalho
from utils.api_client import (
    get_transportadoras,
    criar_transportadora,
    atualizar_transportadora,
    deletar_transportadora,
)


def carregar_css_transportadoras():
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

        div[data-testid="stButton"] button p {
            margin: 0 !important;
            padding: 0 !important;
            white-space: nowrap !important;
            line-height: 1 !important;
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

        .erp-form-page-title {
            font-size: 24px;
            font-weight: 500;
            color: #111827;
            margin: 6px 0 18px 0;
        }

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

        .erp-yellow-info {
            background-color: #fff3cd;
            border: 1px solid #ffe69c;
            color: #856404;
            padding: 11px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin: 8px 0 12px 0;
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

        .erp-form-footer-spacer {
            height: 10px;
            border-top: 1px solid #e5e7eb;
            margin-top: 18px;
            margin-bottom: 8px;
        }

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

        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #2563eb !important;
            background-color: #2563eb !important;
            border: 1px solid #2563eb !important;
            color: #ffffff !important;
        }

        div[data-testid="stFormSubmitButton"] button[kind="secondary"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #374151 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def texto_seguro(valor):
    if valor is None:
        return ""
    return html.escape(str(valor))


def valor_str(item, campo):
    valor = item.get(campo, "")
    if valor is None:
        return ""
    return str(valor)


def item_ativo(valor):
    valor = str(valor).strip().lower()
    return valor in ["ativo", "true", "1", "sim", "active"]


def buscar_transportadoras_api():
    try:
        resp = get_transportadoras()

        if resp is not None and resp.status_code == 200:
            return resp.json()

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar transportadoras. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


def buscar_transportadora_por_id(id_transportadora):
    transportadoras = buscar_transportadoras_api()

    for item in transportadoras:
        if int(item.get("id", 0)) == int(id_transportadora):
            return item

    return {}


def montar_payload_transportadora(
    tipo,
    situacao,
    nome,
    documento,
    razao_social,
    inscricao_estadual,
    inscricao_municipal,
    responsavel,
    email,
    telefone,
    celular,
    cep,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade_uf,
    observacoes,
):
    return {
        "tipo": str(tipo),
        "situacao": str(situacao),
        "nome": str(nome).strip(),
        "documento": str(documento).strip() if str(documento).strip() else None,
        "razao_social": str(razao_social).strip() if str(razao_social).strip() else None,
        "inscricao_estadual": str(inscricao_estadual).strip() if str(inscricao_estadual).strip() else None,
        "inscricao_municipal": str(inscricao_municipal).strip() if str(inscricao_municipal).strip() else None,
        "responsavel": str(responsavel).strip() if str(responsavel).strip() else None,
        "email": str(email).strip() if str(email).strip() else None,
        "telefone": str(telefone).strip() if str(telefone).strip() else None,
        "celular": str(celular).strip() if str(celular).strip() else None,
        "cep": str(cep).strip() if str(cep).strip() else None,
        "logradouro": str(logradouro).strip() if str(logradouro).strip() else None,
        "numero": str(numero).strip() if str(numero).strip() else None,
        "complemento": str(complemento).strip() if str(complemento).strip() else None,
        "bairro": str(bairro).strip() if str(bairro).strip() else None,
        "cidade_uf": str(cidade_uf).strip() if str(cidade_uf).strip() else None,
        "observacoes": str(observacoes).strip() if str(observacoes).strip() else None,
    }


def renderizar_tabela_transportadoras(df):
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

        .erp-action-edit {
            background: #2f855a;
            color: #ffffff !important;
            border: 1px solid #276749;
        }

        .erp-action-delete {
            background: #ef4444;
            color: #ffffff !important;
            border: 1px solid #dc2626;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    h0, h1, h2, h3, h4, h5 = st.columns([0.45, 2.7, 2.25, 1.8, 1.0, 1.15])

    with h0:
        st.markdown('<div class="erp-list-header">☐</div>', unsafe_allow_html=True)
    with h1:
        st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
    with h2:
        st.markdown('<div class="erp-list-header">Documento</div>', unsafe_allow_html=True)
    with h3:
        st.markdown('<div class="erp-list-header">Telefone</div>', unsafe_allow_html=True)
    with h4:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Situação</div>', unsafe_allow_html=True)
    with h5:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

    for index, row in df.reset_index(drop=True).iterrows():
        transportadora_id = int(row.get("id", 0))

        nome = texto_seguro(row.get("nome", ""))
        tipo = texto_seguro(row.get("tipo", ""))
        documento = texto_seguro(row.get("documento", ""))
        telefone = texto_seguro(row.get("telefone", "") or row.get("celular", ""))

        ativo = item_ativo(row.get("situacao", "Ativo"))
        status = "✓" if ativo else "×"
        status_class = "erp-status-ok" if ativo else "erp-status-no"

        cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

        c0, c1, c2, c3, c4, c5 = st.columns([0.45, 2.7, 2.25, 1.8, 1.0, 1.15])

        with c0:
            st.markdown(f'<div class="{cell_class}">☐</div>', unsafe_allow_html=True)

        with c1:
            subtitulo = f'<span class="erp-list-small">({tipo})</span>' if tipo else ""
            st.markdown(
                f'<div class="{cell_class}"><span><span class="erp-list-name">{nome}</span>{subtitulo}</span></div>',
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(f'<div class="{cell_class}">{documento}</div>', unsafe_allow_html=True)

        with c3:
            st.markdown(f'<div class="{cell_class}">{telefone}</div>', unsafe_allow_html=True)

        with c4:
            st.markdown(f'<div class="{cell_class} {status_class}">{status}</div>', unsafe_allow_html=True)

        with c5:
            st.markdown(
                f"""
                <div class="erp-action-links">
                    <a class="erp-action-link erp-action-view" href="?go_to=transportadoras&acao_transportadora=visualizar&id_transportadora={transportadora_id}" target="_self" title="Visualizar">🔍</a>
                    <a class="erp-action-link erp-action-edit" href="?go_to=transportadoras&acao_transportadora=editar&id_transportadora={transportadora_id}" target="_self" title="Editar">✎</a>
                    <a class="erp-action-link erp-action-delete" href="?go_to=transportadoras&acao_transportadora=excluir&id_transportadora={transportadora_id}&nome_transportadora={texto_seguro(row.get("nome", ""))}" target="_self" title="Excluir">×</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def renderizar_confirmacao_exclusao_transportadora(mudar_tela):
    transportadora_id = st.session_state.get("confirmar_exclusao_transportadora")
    transportadora_nome = st.session_state.get("confirmar_exclusao_transportadora_nome", "")

    if not transportadora_id:
        return

    nome_exibicao = texto_seguro(transportadora_nome) if transportadora_nome else f"ID {transportadora_id}"

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
        </style>

        <div class="erp-delete-overlay">
            <div class="erp-delete-modal">
                <div class="erp-delete-body">
                    <div class="erp-delete-icon">▥</div>
                    <div class="erp-delete-message">
                        Deseja remover a transportadora <span class="erp-delete-name">{nome_exibicao}</span>?
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_espaco, col_nao, col_sim = st.columns([7.4, 1.1, 1.1])

    with col_nao:
        if st.button("Não", key="cancelar_exclusao_transportadora", use_container_width=True):
            st.session_state.confirmar_exclusao_transportadora = None
            st.session_state.confirmar_exclusao_transportadora_nome = ""
            st.rerun()

    with col_sim:
        if st.button("Sim", type="primary", key="confirmar_exclusao_transportadora_btn", use_container_width=True):
            try:
                resp = deletar_transportadora(transportadora_id)

                if resp is not None and resp.status_code in [200, 204]:
                    st.toast("✅ Transportadora excluída com sucesso!")
                    st.session_state.confirmar_exclusao_transportadora = None
                    st.session_state.confirmar_exclusao_transportadora_nome = ""
                    mudar_tela("listar")
                    st.rerun()
                else:
                    status = resp.status_code if resp is not None else "sem resposta"
                    st.error(f"Não foi possível excluir esta transportadora. Status: {status}")

            except Exception as erro:
                st.error(f"Erro ao excluir transportadora: {erro}")


def telaTransportadora():
    carregar_css_transportadoras()

    if "tela_atual_transportadoras" not in st.session_state:
        st.session_state.tela_atual_transportadoras = "listar"

    if "id_transportadora_editar" not in st.session_state:
        st.session_state.id_transportadora_editar = None

    if "transportadoras_filtros_avancados" not in st.session_state:
        st.session_state.transportadoras_filtros_avancados = {}

    if "confirmar_exclusao_transportadora" not in st.session_state:
        st.session_state.confirmar_exclusao_transportadora = None

    if "confirmar_exclusao_transportadora_nome" not in st.session_state:
        st.session_state.confirmar_exclusao_transportadora_nome = ""

    def mudar_tela(tela, id_transportadora=None):
        st.query_params.clear()
        st.session_state.tela_atual_transportadoras = tela
        st.session_state.id_transportadora_editar = id_transportadora

    params = st.query_params

    if "acao_transportadora" in params and "id_transportadora" in params:
        acao = params["acao_transportadora"]
        id_param = params["id_transportadora"]

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
            nome_param = params.get("nome_transportadora", "")

            if isinstance(nome_param, (list, tuple)):
                nome_param = nome_param[0]

            st.session_state.confirmar_exclusao_transportadora = id_alvo
            st.session_state.confirmar_exclusao_transportadora_nome = str(nome_param)
            mudar_tela("listar")
            st.rerun()

    tela_atual = st.session_state.tela_atual_transportadoras

    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
        "busca": "Busca Avançada",
    }.get(tela_atual, "Listar")

    cabecalho(titulo="🚚 Transportadoras", modulo="Transportadoras", tela_atual=tela_nome)

    if tela_atual == "listar":
        col_add, col_view, col_space, col_search, col_btn, col_advanced = st.columns(
            [1.25, 0.35, 2.20, 2.35, 0.35, 1.35]
        )

        with col_add:
            if st.button("Adicionar +", type="primary", use_container_width=True):
                mudar_tela("adicionar")
                st.rerun()

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

        transportadoras = buscar_transportadoras_api()

        if not transportadoras:
            st.info("Nenhuma transportadora cadastrada no banco de dados ainda. Clique em 'Adicionar +' para cadastrar a primeira!")
            return

        df = pd.DataFrame(transportadoras).fillna("")

        if busca_texto and "nome" in df.columns:
            df = df[df["nome"].astype(str).str.lower().str.contains(busca_texto.lower(), na=False)]

        filtros = st.session_state.transportadoras_filtros_avancados

        if filtros:
            if filtros.get("situacao") and filtros["situacao"] != "Todos" and "situacao" in df.columns:
                df = df[df["situacao"].astype(str) == filtros["situacao"]]
            if filtros.get("nome") and "nome" in df.columns:
                termo = filtros["nome"].lower()
                df = df[df["nome"].astype(str).str.lower().str.contains(termo, na=False)]

        if df.empty:
            st.warning("Nenhuma transportadora encontrada com os filtros aplicados.")
            return

        renderizar_confirmacao_exclusao_transportadora(mudar_tela)
        renderizar_tabela_transportadoras(df)

    elif tela_atual == "busca":
        col_add, col_view, col_space, col_search, col_btn, col_advanced = st.columns(
            [1.25, 0.35, 2.20, 2.35, 0.35, 1.35]
        )

        with col_add:
            if st.button("Adicionar +", type="primary", use_container_width=True):
                mudar_tela("adicionar")
                st.rerun()

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

        st.markdown('<div class="erp-section-title-clean">🔍 Filtros Avançados de Transportadoras</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([1.8, 2.2])
        with col1:
            situacao = st.selectbox("Situação", ["Todos", "Ativo", "Inativo"])
        with col2:
            nome = st.text_input("Nome")

        c_buscar, c_limpar, _ = st.columns([1.0, 1.0, 8.0])
        with c_buscar:
            buscar = st.button("Buscar", type="primary", use_container_width=True)
        with c_limpar:
            limpar = st.button("Limpar", use_container_width=True)

        if buscar:
            st.session_state.transportadoras_filtros_avancados = {
                "situacao": situacao,
                "nome": nome,
            }
            mudar_tela("listar")
            st.rerun()

        if limpar:
            st.session_state.transportadoras_filtros_avancados = {}
            mudar_tela("listar")
            st.rerun()

    elif tela_atual in ["adicionar", "editar", "visualizar"]:
        modo = tela_atual
        is_visualizar = modo == "visualizar"
        transportadora_atual = {}

        if modo in ["editar", "visualizar"]:
            transportadora_atual = buscar_transportadora_por_id(st.session_state.id_transportadora_editar)
            if not transportadora_atual:
                st.error("Transportadora não encontrada.")
                if st.button("⬅️ Voltar"):
                    mudar_tela("listar")
                    st.rerun()
                return

        titulo_tela = {
            "adicionar": "Adicionar transportadora",
            "editar": "Editar transportadora",
            "visualizar": "Visualizar transportadora",
        }.get(modo, "Transportadora")

        st.markdown(
            f'<div class="erp-form-page-title">{titulo_tela}</div>',
            unsafe_allow_html=True,
        )

        with st.form("form_transportadora"):
            st.markdown('<div class="erp-section-title-clean">✍️ Dados gerais</div>', unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1.4, 1.4, 3.2])
            with col1:
                opcoes_tipo = ["Selecione", "Pessoa Física", "Pessoa Jurídica"]
                valor_tipo = valor_str(transportadora_atual, "tipo") or "Selecione"
                index_tipo = opcoes_tipo.index(valor_tipo) if valor_tipo in opcoes_tipo else 0
                tipo = st.selectbox("Tipo de transportadora*", opcoes_tipo, index=index_tipo, disabled=is_visualizar)
            with col2:
                opcoes_situacao = ["Ativo", "Inativo"]
                valor_situacao = valor_str(transportadora_atual, "situacao") or "Ativo"
                index_situacao = opcoes_situacao.index(valor_situacao) if valor_situacao in opcoes_situacao else 0
                situacao = st.selectbox("Situação", opcoes_situacao, index=index_situacao, disabled=is_visualizar)
            with col3:
                nome = st.text_input("Nome*", value=valor_str(transportadora_atual, "nome"), disabled=is_visualizar)

            col4, col5, col6 = st.columns(3)
            with col4:
                documento = st.text_input("CPF / CNPJ", value=valor_str(transportadora_atual, "documento"), disabled=is_visualizar)
            with col5:
                razao_social = st.text_input("Razão social", value=valor_str(transportadora_atual, "razao_social"), disabled=is_visualizar)
            with col6:
                inscricao_estadual = st.text_input("Inscrição estadual", value=valor_str(transportadora_atual, "inscricao_estadual"), disabled=is_visualizar)

            col7, col8, col9 = st.columns(3)
            with col7:
                inscricao_municipal = st.text_input("Inscrição municipal", value=valor_str(transportadora_atual, "inscricao_municipal"), disabled=is_visualizar)
            with col8:
                responsavel = st.text_input("Responsável", value=valor_str(transportadora_atual, "responsavel"), disabled=is_visualizar)
            with col9:
                email = st.text_input("Email", value=valor_str(transportadora_atual, "email"), disabled=is_visualizar)

            col10, col11 = st.columns(2)
            with col10:
                telefone = st.text_input("Telefone", value=valor_str(transportadora_atual, "telefone"), disabled=is_visualizar)
            with col11:
                celular = st.text_input("Celular", value=valor_str(transportadora_atual, "celular"), disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">📍 Endereços</div>', unsafe_allow_html=True)

            col12, col13, col14 = st.columns([1.2, 3.2, 1.2])
            with col12:
                cep = st.text_input("CEP", value=valor_str(transportadora_atual, "cep"), disabled=is_visualizar, placeholder="Digite para buscar")
            with col13:
                logradouro = st.text_input("Logradouro", value=valor_str(transportadora_atual, "logradouro"), disabled=is_visualizar)
            with col14:
                numero = st.text_input("Número", value=valor_str(transportadora_atual, "numero"), disabled=is_visualizar)

            col15, col16, col17 = st.columns(3)
            with col15:
                complemento = st.text_input("Complemento", value=valor_str(transportadora_atual, "complemento"), disabled=is_visualizar)
            with col16:
                bairro = st.text_input("Bairro", value=valor_str(transportadora_atual, "bairro"), disabled=is_visualizar)
            with col17:
                cidade_uf = st.text_input("Cidade/UF", value=valor_str(transportadora_atual, "cidade_uf"), disabled=is_visualizar, placeholder="Digite para buscar")

            if not is_visualizar:
                st.markdown('<div class="erp-visual-button-dark">⊕ Inserir novo endereço</div>', unsafe_allow_html=True)

            st.markdown('<div class="erp-section-title-clean">📣 Contatos</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-soft-info">Estrutura visual preparada para múltiplos contatos. Vamos ligar em tabela própria depois.</div>', unsafe_allow_html=True)

            if not is_visualizar:
                st.markdown('<div class="erp-visual-button-dark">⊕ Inserir novo contato</div>', unsafe_allow_html=True)

            st.markdown('<div class="erp-section-title-clean">✍️ Observações</div>', unsafe_allow_html=True)
            observacoes = st.text_area(
                "Observações",
                value=valor_str(transportadora_atual, "observacoes"),
                height=120,
                label_visibility="collapsed",
                disabled=is_visualizar,
            )

            st.markdown('<div class="erp-form-footer-spacer"></div>', unsafe_allow_html=True)

            _, col_salvar, col_cancelar = st.columns([7.0, 1.4, 1.4])

            with col_salvar:
                texto_botao = "Cadastrar" if modo == "adicionar" else "Salvar" if modo == "editar" else "Visualizar"
                salvar = st.form_submit_button(texto_botao, type="primary", disabled=is_visualizar, use_container_width=True)

            with col_cancelar:
                cancelar = st.form_submit_button("Voltar" if is_visualizar else "Cancelar", type="secondary", use_container_width=True)

            if salvar and not is_visualizar:
                if tipo == "Selecione" or not str(nome).strip():
                    st.error("⚠️ Os campos Tipo de transportadora e Nome são obrigatórios.")
                    return

                payload_transportadora = montar_payload_transportadora(
                    tipo=tipo,
                    situacao=situacao,
                    nome=nome,
                    documento=documento,
                    razao_social=razao_social,
                    inscricao_estadual=inscricao_estadual,
                    inscricao_municipal=inscricao_municipal,
                    responsavel=responsavel,
                    email=email,
                    telefone=telefone,
                    celular=celular,
                    cep=cep,
                    logradouro=logradouro,
                    numero=numero,
                    complemento=complemento,
                    bairro=bairro,
                    cidade_uf=cidade_uf,
                    observacoes=observacoes,
                )

                with st.spinner("Enviando dados para o servidor..."):
                    if modo == "adicionar":
                        resposta = criar_transportadora(payload_transportadora)
                    else:
                        resposta = atualizar_transportadora(st.session_state.id_transportadora_editar, payload_transportadora)

                if resposta is not None and resposta.status_code in [200, 201, 204]:
                    st.success("✅ Transportadora salva com sucesso!")
                    mudar_tela("listar")
                    st.rerun()

                else:
                    status = resposta.status_code if resposta is not None else "sem resposta"
                    st.error(f"🔴 Erro ao salvar transportadora. Status: {status}")
                    try:
                        st.code(resposta.text)
                    except Exception:
                        pass

            if cancelar:
                mudar_tela("listar")
                st.rerun()
