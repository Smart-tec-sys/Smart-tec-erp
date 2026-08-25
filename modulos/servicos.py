# =========================================================
# SMARTTEC ERP - SERVIÇOS
# ETAPA 1 FINALIZADA
# - Listar
# - Adicionar
# - Visualizar
# - Editar
# - Excluir
# - Filtros
# - Tipos de cálculo preparados para Orçamentos/Pedidos/O.S.
# =========================================================

import streamlit as st
from datetime import datetime

try:
    from utils.ui import cabecalho
except Exception:

    def cabecalho(titulo, modulo, tela_atual, funcao_mudar_tela=None):
        st.markdown(f"## {titulo}")

TIPOS_CALCULO = ["Valor fixo", "Por peça", "Por unidade", "Por m²", "Por altura", "Por metro linear", "Por hora", "Por visita", "Por km"]
CATEGORIAS_SERVICO = ["Instalação", "Lavagem", "Manutenção", "Assistência técnica", "Reforma", "Motorização", "Visita técnica", "Mão de obra", "Custos adicionais", "Outros"]
SITUACOES = ["Ativo", "Inativo"]


def carregar_css_servicos():
    st.markdown("""
    <style>
    .block-container{padding-top:4.6rem!important;max-width:100%!important;}
    div[data-testid="stButton"] button{min-height:40px!important;height:40px!important;border-radius:4px!important;font-size:14px!important;font-weight:700!important;box-shadow:none!important;white-space:nowrap!important;}
    div[data-testid="stButton"] button[kind="primary"]{background-color:#2563eb!important;border-color:#2563eb!important;color:white!important;}
    /* Botões secundários ficam no padrão claro do Streamlit.
       Assim Visualizar/Editar/Excluir não ficam todos pretos. */
    div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,textarea{min-height:40px!important;border-radius:4px!important;background-color:#fff!important;border:1.5px solid #9ca3af!important;color:#111827!important;}
    div[data-testid="stSelectbox"] div[data-baseweb="select"]{min-height:40px!important;border-radius:4px!important;background-color:#fff!important;border:1.5px solid #9ca3af!important;color:#111827!important;}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] *{color:#111827!important;}
    .serv-section-title{background:#fff;border:1px solid #d9dee3;border-radius:4px;padding:12px 16px;font-size:19px;font-weight:500;color:#111827;margin-top:14px;margin-bottom:14px;}
    .serv-table-header{font-weight:700;font-size:14px;color:#111827;background:#fff;border-top:1px solid #d9dee3;border-bottom:1px solid #d9dee3;padding:10px 6px;min-height:42px;}
    .serv-table-cell{font-size:13px;color:#111827;padding:8px 6px;min-height:46px;border-bottom:1px solid #d9dee3;display:flex;align-items:center;}
    .serv-action-wrap{display:flex;gap:6px;align-items:center;justify-content:center;min-height:46px;border-bottom:1px solid #d9dee3;padding:5px 0;}
    .serv-btn-action{width:34px;height:34px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none!important;font-size:16px;font-weight:800;border:1px solid #d1d5db;line-height:1;}
    .serv-btn-view{background:#ffffff!important;color:#111827!important;border-color:#d1d5db!important;}
    .serv-btn-edit{background:#198754!important;color:#ffffff!important;border-color:#198754!important;}
    .serv-btn-delete{background:#dc3545!important;color:#ffffff!important;border-color:#dc3545!important;}
    .serv-btn-edit span,.serv-btn-delete span{color:#ffffff!important;}
    </style>
    """, unsafe_allow_html=True)


