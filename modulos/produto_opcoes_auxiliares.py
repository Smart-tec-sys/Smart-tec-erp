import streamlit as st
import pandas as pd

from utils.api_client import (
    get_opcoes_auxiliares_por_categoria,
    criar_opcao_auxiliar,
    atualizar_opcao_auxiliar,
    deletar_opcao_auxiliar,
)
from utils.ui import cabecalho

CATEGORIAS_PRODUTOS = {
    "grupo_produto": {
        "titulo": "Grupos de produtos",
        "icone": "📦",
        "descricao": "Organize os produtos por grupos como Persianas, Cortinas, Toldos, Motores e Acessórios.",
    },
    "unidade_medida": {
        "titulo": "Unidades de medida",
        "icone": "📏",
        "descricao": "Cadastre unidades como Unidade, m², Metro linear, Peça, Kit e Rolo.",
    },
    "tipo_produto": {
        "titulo": "Tipos de produto",
        "icone": "🏷️",
        "descricao": "Defina se o item é produto simples, produto fabricado, insumo, componente ou serviço.",
    },
    "linha_produto": {
        "titulo": "Linhas",
        "icone": "🧵",
        "descricao": "Cadastre linhas de produtos, como Rolô, Romana, Painel, Vertical, Toldo e Persiana externa.",
    },
    "modelo_produto": {
        "titulo": "Modelos",
        "icone": "🧩",
        "descricao": "Cadastre modelos específicos usados nos produtos.",
    },
    "material_tecido": {
        "titulo": "Materiais / tecidos",
        "icone": "🪟",
        "descricao": "Cadastre tecidos, telas, blackout, screen, voil, alumínio e outros materiais.",
    },
    "cor_produto": {
        "titulo": "Cores",
        "icone": "🎨",
        "descricao": "Cadastre cores usadas nos produtos e componentes.",
    },
    "tipo_cortina_persiana": {
        "titulo": "Tipos de cortina/persiana",
        "icone": "🪟",
        "descricao": "Cadastre tipos como Persiana Rolô, Cortina de tecido, Persiana externa e Toldo.",
    },
    "tipo_acionamento": {
        "titulo": "Tipos de acionamento",
        "icone": "⚙️",
        "descricao": "Cadastre acionamentos como Manual, Corrente, Motorizado, Controle remoto e Automação.",
    },
    "tipo_instalacao": {
        "titulo": "Tipos de instalação",
        "icone": "🛠️",
        "descricao": "Cadastre tipos de instalação, como Parede, Teto, Embutido, Sobreposto e Externo.",
    },
    "ambiente": {
        "titulo": "Ambientes",
        "icone": "🏠",
        "descricao": "Cadastre ambientes como Sala, Quarto, Cozinha, Escritório, Sacada e Área externa.",
    },
    "tipo_componente": {
        "titulo": "Tipos de componentes",
        "icone": "🔩",
        "descricao": "Cadastre componentes como tecido, tubo, perfil, motor, controle, suporte, trilho e instalação.",
    },
    "regra_calculo": {
        "titulo": "Regras de cálculo",
        "icone": "🧮",
        "descricao": "Prepare regras para a fase 2, como m², metro linear, peça, kit, percentual e perda técnica.",
    },
}


