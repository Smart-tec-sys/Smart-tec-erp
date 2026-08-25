import streamlit as st
import pandas as pd
import json

from utils.ui import cabecalho
from utils.api_client import (
    get_opcoes_auxiliares_por_categoria,
    criar_opcao_auxiliar,
    atualizar_opcao_auxiliar,
    deletar_opcao_auxiliar,
)

CATEGORIA_VALORES_VENDA = "valor_venda_produto"


def carregar_css_valores_venda():
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
            border-radius: 4px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            white-space: nowrap !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
            border-radius: 4px !important;
        }

        div[data-testid="stNumberInput"] button {
            display: none !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        textarea:focus {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb33 !important;
            outline: none !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
            border-radius: 4px !important;
        }

        .erp-info {
            background-color: #d9edf7;
            border: 1px solid #bce8f1;
            color: #31708f;
            padding: 12px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin: 8px 0 14px 0;
        }

        .erp-table-header {
            font-weight: 700;
            font-size: 14px;
            color: #111827;
            background: #ffffff;
            border-top: 1px solid #d9dee3;
            border-bottom: 1px solid #d9dee3;
            padding: 10px 8px;
        }

        .erp-table-cell {
            font-size: 13px;
            color: #111827;
            border-bottom: 1px solid #d9dee3;
            padding: 10px 8px;
            min-height: 45px;
        }

        .erp-action-links {
            display: flex;
            justify-content: center;
            gap: 6px;
        }

        .erp-action-link {
            width: 34px;
            height: 34px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none !important;
            font-size: 15px;
            font-weight: 700;
        }

        .erp-action-view {
            background: #ffffff;
            color: #111827 !important;
            border: 1px solid #d1d5db;
        }

        .erp-action-edit {
            background: #198754;
            color: #ffffff !important;
            border: 1px solid #198754;
        }

        .erp-action-delete {
            background: #dc3545;
            color: #ffffff !important;
            border: 1px solid #dc3545;
        }

        .erp-modal-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.55);
            z-index: 999990;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .erp-modal-card {
            width: min(540px, calc(100vw - 40px));
            background: #ffffff;
            border-radius: 6px;
            box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
            border: 1px solid #d1d5db;
            overflow: hidden;
        }

        .erp-modal-body {
            padding: 28px 34px 24px 34px;
        }

        .erp-modal-icon {
            text-align: center;
            color: #dc3545;
            font-size: 56px;
            line-height: 1;
            margin-bottom: 20px;
        }

        .erp-modal-text {
            text-align: center;
            font-size: 18px;
            color: #1f2937;
            line-height: 1.35;
            margin-bottom: 6px;
        }

        .erp-modal-text strong {
            font-weight: 800;
            color: #111827;
        }

        .erp-modal-footer {
            border-top: 1px solid #e5e7eb;
            background: #ffffff;
            padding: 14px 16px;
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }

        .erp-modal-btn {
            min-width: 52px;
            height: 38px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none !important;
            font-size: 14px;
            font-weight: 700;
            padding: 0 14px;
        }

        .erp-modal-btn-nao {
            background: #6c757d;
            color: #ffffff !important;
            border: 1px solid #6c757d;
        }

        .erp-modal-btn-sim {
            background: #061523;
            color: #ffffff !important;
            border: 1px solid #061523;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inicializar_estado():
    if "tela_valores_venda" not in st.session_state:
        st.session_state.tela_valores_venda = "listar"

    if "id_valor_venda_editar" not in st.session_state:
        st.session_state.id_valor_venda_editar = None

    if "confirmar_exclusao_valor_venda" not in st.session_state:
        st.session_state.confirmar_exclusao_valor_venda = None

    if "confirmar_exclusao_valor_venda_nome" not in st.session_state:
        st.session_state.confirmar_exclusao_valor_venda_nome = ""

    if "_ultima_acao_valor_venda_url_processada" not in st.session_state:
        st.session_state._ultima_acao_valor_venda_url_processada = ""

    if "_ultima_confirmacao_valor_venda_url_processada" not in st.session_state:
        st.session_state._ultima_confirmacao_valor_venda_url_processada = ""


def mudar_tela(tela, id_registro=None):
    st.session_state.tela_valores_venda = tela
    st.session_state.id_valor_venda_editar = id_registro


def texto_seguro(valor):
    import html
    return html.escape(str(valor or ""))


def normalizar_percentual(valor):
    try:
        return float(str(valor or "0").replace("%", "").replace(",", ".").strip())
    except Exception:
        return 0.0


def normalizar_lista_api(dados):
    if dados is None:
        return []

    if hasattr(dados, "json"):
        try:
            dados = dados.json()
        except Exception:
            try:
                dados = dados.text
            except Exception:
                return []

    if isinstance(dados, (bytes, bytearray)):
        try:
            dados = dados.decode("utf-8")
        except Exception:
            return []

    if isinstance(dados, str):
        texto = dados.strip()
        if not texto:
            return []
        try:
            dados = json.loads(texto)
        except Exception:
            return []

    if isinstance(dados, dict):
        for chave in ["dados", "items", "result", "results", "data"]:
            if isinstance(dados.get(chave), list):
                dados = dados.get(chave)
                break
        else:
            dados = [dados]

    if not isinstance(dados, list):
        return []

    return [item for item in dados if isinstance(item, dict)]


def buscar_valores_venda():
    try:
        dados = get_opcoes_auxiliares_por_categoria(CATEGORIA_VALORES_VENDA)
        return normalizar_lista_api(dados)
    except Exception:
        return []


def buscar_por_id(id_registro):
    for item in buscar_valores_venda():
        if int(item.get("id", 0)) == int(id_registro):
            return item
    return {}


def inserir_padrao_se_vazio():
    if buscar_valores_venda():
        return

    padroes = [
        ("Varejo", 150.0, 1),
        ("Consumidor final", 200.0, 2),
        ("Decorador", 100.0, 3),
    ]

    for nome, lucro, ordem in padroes:
        payload = {
            "categoria": CATEGORIA_VALORES_VENDA,
            "nome": nome,
            "descricao": str(lucro),
            "tipo_campo": "Número",
            "obrigatorio": "Não",
            "situacao": "Ativo",
            "ordem": ordem,
        }
        criar_opcao_auxiliar(payload)


def renderizar_confirmacao_exclusao():
    id_registro = st.session_state.get("confirmar_exclusao_valor_venda")
    nome = st.session_state.get("confirmar_exclusao_valor_venda_nome", "")

    if not id_registro:
        return

    link_nao = "?go_to=produtos_valores&confirmar_exclusao_valor_venda=nao"
    link_sim = f"?go_to=produtos_valores&confirmar_exclusao_valor_venda=sim&id_valor_venda={id_registro}"

    st.markdown(
        f"""
        <div class="erp-modal-backdrop">
            <div class="erp-modal-card">
                <div class="erp-modal-body">
                    <div class="erp-modal-icon">🗑️</div>
                    <div class="erp-modal-text">
                        Deseja realmente excluir o valor de venda <strong>{texto_seguro(nome)}</strong>?
                    </div>
                </div>
                <div class="erp-modal-footer">
                    <a class="erp-modal-btn erp-modal-btn-nao" href="{link_nao}" target="_self">Não</a>
                    <a class="erp-modal-btn erp-modal-btn-sim" href="{link_sim}" target="_self">Sim</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tratar_query_params():
    params = st.query_params

    if "confirmar_exclusao_valor_venda" in params:
        decisao = params.get("confirmar_exclusao_valor_venda", "")
        id_registro = params.get("id_valor_venda", st.session_state.get("confirmar_exclusao_valor_venda"))

        if isinstance(decisao, (list, tuple)):
            decisao = decisao[0]

        if isinstance(id_registro, (list, tuple)):
            id_registro = id_registro[0]

        chave = f"{decisao}|{id_registro}"

        if st.session_state._ultima_confirmacao_valor_venda_url_processada != chave:
            st.session_state._ultima_confirmacao_valor_venda_url_processada = chave

            if decisao == "nao":
                st.session_state.confirmar_exclusao_valor_venda = None
                st.session_state.confirmar_exclusao_valor_venda_nome = ""

            elif decisao == "sim" and id_registro:
                try:
                    resp = deletar_opcao_auxiliar(int(id_registro))

                    if resp is not None and resp.status_code in [200, 204]:
                        st.session_state.confirmar_exclusao_valor_venda = None
                        st.session_state.confirmar_exclusao_valor_venda_nome = ""
                        st.query_params.clear()
                        st.success("Valor de venda excluído com sucesso!")
                        st.rerun()
                    else:
                        status = resp.status_code if resp is not None else "sem resposta"
                        st.error(f"Não foi possível excluir. Status: {status}")
                except Exception as erro:
                    st.error(f"Erro ao excluir: {erro}")

    if "acao_valor_venda" in params and "id_valor_venda" in params:
        acao = params.get("acao_valor_venda")
        id_registro = params.get("id_valor_venda")
        nome = params.get("nome_valor_venda", "")

        if isinstance(acao, (list, tuple)):
            acao = acao[0]

        if isinstance(id_registro, (list, tuple)):
            id_registro = id_registro[0]

        if isinstance(nome, (list, tuple)):
            nome = nome[0]

        chave = f"{acao}|{id_registro}|{nome}"

        if st.session_state._ultima_acao_valor_venda_url_processada != chave:
            st.session_state._ultima_acao_valor_venda_url_processada = chave

            if acao == "visualizar":
                mudar_tela("visualizar", int(id_registro))
                st.rerun()

            elif acao == "editar":
                mudar_tela("editar", int(id_registro))
                st.rerun()

            elif acao == "excluir":
                st.session_state.confirmar_exclusao_valor_venda = int(id_registro)
                st.session_state.confirmar_exclusao_valor_venda_nome = str(nome or id_registro)
                mudar_tela("listar")
                st.rerun()


def renderizar_tabela(dados):
    if not dados:
        st.info("Nenhum valor de venda cadastrado ainda. Clique em 'Adicionar +' para criar o primeiro.")
        return

    df = pd.DataFrame(dados).fillna("")
    if "ordem" in df.columns:
        df = df.sort_values(by=["ordem", "nome"], ascending=True)

    h1, h2, h3, h4 = st.columns([3.2, 2.0, 1.2, 1.4])
    h1.markdown('<div class="erp-table-header">Nome</div>', unsafe_allow_html=True)
    h2.markdown('<div class="erp-table-header">Lucro sugerido (%)</div>', unsafe_allow_html=True)
    h3.markdown('<div class="erp-table-header">Situação</div>', unsafe_allow_html=True)
    h4.markdown('<div class="erp-table-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

    for _, row in df.iterrows():
        id_registro = int(row.get("id", 0))
        nome = str(row.get("nome", ""))
        lucro = normalizar_percentual(row.get("descricao", 0))
        situacao = str(row.get("situacao", "Ativo"))
        icone_situacao = "✓" if situacao != "Inativo" else "×"

        c1, c2, c3, c4 = st.columns([3.2, 2.0, 1.2, 1.4])
        c1.markdown(f'<div class="erp-table-cell">{texto_seguro(nome)}</div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="erp-table-cell">{lucro:.2f}%</div>'.replace(".", ","), unsafe_allow_html=True)
        c3.markdown(f'<div class="erp-table-cell" style="text-align:center;color:#00a65a;font-size:20px;font-weight:700;">{icone_situacao}</div>', unsafe_allow_html=True)

        with c4:
            nome_url = texto_seguro(nome)
            st.markdown(
                f"""
                <div class="erp-action-links">
                    <a class="erp-action-link erp-action-view" href="?go_to=produtos_valores&acao_valor_venda=visualizar&id_valor_venda={id_registro}" target="_self" title="Visualizar">🔍</a>
                    <a class="erp-action-link erp-action-edit" href="?go_to=produtos_valores&acao_valor_venda=editar&id_valor_venda={id_registro}" target="_self" title="Editar">✎</a>
                    <a class="erp-action-link erp-action-delete" href="?go_to=produtos_valores&acao_valor_venda=excluir&id_valor_venda={id_registro}&nome_valor_venda={nome_url}" target="_self" title="Excluir">×</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def renderizar_formulario():
    tela = st.session_state.tela_valores_venda
    is_visualizar = tela == "visualizar"

    registro = {}
    if tela in ["editar", "visualizar"]:
        registro = buscar_por_id(st.session_state.id_valor_venda_editar)

        if not registro:
            st.error("Registro não encontrado.")
            if st.button("Voltar"):
                mudar_tela("listar", None)
                st.rerun()
            return

    titulo = {
        "adicionar": "Adicionar valor de venda",
        "editar": "Editar valor de venda",
        "visualizar": "Visualizar valor de venda",
    }.get(tela, "Valor de venda")

    st.subheader(titulo)

    with st.form("form_valores_venda"):
        nome = st.text_input(
            "Nome *",
            value=str(registro.get("nome", "")),
            disabled=is_visualizar,
        )

        lucro = st.number_input(
            "Lucro (%) *",
            min_value=0.0,
            value=normalizar_percentual(registro.get("descricao", 0)),
            step=1.0,
            format="%.2f",
            disabled=is_visualizar,
        )

        col1, col2 = st.columns(2)

        with col1:
            situacao = st.selectbox(
                "Situação",
                ["Ativo", "Inativo"],
                index=0 if str(registro.get("situacao", "Ativo")) != "Inativo" else 1,
                disabled=is_visualizar,
            )

        with col2:
            ordem = st.number_input(
                "Ordem",
                min_value=0,
                value=int(registro.get("ordem") or 0),
                step=1,
                disabled=is_visualizar,
            )

        col_salvar, col_cancelar, _ = st.columns([1.2, 1.2, 5])

        with col_salvar:
            salvar = st.form_submit_button(
                "Cadastrar" if tela == "adicionar" else "Salvar",
                type="primary",
                disabled=is_visualizar,
                use_container_width=True,
            )

        with col_cancelar:
            cancelar = st.form_submit_button(
                "Voltar" if is_visualizar else "Cancelar",
                use_container_width=True,
            )

        if salvar and not is_visualizar:
            if not nome.strip():
                st.error("O campo Nome é obrigatório.")
                st.stop()

            payload = {
                "categoria": CATEGORIA_VALORES_VENDA,
                "nome": nome.strip(),
                "descricao": str(float(lucro or 0)),
                "tipo_campo": "Número",
                "obrigatorio": "Não",
                "situacao": situacao,
                "ordem": int(ordem or 0),
            }

            if tela == "adicionar":
                resp = criar_opcao_auxiliar(payload)
            else:
                resp = atualizar_opcao_auxiliar(st.session_state.id_valor_venda_editar, payload)

            if resp is not None and resp.status_code in [200, 201]:
                st.success("Valor de venda salvo com sucesso!")
                mudar_tela("listar", None)
                st.rerun()
            else:
                status = resp.status_code if resp is not None else "sem resposta"
                st.error(f"Erro ao salvar. Status: {status}")
                try:
                    st.code(resp.text)
                except Exception:
                    pass

        if cancelar:
            mudar_tela("listar", None)
            st.rerun()


def telaProdutosValoresVenda():
    carregar_css_valores_venda()
    inicializar_estado()
    tratar_query_params()

    tela = st.session_state.tela_valores_venda

    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
    }.get(tela, "Listar")

    cabecalho(
        titulo="💲 Valores de venda",
        modulo="Produtos",
        tela_atual=tela_nome,
    )

    if tela == "listar":
        col_add, col_seed, col_space, col_search = st.columns([1.3, 1.8, 3.8, 2.5])

        with col_add:
            if st.button("Adicionar +", type="primary", use_container_width=True):
                mudar_tela("adicionar", None)
                st.rerun()

        with col_seed:
            if st.button("⚙️ Criar padrões", use_container_width=True):
                inserir_padrao_se_vazio()
                st.success("Valores padrões verificados/criados.")
                st.rerun()

        with col_space:
            st.markdown("")

        with col_search:
            busca = st.text_input("Buscar", placeholder="Buscar", label_visibility="collapsed")

        st.markdown(
            """
            <div class="erp-info">
                Cadastre tabelas de venda usadas nos produtos, como Varejo, Consumidor final, Decorador, Revenda e Atacado.
                O campo Lucro (%) será usado para sugerir automaticamente o valor de venda no cadastro do produto.
            </div>
            """,
            unsafe_allow_html=True,
        )

        dados = buscar_valores_venda()

        if busca:
            dados = [
                d for d in dados
                if busca.lower() in str(d.get("nome", "")).lower()
            ]

        renderizar_confirmacao_exclusao()
        renderizar_tabela(dados)

    else:
        renderizar_formulario()
