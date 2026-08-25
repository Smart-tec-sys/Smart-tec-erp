import time
import html
import pandas as pd
import streamlit as st

from utils.ui import cabecalho
from utils.api_client import (
    get_opcoes_auxiliares,
    get_opcoes_auxiliares_por_categoria,
    criar_opcao_auxiliar,
    atualizar_opcao_auxiliar,
    deletar_opcao_auxiliar,
)


def carregar_css_opcoes_auxiliares():
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

        .erp-info-blue {
            background: #d9edf7;
            border: 1px solid #bce8f1;
            color: #31708f;
            padding: 12px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin: 12px 0 16px 0;
        }

        .erp-list-header {
            font-weight: 700;
            font-size: 14px;
            color: #111827;
            background: #ffffff;
            border-top: 1px solid #d9dee3;
            border-bottom: 1px solid #d9dee3;
            padding: 10px 12px;
            min-height: 42px;
        }

        .erp-list-cell {
            font-size: 13px;
            color: #111827;
            padding: 10px 12px;
            min-height: 50px;
            border-bottom: 1px solid #d9dee3;
            display: flex;
            align-items: center;
        }

        .erp-list-cell-alt {
            background: #f3f4f6;
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
            min-height: 50px;
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

        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #2563eb !important;
            border: 1px solid #2563eb !important;
            color: #ffffff !important;
        }

        div[data-testid="stFormSubmitButton"] button[kind="secondary"] {
            background: #ffffff !important;
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


def valor_str(registro, campo):
    valor = registro.get(campo, "")
    if valor is None:
        return ""
    return str(valor)


def ativo(valor):
    valor = str(valor).strip().lower()
    return valor in ["ativo", "true", "1", "sim", "active"]


def buscar_opcoes_api():
    try:
        resp = get_opcoes_auxiliares()

        if resp is not None and resp.status_code == 200:
            return resp.json()

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar opções auxiliares. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


def buscar_opcoes_por_categoria_api(categoria):
    try:
        resp = get_opcoes_auxiliares_por_categoria(categoria)

        if resp is not None and resp.status_code == 200:
            return resp.json()

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar opções da categoria {categoria}. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


def buscar_opcao_por_id(id_opcao):
    opcoes = buscar_opcoes_api()

    for opcao in opcoes:
        if int(opcao.get("id", 0)) == int(id_opcao):
            return opcao

    return {}


def montar_payload_opcao(categoria, nome, descricao, tipo_campo, obrigatorio, situacao, ordem):
    return {
        "categoria": str(categoria).strip(),
        "nome": str(nome).strip(),
        "descricao": str(descricao).strip() if str(descricao).strip() else None,
        "tipo_campo": str(tipo_campo).strip() if str(tipo_campo).strip() else None,
        "obrigatorio": str(obrigatorio).strip() if str(obrigatorio).strip() else "Não",
        "situacao": str(situacao).strip() if str(situacao).strip() else "Ativo",
        "ordem": int(ordem or 0),
    }


def dados_categoria(categoria):
    mapa = {
        "tipo_contato": {
            "titulo": "Tipos de contatos",
            "singular": "tipo de contato",
            "icone": "📣",
            "info": "Durante o cadastro de clientes, fornecedores e transportadoras é possível informar o tipo de contato ao qual eles pertencem.",
            "breadcrumb": "Tipos de contatos",
        },
        "tipo_endereco": {
            "titulo": "Tipos de endereços",
            "singular": "tipo de endereço",
            "icone": "📍",
            "info": "Durante o cadastro de clientes, fornecedores e transportadoras é possível informar o tipo de endereço ao qual eles pertencem.",
            "breadcrumb": "Tipos de endereços",
        },
        "campo_extra": {
            "titulo": "Campos extras",
            "singular": "campo extra",
            "icone": "📋",
            "info": "Durante o cadastro de clientes, é possível vincular campos extras personalizados.",
            "breadcrumb": "Campos extras",
        },
    }

    return mapa.get(categoria, mapa["tipo_contato"])


def renderizar_tabela_opcoes(df, categoria):
    meta = dados_categoria(categoria)

    if categoria == "campo_extra":
        h1, h2, h3, h4, h5 = st.columns([2.8, 1.2, 1.2, 1.0, 1.0])

        with h1:
            st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
        with h2:
            st.markdown('<div class="erp-list-header">Tipo</div>', unsafe_allow_html=True)
        with h3:
            st.markdown('<div class="erp-list-header">Obrigatório</div>', unsafe_allow_html=True)
        with h4:
            st.markdown('<div class="erp-list-header" style="text-align:center;">Situação</div>', unsafe_allow_html=True)
        with h5:
            st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

        for index, row in df.reset_index(drop=True).iterrows():
            opcao_id = int(row.get("id", 0))
            nome = texto_seguro(row.get("nome", ""))
            tipo_campo = texto_seguro(row.get("tipo_campo", ""))
            obrigatorio = texto_seguro(row.get("obrigatorio", "Não"))
            status = "✓" if ativo(row.get("situacao", "Ativo")) else "×"
            status_class = "erp-status-ok" if ativo(row.get("situacao", "Ativo")) else "erp-status-no"
            cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

            c1, c2, c3, c4, c5 = st.columns([2.8, 1.2, 1.2, 1.0, 1.0])

            with c1:
                st.markdown(f'<div class="{cell_class}">{nome}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="{cell_class}">{tipo_campo}</div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="{cell_class}">{obrigatorio}</div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="{cell_class} {status_class}">{status}</div>', unsafe_allow_html=True)
            with c5:
                st.markdown(
                    f"""
                    <div class="erp-action-links">
                        <a class="erp-action-link erp-action-view" href="?go_to=opcoes_auxiliares&categoria={categoria}&acao_opcao=visualizar&id_opcao={opcao_id}" target="_self" title="Visualizar">🔍</a>
                        <a class="erp-action-link erp-action-edit" href="?go_to=opcoes_auxiliares&categoria={categoria}&acao_opcao=editar&id_opcao={opcao_id}" target="_self" title="Editar">✎</a>
                        <a class="erp-action-link erp-action-delete" href="?go_to=opcoes_auxiliares&categoria={categoria}&acao_opcao=excluir&id_opcao={opcao_id}&nome_opcao={nome}" target="_self" title="Excluir">×</a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    else:
        h1, h2 = st.columns([5.5, 1.0])

        with h1:
            st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
        with h2:
            st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

        for index, row in df.reset_index(drop=True).iterrows():
            opcao_id = int(row.get("id", 0))
            nome = texto_seguro(row.get("nome", ""))
            cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

            c1, c2 = st.columns([5.5, 1.0])

            with c1:
                st.markdown(f'<div class="{cell_class}">{nome}</div>', unsafe_allow_html=True)

            with c2:
                st.markdown(
                    f"""
                    <div class="erp-action-links">
                        <a class="erp-action-link erp-action-view" href="?go_to=opcoes_auxiliares&categoria={categoria}&acao_opcao=visualizar&id_opcao={opcao_id}" target="_self" title="Visualizar">🔍</a>
                        <a class="erp-action-link erp-action-edit" href="?go_to=opcoes_auxiliares&categoria={categoria}&acao_opcao=editar&id_opcao={opcao_id}" target="_self" title="Editar">✎</a>
                        <a class="erp-action-link erp-action-delete" href="?go_to=opcoes_auxiliares&categoria={categoria}&acao_opcao=excluir&id_opcao={opcao_id}&nome_opcao={nome}" target="_self" title="Excluir">×</a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def renderizar_confirmacao_exclusao_opcao(mudar_tela):
    opcao_id = st.session_state.get("confirmar_exclusao_opcao")
    opcao_nome = st.session_state.get("confirmar_exclusao_opcao_nome", "")

    if not opcao_id:
        return

    nome_exibicao = texto_seguro(opcao_nome) if opcao_nome else f"ID {opcao_id}"

    st.markdown(
        f"""
        <style>
        .erp-delete-overlay {{
            background: rgba(17, 24, 39, 0.35);
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
        }}
        </style>

        <div class="erp-delete-overlay">
            <div class="erp-delete-modal">
                <div class="erp-delete-body">
                    <div class="erp-delete-icon">▥</div>
                    <div class="erp-delete-message">
                        Deseja realmente excluir <span class="erp-delete-name">{nome_exibicao}</span>?
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_espaco, col_nao, col_sim = st.columns([7.4, 1.1, 1.1])

    with col_nao:
        if st.button("Não", key="cancelar_exclusao_opcao", use_container_width=True):
            st.session_state.confirmar_exclusao_opcao = None
            st.session_state.confirmar_exclusao_opcao_nome = ""
            st.rerun()

    with col_sim:
        if st.button("Sim", type="primary", key="confirmar_exclusao_opcao_btn", use_container_width=True):
            try:
                resp = deletar_opcao_auxiliar(opcao_id)

                if resp is not None and resp.status_code in [200, 204]:
                    st.toast("✅ Opção removida com sucesso!")
                    st.session_state.confirmar_exclusao_opcao = None
                    st.session_state.confirmar_exclusao_opcao_nome = ""
                    mudar_tela("listar")
                    st.rerun()
                else:
                    status = resp.status_code if resp is not None else "sem resposta"
                    st.error(f"Não foi possível excluir. Status: {status}")

            except Exception as erro:
                st.error(f"Erro ao excluir: {erro}")


def telaOpcaoAuxiliar():
    carregar_css_opcoes_auxiliares()

    if "tela_atual_opcoes" not in st.session_state:
        st.session_state.tela_atual_opcoes = "listar"

    if "categoria_opcoes" not in st.session_state:
        st.session_state.categoria_opcoes = "tipo_contato"

    if "id_opcao_editar" not in st.session_state:
        st.session_state.id_opcao_editar = None

    if "confirmar_exclusao_opcao" not in st.session_state:
        st.session_state.confirmar_exclusao_opcao = None

    if "confirmar_exclusao_opcao_nome" not in st.session_state:
        st.session_state.confirmar_exclusao_opcao_nome = ""

    def mudar_tela(tela, id_opcao=None):
        st.query_params.clear()
        st.session_state.tela_atual_opcoes = tela
        st.session_state.id_opcao_editar = id_opcao

    def mudar_categoria(categoria):
        st.query_params.clear()
        st.session_state.categoria_opcoes = categoria
        st.session_state.tela_atual_opcoes = "listar"
        st.session_state.id_opcao_editar = None

    params = st.query_params

    if "categoria" in params:
        categoria_param = params["categoria"]
        if isinstance(categoria_param, (list, tuple)):
            categoria_param = categoria_param[0]
        st.session_state.categoria_opcoes = categoria_param

    if "acao_opcao" in params and "id_opcao" in params:
        acao = params["acao_opcao"]
        id_param = params["id_opcao"]

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
            nome_param = params.get("nome_opcao", "")

            if isinstance(nome_param, (list, tuple)):
                nome_param = nome_param[0]

            st.session_state.confirmar_exclusao_opcao = id_alvo
            st.session_state.confirmar_exclusao_opcao_nome = str(nome_param)
            mudar_tela("listar")
            st.rerun()

    categoria = st.session_state.categoria_opcoes
    tela_atual = st.session_state.tela_atual_opcoes
    meta = dados_categoria(categoria)

    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
        "busca": "Busca",
    }.get(tela_atual, "Listar")

    cabecalho(
        titulo=f"{meta['icone']} {meta['titulo']}",
        modulo=meta["breadcrumb"],
        tela_atual=tela_nome,
    )

    if tela_atual == "listar":
        col_add, col_space, col_search, col_btn = st.columns([1.1, 4.4, 2.2, 0.35])

        with col_add:
            if st.button(
                "Adicionar +",
                type="primary",
                use_container_width=True,
                key="btn_opcoes_adicionar",
            ):
                mudar_tela("adicionar")
                st.rerun()

        with col_space:
            st.markdown("")

        with col_search:
            busca_texto = st.text_input(
                "Buscar",
                placeholder="Buscar",
                label_visibility="collapsed",
                key="input_buscar_opcoes_auxiliares",
            )

        with col_btn:
            st.button("🔍", use_container_width=True, key="btn_buscar_opcoes_auxiliares")

        st.markdown(f'<div class="erp-info-blue">{meta["info"]}</div>', unsafe_allow_html=True)

        opcoes = buscar_opcoes_por_categoria_api(categoria)

        if not opcoes:
            st.info("Nenhum registro cadastrado ainda. Clique em 'Adicionar +' para criar o primeiro.")
            return

        df = pd.DataFrame(opcoes).fillna("")

        if busca_texto and "nome" in df.columns:
            df = df[df["nome"].astype(str).str.lower().str.contains(busca_texto.lower(), na=False)]

        if df.empty:
            st.warning("Nenhum registro encontrado com os filtros aplicados.")
            return

        renderizar_confirmacao_exclusao_opcao(mudar_tela)
        renderizar_tabela_opcoes(df, categoria)

        st.caption(f"Mostrando 1 a {len(df)} de um total de {len(df)}")

    elif tela_atual in ["adicionar", "editar", "visualizar"]:
        modo = tela_atual
        is_visualizar = modo == "visualizar"
        opcao_atual = {}

        if modo in ["editar", "visualizar"]:
            opcao_atual = buscar_opcao_por_id(st.session_state.id_opcao_editar)

            if not opcao_atual:
                st.error("Registro não encontrado.")
                if st.button("⬅️ Voltar"):
                    mudar_tela("listar")
                    st.rerun()
                return

        titulo_tela = {
            "adicionar": f"Adicionar {meta['singular']}",
            "editar": f"Editar {meta['singular']}",
            "visualizar": f"Visualizar {meta['singular']}",
        }.get(modo, meta["singular"])

        st.markdown(f'<div class="erp-form-page-title">{titulo_tela}</div>', unsafe_allow_html=True)

        with st.form("form_opcao_auxiliar"):
            # Layout propositalmente simples, no padrão do GestãoClick:
            # Tipos de contato/endereço têm apenas Nome.
            # Campos extras têm Nome, Tipo e Obrigatório.
            if categoria == "campo_extra":
                col1, col2, col3 = st.columns([2.2, 1.6, 1.2])

                with col1:
                    nome = st.text_input("Nome*", value=valor_str(opcao_atual, "nome"), disabled=is_visualizar)

                with col2:
                    opcoes_tipo = ["Texto", "Número", "Data", "Lista", "Sim/Não"]
                    valor_tipo = valor_str(opcao_atual, "tipo_campo") or "Texto"
                    index_tipo = opcoes_tipo.index(valor_tipo) if valor_tipo in opcoes_tipo else 0
                    tipo_campo = st.selectbox("Tipo", opcoes_tipo, index=index_tipo, disabled=is_visualizar)

                with col3:
                    opcoes_obrigatorio = ["Não", "Sim"]
                    valor_obrigatorio = valor_str(opcao_atual, "obrigatorio") or "Não"
                    index_obrigatorio = opcoes_obrigatorio.index(valor_obrigatorio) if valor_obrigatorio in opcoes_obrigatorio else 0
                    obrigatorio = st.selectbox("Obrigatório", opcoes_obrigatorio, index=index_obrigatorio, disabled=is_visualizar)

            else:
                nome = st.text_input("Nome*", value=valor_str(opcao_atual, "nome"), disabled=is_visualizar)
                tipo_campo = ""
                obrigatorio = "Não"

            descricao = valor_str(opcao_atual, "descricao")
            situacao = valor_str(opcao_atual, "situacao") or "Ativo"
            ordem = int(opcao_atual.get("ordem") or 0)

            st.markdown('<div class="erp-form-footer-spacer"></div>', unsafe_allow_html=True)

            _, col_salvar, col_cancelar = st.columns([7.0, 1.4, 1.4])

            with col_salvar:
                texto_botao = "Cadastrar" if modo == "adicionar" else "Salvar" if modo == "editar" else "Visualizar"
                salvar = st.form_submit_button(texto_botao, type="primary", disabled=is_visualizar, use_container_width=True)

            with col_cancelar:
                cancelar = st.form_submit_button("Voltar" if is_visualizar else "Cancelar", type="secondary", use_container_width=True)

            if salvar and not is_visualizar:
                if not str(nome).strip():
                    st.error("⚠️ O campo Nome é obrigatório.")
                    return

                payload = montar_payload_opcao(
                    categoria=categoria,
                    nome=nome,
                    descricao=descricao,
                    tipo_campo=tipo_campo,
                    obrigatorio=obrigatorio,
                    situacao=situacao,
                    ordem=ordem,
                )

                with st.spinner("Enviando dados para o servidor..."):
                    if modo == "adicionar":
                        resposta = criar_opcao_auxiliar(payload)
                    else:
                        resposta = atualizar_opcao_auxiliar(st.session_state.id_opcao_editar, payload)

                if resposta is not None and resposta.status_code in [200, 201, 204]:
                    st.success("✅ Registro salvo com sucesso!")
                    time.sleep(0.4)
                    mudar_tela("listar")
                    st.rerun()
                else:
                    status = resposta.status_code if resposta is not None else "sem resposta"
                    st.error(f"🔴 Erro ao salvar. Status: {status}")
                    try:
                        st.code(resposta.text)
                    except Exception:
                        pass

            if cancelar:
                mudar_tela("listar")
                st.rerun()
