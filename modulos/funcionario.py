import html
import pandas as pd
import streamlit as st

from utils.ui import cabecalho
from utils.api_client import (
    get_funcionarios,
    criar_funcionario,
    atualizar_funcionario,
    deletar_funcionario,
)


def carregar_css_funcionarios():
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def texto_seguro(valor):
    if valor is None:
        return ""
    return html.escape(str(valor))


def valor_str(funcionario, campo):
    valor = funcionario.get(campo, "")
    if valor is None:
        return ""
    return str(valor)


def funcionario_ativo(valor):
    valor = str(valor).strip().lower()
    return valor in ["ativo", "true", "1", "sim", "active"]


def funcionario_permite_acesso(valor):
    valor = str(valor).strip().lower()
    return valor in ["sim", "true", "1", "ativo", "s"]


def buscar_funcionarios_api():
    try:
        resp = get_funcionarios()

        if resp is not None and resp.status_code == 200:
            return resp.json()

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar funcionários. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


def buscar_funcionario_por_id(id_funcionario):
    funcionarios = buscar_funcionarios_api()

    for funcionario in funcionarios:
        if int(funcionario.get("id", 0)) == int(id_funcionario):
            return funcionario

    return {}


def montar_payload_funcionario(
    nome,
    cpf,
    rg,
    data_nascimento,
    sexo,
    email,
    comissao,
    situacao,
    permite_acesso,
    observacoes,
    cargo,
    departamento,
    salario,
    telefone,
    celular1,
    celular2,
    cep,
    logradouro,
    numero,
    complemento,
    bairro,
    cidade,
    estado,
):
    return {
        "nome": str(nome).strip(),
        "cpf": str(cpf).strip() if str(cpf).strip() else None,
        "rg": str(rg).strip() if str(rg).strip() else None,
        "data_nascimento": str(data_nascimento).strip() if str(data_nascimento).strip() else None,
        "sexo": str(sexo).strip() if str(sexo).strip() and str(sexo).strip() != "Selecione" else None,
        "email": str(email).strip() if str(email).strip() else None,
        "comissao": float(comissao or 0),
        "situacao": str(situacao),
        "permite_acesso": "Sim" if permite_acesso else "Não",
        "observacoes": str(observacoes).strip() if str(observacoes).strip() else None,
        "cargo": str(cargo).strip() if str(cargo).strip() else None,
        "departamento": str(departamento).strip() if str(departamento).strip() else None,
        "salario": float(salario or 0),
        "telefone": str(telefone).strip() if str(telefone).strip() else None,
        "celular1": str(celular1).strip() if str(celular1).strip() else None,
        "celular2": str(celular2).strip() if str(celular2).strip() else None,
        "cep": str(cep).strip() if str(cep).strip() else None,
        "logradouro": str(logradouro).strip() if str(logradouro).strip() else None,
        "numero": str(numero).strip() if str(numero).strip() else None,
        "complemento": str(complemento).strip() if str(complemento).strip() else None,
        "bairro": str(bairro).strip() if str(bairro).strip() else None,
        "cidade": str(cidade).strip() if str(cidade).strip() else None,
        "estado": str(estado).strip() if str(estado).strip() else None,
    }


def menu_mais_acoes_funcionarios(opcoes):
    acao_escolhida = None

    with st.popover("Ações +", use_container_width=True):
        for opcao in opcoes:
            if st.button(opcao, use_container_width=True, key=f"acao_funcionario_{opcao}"):
                acao_escolhida = opcao

    return acao_escolhida