def moeda_br(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def gerar_codigo_servico():
    return "SRV-" + datetime.now().strftime("%y%m%d%H%M%S")


def servico_base(idx, nome, categoria, tipo_calculo, custo, venda):
    return {
        "id": idx, "codigo": f"SRV-{idx:03d}", "nome": nome, "categoria": categoria, "tipo_calculo": tipo_calculo,
        "valor_custo": float(custo or 0), "valor_venda": float(venda or 0), "comissao": 0.0, "situacao": "Ativo",
        "descricao": "", "observacao_orcamento": "", "disponivel_orcamento": "Sim", "disponivel_pedido": "Sim",
        "disponivel_os": "Sim", "atividade_servico": "", "codigo_servico": "", "codigo_tributacao": "", "codigo_nbs": "",
        "cnae": "", "iss": 0.0, "cofins": 0.0, "pis": 0.0, "csll": 0.0, "ir": 0.0, "inss": 0.0, "fornecedor": "",
    }


def inicializar_servicos():
    if "servicos_lista" not in st.session_state:
        # Cliente novo começa limpo.
        # Cada empresa cadastra os serviços conforme o próprio segmento.
        st.session_state.servicos_lista = []
    st.session_state.setdefault("tela_servicos", "listar")
    st.session_state.setdefault("id_servico_editar", None)
    st.session_state.setdefault("servicos_busca", "")
    st.session_state.setdefault("servicos_filtro_categoria", "Todas")
    st.session_state.setdefault("servicos_filtro_situacao", "Todos")

    # Ações vindas dos botões coloridos por link interno.
    try:
        params = st.query_params
        acao = params.get("acao_servico")
        id_servico = params.get("id_servico")
    except Exception:
        acao = None
        id_servico = None

    if acao in ["visualizar", "editar", "excluir"] and id_servico:
        st.session_state.tela_servicos = acao
        st.session_state.id_servico_editar = int(id_servico)
        try:
            del st.query_params["acao_servico"]
            del st.query_params["id_servico"]
        except Exception:
            pass


def obter_servico_por_id(servico_id):
    for servico in st.session_state.servicos_lista:
        if int(servico.get("id")) == int(servico_id):
            return servico
    return None


def proximo_id():
    return max([int(s.get("id", 0)) for s in st.session_state.servicos_lista] or [0]) + 1


def normalizar_texto(valor):
    return str(valor or "").strip().lower()


def filtrar_servicos(servicos):
    termo = normalizar_texto(st.session_state.get("servicos_busca", ""))
    categoria = st.session_state.get("servicos_filtro_categoria", "Todas")
    situacao = st.session_state.get("servicos_filtro_situacao", "Todos")
    resultado = servicos
    if termo:
        resultado = [s for s in resultado if termo in normalizar_texto(s.get("nome")) or termo in normalizar_texto(s.get("codigo")) or termo in normalizar_texto(s.get("categoria")) or termo in normalizar_texto(s.get("tipo_calculo"))]
    if categoria != "Todas":
        resultado = [s for s in resultado if s.get("categoria") == categoria]
    if situacao != "Todos":
        resultado = [s for s in resultado if s.get("situacao") == situacao]
    return resultado


def ir_listar():
    st.session_state.tela_servicos = "listar"
    st.session_state.id_servico_editar = None
    st.rerun()


def tela_listar_servicos():
    cabecalho("🔧 Serviços", "Serviços", "Listar")
    col_add, col_espaco, col_busca, col_lupa, col_busca_av = st.columns([1.2, 3.2, 2.8, 0.5, 1.5])
    with col_add:
        if st.button("Adicionar+", type="primary", use_container_width=True):
            st.session_state.tela_servicos = "adicionar"; st.session_state.id_servico_editar = None; st.rerun()
    with col_busca:
        st.text_input("Buscar", label_visibility="collapsed", placeholder="Buscar serviço...", key="servicos_busca")
    with col_lupa:
        st.button("🔍", use_container_width=True)
    with col_busca_av:
        st.button("🔎 Busca avançada", use_container_width=True)

    col_f1, col_f2, col_f3 = st.columns([1.4, 1.2, 4.4])
    with col_f1:
        st.selectbox("Categoria", ["Todas"] + CATEGORIAS_SERVICO, key="servicos_filtro_categoria")
    with col_f2:
        st.selectbox("Situação", ["Todos"] + SITUACOES, key="servicos_filtro_situacao")

    servicos_filtrados = filtrar_servicos(st.session_state.servicos_lista)
    st.caption(f"Mostrando {len(servicos_filtrados)} serviço(s) de {len(st.session_state.servicos_lista)} cadastrado(s).")

    if not servicos_filtrados:
        st.info("Nenhum serviço encontrado.")
        return

    header = st.columns([1.1, 3.1, 1.5, 1.4, 1.3, 1.3, 0.9, 1.2])
    for col, titulo in zip(header, ["Código", "Nome", "Categoria", "Cálculo", "Vr. custo", "Vr. venda", "Situação", "Ações"]):
        col.markdown(f'<div class="serv-table-header">{titulo}</div>', unsafe_allow_html=True)

    for s in servicos_filtrados:
        cols = st.columns([1.1, 3.1, 1.5, 1.4, 1.3, 1.3, 0.9, 1.2])
        cols[0].markdown(f'<div class="serv-table-cell">{s.get("codigo", "")}</div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div class="serv-table-cell">{s.get("nome", "")}</div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div class="serv-table-cell">{s.get("categoria", "")}</div>', unsafe_allow_html=True)
        cols[3].markdown(f'<div class="serv-table-cell">{s.get("tipo_calculo", "")}</div>', unsafe_allow_html=True)
        cols[4].markdown(f'<div class="serv-table-cell">{moeda_br(s.get("valor_custo", 0))}</div>', unsafe_allow_html=True)
        cols[5].markdown(f'<div class="serv-table-cell">{moeda_br(s.get("valor_venda", 0))}</div>', unsafe_allow_html=True)
        cols[6].markdown(f'<div class="serv-table-cell">{"✅" if s.get("situacao") == "Ativo" else "⛔"}</div>', unsafe_allow_html=True)
        with cols[7]:
            sid = s["id"]
            st.markdown(
                f"""
                <div class="serv-action-wrap">
                    <a class="serv-btn-action serv-btn-view" href="?go_to=servicos&acao_servico=visualizar&id_servico={sid}" target="_self" title="Visualizar">🔍</a>
                    <a class="serv-btn-action serv-btn-edit" href="?go_to=servicos&acao_servico=editar&id_servico={sid}" target="_self" title="Editar"><span>✎</span></a>
                    <a class="serv-btn-action serv-btn-delete" href="?go_to=servicos&acao_servico=excluir&id_servico={sid}" target="_self" title="Excluir"><span>×</span></a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def montar_formulario_servico(servico=None, modo="adicionar"):
    editando = modo == "editar"; visualizando = modo == "visualizar"
    titulo = "Adicionar" if modo == "adicionar" else ("Editar" if editando else "Visualizar")
    cabecalho("🔧 Serviços", "Serviços", titulo)
    servico = servico or {}

    with st.form("form_servico", clear_on_submit=False):
        st.markdown('<div class="serv-section-title">📝 Dados gerais</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([2.3, 1.5, 1.5, 1.5])
        nome = c1.text_input("Nome *", value=servico.get("nome", ""), disabled=visualizando)
        codigo = c2.text_input("Código interno", value=servico.get("codigo", gerar_codigo_servico()), disabled=visualizando)
        valor_custo = c3.number_input("Valor de custo", value=float(servico.get("valor_custo", 0) or 0), min_value=0.0, step=1.0, disabled=visualizando)
        valor_venda = c4.number_input("Valor de venda", value=float(servico.get("valor_venda", 0) or 0), min_value=0.0, step=1.0, disabled=visualizando)

        c5, c6, c7, c8 = st.columns(4)
        categoria_atual = servico.get("categoria", "Instalação")
        categoria = c5.selectbox("Categoria", CATEGORIAS_SERVICO, index=CATEGORIAS_SERVICO.index(categoria_atual) if categoria_atual in CATEGORIAS_SERVICO else 0, disabled=visualizando)
        tipo_atual = servico.get("tipo_calculo", "Valor fixo")
        tipo_calculo = c6.selectbox("Tipo de cálculo", TIPOS_CALCULO, index=TIPOS_CALCULO.index(tipo_atual) if tipo_atual in TIPOS_CALCULO else 0, disabled=visualizando)
        comissao = c7.number_input("Comissão (%)", value=float(servico.get("comissao", 0) or 0), min_value=0.0, step=1.0, disabled=visualizando)
        situacao_atual = servico.get("situacao", "Ativo")
        situacao = c8.selectbox("Situação", SITUACOES, index=SITUACOES.index(situacao_atual) if situacao_atual in SITUACOES else 0, disabled=visualizando)

        st.markdown('<div class="serv-section-title">🔗 Integração</div>', unsafe_allow_html=True)
        i1, i2, i3 = st.columns(3)
        disponivel_orcamento = i1.selectbox("Disponível para orçamento?", ["Sim", "Não"], index=0 if servico.get("disponivel_orcamento", "Sim") == "Sim" else 1, disabled=visualizando)
        disponivel_pedido = i2.selectbox("Disponível para pedido?", ["Sim", "Não"], index=0 if servico.get("disponivel_pedido", "Sim") == "Sim" else 1, disabled=visualizando)
        disponivel_os = i3.selectbox("Disponível para O.S.?", ["Sim", "Não"], index=0 if servico.get("disponivel_os", "Sim") == "Sim" else 1, disabled=visualizando)

        descricao = st.text_area("Descrição", value=servico.get("descricao", ""), height=110, disabled=visualizando)
        observacao_orcamento = st.text_area("Observação padrão para orçamento", value=servico.get("observacao_orcamento", ""), height=90, disabled=visualizando, placeholder="Ex.: Instalação no ambiente informado pelo cliente.")

        st.markdown('<div class="serv-section-title">🧾 Fiscal</div>', unsafe_allow_html=True)
        st.warning("Caso você não tenha conhecimento sobre estas informações, consulte seu contador.")
        f1, f2, f3, f4 = st.columns(4)
        atividade_servico = f1.text_input("Atividade de serviço", value=servico.get("atividade_servico", ""), disabled=visualizando)
        codigo_servico = f2.text_input("Código do serviço", value=servico.get("codigo_servico", ""), disabled=visualizando)
        codigo_tributacao = f3.text_input("Código de tributação", value=servico.get("codigo_tributacao", ""), disabled=visualizando)
        codigo_nbs = f4.text_input("Código NBS", value=servico.get("codigo_nbs", ""), disabled=visualizando)
        f5, f6, f7, f8 = st.columns(4)
        cnae = f5.text_input("CNAE", value=servico.get("cnae", ""), disabled=visualizando)
        iss = f6.number_input("% ISS", value=float(servico.get("iss", 0) or 0), min_value=0.0, step=0.1, disabled=visualizando)
        cofins = f7.number_input("% COFINS", value=float(servico.get("cofins", 0) or 0), min_value=0.0, step=0.1, disabled=visualizando)
        pis = f8.number_input("% PIS", value=float(servico.get("pis", 0) or 0), min_value=0.0, step=0.1, disabled=visualizando)
        f9, f10, f11 = st.columns(3)
        csll = f9.number_input("% CSLL", value=float(servico.get("csll", 0) or 0), min_value=0.0, step=0.1, disabled=visualizando)
        ir = f10.number_input("% IR", value=float(servico.get("ir", 0) or 0), min_value=0.0, step=0.1, disabled=visualizando)
        inss = f11.number_input("% INSS", value=float(servico.get("inss", 0) or 0), min_value=0.0, step=0.1, disabled=visualizando)

        st.markdown('<div class="serv-section-title">🏭 Fornecedor</div>', unsafe_allow_html=True)
        fornecedor = st.text_input("Fornecedor principal", value=servico.get("fornecedor", ""), disabled=visualizando)
        st.markdown("---")
        b1, b2, b3 = st.columns([1, 1, 4])
        salvar = b1.form_submit_button("Cadastrar" if modo == "adicionar" else "Salvar", type="primary", use_container_width=True) if not visualizando else False
        voltar = b2.form_submit_button("Cancelar" if not visualizando else "Voltar", use_container_width=True)

    if voltar:
        ir_listar()
    if salvar:
        if not nome.strip():
            st.error("Informe o nome do serviço."); return
        payload = {
            "id": servico.get("id", proximo_id()), "codigo": codigo.strip() or gerar_codigo_servico(), "nome": nome.strip().upper(),
            "categoria": categoria, "tipo_calculo": tipo_calculo, "valor_custo": float(valor_custo or 0), "valor_venda": float(valor_venda or 0),
            "comissao": float(comissao or 0), "situacao": situacao, "descricao": descricao, "observacao_orcamento": observacao_orcamento,
            "disponivel_orcamento": disponivel_orcamento, "disponivel_pedido": disponivel_pedido, "disponivel_os": disponivel_os,
            "atividade_servico": atividade_servico, "codigo_servico": codigo_servico, "codigo_tributacao": codigo_tributacao, "codigo_nbs": codigo_nbs,
            "cnae": cnae, "iss": float(iss or 0), "cofins": float(cofins or 0), "pis": float(pis or 0), "csll": float(csll or 0),
            "ir": float(ir or 0), "inss": float(inss or 0), "fornecedor": fornecedor,
        }
        if editando:
            for i, item in enumerate(st.session_state.servicos_lista):
                if int(item.get("id")) == int(servico.get("id")):
                    st.session_state.servicos_lista[i] = payload; break
            st.success("Serviço atualizado com sucesso.")
        else:
            st.session_state.servicos_lista.append(payload); st.success("Serviço cadastrado com sucesso.")
        ir_listar()


def tela_excluir_servico():
    servico = obter_servico_por_id(st.session_state.id_servico_editar)
    cabecalho("🔧 Serviços", "Serviços", "Excluir")
    if not servico:
        st.error("Serviço não encontrado.")
        if st.button("Voltar"): ir_listar()
        return
    st.warning(f"Tem certeza que deseja excluir o serviço **{servico.get('nome')}**?")
    c1, c2, c3 = st.columns([1, 1, 4])
    if c1.button("Sim, excluir", type="primary", use_container_width=True):
        st.session_state.servicos_lista = [s for s in st.session_state.servicos_lista if int(s.get("id")) != int(servico.get("id"))]
        st.success("Serviço excluído com sucesso."); ir_listar()
    if c2.button("Cancelar", use_container_width=True): ir_listar()


def telaServicos():
    carregar_css_servicos()
    inicializar_servicos()
    tela = st.session_state.get("tela_servicos", "listar")
    if tela == "listar": tela_listar_servicos()
    elif tela == "adicionar": montar_formulario_servico(modo="adicionar")
    elif tela == "editar":
        servico = obter_servico_por_id(st.session_state.id_servico_editar)
        montar_formulario_servico(servico, modo="editar") if servico else st.error("Serviço não encontrado.")
    elif tela == "visualizar":
        servico = obter_servico_por_id(st.session_state.id_servico_editar)
        montar_formulario_servico(servico, modo="visualizar") if servico else st.error("Serviço não encontrado.")
    elif tela == "excluir": tela_excluir_servico()
    else:
        st.session_state.tela_servicos = "listar"; st.rerun()


def tela_servicos():
    telaServicos()