def aplicar_css_produto_opcoes():
    st.markdown(
        """
        <style>
        .opcao-produto-info {
            background-color: #d9edf7;
            border: 1px solid #bce8f1;
            color: #31708f;
            padding: 12px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin: 8px 0 14px 0;
        }

        .produto-opcao-tabela-header {
            font-weight: 700;
            font-size: 14px;
            color: #111827;
            background: #ffffff;
            border-top: 1px solid #d9dee3;
            border-bottom: 1px solid #d9dee3;
            padding: 10px 8px;
        }

        .produto-opcao-tabela-cell {
            font-size: 13px;
            color: #111827;
            padding: 9px 8px;
            min-height: 46px;
            border-bottom: 1px solid #d9dee3;
            display: flex;
            align-items: center;
        }

        div[data-testid="stButton"] button {
            min-height: 38px !important;
            height: 38px !important;
            border-radius: 4px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
        }

        /* Campos das opções auxiliares bem visíveis */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            min-height: 40px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
            border-radius: 4px !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        textarea:focus {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb33 !important;
            outline: none !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 40px !important;
            height: 40px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
            border-radius: 4px !important;
            box-shadow: none !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb33 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
            color: #111827 !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def normalizar_resposta(resp):
    if resp is None:
        return []

    if resp.status_code == 200:
        return resp.json()

    st.error(f"Erro na API. Status: {resp.status_code}")
    try:
        st.code(resp.text)
    except Exception:
        pass

    return []


def inicializar_estado():
    st.session_state.setdefault("categoria_produto_opcoes", "grupo_produto")
    st.session_state.setdefault("tela_produto_opcoes", "listar")
    st.session_state.setdefault("id_produto_opcao_editar", None)
    st.session_state.setdefault("confirmar_exclusao_produto_opcao", None)
    st.session_state.setdefault("confirmar_exclusao_produto_opcao_nome", "")


def mudar_categoria(categoria):
    st.session_state.categoria_produto_opcoes = categoria
    st.session_state.tela_produto_opcoes = "listar"
    st.session_state.id_produto_opcao_editar = None
    st.session_state.confirmar_exclusao_produto_opcao = None
    st.session_state.confirmar_exclusao_produto_opcao_nome = ""


def mudar_tela(tela, id_opcao=None):
    st.session_state.tela_produto_opcoes = tela
    st.session_state.id_produto_opcao_editar = id_opcao
    st.session_state.confirmar_exclusao_produto_opcao = None
    st.session_state.confirmar_exclusao_produto_opcao_nome = ""


def buscar_registros_categoria(categoria):
    try:
        resp = get_opcoes_auxiliares_por_categoria(categoria)
        return normalizar_resposta(resp)
    except Exception as erro:
        st.error(f"Erro ao carregar opções: {erro}")
        return []


def buscar_opcao_por_id(categoria, opcao_id):
    registros = buscar_registros_categoria(categoria)

    for item in registros:
        if int(item.get("id", 0)) == int(opcao_id):
            return item

    return {}


def renderizar_categorias(categoria_atual):
    categorias_lista = list(CATEGORIAS_PRODUTOS.items())

    # 4 colunas para não ficar muito largo
    cols = st.columns(4)

    for i, (cat_key, cat_info) in enumerate(categorias_lista):
        with cols[i % 4]:
            tipo_botao = "primary" if categoria_atual == cat_key else "secondary"

            st.button(
                f"{cat_info['icone']} {cat_info['titulo']}",
                key=f"btn_cat_produto_{cat_key}",
                type=tipo_botao,
                use_container_width=True,
                on_click=mudar_categoria,
                args=(cat_key,),
            )


def renderizar_listagem(categoria):
    col_add, col_space, col_busca = st.columns([1.2, 4, 2])

    with col_add:
        st.button(
            "Adicionar +",
            type="primary",
            use_container_width=True,
            key="add_produto_opcao",
            on_click=mudar_tela,
            args=("adicionar", None),
        )

    with col_busca:
        busca = st.text_input("Buscar", placeholder="Buscar", label_visibility="collapsed", key="busca_produto_opcao")

    registros = buscar_registros_categoria(categoria)

    if not registros:
        st.info("Nenhum registro cadastrado ainda. Clique em 'Adicionar +' para criar o primeiro.")
        return

    df = pd.DataFrame(registros).fillna("")

    if busca and "nome" in df.columns:
        df = df[df["nome"].astype(str).str.lower().str.contains(busca.lower(), na=False)]

    if df.empty:
        st.warning("Nenhum registro encontrado.")
        return

    h1, h2, h3, h4 = st.columns([3, 4, 1.2, 1.4])
    with h1:
        st.markdown('<div class="produto-opcao-tabela-header">Nome</div>', unsafe_allow_html=True)
    with h2:
        st.markdown('<div class="produto-opcao-tabela-header">Descrição</div>', unsafe_allow_html=True)
    with h3:
        st.markdown('<div class="produto-opcao-tabela-header">Situação</div>', unsafe_allow_html=True)
    with h4:
        st.markdown('<div class="produto-opcao-tabela-header">Ações</div>', unsafe_allow_html=True)

    for _, row in df.iterrows():
        opcao_id = int(row.get("id", 0))
        nome = str(row.get("nome", ""))
        descricao = str(row.get("descricao", ""))
        situacao = str(row.get("situacao", "Ativo"))

        c1, c2, c3, c4 = st.columns([3, 4, 1.2, 1.4])

        with c1:
            st.markdown(f'<div class="produto-opcao-tabela-cell">{nome}</div>', unsafe_allow_html=True)

        with c2:
            st.markdown(f'<div class="produto-opcao-tabela-cell">{descricao}</div>', unsafe_allow_html=True)

        with c3:
            simbolo = "✓" if situacao == "Ativo" else "×"
            cor = "#00a65a" if situacao == "Ativo" else "#ff0019"
            st.markdown(
                f'<div class="produto-opcao-tabela-cell" style="font-size:20px;font-weight:800;color:{cor};justify-content:center;">{simbolo}</div>',
                unsafe_allow_html=True,
            )

        with c4:
            a1, a2, a3 = st.columns(3)

            with a1:
                st.button(
                    "🔍",
                    key=f"ver_produto_opcao_{opcao_id}",
                    use_container_width=True,
                    on_click=mudar_tela,
                    args=("visualizar", opcao_id),
                )

            with a2:
                st.button(
                    "✏️",
                    key=f"editar_produto_opcao_{opcao_id}",
                    use_container_width=True,
                    on_click=mudar_tela,
                    args=("editar", opcao_id),
                )

            with a3:
                if st.button("×", key=f"excluir_produto_opcao_{opcao_id}", use_container_width=True):
                    st.session_state.confirmar_exclusao_produto_opcao = opcao_id
                    st.session_state.confirmar_exclusao_produto_opcao_nome = nome
                    st.rerun()

    if st.session_state.get("confirmar_exclusao_produto_opcao"):
        st.warning(
            f"Deseja realmente excluir: {st.session_state.get('confirmar_exclusao_produto_opcao_nome', '')}?"
        )

        col_nao, col_sim, _ = st.columns([1, 1, 6])

        with col_nao:
            if st.button("Não", key="nao_excluir_produto_opcao", use_container_width=True):
                st.session_state.confirmar_exclusao_produto_opcao = None
                st.session_state.confirmar_exclusao_produto_opcao_nome = ""
                st.rerun()

        with col_sim:
            if st.button("Sim", key="sim_excluir_produto_opcao", type="primary", use_container_width=True):
                id_excluir = st.session_state.confirmar_exclusao_produto_opcao
                resp = deletar_opcao_auxiliar(id_excluir)

                if resp is not None and resp.status_code in [200, 204]:
                    st.success("Registro excluído com sucesso!")
                    st.session_state.confirmar_exclusao_produto_opcao = None
                    st.session_state.confirmar_exclusao_produto_opcao_nome = ""
                    st.rerun()
                else:
                    status = resp.status_code if resp is not None else "sem resposta"
                    st.error(f"Erro ao excluir. Status: {status}")


def renderizar_formulario(categoria, tela, titulo):
    opcao_atual = {}
    is_visualizar = tela == "visualizar"

    if tela in ["editar", "visualizar"]:
        opcao_atual = buscar_opcao_por_id(categoria, st.session_state.id_produto_opcao_editar)

        if not opcao_atual:
            st.error("Registro não encontrado.")
            st.button("Voltar", on_click=mudar_tela, args=("listar", None))
            return

    titulo_form = {
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
    }.get(tela, "Adicionar")

    st.subheader(f"{titulo_form} - {titulo}")

    with st.form("form_produto_opcao_auxiliar"):
        nome = st.text_input(
            "Nome*",
            value=str(opcao_atual.get("nome", "")),
            disabled=is_visualizar,
        )

        descricao = st.text_area(
            "Descrição",
            value=str(opcao_atual.get("descricao", "")),
            height=90,
            disabled=is_visualizar,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            situacao = st.selectbox(
                "Situação",
                ["Ativo", "Inativo"],
                index=0 if str(opcao_atual.get("situacao", "Ativo")) != "Inativo" else 1,
                disabled=is_visualizar,
            )

        with col2:
            obrigatorio = st.selectbox(
                "Obrigatório",
                ["Não", "Sim"],
                index=1 if str(opcao_atual.get("obrigatorio", "Não")) == "Sim" else 0,
                disabled=is_visualizar,
            )

        with col3:
            ordem = st.number_input(
                "Ordem",
                min_value=0,
                value=int(opcao_atual.get("ordem") or 0),
                step=1,
                disabled=is_visualizar,
            )

        tipo_campo_opcoes = ["Texto", "Número", "Data", "Lista", "Booleano"]
        valor_tipo_campo = str(opcao_atual.get("tipo_campo", "Texto")) or "Texto"
        index_tipo_campo = tipo_campo_opcoes.index(valor_tipo_campo) if valor_tipo_campo in tipo_campo_opcoes else 0

        tipo_campo = st.selectbox(
            "Tipo de campo",
            tipo_campo_opcoes,
            index=index_tipo_campo,
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
                "categoria": categoria,
                "nome": nome.strip(),
                "descricao": descricao.strip() if descricao else None,
                "tipo_campo": tipo_campo,
                "obrigatorio": obrigatorio,
                "situacao": situacao,
                "ordem": ordem,
            }

            if tela == "adicionar":
                resp = criar_opcao_auxiliar(payload)
            else:
                resp = atualizar_opcao_auxiliar(
                    st.session_state.id_produto_opcao_editar,
                    payload,
                )

            if resp is not None and resp.status_code in [200, 201]:
                st.success("Registro salvo com sucesso!")
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


def telaProdutoOpcoesAuxiliares():
    aplicar_css_produto_opcoes()
    inicializar_estado()

    categoria = st.session_state.categoria_produto_opcoes
    tela = st.session_state.tela_produto_opcoes

    dados_categoria = CATEGORIAS_PRODUTOS.get(categoria, CATEGORIAS_PRODUTOS["grupo_produto"])
    titulo = dados_categoria["titulo"]
    icone = dados_categoria["icone"]

    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
    }.get(tela, "Listar")

    cabecalho(
        titulo=f"{icone} {titulo}",
        modulo="Produtos / Opções auxiliares",
        tela_atual=tela_nome,
    )

    renderizar_categorias(categoria)

    st.markdown(
        f"""
        <div class="opcao-produto-info">
            {dados_categoria["descricao"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if tela == "listar":
        renderizar_listagem(categoria)

    elif tela in ["adicionar", "editar", "visualizar"]:
        renderizar_formulario(categoria, tela, titulo)