def renderizar_tabela_funcionarios(df):
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

    h0, h1, h2, h3, h4, h5, h6 = st.columns([0.45, 2.5, 2.2, 1.4, 1.25, 0.95, 1.15])

    with h0:
        st.markdown('<div class="erp-list-header">☐</div>', unsafe_allow_html=True)
    with h1:
        st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
    with h2:
        st.markdown('<div class="erp-list-header">E-mail</div>', unsafe_allow_html=True)
    with h3:
        st.markdown('<div class="erp-list-header">Telefone</div>', unsafe_allow_html=True)
    with h4:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Permite acesso</div>', unsafe_allow_html=True)
    with h5:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Situação</div>', unsafe_allow_html=True)
    with h6:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

    for index, row in df.reset_index(drop=True).iterrows():
        funcionario_id = int(row.get("id", 0))

        nome = texto_seguro(row.get("nome", ""))
        email = texto_seguro(row.get("email", ""))
        telefone = texto_seguro(row.get("telefone", "") or row.get("celular1", "") or row.get("celular2", ""))
        cargo = texto_seguro(row.get("cargo", ""))

        acesso = funcionario_permite_acesso(row.get("permite_acesso", "Não"))
        acesso_texto = "✓" if acesso else "×"
        acesso_class = "erp-status-ok" if acesso else "erp-status-no"

        ativo = funcionario_ativo(row.get("situacao", "Ativo"))
        status = "✓" if ativo else "×"
        status_class = "erp-status-ok" if ativo else "erp-status-no"

        cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

        c0, c1, c2, c3, c4, c5, c6 = st.columns([0.45, 2.5, 2.2, 1.4, 1.25, 0.95, 1.15])

        with c0:
            st.markdown(f'<div class="{cell_class}">☐</div>', unsafe_allow_html=True)

        with c1:
            subtitulo = f'<span class="erp-list-small">({cargo})</span>' if cargo else ""
            st.markdown(
                f'<div class="{cell_class}"><span><span class="erp-list-name">{nome}</span>{subtitulo}</span></div>',
                unsafe_allow_html=True,
            )

        with c2:
            st.markdown(f'<div class="{cell_class}">{email}</div>', unsafe_allow_html=True)

        with c3:
            st.markdown(f'<div class="{cell_class}">{telefone}</div>', unsafe_allow_html=True)

        with c4:
            st.markdown(f'<div class="{cell_class} {acesso_class}">{acesso_texto}</div>', unsafe_allow_html=True)

        with c5:
            st.markdown(f'<div class="{cell_class} {status_class}">{status}</div>', unsafe_allow_html=True)

        with c6:
            st.markdown(
                f"""
                <div class="erp-action-links">
                    <a class="erp-action-link erp-action-view" href="?go_to=funcionarios&acao_funcionario=visualizar&id_funcionario={funcionario_id}" target="_self" title="Visualizar">🔍</a>
                    <a class="erp-action-link erp-action-edit" href="?go_to=funcionarios&acao_funcionario=editar&id_funcionario={funcionario_id}" target="_self" title="Editar">✎</a>
                    <a class="erp-action-link erp-action-delete" href="?go_to=funcionarios&acao_funcionario=excluir&id_funcionario={funcionario_id}&nome_funcionario={texto_seguro(row.get("nome", ""))}" target="_self" title="Excluir">×</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def renderizar_confirmacao_exclusao_funcionario(mudar_tela):
    funcionario_id = st.session_state.get("confirmar_exclusao_funcionario")
    funcionario_nome = st.session_state.get("confirmar_exclusao_funcionario_nome", "")

    if not funcionario_id:
        return

    nome_exibicao = texto_seguro(funcionario_nome) if funcionario_nome else f"ID {funcionario_id}"

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
                        Deseja remover o funcionário <span class="erp-delete-name">{nome_exibicao}</span>?
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_espaco, col_nao, col_sim = st.columns([7.4, 1.1, 1.1])

    with col_nao:
        if st.button("Não", key="cancelar_exclusao_funcionario", use_container_width=True):
            st.session_state.confirmar_exclusao_funcionario = None
            st.session_state.confirmar_exclusao_funcionario_nome = ""
            st.rerun()

    with col_sim:
        if st.button("Sim", type="primary", key="confirmar_exclusao_funcionario_btn", use_container_width=True):
            try:
                resp = deletar_funcionario(funcionario_id)

                if resp is not None and resp.status_code in [200, 204]:
                    st.toast("✅ Funcionário excluído com sucesso!")
                    st.session_state.confirmar_exclusao_funcionario = None
                    st.session_state.confirmar_exclusao_funcionario_nome = ""
                    mudar_tela("listar")
                    st.rerun()
                else:
                    status = resp.status_code if resp is not None else "sem resposta"
                    st.error(f"Não foi possível excluir este funcionário. Status: {status}")

            except Exception as erro:
                st.error(f"Erro ao excluir funcionário: {erro}")


def telaFuncionario():
    carregar_css_funcionarios()

    st.session_state.pagina_atual = "Funcionários"

    if "tela_atual_funcionarios" not in st.session_state:
        st.session_state.tela_atual_funcionarios = "listar"

    if "id_funcionario_editar" not in st.session_state:
        st.session_state.id_funcionario_editar = None

    if "funcionarios_filtros_avancados" not in st.session_state:
        st.session_state.funcionarios_filtros_avancados = {}

    if "confirmar_exclusao_funcionario" not in st.session_state:
        st.session_state.confirmar_exclusao_funcionario = None

    if "confirmar_exclusao_funcionario_nome" not in st.session_state:
        st.session_state.confirmar_exclusao_funcionario_nome = ""

    def mudar_tela(tela, id_funcionario=None):
        st.query_params.clear()
        st.session_state.tela_atual_funcionarios = tela
        st.session_state.id_funcionario_editar = id_funcionario

    params = st.query_params

    if "acao_funcionario" in params and "id_funcionario" in params:
        acao = params["acao_funcionario"]
        id_param = params["id_funcionario"]

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
            nome_param = params.get("nome_funcionario", "")

            if isinstance(nome_param, (list, tuple)):
                nome_param = nome_param[0]

            st.session_state.confirmar_exclusao_funcionario = id_alvo
            st.session_state.confirmar_exclusao_funcionario_nome = str(nome_param)
            mudar_tela("listar")
            st.rerun()

    tela_atual = st.session_state.tela_atual_funcionarios

    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
        "busca": "Busca Avançada",
    }.get(tela_atual, "Listar")

    cabecalho(titulo="👨‍💼 Funcionários", modulo="Funcionários", tela_atual=tela_nome)

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

        funcionarios = buscar_funcionarios_api()

        if not funcionarios:
            st.info("Nenhum funcionário cadastrado no banco de dados ainda. Clique em 'Adicionar +' para cadastrar o primeiro!")
            return

        df = pd.DataFrame(funcionarios).fillna("")

        if busca_texto and "nome" in df.columns:
            df = df[df["nome"].astype(str).str.lower().str.contains(busca_texto.lower(), na=False)]

        filtros = st.session_state.funcionarios_filtros_avancados

        if filtros:
            if filtros.get("permite_acesso") and filtros["permite_acesso"] != "Todos" and "permite_acesso" in df.columns:
                esperado = filtros["permite_acesso"]
                df = df[df["permite_acesso"].astype(str) == esperado]
            if filtros.get("nome") and "nome" in df.columns:
                termo = filtros["nome"].lower()
                df = df[df["nome"].astype(str).str.lower().str.contains(termo, na=False)]

        if df.empty:
            st.warning("Nenhum funcionário encontrado com os filtros aplicados.")
            return

        renderizar_confirmacao_exclusao_funcionario(mudar_tela)
        renderizar_tabela_funcionarios(df)

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

        st.markdown('<div class="erp-section-title-clean">🔍 Filtros Avançados de Funcionários</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([1.8, 2.2])
        with col1:
            permite_acesso = st.selectbox("Permite acesso", ["Todos", "Sim", "Não"])
        with col2:
            nome = st.text_input("Nome")

        c_buscar, c_limpar, _ = st.columns([1.0, 1.0, 8.0])
        with c_buscar:
            buscar = st.button("Buscar", type="primary", use_container_width=True)
        with c_limpar:
            limpar = st.button("Limpar", use_container_width=True)

        if buscar:
            st.session_state.funcionarios_filtros_avancados = {
                "permite_acesso": permite_acesso,
                "nome": nome,
            }
            mudar_tela("listar")
            st.rerun()

        if limpar:
            st.session_state.funcionarios_filtros_avancados = {}
            mudar_tela("listar")
            st.rerun()

    elif tela_atual in ["adicionar", "editar", "visualizar"]:
        modo = tela_atual
        is_visualizar = modo == "visualizar"
        funcionario_atual = {}

        id_funcionario_form = st.session_state.id_funcionario_editar

        if modo in ["editar", "visualizar"]:
            funcionario_atual = buscar_funcionario_por_id(st.session_state.id_funcionario_editar)
            if not funcionario_atual:
                st.error("Funcionário não encontrado.")
                if st.button("⬅️ Voltar"):
                    mudar_tela("listar")
                    st.rerun()
                return

            id_funcionario_form = int(funcionario_atual.get("id", st.session_state.id_funcionario_editar))

        titulo_tela = {
            "adicionar": "Adicionar funcionário",
            "editar": "Editar funcionário",
            "visualizar": "Visualizar funcionário",
        }.get(modo, "Funcionário")

        st.markdown(
            f'<div class="erp-form-page-title">{titulo_tela}</div>',
            unsafe_allow_html=True,
        )

        if modo == "editar":
            st.caption(f"Editando funcionário ID: {st.session_state.id_funcionario_editar}")

        with st.container():
            st.markdown('<div class="erp-section-title-clean">✍️ Dados gerais</div>', unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                nome = st.text_input("Nome*", value=valor_str(funcionario_atual, "nome"), disabled=is_visualizar)
            with col2:
                cpf = st.text_input("CPF", value=valor_str(funcionario_atual, "cpf"), disabled=is_visualizar)
            with col3:
                rg = st.text_input("RG", value=valor_str(funcionario_atual, "rg"), disabled=is_visualizar)
            with col4:
                data_nascimento = st.text_input("Data de nascimento", value=valor_str(funcionario_atual, "data_nascimento"), disabled=is_visualizar)

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                opcoes_sexo = ["Selecione", "Masculino", "Feminino", "Outro"]
                valor_sexo = valor_str(funcionario_atual, "sexo") or "Selecione"
                index_sexo = opcoes_sexo.index(valor_sexo) if valor_sexo in opcoes_sexo else 0
                sexo = st.selectbox("Sexo", opcoes_sexo, index=index_sexo, disabled=is_visualizar)
            with col6:
                email = st.text_input("E-mail", value=valor_str(funcionario_atual, "email"), disabled=is_visualizar)
            with col7:
                comissao = st.number_input("Comissão(%)", min_value=0.0, max_value=100.0, value=float(funcionario_atual.get("comissao") or 0), step=0.5, disabled=is_visualizar)
            with col8:
                opcoes_situacao = ["Ativo", "Inativo", "Bloqueado"]
                valor_situacao = valor_str(funcionario_atual, "situacao") or "Ativo"
                index_situacao = opcoes_situacao.index(valor_situacao) if valor_situacao in opcoes_situacao else 0
                situacao = st.selectbox("Situação", opcoes_situacao, index=index_situacao, disabled=is_visualizar)

            permite_acesso = st.checkbox(
                "Permitir acesso ao sistema",
                value=funcionario_permite_acesso(funcionario_atual.get("permite_acesso", "Não")),
                disabled=is_visualizar,
            )

            col9, col10, col11 = st.columns(3)
            with col9:
                cargo = st.text_input("Cargo", value=valor_str(funcionario_atual, "cargo"), disabled=is_visualizar)
            with col10:
                departamento = st.text_input("Departamento", value=valor_str(funcionario_atual, "departamento"), disabled=is_visualizar)
            with col11:
                salario = st.number_input("Salário", min_value=0.0, value=float(funcionario_atual.get("salario") or 0), step=100.0, disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">📷 Foto</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-yellow-info">Insira uma imagem JPG, PNG ou GIF de até 5MB. Upload real será ligado em etapa própria.</div>', unsafe_allow_html=True)

            col_foto_preview, col_foto_info = st.columns([1.3, 5.7])
            with col_foto_preview:
                st.markdown('<div class="erp-placeholder-photo">👤</div>', unsafe_allow_html=True)
            with col_foto_info:
                if not is_visualizar:
                    st.markdown('<div class="erp-visual-button-dark">📁 Selecione uma foto</div>', unsafe_allow_html=True)

            st.markdown('<div class="erp-section-title-clean">📣 Contatos</div>', unsafe_allow_html=True)

            col12, col13, col14 = st.columns(3)
            with col12:
                telefone = st.text_input("Telefone fixo", value=valor_str(funcionario_atual, "telefone"), disabled=is_visualizar)
            with col13:
                celular1 = st.text_input("Celular 1", value=valor_str(funcionario_atual, "celular1"), disabled=is_visualizar)
            with col14:
                celular2 = st.text_input("Celular 2", value=valor_str(funcionario_atual, "celular2"), disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">📍 Endereço</div>', unsafe_allow_html=True)

            col15, col16 = st.columns(2)
            with col15:
                cep = st.text_input("CEP", value=valor_str(funcionario_atual, "cep"), disabled=is_visualizar)
            with col16:
                logradouro = st.text_input("Logradouro", value=valor_str(funcionario_atual, "logradouro"), disabled=is_visualizar)

            col17, col18 = st.columns(2)
            with col17:
                numero = st.text_input("Número", value=valor_str(funcionario_atual, "numero"), disabled=is_visualizar)
            with col18:
                complemento = st.text_input("Complemento", value=valor_str(funcionario_atual, "complemento"), disabled=is_visualizar)

            col19, col20, col21 = st.columns([2.0, 2.0, 0.8])
            with col19:
                bairro = st.text_input("Bairro", value=valor_str(funcionario_atual, "bairro"), disabled=is_visualizar)
            with col20:
                cidade = st.text_input("Cidade", value=valor_str(funcionario_atual, "cidade"), disabled=is_visualizar)
            with col21:
                estado = st.text_input("UF", value=valor_str(funcionario_atual, "estado"), disabled=is_visualizar, max_chars=2)

            st.markdown('<div class="erp-section-title-clean">📎 Anexos</div>', unsafe_allow_html=True)
            st.markdown('<div class="erp-yellow-info">Utilize este espaço para anexar arquivos e documentos. Tamanho máximo 5MB. Será ligado em etapa própria.</div>', unsafe_allow_html=True)

            if not is_visualizar:
                st.markdown('<div class="erp-visual-button-dark">📁 Selecionar arquivo</div>', unsafe_allow_html=True)

            st.markdown('<div class="erp-section-title-clean">✍️ Observações</div>', unsafe_allow_html=True)
            observacoes = st.text_area(
                "Observações",
                value=valor_str(funcionario_atual, "observacoes"),
                height=120,
                label_visibility="collapsed",
                disabled=is_visualizar,
                placeholder="Digite aqui observações importantes sobre o funcionário.",
            )

            st.markdown('<div class="erp-form-footer-spacer"></div>', unsafe_allow_html=True)

            _, col_salvar, col_cancelar = st.columns([7.0, 1.4, 1.4])

            with col_salvar:
                texto_botao = "Cadastrar" if modo == "adicionar" else "Salvar" if modo == "editar" else "Visualizar"
                salvar = st.button(texto_botao, type="primary", disabled=is_visualizar, use_container_width=True, key=f"btn_salvar_funcionario_{modo}")

            with col_cancelar:
                cancelar = st.button("Voltar" if is_visualizar else "Cancelar", type="secondary", use_container_width=True, key=f"btn_cancelar_funcionario_{modo}")

            if salvar and not is_visualizar:
                if not str(nome).strip():
                    st.error("⚠️ O campo Nome é obrigatório.")
                    return

                payload_funcionario = montar_payload_funcionario(
                    nome=nome,
                    cpf=cpf,
                    rg=rg,
                    data_nascimento=data_nascimento,
                    sexo=sexo,
                    email=email,
                    comissao=comissao,
                    situacao=situacao,
                    permite_acesso=permite_acesso,
                    observacoes=observacoes,
                    cargo=cargo,
                    departamento=departamento,
                    salario=salario,
                    telefone=telefone,
                    celular1=celular1,
                    celular2=celular2,
                    cep=cep,
                    logradouro=logradouro,
                    numero=numero,
                    complemento=complemento,
                    bairro=bairro,
                    cidade=cidade,
                    estado=estado,
                )

                id_funcionario_atual = id_funcionario_form

                with st.spinner("Enviando dados para o servidor..."):
                    if modo == "adicionar":
                        resposta = criar_funcionario(payload_funcionario)
                    else:
                        resposta = atualizar_funcionario(id_funcionario_atual, payload_funcionario)

                if resposta is not None and resposta.status_code in [200, 201, 204]:
                    st.toast("✅ Funcionário salvo com sucesso!")

                    st.session_state.pagina_atual = "Funcionários"
                    st.session_state.tela_atual_funcionarios = "listar"
                    st.session_state.id_funcionario_editar = None

                    st.query_params.clear()
                    st.rerun()
                else:
                    status = resposta.status_code if resposta is not None else "sem resposta"
                    st.error(f"🔴 Erro ao salvar funcionário. Status: {status}")
                    try:
                        st.code(resposta.text)
                    except Exception:
                        pass

            if cancelar:
                mudar_tela("listar")
                st.rerun()
