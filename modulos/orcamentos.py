import streamlit as st
from datetime import date, datetime, timedelta
import csv
import io
import calendar
import math
from decimal import Decimal, ROUND_HALF_UP

# SMARTTEC ERP - ORÇAMENTOS - INTEGRAÇÃO REAL DOS CADASTROS
# Cliente, Cliente Final, Produto e Representante via API real. Serviços via session_state até existir API.

try:
    from utils.ui import cabecalho
except Exception:

    def cabecalho(titulo, modulo, tela_atual, funcao_mudar_tela=None):
        st.markdown(f"## {titulo}")

# Integração real com os cadastros do SmartTec ERP (FastAPI).
# Se o backend estiver fora do ar, o orçamento continua funcionando com fallback visual.
try:
    from utils.api_client import (get_clientes, get_produtos_todos, get_funcionarios, get_opcoes_auxiliares_por_categoria,
        get_orcamentos, criar_orcamento, atualizar_orcamento, deletar_orcamento)
except Exception:
    get_clientes = None
    get_produtos_todos = None
    get_funcionarios = None
    get_opcoes_auxiliares_por_categoria = None
    get_orcamentos = criar_orcamento = atualizar_orcamento = deletar_orcamento = None

SITUACOES_ORCAMENTO = ["Em aberto", "Aprovado", "Reprovado", "Cancelado"]
CANAIS_VENDA = ["WhatsApp", "Telefone", "Loja", "Instagram", "Site", "Indicação", "Outro"]
TIPOS_ORCAMENTO = ["Produtos", "Serviços", "Produtos + Serviços"]
FORMAS_PAGAMENTO = [
    "SELECIONE",
    "A COMBINAR",
    "BOLETO",
    "CARTÃO DE CRÉDITO",
    "CARTÃO DE DÉBITO",
    "CHEQUE",
    "DINHEIRO À VISTA",
    "DINHEIRO PARCELADO",
    "LINK PAGAMENTO",
    "PIX",
    "TRANSFERÊNCIA",
]


def carregar_css_orcamentos():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 4.6rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            max-width: 100% !important;
            width: 100% !important;
            overflow-x: hidden !important;
        }

        /* =====================================================
           PADRÃO SMARTTEC / GESTÃOCLICK PARA TABELAS DE ITENS
           Use .orc-form-wide + .orc-card-title + .orc-card-body
           em Produtos, Serviços e futuras telas do sistema.
           Mantém tudo dentro do campo de visão e evita quebra lateral.
        ===================================================== */
        .orc-form-wide {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }

        .orc-card-body {
            overflow-x: hidden !important;
        }

        .orc-form-wide div[data-testid="stHorizontalBlock"] {
            gap: 0.40rem !important;
        }

        .orc-item-header {
            font-weight: 700;
            font-size: 12.5px;
            color: #111827;
            background: #ffffff;
            border-top: 1px solid #d9dee3;
            border-bottom: 1px solid #d9dee3;
            padding: 7px 5px;
            min-height: 34px;
            display: flex;
            align-items: center;
            white-space: nowrap;
        }

        .orc-item-header .req {
            color: #dc2626;
            font-weight: 800;
            margin-left: 1px;
        }

        .orc-item-row-spacer {
            height: 6px;
        }

        .orc-form-wide div[data-testid="stTextInput"] input,
        .orc-form-wide div[data-testid="stNumberInput"] input {
            height: 36px !important;
            min-height: 36px !important;
            padding-left: 8px !important;
            padding-right: 8px !important;
            font-size: 13px !important;
        }

        .orc-form-wide div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 36px !important;
            height: 36px !important;
            font-size: 13px !important;
        }

        .orc-form-wide div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 36px !important;
            height: 36px !important;
            align-items: center !important;
        }

        .orc-form-wide div[data-testid="stTextInput"] label,
        .orc-form-wide div[data-testid="stNumberInput"] label,
        .orc-form-wide div[data-testid="stSelectbox"] label {
            display: none !important;
        }

        .orc-form-wide div[data-testid="stButton"] button {
            height: 36px !important;
            min-height: 36px !important;
            padding: 0 8px !important;
        }

        .orc-form-wide div[data-testid="stButton"] button:has(p) {
            font-size: 14px !important;
            line-height: 1 !important;
        }

        /* Botões Adicionar produto/serviço no padrão GestãoClick */
        .orc-btn-add-row button {
            background: #06151d !important;
            border-color: #06151d !important;
            color: #ffffff !important;
            width: auto !important;
            min-width: 155px !important;
            padding-left: 12px !important;
            padding-right: 12px !important;
        }

        .orc-btn-add-row button:hover {
            background: #000000 !important;
            border-color: #000000 !important;
            color: #ffffff !important;
        }

        .orc-btn-add-row button * {
            color: #ffffff !important;
        }

        .orc-line-caption {
            color: #64748b;
            font-size: 13px;
            margin: 7px 0 16px 0;
        }

        .orc-action-btn-compact button {
            width: 36px !important;
            min-width: 36px !important;
            max-width: 36px !important;
            height: 36px !important;
            min-height: 36px !important;
            padding: 0 !important;
            background: #dc3545 !important;
            border-color: #dc3545 !important;
            color: #ffffff !important;
            border-radius: 4px !important;
        }

        .orc-action-btn-compact button:hover {
            background: #bb2d3b !important;
            border-color: #bb2d3b !important;
            color: #ffffff !important;
        }

        .orc-action-btn-compact button * {
            color: #ffffff !important;
        }

        div[data-testid="stButton"] button {
            min-height: 40px !important;
            height: 40px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
            white-space: nowrap !important;
        }

        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
            color: white !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            min-height: 40px !important;
            border-radius: 4px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 40px !important;
            border-radius: 4px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
            color: #111827 !important;
        }

        .orc-card-title {
            background: #ffffff;
            border: 1px solid #d9dee3;
            border-radius: 4px 4px 0 0;
            padding: 8px 14px;
            font-size: 19px;
            font-weight: 500;
            color: #111827;
            margin-top: 12px;
        }

        .orc-card-body {
            border: 1px solid #d9dee3;
            border-top: none;
            padding: 10px 14px 12px 14px;
            border-radius: 0 0 4px 4px;
            margin-bottom: 12px;
            background: #ffffff10;
        }

        .orc-btn-dark button {
            background:#06151d!important;
            border-color:#06151d!important;
            color:white!important;
        }

        .orc-toolbar-btn-dark {
            width: 100%;
            min-height: 40px;
            height: 40px;
            border-radius: 4px;
            border: 1px solid #111827;
            background: #111827;
            color: #ffffff;
            font-size: 14px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            white-space: nowrap;
            box-shadow: none;
            text-decoration: none;
            padding: 0 12px;
            box-sizing: border-box;
        }

        .orc-toolbar-btn-dark,
        a.orc-toolbar-btn-dark,
        a.orc-toolbar-btn-dark:link,
        a.orc-toolbar-btn-dark:visited,
        a.orc-toolbar-btn-dark:hover,
        a.orc-toolbar-btn-dark:active {
            color: #ffffff !important;
            text-decoration: none !important;
        }

        .orc-toolbar-btn-dark:hover,
        a.orc-toolbar-btn-dark:hover {
            background: #000000 !important;
            border-color: #000000 !important;
            color: #ffffff !important;
        }

        .orc-toolbar-btn-dark *,
        a.orc-toolbar-btn-dark * {
            color: #ffffff !important;
            text-decoration: none !important;
        }

        .orc-toolbar-btn-square {
            width: 100%;
            min-height: 40px;
            height: 40px;
            border-radius: 4px;
            border: 1px solid #111827;
            background: #111827;
            color: #ffffff;
            font-size: 16px;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-shadow: none;
            text-decoration: none;
            box-sizing: border-box;
        }

        .orc-toolbar-btn-square:hover {
            background: #000000;
            border-color: #000000;
            color: #ffffff;
        }

        .orc-small-help {
            font-size: 12px;
            color: #6b7280;
            margin-top: -6px;
            margin-bottom: 8px;
        }

        .orc-search-rule {
            background: #eef6ff;
            border: 1px solid #bfdbfe;
            color: #1d4ed8;
            padding: 10px 12px;
            border-radius: 4px;
            font-size: 13px;
            margin-bottom: 10px;
        }

        .orc-table-header {
            font-weight: 700;
            font-size: 14px;
            color: #111827;
            background: #ffffff;
            border-top: 1px solid #d9dee3;
            border-bottom: 1px solid #d9dee3;
            padding: 10px 6px;
            min-height: 42px;
        }

        .orc-table-cell {
            font-size: 13px;
            color: #111827;
            padding: 8px 6px;
            min-height: 48px;
            border-bottom: 1px solid #d9dee3;
            display: flex;
            align-items: center;
        }

        .orc-action-wrap {
            display: flex;
            gap: 6px;
            align-items: center;
            justify-content: center;
            min-height: 48px;
            border-bottom: 1px solid #d9dee3;
            padding: 5px 0;
        }

        .orc-btn-action {
            width: 34px;
            height: 34px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none !important;
            font-size: 16px;
            font-weight: 800;
            border: 1px solid #d1d5db;
            line-height: 1;
        }

        .orc-btn-view { background:#ffffff!important; color:#111827!important; border-color:#d1d5db!important; }
        .orc-btn-edit { background:#198754!important; color:#ffffff!important; border-color:#0d6efd!important; }
        .orc-btn-delete { background:#dc3545!important; color:#ffffff!important; border-color:#dc3545!important; }
        .orc-btn-menu { background:#0d6efd!important; color:#ffffff!important; border-color:#0d6efd!important; }

        /* ===== Toolbar Orçamentos: padrão igual Produtos ===== */
        div[data-testid="stPopover"] button {
            background: #111827 !important;
            color: #ffffff !important;
            border: 1px solid #111827 !important;
            border-radius: 4px !important;
            box-shadow: none !important;
            min-height: 40px !important;
            height: 40px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            white-space: nowrap !important;
        }

        div[data-testid="stPopover"] button:hover {
            background: #000000 !important;
            border-color: #000000 !important;
            color: #ffffff !important;
        }

        div[data-testid="stPopover"] button * {
            color: #ffffff !important;
        }

        .orc-total-box {
            background: #f8fafc;
            border: 1px solid #d9dee3;
            padding: 12px;
            border-radius: 4px;
            font-weight: 700;
        }


        /* Campos numéricos sem botões de + e - para manter alinhamento limpo */
        div[data-testid="stNumberInput"] button {
            display: none !important;
        }

        div[data-testid="stNumberInput"] > div {
            width: 100% !important;
        }

        div[data-testid="stNumberInput"] input {
            padding-right: 10px !important;
        }

        .orc-filter-button-spacer {
            height: 28px;
        }

        /* Campos das linhas de Produto/Serviço mais compactos e alinhados */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input {
            padding-left: 10px !important;
            padding-right: 10px !important;
        }

        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #06151d !important;
            border-color: #06151d !important;
            color: #ffffff !important;
        }

        div[data-testid="stButton"] button[kind="secondary"]:hover {
            background-color: #000000 !important;
            border-color: #000000 !important;
            color: #ffffff !important;
        }


        
        /* AJUSTE FINAL: botão Excluir das linhas de Produto/Serviço
           alinhado na coluna Ação e vermelho, sem herdar o botão secundário preto. */
        .orc-form-wide .orc-action-btn-compact {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            height: 36px !important;
            min-height: 36px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .orc-form-wide .orc-action-btn-compact div[data-testid="stButton"],
        .orc-form-wide .orc-action-btn-compact div[data-testid="stButton"] > button,
        .orc-form-wide .orc-action-btn-compact button,
        .orc-form-wide .orc-action-btn-compact button[kind="secondary"],
        .orc-form-wide .orc-action-btn-compact button:disabled {
            width: 36px !important;
            min-width: 36px !important;
            max-width: 36px !important;
            height: 36px !important;
            min-height: 36px !important;
            max-height: 36px !important;
            padding: 0 !important;
            margin: 0 auto !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: #dc3545 !important;
            background-color: #dc3545 !important;
            border: 1px solid #dc3545 !important;
            color: #ffffff !important;
            border-radius: 4px !important;
            opacity: 1 !important;
            box-shadow: none !important;
        }

        .orc-form-wide .orc-action-btn-compact button:hover,
        .orc-form-wide .orc-action-btn-compact button[kind="secondary"]:hover {
            background: #bb2d3b !important;
            background-color: #bb2d3b !important;
            border-color: #bb2d3b !important;
            color: #ffffff !important;
        }

        .orc-form-wide .orc-action-btn-compact button p,
        .orc-form-wide .orc-action-btn-compact button span,
        .orc-form-wide .orc-action-btn-compact button * {
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            font-size: 15px !important;
        }

        /* AJUSTE FINAL DEFINITIVO - Linhas de Produtos/Serviços */
        .orc-form-wide .orc-item-header {
            min-height: 34px !important;
            height: 34px !important;
            padding: 7px 6px !important;
            display: flex !important;
            align-items: center !important;
        }

        .orc-form-wide div[data-testid="stTextInput"] input,
        .orc-form-wide div[data-testid="stNumberInput"] input,
        .orc-form-wide div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 36px !important;
            height: 36px !important;
        }

        .orc-form-wide .orc-btn-add-row button,
        .orc-btn-add-row button {
            background: #06151d !important;
            border-color: #06151d !important;
            color: #ffffff !important;
            height: 36px !important;
            min-height: 36px !important;
        }



        /* Ajuste das tabelas para caber melhor no campo de visão */
        .orc-form-wide .orc-card-body,
        .orc-form-wide {
            overflow-x: hidden !important;
        }

        .orc-form-wide div[data-testid="stHorizontalBlock"] {
            gap: 0.32rem !important;
        }

        .orc-form-wide .orc-item-header {
            font-size: 12px !important;
            padding-left: 5px !important;
            padding-right: 5px !important;
        }


        /* MENU AZUL DE AÇÕES DA LISTAGEM - padrão SmartTec */
        .orc-btn-menu {
            background:#0d6efd!important;
            color:#ffffff!important;
            border-color:#0d6efd!important;
            position:relative!important;
        }

        .orc-menu-dropdown-wrap {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .orc-menu-dropdown-wrap:hover .orc-menu-dropdown {
            display: block;
        }

        .orc-menu-dropdown {
            display: none;
            position: absolute;
            right: 0;
            top: 36px;
            min-width: 215px;
            background: #ffffff;
            border: 1px solid #d1d5db;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
            border-radius: 4px;
            z-index: 9999;
            padding: 6px 0;
            text-align: left;
        }

        .orc-menu-dropdown a,
        .orc-menu-dropdown .orc-menu-label {
            display: block;
            padding: 9px 14px;
            color: #111827 !important;
            text-decoration: none !important;
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
            line-height: 1.2;
        }

        .orc-menu-dropdown a:hover {
            background: #0b1f2a !important;
            color: #ffffff !important;
        }

        .orc-menu-dropdown .orc-menu-section {
            border-top: 1px solid #e5e7eb;
            margin-top: 4px;
            padding-top: 4px;
        }

        .orc-menu-dropdown .orc-menu-muted {
            color: #6b7280 !important;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .02em;
            padding: 7px 14px 4px 14px;
        }

        /* Links dentro do popover de ações da listagem */
        .orc-menu-link {
            display:block;
            padding:8px 10px;
            color:#111827 !important;
            text-decoration:none !important;
            font-size:14px;
            font-weight:500;
            border-radius:4px;
        }
        .orc-menu-link:hover {
            background:#0b1f2a !important;
            color:#ffffff !important;
        }


        /* Botão da setinha de ações na listagem: azul SmartTec, só o ícone */
        .orc-row-popover-blue div[data-testid="stPopover"] button {
            width: 34px !important;
            min-width: 34px !important;
            max-width: 34px !important;
            height: 34px !important;
            min-height: 34px !important;
            padding: 0 !important;
            background: #0d6efd !important;
            background-color: #0d6efd !important;
            border: 1px solid #0d6efd !important;
            color: #ffffff !important;
            border-radius: 4px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 15px !important;
            font-weight: 800 !important;
            line-height: 1 !important;
        }

        .orc-row-popover-blue div[data-testid="stPopover"] button:hover {
            background: #0b5ed7 !important;
            background-color: #0b5ed7 !important;
            border-color: #0b5ed7 !important;
            color: #ffffff !important;
        }

        .orc-row-popover-blue div[data-testid="stPopover"] button * {
            color: #ffffff !important;
            font-size: 15px !important;
            line-height: 1 !important;
        }

        .orc-popover-menu-title {
            font-size: 12px;
            color: #6b7280;
            font-weight: 800;
            text-transform: uppercase;
            margin: 8px 0 4px 0;
        }

        .orc-popover-divider {
            height: 1px;
            background: #e5e7eb;
            margin: 7px 0;
        }

</style>
        """,
        unsafe_allow_html=True,
    )


def moeda_br(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def gerar_numero_orcamento():
    return int(datetime.now().strftime("%m%d%H%M"))


def orcamento_base(idx, cliente, valor):
    hoje = date.today()
    return {
        "id": idx,
        "numero": 1200 + idx,
        "cliente": cliente,
        "cliente_final": "CLIENTE FINAL",
        "representante": "REPRESENTANTE",
        "data": hoje.strftime("%d/%m/%Y"),
        "prazo_entrega": (hoje + timedelta(days=10)).strftime("%d/%m/%Y"),
        "vendedor": "Valmir Barbosa",
        "canal_venda": "WhatsApp",
        "tipo_orcamento": "Produtos",
        "situacao": "Em aberto",
        "valor_total": float(valor),
        "introducao": "",
        "produtos": [],
        "servicos": [],
        "frete": 0.0,
        "transportadora": "",
        "desconto_rs": 0.0,
        "desconto_percentual": 0.0,
        "forma_pagamento": "PIX",
        "observacoes": "PRAZO ENTREGA 10 DIAS ÚTEIS\\nGARANTIA 3 ANOS DEFEITO FABRICAÇÃO\\nFORMA PAGAMENTO",
        "observacoes_internas": "",
    }


def inicializar_orcamentos():
    if "orcamentos_lista" not in st.session_state:
        try:
            resposta = get_orcamentos() if get_orcamentos else None
            if resposta is None or resposta.status_code != 200:
                raise RuntimeError("API de Orçamentos indisponível")
            st.session_state.orcamentos_lista = [orcamento_api_para_tela(item) for item in resposta.json()]
            st.session_state.orcamentos_api_ativa = True
        except Exception:
            st.session_state.orcamentos_api_ativa = False
            st.session_state.orcamentos_lista = []

    st.session_state.setdefault("tela_orcamentos", "listar")
    st.session_state.setdefault("id_orcamento_editar", None)
    st.session_state.setdefault("orcamentos_busca", "")
    st.session_state.setdefault("orcamentos_filtro_situacao", "Todos")
    st.session_state.setdefault("orcamentos_periodo_label", "Este mês")
    hoje = date.today()
    primeiro_dia = hoje.replace(day=1)
    ultimo_dia = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    st.session_state.setdefault("orcamentos_data_inicio", primeiro_dia)
    st.session_state.setdefault("orcamentos_data_fim", ultimo_dia)
    st.session_state.setdefault("orcamentos_busca_avancada_aberta", False)
    st.session_state.setdefault("orcamentos_filtro_codigo", "")
    st.session_state.setdefault("orcamentos_filtro_cliente", "")
    st.session_state.setdefault("orcamentos_filtro_produto", "")
    st.session_state.setdefault("orcamentos_filtro_servico", "")
    st.session_state.setdefault("orcamentos_filtro_centro_custo", "Todos")
    st.session_state.setdefault("orcamentos_filtro_cliente_final", "")
    st.session_state.setdefault("orcamentos_filtro_representante", "")
    st.session_state.setdefault("orcamentos_filtro_tipo", "Todos")
    st.session_state.setdefault("orcamentos_filtro_canal", "Todos")
    st.session_state.setdefault("orcamentos_filtro_valor_de", 0.0)
    st.session_state.setdefault("orcamentos_filtro_valor_ate", 0.0)
    st.session_state.setdefault("orc_col_numero", True)
    st.session_state.setdefault("orc_col_cliente", True)
    st.session_state.setdefault("orc_col_cliente_final", True)
    st.session_state.setdefault("orc_col_representante", True)
    st.session_state.setdefault("orc_col_data", True)
    st.session_state.setdefault("orc_col_situacao", True)
    st.session_state.setdefault("orc_col_valor", True)
    st.session_state.setdefault("orcamentos_agrupar_situacao", False)

    # Base inicial para o fluxo comercial completo.
    # Por enquanto fica em session_state para não depender ainda do módulo definitivo de Pedidos/O.S./Financeiro.
    st.session_state.setdefault("pedidos_lista", [])
    st.session_state.setdefault("ordens_servico_lista", [])
    st.session_state.setdefault("comissoes_parceiros_lista", [])


def gerar_csv_orcamentos(lista):
    buffer = io.StringIO()
    campos = [
        "numero", "cliente", "cliente_final", "representante", "data",
        "prazo_entrega", "vendedor", "canal_venda", "tipo_orcamento",
        "situacao", "valor_total", "forma_pagamento", "observacoes",
    ]
    writer = csv.DictWriter(buffer, fieldnames=campos, delimiter=";")
    writer.writeheader()
    for item in lista:
        writer.writerow({campo: item.get(campo, "") for campo in campos})
    return buffer.getvalue().encode("utf-8-sig")


def obter_orcamento_por_id(orcamento_id):
    for item in st.session_state.orcamentos_lista:
        if int(item.get("id")) == int(orcamento_id):
            return item
    return None


def orcamento_api_para_tela(item):
    produtos, servicos = [], []
    for registro in item.get("itens") or []:
        convertido = {"produto":registro.get("descricao", ""), "produto_original":registro.get("descricao", ""), "servico":registro.get("descricao", ""), "detalhe":registro.get("observacao_item", ""), "produto_id":registro.get("produto_id"), "codigo_interno":registro.get("codigo_interno"), "grupo_tecnico":registro.get("grupo_tecnico"), "modelo_tecnico":registro.get("modelo_tecnico"), "modelo_calculo":"Romana de teto" if registro.get("modelo_tecnico") == "ROMANA_TETO" else ("Romana" if registro.get("modelo_tecnico") == "ROMANA" else "Manual"), "unidade":registro.get("unidade"), "quantidade":registro.get("quantidade", 1), "quantidade_pecas":registro.get("quantidade", 1), "largura":registro.get("largura", 0), "altura":registro.get("altura", 0), "area_m2":registro.get("area", 0), "valor":registro.get("preco_unitario", 0), "desconto":registro.get("desconto", 0), "subtotal":registro.get("subtotal", 0), "material":registro.get("material"), "cor":registro.get("cor"), "acionamento":registro.get("acionamento"), "lado_comando":registro.get("lado_comando"), "calculo_producao_status":registro.get("calculo_producao_status")}
        (servicos if registro.get("tipo_item") == "SERVICO" else produtos).append(convertido)
    criado = str(item.get("criado_em") or "")[:10]
    try:data_fmt = datetime.strptime(criado, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:data_fmt = date.today().strftime("%d/%m/%Y")
    return {"id":item.get("id"), "numero":item.get("numero"), "cliente":item.get("cliente_nome", ""), "cliente_id":item.get("cliente_id"), "data":data_fmt, "situacao":item.get("status", "EM_ABERTO"), "valor_total":item.get("total_final", 0), "produtos":produtos, "servicos":servicos, "desconto_rs":item.get("desconto", 0), "desconto_percentual":0, "frete":0, "observacoes":item.get("observacao") or "", "validade_data":item.get("validade"), "tipo_orcamento":"Produtos"}


def proximo_id():
    ids = [int(o.get("id", 0)) for o in st.session_state.orcamentos_lista]
    return max(ids or [0]) + 1


def proximo_id_lista(nome_lista):
    lista = st.session_state.get(nome_lista, [])
    ids = []
    if isinstance(lista, list):
        for item in lista:
            if isinstance(item, dict):
                try:
                    ids.append(int(item.get("id", 0)))
                except Exception:
                    pass
    return max(ids or [0]) + 1


def clonar_dados_comerciais_orcamento(orcamento):
    """
    Cria uma cópia segura dos dados do orçamento para virar Pedido/O.S.
    Mantém produtos, serviços, cliente final, representante, totais e condições.
    """
    base = dict(orcamento or {})
    base["produtos"] = [dict(p) for p in (orcamento or {}).get("produtos", [])]
    base["servicos"] = [dict(s) for s in (orcamento or {}).get("servicos", [])]
    base["parcelas"] = [dict(p) for p in (orcamento or {}).get("parcelas", [])]
    return base


def criar_pedido_a_partir_orcamento(orcamento):
    pedido = clonar_dados_comerciais_orcamento(orcamento)
    pedido["id"] = proximo_id_lista("pedidos_lista")
    pedido["id_orcamento_origem"] = orcamento.get("id")
    pedido["numero_orcamento_origem"] = orcamento.get("numero")
    pedido["numero"] = f"PED-{datetime.now().strftime('%m%d%H%M%S')}"
    pedido["data"] = date.today().strftime("%d/%m/%Y")
    pedido["situacao"] = "Pedido gerado"
    pedido["origem"] = "Orçamento"

    st.session_state.pedidos_lista.append(pedido)

    # Atualiza o orçamento de origem para não perder rastreio.
    orcamento["situacao"] = "Aprovado"
    orcamento["pedido_gerado"] = True
    orcamento["id_pedido_gerado"] = pedido["id"]
    orcamento["numero_pedido_gerado"] = pedido["numero"]

    return pedido


def criar_os_a_partir_orcamento(orcamento):
    ordem = clonar_dados_comerciais_orcamento(orcamento)
    ordem["id"] = proximo_id_lista("ordens_servico_lista")
    ordem["id_orcamento_origem"] = orcamento.get("id")
    ordem["numero_orcamento_origem"] = orcamento.get("numero")
    ordem["numero"] = f"OS-{datetime.now().strftime('%m%d%H%M%S')}"
    ordem["data"] = date.today().strftime("%d/%m/%Y")
    ordem["situacao"] = "Aberta"
    ordem["origem"] = "Orçamento"

    st.session_state.ordens_servico_lista.append(ordem)
    orcamento["os_gerada"] = True
    orcamento["id_os_gerada"] = ordem["id"]
    orcamento["numero_os_gerada"] = ordem["numero"]
    return ordem


def registrar_repasse_parceiro_previsto(orcamento, pedido=None):
    """
    Primeira base do financeiro de parceiros.
    Se o orçamento tiver campos de parceiro/comissão, já cria uma previsão de repasse.
    Se ainda não tiver, não força nada e não quebra o fluxo.
    """
    parceiro = str(orcamento.get("parceiro") or orcamento.get("decorador") or orcamento.get("representante") or "").strip()
    repasse = float(orcamento.get("repasse_parceiro", 0) or orcamento.get("repasse_previsto", 0) or 0)

    if not parceiro or repasse <= 0:
        return None

    registro = {
        "id": proximo_id_lista("comissoes_parceiros_lista"),
        "id_orcamento": orcamento.get("id"),
        "numero_orcamento": orcamento.get("numero"),
        "id_pedido": (pedido or {}).get("id"),
        "numero_pedido": (pedido or {}).get("numero"),
        "parceiro": parceiro,
        "cliente": orcamento.get("cliente", ""),
        "cliente_final": orcamento.get("cliente_final", ""),
        "valor_cliente": float(orcamento.get("valor_total", 0) or 0),
        "repasse_previsto": repasse,
        "status": "Pendente",
        "data_previsao": date.today().strftime("%d/%m/%Y"),
    }
    st.session_state.comissoes_parceiros_lista.append(registro)
    return registro


def normalizar_texto(valor):
    return str(valor or "").strip().lower()


def normalizar_filtro_busca(valor):
    valor = str(valor or "").strip()
    if valor in ["Digite para buscar", "Selecione o cliente", "Selecione o cliente final", "Selecione o representante"]:
        return ""
    if valor.startswith("➕ Adicionar novo"):
        return ""
    return valor


def extrair_nome_registro(registro):
    if isinstance(registro, dict):
        return (
            registro.get("nome")
            or registro.get("razao_social")
            or registro.get("cliente")
            or registro.get("descricao")
            or ""
        )
    return str(registro or "")


def extrair_valor_registro(registro, campos):
    """
    Lê vários formatos possíveis de cadastro sem quebrar o orçamento.
    Assim o módulo funciona com listas vindas do session_state, banco, API ou dados temporários.
    """
    if isinstance(registro, dict):
        for campo in campos:
            valor = registro.get(campo)
            if valor not in [None, ""]:
                return str(valor).strip()
        return ""

    return str(registro or "").strip()


def obter_lista_session_state(possiveis_chaves):
    dados_encontrados = []

    for chave in possiveis_chaves:
        dados = st.session_state.get(chave)

        if isinstance(dados, list):
            dados_encontrados.extend(dados)

        elif isinstance(dados, dict):
            # Alguns módulos podem guardar {"dados": [...]} ou {"lista": [...]}
            for subchave in ["dados", "lista", "itens", "registros"]:
                subdados = dados.get(subchave)
                if isinstance(subdados, list):
                    dados_encontrados.extend(subdados)

    return dados_encontrados


def normalizar_lista_api(dados):
    """
    Aceita Response do requests, lista direta, dict com dados/items/results/data,
    string JSON ou bytes. Assim o Orçamento não quebra se o retorno mudar.
    """
    if dados is None:
        return []

    if hasattr(dados, "status_code"):
        try:
            if int(getattr(dados, "status_code", 0)) != 200:
                return []
        except Exception:
            return []

    if hasattr(dados, "json"):
        try:
            dados = dados.json()
        except Exception:
            return []

    if isinstance(dados, (bytes, bytearray)):
        try:
            dados = dados.decode("utf-8")
        except Exception:
            return []

    if isinstance(dados, str):
        import json
        texto = dados.strip()
        if not texto:
            return []
        try:
            dados = json.loads(texto)
        except Exception:
            return []

    if isinstance(dados, dict):
        for chave in ["dados", "items", "result", "results", "data", "lista", "registros"]:
            if isinstance(dados.get(chave), list):
                dados = dados.get(chave)
                break
        else:
            dados = [dados]

    if not isinstance(dados, list):
        return []

    return [item for item in dados if isinstance(item, dict)]


def carregar_cadastros_api(tipo):
    """
    Carrega cadastros reais para o Orçamento.
    - Cliente e Cliente final vêm de /clientes/
    - Produto vem de /produtos/
    - Representante vem de /funcionarios/
    - Serviço ainda vem do session_state, pois o módulo Serviços atual ainda não tem API própria.
    """
    mapa_funcoes = {
        "cliente": get_clientes,
        "cliente_final": get_clientes,
        "produto": get_produtos_todos,
        "representante": get_funcionarios,
    }

    funcao = mapa_funcoes.get(tipo)
    if not funcao:
        return []

    tenant_id_cache = st.session_state.get("tenant_empresa_id")
    chave_cache = f"tenant_{tenant_id_cache}_orc_cache_api_{tipo}"

    try:
        resposta = funcao()
        lista = normalizar_lista_api(resposta)
        if lista:
            st.session_state[chave_cache] = lista
            return lista
    except Exception:
        pass

    return st.session_state.get(chave_cache, []) if isinstance(st.session_state.get(chave_cache), list) else []


def montar_registros_busca_global(tipo):
    configuracao_chaves = {
        "cliente": ["clientes_lista", "lista_clientes", "clientes", "dados_clientes"],
        "cliente_final": ["clientes_finais_lista", "lista_clientes_finais", "clientes_finais", "clientes_lista", "lista_clientes", "clientes", "dados_clientes"],
        "representante": ["representantes_lista", "lista_representantes", "representantes", "funcionarios_lista", "lista_funcionarios", "funcionarios", "dados_funcionarios"],
        "produto": ["produtos_lista", "lista_produtos", "produtos", "dados_produtos"],
        "servico": ["servicos_lista", "lista_servicos", "servicos", "dados_servicos"],
    }

    registros_api = carregar_cadastros_api(tipo)
    registros_session = obter_lista_session_state(configuracao_chaves.get(tipo, []))

    # API vem primeiro porque é o cadastro real. Session_state entra como complemento/fallback.
    registros = registros_api + registros_session
    if tipo == "produto":
        # Opções comerciais temporárias: não criam Produto e não fingem possuir receita produtiva.
        registros += [
            {"nome": "ROMANA — ITEM COMERCIAL", "modelo_tecnico": "ROMANA", "grupo_tecnico": "PERSIANA_ROMANA", "unidade_venda": "M²"},
            {"nome": "ROMANA DE TETO — ITEM COMERCIAL", "modelo_tecnico": "ROMANA_TETO", "grupo_tecnico": "PERSIANA_ROMANA_TETO", "unidade_venda": "M²"},
        ]
    return registros


def campos_nome_por_tipo(tipo):
    return {
        "cliente": ["nome", "razao_social", "cliente", "fantasia", "descricao"],
        "cliente_final": ["cliente_final", "nome", "razao_social", "cliente", "fantasia", "descricao"],
        "representante": ["representante", "nome", "razao_social", "funcionario", "vendedor", "descricao"],
        "produto": ["produto", "nome", "descricao", "nome_produto", "titulo"],
        "servico": ["servico", "nome", "descricao", "tipo_servico", "titulo"],
    }.get(tipo, ["nome", "descricao"])


def obter_registro_por_nome(tipo, nome):
    nome_norm = normalizar_texto(nome)
    if not nome_norm:
        return {}

    for registro in montar_registros_busca_global(tipo):
        nome_registro = extrair_valor_registro(registro, campos_nome_por_tipo(tipo))
        if normalizar_texto(nome_registro) == nome_norm:
            return registro

    return {}


def extrair_float_registro(registro, campos, padrao=0.0):
    if not isinstance(registro, dict):
        return padrao

    for campo in campos:
        valor = registro.get(campo)
        if valor in [None, ""]:
            continue
        try:
            if isinstance(valor, (int, float)):
                return float(valor)
            texto = str(valor).replace("R$", "").replace("%", "").strip()
            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", ".")
            return float(texto)
        except Exception:
            continue

    return padrao


def extrair_detalhe_registro(registro):
    if not isinstance(registro, dict):
        return ""
    # Cor é atributo estruturado do item e não deve ocupar o campo livre
    # Ambiente/Detalhes do orçamento.
    for campo in ["descricao", "observacao_orcamento", "observacoes", "categoria", "tipo_calculo", "grupo_produto"]:
        valor = registro.get(campo)
        if valor not in [None, ""]:
            return str(valor).strip()
    return ""


def cor_estruturada_produto(registro):
    """Obtém a cor comercial sem recorrer a descrição ou observação."""
    if not isinstance(registro, dict):
        return ""
    for campo in ["cor", "cor_componente", "variacao_cor"]:
        valor = str(registro.get(campo) or "").strip()
        if valor:
            return valor
    return ""


def produto_mesma_familia_cor_orcamento(produto, familia_tecnica, cor):
    if not isinstance(produto, dict):
        return False
    familia = normalizar_texto(produto.get("familia_tecnica"))
    cor_produto = normalizar_texto(cor_estruturada_produto(produto))
    ativo = produto.get("ativo", True)
    situacao = normalizar_texto(produto.get("situacao", "Ativo"))
    return (
        bool(familia)
        and familia == normalizar_texto(familia_tecnica)
        and cor_produto == normalizar_texto(cor)
        and ativo is not False
        and situacao != "inativo"
    )


def opcoes_cor_familia_orcamento(produtos, produto_atual):
    """Retorna cores apenas quando a família tem variantes ativas inequívocas."""
    if not isinstance(produto_atual, dict) or not produto_atual.get("familia_tecnica"):
        return []
    familia = normalizar_texto(produto_atual.get("familia_tecnica"))
    por_cor = {}
    for produto in produtos or []:
        if normalizar_texto(produto.get("familia_tecnica")) != familia:
            continue
        if produto.get("ativo", True) is False or normalizar_texto(produto.get("situacao", "Ativo")) == "inativo":
            continue
        cor = cor_estruturada_produto(produto)
        if cor:
            identidade = produto.get("id") or (
                normalizar_texto(produto.get("nome")),
                normalizar_texto(produto.get("codigo_interno")),
                normalizar_texto(cor),
            )
            por_cor.setdefault(normalizar_texto(cor), {})[identidade] = cor
    # Duas linhas para a mesma cor tornam a troca de SKU ambígua.
    if len(por_cor) < 2 or any(len(itens) != 1 for itens in por_cor.values()):
        return []
    return sorted((next(iter(itens.values())) for itens in por_cor.values()), key=normalizar_texto)


def procurar_substituto_mesma_familia_cor_orcamento(produtos, produto_atual, cor):
    """Localiza outro SKU da mesma família e cor, sem usar Detalhes."""
    if not isinstance(produto_atual, dict) or not cor:
        return None
    # A família estruturada e suas variantes ativas são a fonte da troca;
    # varia_cor legado não pode contornar a proteção contra ambiguidade.
    if not opcoes_cor_familia_orcamento(produtos, produto_atual):
        return None
    familia = produto_atual.get("familia_tecnica")
    candidatos = [
        p for p in (produtos or [])
        if produto_mesma_familia_cor_orcamento(p, familia, cor)
    ]
    return sorted(candidatos, key=lambda p: int(p.get("id") or 0))[0] if candidatos else None


def atualizar_valor_item_por_cadastro(prefixo, tipo, nome, item):
    """
    Quando o usuário troca Produto/Serviço, puxa o valor de venda do cadastro real.
    Não trava caso o campo não exista no banco atual.
    """
    chave_nome = f"{prefixo}_cadastro_nome_atual"
    chave_valor = f"{prefixo}_valor"

    nome_limpo = str(nome or "").strip()
    if not nome_limpo:
        return

    if st.session_state.get(chave_nome) == nome_limpo:
        return

    registro = obter_registro_por_nome(tipo, nome_limpo)
    valor_cadastro = extrair_float_registro(
        registro,
        [
            "valor_venda",
            "vr_venda",
            "preco_venda",
            "preco",
            "valor",
            "valor_unitario",
            "venda",
        ],
        padrao=0.0,
    )

    st.session_state[chave_nome] = nome_limpo
    if valor_cadastro > 0 and not disabled_global_guard():
        st.session_state[chave_valor] = float(valor_cadastro)


def disabled_global_guard():
    # Mantém compatibilidade caso o Streamlit rode widgets em modo visualização.
    return False


def montar_opcoes_busca_global(tipo):
    """
    Busca Inteligente Global do orçamento.
    Tipos suportados:
    - cliente
    - cliente_final
    - representante
    - produto
    - servico

    A função procura primeiro cadastros reais já carregados no session_state.
    Se ainda não houver integração carregada, usa fallback visual para não travar a tela.
    """

    configuracao = {
        "cliente": {
            "chaves": ["clientes_lista", "lista_clientes", "clientes", "dados_clientes"],
            "campos": ["nome", "razao_social", "cliente", "fantasia", "descricao"],
            "fallback": [
                "LÍDIA MACHADO AMBIENTES INTERNOS",
                "ALESSANDRA FARIA",
                "ALESSANDRA CONDE",
                "MARIA DA GLORIA MARTINS",
            ],
            "adicionar": "➕ Adicionar novo cliente",
        },
        "cliente_final": {
            "chaves": [
                "clientes_finais_lista",
                "lista_clientes_finais",
                "clientes_finais",
                "clientes_lista",
                "lista_clientes",
                "clientes",
                "dados_clientes",
            ],
            "campos": ["cliente_final", "nome", "razao_social", "cliente", "fantasia", "descricao"],
            "fallback": [
                "CLIENTE FINAL",
                "OBRA RESIDENCIAL",
                "APARTAMENTO CLIENTE",
            ],
            "adicionar": "➕ Adicionar novo cliente final",
        },
        "representante": {
            "chaves": [
                "representantes_lista",
                "lista_representantes",
                "representantes",
                "funcionarios_lista",
                "lista_funcionarios",
                "funcionarios",
                "dados_funcionarios",
            ],
            "campos": ["representante", "nome", "razao_social", "funcionario", "vendedor", "descricao"],
            "fallback": [
                "REPRESENTANTE",
                "VALMIR BARBOSA",
                "LÍDIA MACHADO",
            ],
            "adicionar": "➕ Adicionar novo representante",
        },
        "produto": {
            "chaves": ["produtos_lista", "lista_produtos", "produtos", "dados_produtos"],
            "campos": ["produto", "nome", "descricao", "nome_produto", "titulo"],
            "fallback": [
                "PERSIANA ROLÔ",
                "ROLÔ MOTORIZADA",
                "CORTINA WAVE",
                "DOUBLE VISION",
            ],
            "adicionar": "➕ Adicionar novo produto",
        },
        "servico": {
            "chaves": ["servicos_lista", "lista_servicos", "servicos", "dados_servicos"],
            "campos": ["servico", "nome", "descricao", "tipo_servico", "titulo"],
            "fallback": [
                "INSTALAÇÃO",
                "LAVAGEM DE CORTINA",
                "MANUTENÇÃO",
                "VISITA TÉCNICA",
            ],
            "adicionar": "➕ Adicionar novo serviço",
        },
    }

    cfg = configuracao.get(tipo, configuracao["cliente"])
    registros = montar_registros_busca_global(tipo)

    opcoes = []
    for registro in registros:
        if tipo == "produto" and (
            registro.get("ativo", True) is False
            or normalizar_texto(registro.get("situacao", "Ativo")) == "inativo"
        ):
            continue
        nome = extrair_valor_registro(registro, cfg["campos"]).strip()
        if nome:
            opcoes.append(nome.upper())

    if not opcoes:
        opcoes = cfg["fallback"]

    opcoes = sorted(set(opcoes))
    return ["Digite para buscar"] + opcoes + [cfg["adicionar"]]


def campo_busca_inteligente_global(
    label,
    tipo,
    valor_atual="",
    key="busca_inteligente_global",
    disabled=False,
    label_visibility="visible",
):
    """
    Campo padrão de busca inteligente para todos os cadastros usados no orçamento.
    Proteção importante: quando a lista vem da API, o cadastro pode mudar entre um rerun e outro.
    Se o valor salvo no session_state não existir mais nas opções, o Streamlit quebra com:
    ValueError: ... is not in iterable.
    Por isso normalizamos o valor antes de renderizar o selectbox.
    """
    opcoes = montar_opcoes_busca_global(tipo)

    if tipo == "produto":
        import unicodedata

        def normalizar_busca_produto(valor):
            texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
            return "".join(
                caractere
                for caractere in texto
                if not unicodedata.combining(caractere)
                and (caractere.isalnum() or caractere.isspace())
            )

        busca_produto = st.text_input(
            "Buscar produto",
            key=f"{key}_pesquisa",
            disabled=disabled,
        )
        termos_busca = [
            normalizar_busca_produto(termo)
            for termo in str(busca_produto or "").split()
            if normalizar_busca_produto(termo)
        ]
        opcoes_especiais = {"Digite para buscar", "➕ Adicionar novo produto"}
        opcoes_filtradas = [
            opcao for opcao in opcoes
            if opcao in opcoes_especiais
            or all(termo in normalizar_busca_produto(opcao) for termo in termos_busca)
        ]
        opcoes = opcoes_filtradas

    # Proteção definitiva para o st.selectbox:
    # - options nunca pode ser vazio
    # - options precisa conter apenas strings válidas
    # - qualquer valor antigo salvo no session_state que não exista nas opções
    #   deve ser substituído ANTES do widget ser renderizado.
    opcoes = [str(opcao).strip() for opcao in (opcoes or []) if str(opcao or "").strip()]
    if not opcoes:
        opcoes = ["Digite para buscar"]

    valor_atual = str(valor_atual or "").strip().upper()

    if valor_atual and valor_atual in opcoes:
        index = opcoes.index(valor_atual)
    else:
        index = 0

    valor_padrao = opcoes[index] if 0 <= index < len(opcoes) else opcoes[0]

    # Streamlit reaproveita o valor salvo pela key. Se ele for "" ou um valor que saiu da API,
    # o selectbox quebra com: ValueError: <valor> is not in iterable.
    valor_state = st.session_state.get(key, None)
    if valor_state not in opcoes:
        st.session_state[key] = valor_padrao

    selecionado = st.selectbox(
        label,
        opcoes,
        index=index,
        key=key,
        disabled=disabled,
        label_visibility=label_visibility,
    )

    selecionado = str(selecionado or "").strip()

    if selecionado.startswith("➕ Adicionar novo"):
        st.info("Próxima etapa: abrir cadastro rápido sem sair do orçamento.")
        return ""

    if selecionado == "Digite para buscar":
        return ""

    return selecionado


def obter_opcoes_clientes():
    return montar_opcoes_busca_global("cliente")


def campo_busca_inteligente_cliente(label, valor_atual="", key="cliente_orcamento", disabled=False):
    return campo_busca_inteligente_global(
        label=label,
        tipo="cliente",
        valor_atual=valor_atual,
        key=key,
        disabled=disabled,
    )


def converter_data_br(valor):
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor), "%d/%m/%Y").date()
    except Exception:
        return None


def definir_periodo_orcamentos(label):
    hoje = date.today()

    if label == "Hoje":
        inicio = fim = hoje
    elif label == "Esta semana":
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    elif label == "Mês passado":
        primeiro_mes_atual = hoje.replace(day=1)
        ultimo_mes_passado = primeiro_mes_atual - timedelta(days=1)
        inicio = ultimo_mes_passado.replace(day=1)
        fim = ultimo_mes_passado
    elif label == "Próximo mês":
        ano = hoje.year + (1 if hoje.month == 12 else 0)
        mes = 1 if hoje.month == 12 else hoje.month + 1
        inicio = date(ano, mes, 1)
        fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    elif label == "Todo o período":
        inicio = date(2000, 1, 1)
        fim = date(2099, 12, 31)
    else:  # Este mês / Escolha o período
        inicio = hoje.replace(day=1)
        fim = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

    st.session_state.orcamentos_periodo_label = label
    st.session_state.orcamentos_data_inicio = inicio
    st.session_state.orcamentos_data_fim = fim


def limpar_busca_avancada_orcamentos():
    st.session_state.orcamentos_filtro_codigo = ""
    st.session_state.orcamentos_filtro_situacao = "Todos"
    st.session_state.orcamentos_filtro_cliente = ""
    st.session_state.orcamentos_filtro_produto = ""
    st.session_state.orcamentos_filtro_servico = ""
    st.session_state.orcamentos_filtro_centro_custo = "Todos"
    st.session_state.orcamentos_filtro_cliente_final = ""
    st.session_state.orcamentos_filtro_representante = ""
    st.session_state.orcamentos_filtro_tipo = "Todos"
    st.session_state.orcamentos_filtro_canal = "Todos"
    st.session_state.orcamentos_filtro_valor_de = 0.0
    st.session_state.orcamentos_filtro_valor_ate = 0.0
    definir_periodo_orcamentos("Este mês")


def filtrar_orcamentos(lista):
    busca_global = normalizar_texto(st.session_state.get("orcamentos_busca", ""))
    codigo = normalizar_texto(st.session_state.get("orcamentos_filtro_codigo", ""))
    cliente = normalizar_texto(normalizar_filtro_busca(st.session_state.get("orcamentos_filtro_cliente", "")))
    produto = normalizar_texto(st.session_state.get("orcamentos_filtro_produto", ""))
    servico = normalizar_texto(st.session_state.get("orcamentos_filtro_servico", ""))
    centro_custo = st.session_state.get("orcamentos_filtro_centro_custo", "Todos")
    cliente_final = normalizar_texto(normalizar_filtro_busca(st.session_state.get("orcamentos_filtro_cliente_final", "")))
    representante = normalizar_texto(normalizar_filtro_busca(st.session_state.get("orcamentos_filtro_representante", "")))
    situacao = st.session_state.get("orcamentos_filtro_situacao", "Todos")
    tipo_orcamento = st.session_state.get("orcamentos_filtro_tipo", "Todos")
    canal_venda = st.session_state.get("orcamentos_filtro_canal", "Todos")
    valor_de = float(st.session_state.get("orcamentos_filtro_valor_de", 0) or 0)
    valor_ate = float(st.session_state.get("orcamentos_filtro_valor_ate", 0) or 0)
    data_inicio = st.session_state.get("orcamentos_data_inicio")
    data_fim = st.session_state.get("orcamentos_data_fim")

    resultado = lista

    if data_inicio and data_fim:
        resultado = [
            o for o in resultado
            if converter_data_br(o.get("data"))
            and data_inicio <= converter_data_br(o.get("data")) <= data_fim
        ]

    if busca_global:

        def contem_busca_global(o):
            campos = [
                o.get("numero", ""),
                o.get("cliente", ""),
                o.get("cliente_final", ""),
                o.get("representante", ""),
                o.get("vendedor", ""),
                o.get("situacao", ""),
                o.get("tipo_orcamento", ""),
                o.get("canal_venda", ""),
                o.get("forma_pagamento", ""),
                o.get("observacoes", ""),
            ]
            campos += [p.get("produto", "") for p in o.get("produtos", [])]
            campos += [p.get("detalhe", "") for p in o.get("produtos", [])]
            campos += [s.get("servico", "") for s in o.get("servicos", [])]
            campos += [s.get("detalhe", "") for s in o.get("servicos", [])]
            return any(busca_global in normalizar_texto(campo) for campo in campos)

        resultado = [o for o in resultado if contem_busca_global(o)]

    if codigo:
        resultado = [o for o in resultado if codigo in normalizar_texto(o.get("numero"))]

    if situacao != "Todos":
        resultado = [o for o in resultado if o.get("situacao") == situacao]

    if tipo_orcamento != "Todos":
        resultado = [o for o in resultado if o.get("tipo_orcamento") == tipo_orcamento]

    if canal_venda != "Todos":
        resultado = [o for o in resultado if o.get("canal_venda") == canal_venda]

    if valor_de > 0:
        resultado = [o for o in resultado if float(o.get("valor_total", 0) or 0) >= valor_de]

    if valor_ate > 0:
        resultado = [o for o in resultado if float(o.get("valor_total", 0) or 0) <= valor_ate]

    if cliente:
        resultado = [o for o in resultado if cliente in normalizar_texto(o.get("cliente"))]

    if cliente_final:
        resultado = [o for o in resultado if cliente_final in normalizar_texto(o.get("cliente_final"))]

    if representante:
        resultado = [o for o in resultado if representante in normalizar_texto(o.get("representante"))]

    if centro_custo != "Todos":
        resultado = [o for o in resultado if normalizar_texto(o.get("centro_custo")) == normalizar_texto(centro_custo)]

    if produto:
        resultado = [
            o for o in resultado
            if any(produto in normalizar_texto(p.get("produto")) for p in o.get("produtos", []))
        ]

    if servico:
        resultado = [
            o for o in resultado
            if any(servico in normalizar_texto(s.get("servico")) for s in o.get("servicos", []))
        ]

    return resultado


def ir_listar():
    st.session_state.tela_orcamentos = "listar"
    st.session_state.id_orcamento_editar = None
    st.rerun()


def detectar_modelo_calculo_orcamento(nome_produto, registro=None):
    """
    Motor inicial do orçamento.
    Detecta o modelo de cálculo pelo nome/grupo do produto cadastrado.
    Nesta primeira entrega ativamos Rolô, Rolô Motorizada e Double Vision.
    Os demais produtos continuam no cálculo manual por quantidade x valor.
    """
    partes = [nome_produto]
    if isinstance(registro, dict):
        for campo in ["modelo", "grupo_produto", "tipo_produto", "familia_tecnica", "categoria", "descricao"]:
            if registro.get(campo):
                partes.append(str(registro.get(campo)))

    texto = " ".join([str(p or "") for p in partes]).upper()

    if "ROMANA DE TETO" in texto or "ROMANA_TETO" in texto:
        return "Romana de teto"
    if "ROMANA" in texto:
        return "Romana Motorizada" if any(t in texto for t in ["MOTORIZADA", "MOTOR", "MOTORIZADO"]) else "Romana"

    if any(t in texto for t in ["DOUBLE VISION", "DUPLA VISAO", "DUPLA VISÃO"]):
        if any(t in texto for t in ["MOTORIZADA", "MOTOR", "MOTORIZADO"]):
            return "Double Vision Motorizada"
        return "Double Vision"

    if any(t in texto for t in ["MOTORIZADA", "MOTOR", "MOTORIZADO"]):
        if any(t in texto for t in ["ROLÔ", "ROLO", "ROL "]):
            return "Rolô Motorizada"

    if any(t in texto for t in ["ROLÔ", "ROLO", "ROL "]):
        return "Rolô"

    return "Manual"


def escolher_tubo_rolo(largura):
    """
    Regra técnica central para Rolô (delega para app.technical.rules.rolo).
    Mantém interface compatível: retorna "32mm", "38mm", "43mm", "65mm" ou "".
    """
    try:
        from app.technical.rules.rolo import selecionar_tubo_rolo, MotorObrigatorioErro
    except Exception:
        # Fallback se módulo não estiver disponível
        try:
            largura = float(largura or 0)
        except Exception:
            largura = 0.0
        if largura <= 0:
            return ""
        if largura <= 1.80:
            return "32mm"
        if largura <= 2.50:
            return "38mm"
        if largura <= 3.20:
            return "43mm"
        return "65mm"

    try:
        largura = float(largura or 0)
    except Exception:
        largura = 0.0

    if largura <= 0:
        return ""

    try:
        selecao = selecionar_tubo_rolo(largura, acionamento="manual")
        return selecao.diametro.value
    except MotorObrigatorioErro:
        # Para orçamento, retorna a sugestão de motorização
        return "65mm"


def kit_por_tubo_rolo(tubo):
    tubo = str(tubo or "").strip()
    if "32" in tubo:
        return "Kit Comando Ação Premium 32mm"
    if "38" in tubo:
        return "Kit Comando Ação Premium 38mm"
    if "43" in tubo:
        return "Kit Comando Ação Premium 43mm"
    if "65" in tubo:
        return "Kit Comando Ação Premium 65mm"
    if "70" in tubo:
        return "Kit Comando Ação Premium 70mm"
    return ""


def calcular_item_produto_orcamento(modelo, largura, altura, quantidade_manual):
    """
    Calcula a quantidade comercial do item.
    Para modelos sob medida, quantidade = área m².
    Para itens manuais, mantém a quantidade digitada.
    """
    try:
        largura = float(largura or 0)
        altura = float(altura or 0)
    except Exception:
        largura, altura = 0.0, 0.0

    area = round(largura * altura, 3) if largura > 0 and altura > 0 else 0.0

    if modelo in ["Rolô", "Rolô Motorizada", "Double Vision", "Double Vision Motorizada", "Romana", "Romana Motorizada", "Romana de teto"] and area > 0:
        return area, area

    return float(quantidade_manual or 1), area


def montar_detalhe_calculo_produto(modelo, largura, altura, tubo, kit, detalhe_atual=""):
    try:
        largura = float(largura or 0)
        altura = float(altura or 0)
    except Exception:
        largura, altura = 0.0, 0.0

    if modelo not in ["Rolô", "Rolô Motorizada", "Double Vision"] or largura <= 0 or altura <= 0:
        return detalhe_atual or ""

    area = largura * altura
    partes = [
        f"{modelo}",
        f"Largura {largura:.2f}m".replace(".", ","),
        f"Altura {altura:.2f}m".replace(".", ","),
        f"Área {area:.2f}m²".replace(".", ","),
    ]

    if tubo:
        partes.append(f"Tubo {tubo}")
    if kit:
        partes.append(kit)

    return " | ".join(partes)


# =========================================================
# TABELAS / TIPO DE VENDA NO ORÇAMENTO
# =========================================================
CATEGORIA_TABELA_VENDA_ORCAMENTO = "valor_venda_produto"


def normalizar_percentual_orcamento(valor):
    try:
        return float(str(valor or "0").replace("%", "").replace(",", ".").strip())
    except Exception:
        return 0.0


def carregar_tabelas_venda_orcamento():
    """
    Carrega as tabelas reais cadastradas em Produtos > Valores de venda.
    Se a API não responder, mantém os três padrões do SmartTec.
    """
    padroes = [
        {"nome": "Varejo", "lucro": 100.0, "ordem": 1},
        {"nome": "Consumidor final", "lucro": 150.0, "ordem": 2},
        {"nome": "Decorador", "lucro": 50.0, "ordem": 3},
    ]

    tabelas = []

    try:
        if get_opcoes_auxiliares_por_categoria is not None:
            resposta = get_opcoes_auxiliares_por_categoria(CATEGORIA_TABELA_VENDA_ORCAMENTO)
            dados = normalizar_lista_api(resposta)
            for item in dados:
                if str(item.get("situacao", "Ativo")).strip().lower() == "inativo":
                    continue
                nome = str(item.get("nome", "")).strip()
                if not nome:
                    continue
                lucro = normalizar_percentual_orcamento(item.get("descricao", 0))
                tabelas.append({
                    "nome": nome,
                    "lucro": lucro,
                    "ordem": int(item.get("ordem") or 0),
                })
    except Exception:
        tabelas = []

    if not tabelas:
        tabelas = padroes

    # Garante que os três tipos básicos sempre existam.
    existentes = {str(t.get("nome", "")).strip().lower() for t in tabelas}
    for padrao in padroes:
        if padrao["nome"].lower() not in existentes:
            tabelas.append(padrao)

    tabelas = sorted(tabelas, key=lambda x: (x.get("ordem", 0), x.get("nome", "")))
    return tabelas


def opcoes_tipo_venda_orcamento():
    nomes = []
    for tabela in carregar_tabelas_venda_orcamento():
        nome = str(tabela.get("nome", "")).strip()
        if nome:
            nomes.append(nome)
    nomes = sorted(set(nomes), key=lambda x: x.lower())
    return nomes + ["➕ Cadastrar nova tabela"]


def obter_lucro_tabela_venda_orcamento(nome_tabela):
    nome_norm = normalizar_texto(nome_tabela)
    for tabela in carregar_tabelas_venda_orcamento():
        if normalizar_texto(tabela.get("nome")) == nome_norm:
            return float(tabela.get("lucro", 0) or 0)
    return 0.0


def calcular_valor_produto_por_tipo_venda(registro_produto, tipo_venda, valor_base=0.0):
    """
    Calcula o valor conforme o tipo/tabela de venda.
    Prioridade:
    1) Se existir custo no produto, calcula custo + lucro da tabela.
    2) Se não existir custo, usa valor_venda/preço do cadastro.
    """
    custo = extrair_float_registro(
        registro_produto,
        ["custo_final", "valor_custo", "vr_custo", "preco_custo", "custo", "valor_compra"],
        0.0,
    )

    if custo > 0:
        lucro = obter_lucro_tabela_venda_orcamento(tipo_venda)
        valor = Decimal(str(custo)) * (Decimal("1") + Decimal(str(lucro)) / Decimal("100"))
        return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    valor_cadastro = extrair_float_registro(
        registro_produto,
        ["valor_venda", "vr_venda", "preco_venda", "preco", "valor", "valor_unitario", "venda"],
        0.0,
    )

    if valor_cadastro > 0:
        return float(Decimal(str(valor_cadastro)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return float(Decimal(str(float(valor_base or 0))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def garantir_selectbox_valido(key, opcoes, valor_padrao):
    opcoes = [str(o).strip() for o in (opcoes or []) if str(o or "").strip()]
    if not opcoes:
        opcoes = [str(valor_padrao or "").strip() or "Selecione"]
    if str(st.session_state.get(key, "")).strip() not in opcoes:
        st.session_state[key] = valor_padrao if valor_padrao in opcoes else opcoes[0]
    return opcoes


def number_input_stateful(coluna, label, key, valor_padrao=0.0, min_value=0.0, step=1.0, disabled=False, format=None):
    """
    Campo numérico padrão SmartTec para linhas de itens.
    Evita o aviso do Streamlit:
    widget criado com value e também alterado via session_state.
    """
    if key not in st.session_state:
        st.session_state[key] = float(valor_padrao or 0)
    kwargs = dict(
        label=label,
        min_value=min_value,
        step=step,
        key=key,
        disabled=disabled,
        label_visibility="collapsed",
    )
    if format:
        kwargs["format"] = format
    return coluna.number_input(**kwargs)


# =========================================================
# MOTOR DOUBLE VISION / GRUPOS TÉCNICOS SMARTTEC
# =========================================================
GRUPOS_TECNICOS_SMARTTEC = [
    "Tecidos", "Tubos", "Acionamentos", "Motores", "Bandôs",
    "Tampas Bandô", "Suportes", "Correntes", "Controles",
    "Bases", "Acabamentos", "Fixação",
]

CORES_ACESSORIOS_SMARTTEC = ["Branco", "Preto", "Marfim", "Cinza", "Natural", "Personalizado"]


def qtd_grapas_double_vision(largura):
    """
    Double Vision:
    até 1,00m = 2 grapas.
    acima de 1,00m = +1 grapa a cada 50cm.
    """
    try:
        largura = float(largura or 0)
    except Exception:
        largura = 0.0
    if largura <= 1.0:
        return 2
    return max(2, 2 + math.ceil((largura - 1.0) / 0.50))


def tubo_double_vision(modelo, largura, tipo_motor="Convencional", *, tem_validacao_tecido_fornecedor=False):
    """
    Manual: 32/38 conforme largura (regra central Double Vision).
    Motorizada: 41mm padrão; 38mm somente motor bateria.

    Args:
        modelo: "Double Vision" ou "Double Vision Motorizada"
        largura: Largura em metros
        tipo_motor: Tipo de motorização
        tem_validacao_tecido_fornecedor: True se houver evidência explícita
            de compatibilidade do tecido/fornecedor para larguras > 2,60m
    """
    if modelo == "Double Vision Motorizada":
        return "38mm" if str(tipo_motor or "").lower().startswith("bateria") else "41mm"

    try:
        from app.technical.rules.double_vision import (
            selecionar_tubo_double_vision,
            LarguraExcedidaErro,
            LarguraInvalidaErro,
        )
    except Exception:
        # Fallback se módulo não estiver disponível
        try:
            largura_f = float(largura or 0)
        except Exception:
            largura_f = 0.0
        if largura_f <= 1.80:
            return "32mm"
        if largura_f <= 2.80:
            return "38mm"
        return "38mm"

    try:
        largura_f = float(largura or 0)
        selecao = selecionar_tubo_double_vision(largura_f, tem_validacao_tecido_fornecedor=tem_validacao_tecido_fornecedor)
        if selecao.diametro:
            return selecao.diametro.value
        # Se chegou aqui, é um estado de validação pendente ou bloqueado
        # Retorna o diâmetro técnico mas a validação deve ser feita no nível superior
        if selecao.estado.name == "REQUER_VALIDACAO":
            return "38mm"  # Diâmetro técnico, mas requer validação
        return ""
    except (LarguraExcedidaErro, LarguraInvalidaErro):
        return ""


def montar_nome_comercial_double_vision(modelo, com_bando=False):
    if modelo == "Double Vision Motorizada":
        nome = "Persiana Double Vision Motorizada"
    else:
        nome = "Persiana Double Vision"
    if com_bando:
        nome += " com Bandô"
    return nome


def montar_receita_double_vision(largura, altura, quantidade, modelo="Double Vision", com_bando=False, tipo_bando="Bandô Double Vision", cor="Branco", tipo_motor="Convencional", componentes_adicionais="", *, tem_validacao_tecido_fornecedor=False):
    """
    Receita técnica SmartTec para Double Vision manual e motorizada.
    O motor monta a receita padrão, mas o vendedor pode trocar/adicionar componentes no orçamento.
    """
    try:
        largura = float(largura or 0)
        altura = float(altura or 0)
        quantidade = float(quantidade or 1)
    except Exception:
        largura, altura, quantidade = 0.0, 0.0, 1.0

    largura_tecido = max(largura - 0.025, 0)  # largura - 2,5cm
    altura_tecido = max((altura * 2) + 0.15, 0)  # altura dupla + 15cm
    tubo = tubo_double_vision(modelo, largura, tipo_motor, tem_validacao_tecido_fornecedor=tem_validacao_tecido_fornecedor)
    comprimento_tubo = max(largura - 0.025, 0)
    qtd_grapas = qtd_grapas_double_vision(largura)
    manual = modelo == "Double Vision"

    receita = []

    def add(grupo, componente, regra, qtd, unidade="UN", cor_aplicavel=False, observacao=""):
        receita.append({
            "grupo": grupo,
            "componente": componente,
            "regra": regra,
            "quantidade": round(float(qtd or 0) * quantidade, 4),
            "unidade": unidade,
            "cor": cor if cor_aplicavel else "",
            "observacao": observacao,
        })

    add("Tecidos", "Tecido Double Vision", "Largura -2,5cm x altura dupla +15cm", largura_tecido * altura_tecido, "M²")

    if com_bando:
        add("Bandôs", tipo_bando or "Bandô Double Vision", "Largura total, substitui barra estabilizadora", largura, "ML", True)
        add("Tampas Bandô", "Tampa Bandô Double Vision", "Par fixo", 2, "UN", True)
    else:
        add("Acabamentos", "Barra Estabilizadora Double Vision", "Largura total sem desconto", largura, "ML", True)

    add("Tubos", f"Tubo {tubo}", "Largura -2,5cm", comprimento_tubo, "ML")

    if manual:
        add("Acionamentos", f"Kit Comando Ação Premium {tubo}", "1 kit compatível com o tubo", 1, "KIT", True)
        add("Correntes", "Corrente Juta Bola 10", "90% da altura x 2", altura * 0.90 * 2, "ML", True)
        add("Correntes", "Emenda Corrente", "Fixo", 3, "UN", True)
        add("Acabamentos", "Pêndulo Cristal", "1 por persiana", 1, "UN")
    else:
        add("Motores", "Motor Double Vision", "Motor conforme especificação do orçamento", 1, "UN")
        add("Motores", "Suporte/Adaptador Motor Double Vision", "Kit de instalação do motor", 1, "KIT", True)
        add("Controles", "Controle Motor", "1 controle por ambiente/persiana conforme venda", 1, "UN")

    add("Bases", "Eixo Base Double Vision", "Largura -2,8cm", max(largura - 0.028, 0), "ML", True)
    add("Bases", "Base Cunha Double Vision", "Largura -2,0cm", max(largura - 0.020, 0), "ML", True)
    add("Acabamentos", "Tampa Redonda do Eixo Double Vision", "Par fixo", 2, "UN", True)
    add("Acabamentos", "Tampa Base Double Vision", "Par fixo", 2, "UN", True)
    add("Suportes", "CLIPS E SUPORTES - GRAPA 40MM BRANCA - IMPORTADA", "Até 1m = 2; depois +1 a cada 50cm", qtd_grapas, "UN", True)
    add("Acabamentos", "Espaguete 2,5mm", "Largura -2,5cm", largura_tecido, "ML", True)
    add("Acabamentos", "Fita Plástica 1,5mm", "Largura -2,5cm", largura_tecido, "ML", True)

    for linha in str(componentes_adicionais or "").splitlines():
        componente = linha.strip()
        if componente:
            add("Ajuste vendedor", componente, "Componente adicional informado no orçamento", 1, "UN")

    return receita


def resumo_receita_double_vision(receita):
    partes = []
    for item in receita or []:
        comp = item.get("componente", "")
        qtd = item.get("quantidade", 0)
        un = item.get("unidade", "")
        cor = item.get("cor", "")
        if cor:
            partes.append(f"{comp} {cor}: {str(f'{qtd:.2f}').replace('.', ',')} {un}")
        else:
            partes.append(f"{comp}: {str(f'{qtd:.2f}').replace('.', ',')} {un}")
    return " | ".join(partes)


def render_item_produto(prefixo, item=None, disabled=False):
    item = item or {}

    # Padrão GestãoClick / SmartTec:
    # Quantidade = quantidade de peças.
    # Área m² fica automática no motor e aparece somente na linha informativa.
    # Produto / Detalhes / Quant. / Tipo / Largura / Altura / Valor / Desconto / Subtotal / Ação
    pesos_produto = [2.35, 1.15, 0.78, 1.05, 0.78, 0.78, 0.90, 1.05, 0.95, 0.46]

    headers = st.columns(pesos_produto)
    titulos = [
        'Produto<span class="req">*</span>',
        'Detalhes',
        'Quant.<span class="req">*</span>',
        'Tipo<span class="req">*</span>',
        'Largura',
        'Altura',
        'Valor<span class="req">*</span>',
        'Desconto',
        'Subtotal',
        'Ação',
    ]
    for col, titulo in zip(headers, titulos):
        col.markdown(f'<div class="orc-item-header">{titulo}</div>', unsafe_allow_html=True)

    st.markdown('<div class="orc-item-row-spacer"></div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(pesos_produto)

    with c1:
        produto = campo_busca_inteligente_global(
            "Produto*",
            tipo="produto",
            valor_atual=item.get("produto", ""),
            key=f"{prefixo}_produto",
            disabled=disabled,
            label_visibility="collapsed",
        )

    registro_produto = obter_registro_por_nome("produto", produto)
    registros_produtos_api = carregar_cadastros_api("produto") if produto else []
    if produto and registros_produtos_api:
        produto_id_atual = item.get("produto_id")
        candidatos_produto = [
            registro for registro in registros_produtos_api
            if normalizar_texto(extrair_valor_registro(registro, campos_nome_por_tipo("produto"))) == normalizar_texto(produto)
            and registro.get("ativo", True) is not False
            and normalizar_texto(registro.get("situacao", "Ativo")) != "inativo"
        ]
        registro_por_id = next(
            (registro for registro in candidatos_produto if produto_id_atual and registro.get("id") == produto_id_atual),
            None,
        )
        if registro_por_id or not registro_produto.get("familia_tecnica"):
            registro_produto = registro_por_id or (candidatos_produto[0] if candidatos_produto else registro_produto)
    modelo_calculo = detectar_modelo_calculo_orcamento(produto, registro_produto)

    cor_produto = str(item.get("cor", "") or cor_estruturada_produto(registro_produto)).strip()
    if registro_produto.get("familia_tecnica"):
        # Para trocar SKU, use o cadastro autoritativo da API; listas auxiliares
        # da sessão podem repetir ou simplificar produtos e tornar a cor ambígua.
        registros_produtos = registros_produtos_api or montar_registros_busca_global("produto")
        cores_familia = opcoes_cor_familia_orcamento(registros_produtos, registro_produto)
        if cores_familia:
            cor_produto = st.selectbox(
                "Cor/variação do produto",
                cores_familia,
                index=cores_familia.index(cor_produto) if cor_produto in cores_familia else 0,
                key=f"{prefixo}_cor_produto",
                disabled=disabled,
            )
            substituto = procurar_substituto_mesma_familia_cor_orcamento(
                registros_produtos, registro_produto, cor_produto
            )
            if substituto:
                registro_produto = substituto
                produto = str(substituto.get("nome") or produto)
                modelo_calculo = detectar_modelo_calculo_orcamento(produto, registro_produto)

    detalhe_padrao = item.get("detalhe", "") or ""
    detalhe = c2.text_input(
        "Detalhes",
        value=detalhe_padrao,
        key=f"{prefixo}_detalhe",
        disabled=disabled,
        label_visibility="collapsed",
    )

    # Quantidade comercial do orçamento: número de peças.
    quantidade_pecas = number_input_stateful(
        c3,
        "Quant.*",
        key=f"{prefixo}_quant",
        valor_padrao=float(item.get("quantidade", item.get("quantidade_pecas", 1)) or 1),
        min_value=0.0,
        step=1.0,
        disabled=disabled,
    )

    opcoes_tipo = opcoes_tipo_venda_orcamento()
    tipo_padrao = str(item.get("tipo_venda", "") or "Varejo").strip()
    opcoes_tipo = garantir_selectbox_valido(f"{prefixo}_tipo_venda", opcoes_tipo, tipo_padrao)
    tipo_venda = c4.selectbox(
        "Tipo*",
        opcoes_tipo,
        key=f"{prefixo}_tipo_venda",
        disabled=disabled,
        label_visibility="collapsed",
    )

    if tipo_venda == "➕ Cadastrar nova tabela":
        st.info("Para cadastrar uma nova tabela, acesse Produtos > Valores de venda. Depois ela aparecerá aqui automaticamente.")
        tipo_venda_calculo = "Varejo"
    else:
        tipo_venda_calculo = tipo_venda

    largura = number_input_stateful(
        c5,
        "Largura",
        key=f"{prefixo}_largura",
        valor_padrao=float(item.get("largura", 0) or 0),
        min_value=0.0,
        step=0.01,
        disabled=disabled,
        format="%.2f",
    )

    altura = number_input_stateful(
        c6,
        "Altura",
        key=f"{prefixo}_altura",
        valor_padrao=float(item.get("altura", 0) or 0),
        min_value=0.0,
        step=0.01,
        disabled=disabled,
        format="%.2f",
    )

    # Opções técnicas do produto.
    # Para Double Vision, o vendedor escolhe Bandô/Cor e o motor monta a receita automaticamente.
    com_bando = False
    tipo_bando = "Bandô Double Vision"
    cor_acessorios = str(item.get("cor_acessorios", "Branco") or "Branco")
    tipo_motor_dv = str(item.get("tipo_motor", "Convencional") or "Convencional")
    componentes_adicionais = str(item.get("componentes_adicionais", "") or "")

    material = str(item.get("material", "") or "")
    cor_romana = cor_produto
    acionamento = str(item.get("acionamento", "Manual") or "Manual")
    lado_comando = str(item.get("lado_comando", "Direito") or "Direito")
    if modelo_calculo in ["Romana", "Romana Motorizada", "Romana de teto"]:
        st.caption("Cálculo de produção pendente — preço comercial por m².")
        rc1, rc2, rc3, rc4 = st.columns(4)
        material = rc1.text_input("Tecido/material", value=material, key=f"{prefixo}_material", disabled=disabled)
        cor_romana = rc2.text_input("Cor", value=cor_romana, key=f"{prefixo}_cor_romana", disabled=disabled)
        acionamento = rc3.selectbox("Acionamento", ["Manual", "Motorizado"], index=1 if acionamento == "Motorizado" else 0, key=f"{prefixo}_acionamento", disabled=disabled)
        if acionamento == "Manual":
            lado_comando = rc4.selectbox("Lado do comando", ["Direito", "Esquerdo"], index=1 if lado_comando == "Esquerdo" else 0, key=f"{prefixo}_lado_comando", disabled=disabled)

    if modelo_calculo in ["Double Vision", "Double Vision Motorizada"]:
        opt_cols = st.columns([0.85, 1.25, 1.05, 1.15, 2.20])
        with opt_cols[0]:
            com_bando = st.checkbox(
                "Com bandô",
                value=bool(item.get("com_bando", False)),
                key=f"{prefixo}_com_bando",
                disabled=disabled,
            )
        with opt_cols[1]:
            if com_bando:
                tipo_bando = st.selectbox(
                    "Tipo de bandô",
                    ["Bandô Double Vision", "Bandô 90mm", "Bandô 100mm", "Bandô 120mm"],
                    key=f"{prefixo}_tipo_bando",
                    disabled=disabled,
                )
            else:
                st.caption("Sem bandô: usa barra estabilizadora.")
        with opt_cols[2]:
            cor_acessorios = st.selectbox(
                "Cor acessórios",
                CORES_ACESSORIOS_SMARTTEC,
                index=CORES_ACESSORIOS_SMARTTEC.index(cor_acessorios) if cor_acessorios in CORES_ACESSORIOS_SMARTTEC else 0,
                key=f"{prefixo}_cor_acessorios",
                disabled=disabled,
            )
        with opt_cols[3]:
            if modelo_calculo == "Double Vision Motorizada":
                tipo_motor_dv = st.selectbox(
                    "Tipo motor",
                    ["Convencional", "Bateria"],
                    key=f"{prefixo}_tipo_motor",
                    disabled=disabled,
                )
            else:
                st.caption("Manual: kit comando ação premium.")
        with opt_cols[4]:
            componentes_adicionais = st.text_input(
                "+ componentes",
                value=componentes_adicionais,
                key=f"{prefixo}_componentes_add",
                disabled=disabled,
                placeholder="Ex.: suporte especial; controle extra",
            )

    # Área técnica calculada automaticamente pelo motor.
    # Não aparece como campo editável para o vendedor.
    _, area_unitaria_m2 = calcular_item_produto_orcamento(
        modelo_calculo,
        largura,
        altura,
        1,
    )
    quantidade_pecas_float = float(quantidade_pecas or 0)
    area_m2 = round(float(area_unitaria_m2 or 0) * quantidade_pecas_float, 3)

    if modelo_calculo in ["Double Vision", "Double Vision Motorizada"]:
        tubo = tubo_double_vision(modelo_calculo, largura, tipo_motor_dv, tem_validacao_tecido_fornecedor=False)
    else:
        tubo = escolher_tubo_rolo(largura) if modelo_calculo in ["Rolô", "Rolô Motorizada"] else ""
    kit = kit_por_tubo_rolo(tubo) if modelo_calculo != "Double Vision Motorizada" else ""

    valor_base_item = float(item.get("valor", 0) or 0)
    valor_calculado = calcular_valor_produto_por_tipo_venda(
        registro_produto,
        tipo_venda_calculo,
        valor_base=valor_base_item,
    )

    chave_valor = f"{prefixo}_valor"
    chave_controle_valor = f"{prefixo}_produto_tipo_valor_atual"
    controle_atual = f"{produto}|{tipo_venda_calculo}"
    if not disabled and st.session_state.get(chave_controle_valor) != controle_atual:
        # Só altera antes do widget de Valor ser criado neste rerun.
        st.session_state[chave_valor] = float(valor_calculado or 0)
        st.session_state[chave_controle_valor] = controle_atual

    valor = number_input_stateful(
        c7,
        "Valor*",
        key=chave_valor,
        valor_padrao=valor_calculado,
        min_value=0.0,
        step=1.0,
        disabled=disabled,
    )

    desconto = number_input_stateful(
        c8,
        "Desconto",
        key=f"{prefixo}_desc",
        valor_padrao=float(item.get("desconto", 0) or 0),
        min_value=0.0,
        step=1.0,
        disabled=disabled,
    )

    # Para Rolô/Double Vision, valor comercial continua por m².
    # O campo Quant. mostra peças, e a área fica automática no motor.
    modelos_area = ["Rolô", "Rolô Motorizada", "Double Vision", "Double Vision Motorizada", "Romana", "Romana Motorizada", "Romana de teto"]
    base_calculo_subtotal = area_m2 if modelo_calculo in modelos_area and area_m2 > 0 else quantidade_pecas_float
    subtotal = max(0, float(base_calculo_subtotal or 0) * float(valor or 0) - float(desconto or 0))
    c9.text_input(
        "Subtotal",
        value=f"{subtotal:.2f}".replace(".", ","),
        key=f"{prefixo}_subtotal",
        disabled=True,
        label_visibility="collapsed",
    )

    # Botão excluir visual igual ao bloco de Pagamento.
    c10.markdown(
        """
        <div style="display:flex;align-items:center;justify-content:center;height:36px;">
            <button type="button" style="width:36px;height:36px;min-width:36px;border-radius:4px;border:1px solid #dc3545;background:#dc3545;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;padding:0;margin:0;box-shadow:none;cursor:default;">×</button>
        </div>
        """,
        unsafe_allow_html=True,
    )

    receita_tecnica = []
    nome_exibicao = produto
    if modelo_calculo in ["Double Vision", "Double Vision Motorizada"]:
        nome_exibicao = montar_nome_comercial_double_vision(modelo_calculo, com_bando=com_bando)
        receita_tecnica = montar_receita_double_vision(
            largura=largura,
            altura=altura,
            quantidade=quantidade_pecas_float,
            modelo=modelo_calculo,
            com_bando=com_bando,
            tipo_bando=tipo_bando,
            cor=cor_acessorios,
            tipo_motor=tipo_motor_dv,
            componentes_adicionais=componentes_adicionais,
            tem_validacao_tecido_fornecedor=False,
        )

    if produto and modelo_calculo != "Manual":
        st.caption(
            f"Motor aplicado: {modelo_calculo} | Peças: {str(f'{quantidade_pecas_float:.0f}').replace('.', ',')}"
            f" | Área comercial: {str(f'{area_m2:.2f}').replace('.', ',')} m²"
            +(f" | Tubo: {tubo}" if tubo else "")
            +(f" | {kit}" if kit else "")
            +(f" | {('com Bandô' if com_bando else 'sem Bandô')}" if modelo_calculo in ["Double Vision", "Double Vision Motorizada"] else "")
            +f" | Subtotal: {moeda_br(subtotal)}"
        )

        if receita_tecnica:
            with st.expander("🧩 Receita técnica calculada / ajustes do vendedor", expanded=False):
                st.caption("O motor monta a receita padrão. O vendedor pode trocar cor, tipo de bandô e acrescentar componentes no item.")
                st.dataframe(receita_tecnica, use_container_width=True, hide_index=True)

    return {
        "produto": nome_exibicao or produto,
        "produto_original": produto,
        "modelo_calculo": modelo_calculo,
        "com_bando": bool(com_bando),
        "tipo_bando": tipo_bando,
        "cor_acessorios": cor_acessorios,
        "tipo_motor": tipo_motor_dv,
        "componentes_adicionais": componentes_adicionais,
        "receita_tecnica": receita_tecnica,
        "tipo_venda": tipo_venda_calculo,
        "quantidade": quantidade_pecas_float,
        "quantidade_pecas": quantidade_pecas_float,
        "largura": float(largura or 0),
        "altura": float(altura or 0),
        "area_m2": float(area_m2 or 0),
        "tubo": tubo,
        "kit": kit,
        "detalhe": detalhe,
        "valor": valor,
        "desconto": desconto,
        "subtotal": subtotal,
        "produto_id": (registro_produto or {}).get("id"), "codigo_interno": (registro_produto or {}).get("codigo_interno") or (registro_produto or {}).get("codigo"),
        "grupo_tecnico": (registro_produto or {}).get("grupo_tecnico"), "modelo_tecnico": "ROMANA_TETO" if modelo_calculo == "Romana de teto" else ("ROMANA" if modelo_calculo.startswith("Romana") else (registro_produto or {}).get("modelo_tecnico")),
        "unidade": (registro_produto or {}).get("unidade_venda") or "M²", "material":material, "cor":cor_romana, "acionamento":acionamento,
        "lado_comando": lado_comando if acionamento == "Manual" else None, "calculo_producao_status":"CALCULO_PRODUCAO_PENDENTE" if modelo_calculo.startswith("Romana") else None,
    }


def render_item_servico(prefixo, item=None, disabled=False):
    item = item or {}

    # Serviços: sem campo Unidade. Quantidade fica como número normal de serviços/peças.
    pesos_servico = [2.20, 1.75, 0.85, 1.20, 1.35, 1.10, 0.42]

    headers = st.columns(pesos_servico)
    titulos = [
        'Serviço<span class="req">*</span>',
        'Detalhes',
        'Quant.<span class="req">*</span>',
        'Valor<span class="req">*</span>',
        'Desconto',
        'Subtotal',
        'Ação',
    ]
    for col, titulo in zip(headers, titulos):
        col.markdown(f'<div class="orc-item-header">{titulo}</div>', unsafe_allow_html=True)

    st.markdown('<div class="orc-item-row-spacer"></div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6, c7 = st.columns(pesos_servico)

    with c1:
        servico = campo_busca_inteligente_global(
            "Serviço*",
            tipo="servico",
            valor_atual=item.get("servico", ""),
            key=f"{prefixo}_servico",
            disabled=disabled,
            label_visibility="collapsed",
        )

    if not disabled:
        atualizar_valor_item_por_cadastro(prefixo, "servico", servico, item)

    registro_servico = obter_registro_por_nome("servico", servico)
    detalhe_padrao = item.get("detalhe", "") or extrair_detalhe_registro(registro_servico)

    detalhe = c2.text_input("Detalhes", value=detalhe_padrao, key=f"{prefixo}_detalhe", disabled=disabled, label_visibility="collapsed")
    quantidade = number_input_stateful(c3, "Quant.*", key=f"{prefixo}_quant", valor_padrao=float(item.get("quantidade", 1) or 1), min_value=0.0, step=1.0, disabled=disabled)

    valor_padrao = float(item.get("valor", 0) or extrair_float_registro(registro_servico, ["valor_venda", "vr_venda", "preco_venda", "preco", "valor", "valor_unitario", "venda"], 0.0) or 0)
    valor = number_input_stateful(c4, "Valor*", key=f"{prefixo}_valor", valor_padrao=valor_padrao, min_value=0.0, step=1.0, disabled=disabled)
    desconto = number_input_stateful(c5, "Desconto", key=f"{prefixo}_desc", valor_padrao=float(item.get("desconto", 0) or 0), min_value=0.0, step=1.0, disabled=disabled)
    subtotal = max(0, quantidade * valor - desconto)
    c6.text_input("Subtotal", value=f"{subtotal:.2f}".replace(".", ","), key=f"{prefixo}_subtotal", disabled=True, label_visibility="collapsed")

    c7.markdown(
        """
        <div style="display:flex;align-items:center;justify-content:center;height:36px;">
            <button type="button" style="width:36px;height:36px;min-width:36px;border-radius:4px;border:1px solid #dc3545;background:#dc3545;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;padding:0;margin:0;box-shadow:none;cursor:default;">×</button>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return {
        "servico": servico,
        "detalhe": detalhe,
        "quantidade": quantidade,
        "valor": valor,
        "desconto": desconto,
        "subtotal": subtotal,
    }


def bloco_produtos(orcamento=None, disabled=False):
    st.markdown('<div class="orc-form-wide">', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-title">📦 Produtos</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

    produtos = (orcamento or {}).get("produtos") or []
    chave_linhas = f"orc_produtos_linhas_{(orcamento or {}).get('id', 'novo')}"
    if chave_linhas not in st.session_state:
        st.session_state[chave_linhas] = list(range(1, max(1, len(produtos)) + 1))

    linhas = list(st.session_state.get(chave_linhas) or [1])
    produtos_renderizados = []
    remover_linha = None
    for indice, linha_id in enumerate(linhas):
        item_base = produtos[indice] if indice < len(produtos) else {}
        produto = render_item_produto(f"orc_prod_{linha_id}", item_base, disabled=disabled)
        if produto.get("produto"):
            produtos_renderizados.append(produto)
        if not disabled and len(linhas) > 1 and st.button("Remover produto", key=f"btn_rem_produto_orc_{linha_id}"):
            remover_linha = linha_id

    if remover_linha is not None:
        st.session_state[chave_linhas] = [linha for linha in linhas if linha != remover_linha]
        st.rerun()

    st.markdown('<div class="orc-btn-add-row">', unsafe_allow_html=True)
    if st.button("✚ Adicionar produto", key="btn_add_produto_orc", disabled=disabled):
        proximo_id_linha = max(linhas or [0]) + 1
        st.session_state[chave_linhas] = linhas + [proximo_id_linha]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return produtos_renderizados


def bloco_servicos(orcamento=None, disabled=False):
    st.markdown('<div class="orc-form-wide">', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-title">🛠️ Serviços</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

    servicos = (orcamento or {}).get("servicos") or []
    item_base = servicos[0] if servicos else {}
    servico = render_item_servico("orc_serv_1", item_base, disabled=disabled)

    st.markdown('<div class="orc-btn-add-row">', unsafe_allow_html=True)
    if st.button("✚ Adicionar serviço", key="btn_add_servico_orc", disabled=disabled):
        st.info("Próxima etapa: buscar serviços cadastrados no módulo Serviços.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return [servico] if servico.get("servico") else []


def tela_listar_orcamentos():
    cabecalho("📋 Orçamentos", "Orçamentos", "Listar")

    mensagem_acao = st.session_state.pop("orcamento_acao_mensagem", None)
    if mensagem_acao:
        tipo_msg = mensagem_acao.get("tipo", "info")
        texto_msg = mensagem_acao.get("texto", "")
        if tipo_msg == "success":
            st.success(texto_msg)
        elif tipo_msg == "warning":
            st.warning(texto_msg)
        else:
            st.info(texto_msg)

    # Toolbar no padrão Produtos, porém sem campo Buscar na tela de Orçamentos.
    # Ordem: Adicionar + Mais ações + Colunas(ícone) + espaço + Período + Busca avançada.
    col_add, col_mais, col_cols, col_spacer, col_periodo, col_busca_av = st.columns(
        [1.05, 1.75, 0.50, 4.45, 1.55, 1.75]
    )

    # Garante que uma busca global antiga não continue filtrando escondida.
    st.session_state.orcamentos_busca = ""

    with col_add:
        if st.button("Adicionar+", type="primary", use_container_width=True):
            st.session_state.tela_orcamentos = "adicionar"
            st.session_state.id_orcamento_editar = None
            st.rerun()

    with col_mais:
        with st.popover("⚙ Mais ações", use_container_width=True):
            st.markdown("**Ações em lote**")

            st.download_button(
                "📤 Exportar CSV",
                data=gerar_csv_orcamentos(filtrar_orcamentos(st.session_state.orcamentos_lista)),
                file_name=f"orcamentos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            if st.button("🗂️ Agrupar por situação", use_container_width=True):
                st.session_state.orcamentos_agrupar_situacao = not st.session_state.get("orcamentos_agrupar_situacao", False)
                st.rerun()

            if st.button("✉️ Enviar e-mails", use_container_width=True):
                st.info("Próxima etapa: selecionar orçamentos e enviar por e-mail.")

            if st.button("🖊️ Gerar e-Assinaturas", use_container_width=True):
                st.info("Próxima etapa: gerar e-assinaturas dos orçamentos selecionados.")

            if st.button("❌ Excluir selecionados", use_container_width=True):
                st.warning("Seleção em lote será ativada na próxima etapa para excluir múltiplos orçamentos com segurança.")

    with col_cols:
        # Somente ícone, igual ao padrão Produtos.
        with st.popover("☷", use_container_width=True):
            st.markdown("**Gerenciar colunas**")
            st.checkbox("Nº", key="orc_col_numero")
            st.checkbox("Cliente", key="orc_col_cliente")
            st.checkbox("Cliente final", key="orc_col_cliente_final")
            st.checkbox("Representante", key="orc_col_representante")
            st.checkbox("Data", key="orc_col_data")
            st.checkbox("Situação", key="orc_col_situacao")
            st.checkbox("Valor", key="orc_col_valor")

    with col_periodo:
        periodo_atual = st.session_state.get("orcamentos_periodo_label", "Este mês")
        with st.popover(periodo_atual, use_container_width=True):
            for opcao in ["Hoje", "Esta semana", "Mês passado", "Este mês", "Próximo mês", "Todo o período", "Escolha o período"]:
                if st.button(opcao, key=f"orc_periodo_{opcao}", use_container_width=True):
                    definir_periodo_orcamentos(opcao)
                    if opcao == "Escolha o período":
                        st.session_state.orcamentos_busca_avancada_aberta = True
                    st.rerun()

    with col_busca_av:
        # Link estilizado para ficar 100% preto com letras brancas, igual Produtos.
        busca_aberta = st.session_state.get("orcamentos_busca_avancada_aberta", False)
        destino = "0" if busca_aberta else "1"
        texto = "🔎 Ocultar busca" if busca_aberta else "🔎 Busca avançada"
        html_botao_busca = f"""
        <a class="orc-toolbar-btn-dark"
           href="?go_to=orcamentos&busca_avancada_orcamentos={destino}"
           target="_self"
           style="background:#111827 !important; border:1px solid #111827 !important; color:#ffffff !important; text-decoration:none !important;">
            <span style="color:#ffffff !important; text-decoration:none !important;">{texto}</span>
        </a>
        """
        st.markdown(html_botao_busca, unsafe_allow_html=True)

    if st.session_state.get("orcamentos_busca_avancada_aberta", False):
        st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

        a1, a2, a3, a4, a5 = st.columns([1.25, 1.25, 1.70, 1.70, 1.70])
        a1.date_input("Período inicial", key="orcamentos_data_inicio", format="DD/MM/YYYY")
        a2.date_input("Período final", key="orcamentos_data_fim", format="DD/MM/YYYY")
        with a3:
            campo_busca_inteligente_global(
                "Cliente",
                tipo="cliente",
                valor_atual=normalizar_filtro_busca(st.session_state.get("orcamentos_filtro_cliente", "")),
                key="orcamentos_filtro_cliente",
            )
        with a4:
            campo_busca_inteligente_global(
                "Cliente final",
                tipo="cliente_final",
                valor_atual=normalizar_filtro_busca(st.session_state.get("orcamentos_filtro_cliente_final", "")),
                key="orcamentos_filtro_cliente_final",
            )
        with a5:
            campo_busca_inteligente_global(
                "Representante",
                tipo="representante",
                valor_atual=normalizar_filtro_busca(st.session_state.get("orcamentos_filtro_representante", "")),
                key="orcamentos_filtro_representante",
            )

        b1, b2, b3, b4, b5 = st.columns([1.35, 1.45, 1.45, 1.15, 1.15])
        b1.selectbox("Situação", ["Todos"] + SITUACOES_ORCAMENTO, key="orcamentos_filtro_situacao")
        b2.selectbox("Tipo de orçamento", ["Todos"] + TIPOS_ORCAMENTO, key="orcamentos_filtro_tipo")
        b3.selectbox("Canal de venda", ["Todos"] + CANAIS_VENDA, key="orcamentos_filtro_canal")
        b4.number_input("Valor de", min_value=0.0, step=50.0, key="orcamentos_filtro_valor_de")
        b5.number_input("Valor até", min_value=0.0, step=50.0, key="orcamentos_filtro_valor_ate")

        c1, c2, c3, c4 = st.columns([1.70, 1.70, 1.05, 1.05])
        c1.text_input("Produto", key="orcamentos_filtro_produto", placeholder="Digite para buscar")
        c2.text_input("Serviço", key="orcamentos_filtro_servico", placeholder="Digite para buscar")

        # Espaço para alinhar os botões com a altura dos campos Produto/Serviço.
        c3.markdown('<div class="orc-filter-button-spacer"></div>', unsafe_allow_html=True)
        c4.markdown('<div class="orc-filter-button-spacer"></div>', unsafe_allow_html=True)

        if c3.button("↻ Limpar filtros", key="btn_orc_limpar_av", use_container_width=True):
            limpar_busca_avancada_orcamentos()
            st.rerun()
        if c4.button("🔎 Pesquisar", key="btn_orc_buscar_av", type="primary", use_container_width=True):
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    lista = filtrar_orcamentos(st.session_state.orcamentos_lista)
    if st.session_state.get("orcamentos_agrupar_situacao", False):
        lista = sorted(lista, key=lambda x: (x.get("situacao", ""), x.get("cliente", "")))
        st.caption(f"Mostrando {len(lista)} orçamento(s) de {len(st.session_state.orcamentos_lista)} cadastrado(s). Agrupado por situação.")
    else:
        st.caption(f"Mostrando {len(lista)} orçamento(s) de {len(st.session_state.orcamentos_lista)} cadastrado(s).")

    if not lista:
        st.info("Nenhum orçamento encontrado.")
        return

    colunas = []
    if st.session_state.get("orc_col_numero", True):
        colunas.append(("numero", "Nº", 0.65))
    if st.session_state.get("orc_col_cliente", True):
        colunas.append(("cliente", "Cliente", 2.20))
    if st.session_state.get("orc_col_cliente_final", True):
        colunas.append(("cliente_final", "Cliente final", 1.50))
    if st.session_state.get("orc_col_representante", True):
        colunas.append(("representante", "Representante", 1.50))
    if st.session_state.get("orc_col_data", True):
        colunas.append(("data", "Data", 1.00))
    if st.session_state.get("orc_col_situacao", True):
        colunas.append(("situacao", "Situação", 1.00))
    if st.session_state.get("orc_col_valor", True):
        colunas.append(("valor_total", "Valor", 1.05))

    pesos = [c[2] for c in colunas] + [1.45]
    header = st.columns(pesos)

    for col, (_, titulo, _) in zip(header[:-1], colunas):
        col.markdown(f'<div class="orc-table-header">{titulo}</div>', unsafe_allow_html=True)
    header[-1].markdown('<div class="orc-table-header">Ações</div>', unsafe_allow_html=True)

    for o in lista:
        cols = st.columns(pesos)

        for col, (campo, _, _) in zip(cols[:-1], colunas):
            valor = o.get(campo, "")
            if campo == "valor_total":
                valor = moeda_br(valor)
            col.markdown(f'<div class="orc-table-cell">{valor}</div>', unsafe_allow_html=True)

        with cols[-1]:
            oid = o["id"]
            a1, a2, a3, a4 = st.columns([0.34, 0.34, 0.34, 0.36])

            a1.markdown(
                f'<a class="orc-btn-action orc-btn-view" href="?go_to=orcamentos&acao_orcamento=visualizar&id_orcamento={oid}" target="_self" title="Visualizar">🔍</a>',
                unsafe_allow_html=True,
            )
            a2.markdown(
                f'<a class="orc-btn-action orc-btn-edit" href="?go_to=orcamentos&acao_orcamento=editar&id_orcamento={oid}" target="_self" title="Editar">✎</a>',
                unsafe_allow_html=True,
            )
            a3.markdown(
                f'<a class="orc-btn-action orc-btn-delete" href="?go_to=orcamentos&acao_orcamento=excluir&id_orcamento={oid}" target="_self" title="Excluir">×</a>',
                unsafe_allow_html=True,
            )

            a4.markdown(
                f"""
                <div class="orc-menu-dropdown-wrap">
                    <a class="orc-btn-action orc-btn-menu" href="#" title="Mais ações">▾</a>
                    <div class="orc-menu-dropdown">
                        <a href="?go_to=orcamentos&acao_orcamento=visualizar&id_orcamento={oid}" target="_self">📄 Ver proposta</a>

                        <div class="orc-menu-section">
                            <div class="orc-menu-muted">Imprimir</div>
                            <a href="?go_to=orcamentos&acao_orcamento=pdf_cliente&id_orcamento={oid}" target="_self">🖨️ PDF Cliente</a>
                            <a href="?go_to=orcamentos&acao_orcamento=pdf_parceiro&id_orcamento={oid}" target="_self">🤝 PDF Parceiro</a>
                            <a href="?go_to=orcamentos&acao_orcamento=pdf_interno&id_orcamento={oid}" target="_self">🔒 PDF Interno</a>
                        </div>

                        <div class="orc-menu-section">
                            <div class="orc-menu-muted">Compartilhar</div>
                            <a href="?go_to=orcamentos&acao_orcamento=email&id_orcamento={oid}" target="_self">✉️ Via E-mail</a>
                            <a href="?go_to=orcamentos&acao_orcamento=whatsapp&id_orcamento={oid}" target="_self">🟢 Via WhatsApp</a>
                        </div>

                        <div class="orc-menu-section">
                            <a href="?go_to=orcamentos&acao_orcamento=alterar_situacao&id_orcamento={oid}" target="_self">☑️ Alterar situação</a>
                        </div>

                        <div class="orc-menu-section">
                            <div class="orc-menu-muted">Gerar</div>
                            <a href="?go_to=orcamentos&acao_orcamento=gerar_copia&id_orcamento={oid}" target="_self">📋 Cópia</a>
                            <a href="?go_to=orcamentos&acao_orcamento=gerar_pedido&id_orcamento={oid}" target="_self">🛒 Pedido</a>
                            <a href="?go_to=orcamentos&acao_orcamento=gerar_os&id_orcamento={oid}" target="_self">🛠️ O.S.</a>
                            <a href="?go_to=orcamentos&acao_orcamento=gerar_assinatura&id_orcamento={oid}" target="_self">🖊️ e-Assinatura</a>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def montar_formulario_orcamento(orcamento=None, modo="adicionar"):
    editando = modo == "editar"
    visualizando = modo == "visualizar"
    orcamento = orcamento or {}

    titulo = "Adicionar" if modo == "adicionar" else ("Editar" if editando else "Visualizar")
    cabecalho("📋 Orçamentos", "Orçamentos", titulo)
    if visualizando:
        linhas = "".join(f"<tr><td>{p.get('produto','')}</td><td>{p.get('largura',0):.2f}</td><td>{p.get('altura',0):.2f}</td><td>{p.get('quantidade',0):.0f}</td><td>{moeda_br(p.get('subtotal',0))}</td></tr>" for p in orcamento.get("produtos", []))
        html = f"<html><body><h1>Smart-tec</h1><h2>Orçamento {orcamento.get('numero')}</h2><p>Cliente: {orcamento.get('cliente','')}</p><table border='1' cellspacing='0' cellpadding='6'><tr><th>Item</th><th>Largura</th><th>Altura</th><th>Qtd.</th><th>Subtotal</th></tr>{linhas}</table><h3>Total: {moeda_br(orcamento.get('valor_total',0))}</h3><p>{orcamento.get('observacoes','')}</p></body></html>"
        st.download_button("🖨️ Baixar proposta imprimível", html.encode("utf-8"), file_name=f"orcamento_{orcamento.get('numero')}.html", mime="text/html")

    st.markdown('<div class="orc-card-title">📝 Dados gerais</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

    st.markdown(
        '<div class="orc-search-rule">Busca inteligente: clique no campo para ver opções, digite para filtrar e use “Adicionar novo” quando o cadastro ainda não existir.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1.2, 2.5, 2])
    numero = c1.text_input("Número", value=str(orcamento.get("numero", gerar_numero_orcamento())), disabled=True)
    with c2:
        cliente = campo_busca_inteligente_cliente(
            "Cliente *",
            valor_atual=orcamento.get("cliente", ""),
            key=f"cliente_orcamento_{modo}_{orcamento.get('id', 'novo')}",
            disabled=visualizando,
        )
    vendedor = c3.text_input("Vendedor / Responsável", value=orcamento.get("vendedor", "Valmir Barbosa"), disabled=visualizando)

    c4, c5, c6, c7 = st.columns([1.3, 1.3, 1.7, 1.4])
    data_orc = c4.date_input("Data *", value=date.today(), disabled=visualizando)
    prazo_entrega = c5.date_input("Prazo de entrega", value=date.today() + timedelta(days=10), disabled=visualizando)
    aos_cuidados = c6.text_input("Aos cuidados de", value=orcamento.get("aos_cuidados", ""), disabled=visualizando)
    validade = c7.text_input("Validade", value=orcamento.get("validade", "10 dias"), disabled=visualizando)

    c8, c9, c10 = st.columns([1.5, 1.5, 2.5])
    canal_atual = orcamento.get("canal_venda", "WhatsApp")
    canal_venda = c8.selectbox("Canal de venda *", CANAIS_VENDA, index=CANAIS_VENDA.index(canal_atual) if canal_atual in CANAIS_VENDA else 0, disabled=visualizando)
    tipo_atual = orcamento.get("tipo_orcamento", "Produtos")
    tipo_orcamento = c9.selectbox("Tipo de orçamento", TIPOS_ORCAMENTO, index=TIPOS_ORCAMENTO.index(tipo_atual) if tipo_atual in TIPOS_ORCAMENTO else 0, disabled=visualizando)
    centro_custo = c10.text_input("Centro de custo", value=orcamento.get("centro_custo", ""), disabled=visualizando)

    if tipo_orcamento == "Serviços":
        st.markdown('<div class="orc-small-help">Neste modo, Serviços aparecem primeiro e Produtos ficam abaixo para peças/componentes.</div>', unsafe_allow_html=True)
    elif tipo_orcamento == "Produtos":
        st.markdown('<div class="orc-small-help">Neste modo, Produtos aparecem primeiro e Serviços ficam abaixo como adicionais.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="orc-small-help">Produtos e Serviços ficam disponíveis na mesma tela para orçamento completo.</div>', unsafe_allow_html=True)

    introducao = st.text_area("Introdução", value=orcamento.get("introducao", ""), height=100, disabled=visualizando)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="orc-card-title">📎 Campos extras</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

    e1, e2, e3 = st.columns([1.5, 1.5, 3])
    with e1:
        cliente_final = campo_busca_inteligente_global(
            "Cliente final",
            tipo="cliente_final",
            valor_atual=orcamento.get("cliente_final", ""),
            key=f"cliente_final_orcamento_{modo}_{orcamento.get('id', 'novo')}",
            disabled=visualizando,
        )

    with e2:
        representante = campo_busca_inteligente_global(
            "Representante",
            tipo="representante",
            valor_atual=orcamento.get("representante", ""),
            key=f"representante_orcamento_{modo}_{orcamento.get('id', 'novo')}",
            disabled=visualizando,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if tipo_orcamento == "Serviços":
        servicos = bloco_servicos(orcamento, disabled=visualizando)
        produtos = bloco_produtos(orcamento, disabled=visualizando)
    else:
        produtos = bloco_produtos(orcamento, disabled=visualizando)
        servicos = bloco_servicos(orcamento, disabled=visualizando)

    st.markdown('<div class="orc-card-title">🚚 Transporte</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

    t1, t2 = st.columns([1.2, 3.8])
    frete = t1.number_input("Valor do frete", value=float(orcamento.get("frete", 0) or 0), min_value=0.0, step=1.0, disabled=visualizando)
    transportadora = t2.text_input("Transportadora", value=orcamento.get("transportadora", ""), placeholder="Digite para buscar", disabled=visualizando)

    st.markdown("</div>", unsafe_allow_html=True)

    total_produtos = sum(float(p.get("subtotal", 0) or 0) for p in produtos)
    total_servicos = sum(float(s.get("subtotal", 0) or 0) for s in servicos)

    st.markdown('<div class="orc-card-title">💰 Total</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)

    total_cols = st.columns(5)
    total_cols[0].text_input("Produtos", value=f"{total_produtos:.2f}".replace(".", ","), disabled=True)
    total_cols[1].text_input("Serviços", value=f"{total_servicos:.2f}".replace(".", ","), disabled=True)
    desconto_rs = total_cols[2].number_input("Desconto (R$)", value=float(orcamento.get("desconto_rs", 0) or 0), min_value=0.0, step=1.0, disabled=visualizando)
    desconto_percentual = total_cols[3].number_input("Desconto (%)", value=float(orcamento.get("desconto_percentual", 0) or 0), min_value=0.0, step=1.0, disabled=visualizando)
    total_bruto = total_produtos + total_servicos + float(frete or 0)
    desconto_total = float(desconto_rs or 0) + (total_bruto * float(desconto_percentual or 0) / 100)
    total_geral = max(0, total_bruto - desconto_total)
    total_cols[4].text_input("Valor total *", value=f"{total_geral:.2f}".replace(".", ","), disabled=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # PAGAMENTO - padrão GestãoClick / SmartTec
    # À vista gera a condição comercial real: Sinal 50% + Saldo 50% na entrega.
    # Parcelado gera parcelas conforme quantidade/intervalo e permite taxa do banco.
    # =========================================================
    st.markdown('<div class="orc-card-title">💵 Pagamento</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body orc-form-wide">', unsafe_allow_html=True)

    chave_pagamento_base = f"orc_pagamento_{modo}_{orcamento.get('id', 'novo')}"

    gerar_condicoes = st.checkbox(
        "Gerar condições de pagamento",
        value=bool(orcamento.get("gerar_condicoes_pagamento", True)),
        key=f"{chave_pagamento_base}_gerar_condicoes",
        disabled=visualizando,
    )

    tipo_pagamento_atual = orcamento.get("tipo_pagamento", "À vista")
    tipo_pagamento = st.radio(
        "Tipo de pagamento",
        ["À vista", "Parcelado"],
        index=1 if tipo_pagamento_atual == "Parcelado" else 0,
        horizontal=True,
        key=f"{chave_pagamento_base}_tipo",
        disabled=visualizando,
        label_visibility="collapsed",
    )

    forma_atual = str(orcamento.get("forma_pagamento", "PIX")).upper()
    if forma_atual not in FORMAS_PAGAMENTO:
        forma_atual = "PIX" if "PIX" in FORMAS_PAGAMENTO else FORMAS_PAGAMENTO[0]

    intervalo_padrao = int(orcamento.get("intervalo", 30) or 30)
    parcelas_padrao = int(orcamento.get("parcelas", 1) or 1)
    taxa_banco_padrao = float(orcamento.get("taxa_banco_percentual", 0) or 0)
    data_primeira_padrao = date.today()
    data_entrega_padrao = prazo_entrega if isinstance(prazo_entrega, date) else (date.today() + timedelta(days=30))

    parcelas_salvas = orcamento.get("condicoes_pagamento")
    if not isinstance(parcelas_salvas, list):
        parcelas_salvas = []

    def _parcela_base(vencimento, valor, forma, observacao="", descricao=""):
        return {
            "vencimento": vencimento,
            "descricao": descricao,
            "valor": float(valor or 0),
            "forma_pagamento": forma,
            "observacao": observacao,
        }

    def _gerar_avista_50_50(total, forma):
        total = float(total or 0)
        sinal = round(total * 0.50, 2)
        saldo = round(total - sinal, 2)
        return [
            _parcela_base(date.today().strftime("%d/%m/%Y"), sinal, forma, "Sinal", "Sinal (50%)"),
            _parcela_base(data_entrega_padrao.strftime("%d/%m/%Y"), saldo, forma, "Saldo na entrega", "Saldo (50%) - Entrega"),
        ]

    def _gerar_parcelado(total, forma, qtd, intervalo_dias, primeira_data, taxa_percentual=0.0):
        qtd = max(int(qtd or 1), 1)
        total_com_taxa = round(float(total or 0) * (1 + float(taxa_percentual or 0) / 100), 2)
        valor_parcela = round(total_com_taxa / qtd, 2)
        lista = []
        for i in range(qtd):
            vencimento = primeira_data + timedelta(days=int(intervalo_dias or 0) * i)
            lista.append(_parcela_base(vencimento.strftime("%d/%m/%Y"), valor_parcela, forma, "", f"Parcela {i + 1}/{qtd}"))
        soma = sum(float(p.get("valor", 0) or 0) for p in lista)
        diferenca = round(total_com_taxa - soma, 2)
        if lista:
            lista[-1]["valor"] = round(float(lista[-1]["valor"] or 0) + diferenca, 2)
        return lista

    chave_lista_pag = f"{chave_pagamento_base}_parcelas_lista"
    chave_tipo_anterior = f"{chave_pagamento_base}_tipo_anterior"
    if chave_lista_pag not in st.session_state:
        if parcelas_salvas:
            st.session_state[chave_lista_pag] = parcelas_salvas
        elif tipo_pagamento == "À vista":
            st.session_state[chave_lista_pag] = _gerar_avista_50_50(total_geral, forma_atual)
        else:
            st.session_state[chave_lista_pag] = _gerar_parcelado(total_geral, forma_atual, parcelas_padrao, intervalo_padrao, data_primeira_padrao, taxa_banco_padrao)
        st.session_state[chave_tipo_anterior] = tipo_pagamento

    # Ao alternar entre À vista e Parcelado, recria a lista para não manter regra antiga escondida.
    if st.session_state.get(chave_tipo_anterior) != tipo_pagamento:
        if tipo_pagamento == "À vista":
            st.session_state[chave_lista_pag] = _gerar_avista_50_50(total_geral, forma_atual)
        else:
            st.session_state[chave_lista_pag] = _gerar_parcelado(total_geral, forma_atual, parcelas_padrao, intervalo_padrao, data_primeira_padrao, taxa_banco_padrao)
        st.session_state[chave_tipo_anterior] = tipo_pagamento

    forma_pagamento = forma_atual
    intervalo = intervalo_padrao
    parcelas = parcelas_padrao
    taxa_banco_percentual = taxa_banco_padrao if tipo_pagamento == "Parcelado" else 0.0
    data_primeira = data_primeira_padrao

    if gerar_condicoes:
        if tipo_pagamento == "Parcelado":
            st.markdown('<div class="orc-item-row-spacer"></div>', unsafe_allow_html=True)

            h1, h2, h3, h4, h5, h6 = st.columns([1.35, 0.95, 0.95, 0.95, 1.30, 0.50])
            for col, titulo in zip(
                [h1, h2, h3, h4, h5, h6],
                [
                    'Forma de pagamento',
                    'Intervalo <small><i>(dias)</i></small>',
                    'Qnt. parcelas<span class="req">*</span>',
                    'Taxa banco (%)',
                    'Data 1ª parcela<span class="req">*</span>',
                    'Ação',
                ],
            ):
                col.markdown(f'<div class="orc-item-header">{titulo}</div>', unsafe_allow_html=True)

            g1, g2, g3, g4, g5, g6 = st.columns([1.35, 0.95, 0.95, 0.95, 1.30, 0.50])
            forma_pagamento = g1.selectbox(
                "Forma de pagamento",
                FORMAS_PAGAMENTO,
                index=FORMAS_PAGAMENTO.index(forma_atual),
                key=f"{chave_pagamento_base}_forma_gerar",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            intervalo = g2.number_input(
                "Intervalo parcelas (dias)",
                value=intervalo_padrao,
                min_value=0,
                step=1,
                key=f"{chave_pagamento_base}_intervalo",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            opcoes_parcelas = [f"{i} vez" if i == 1 else f"{i} vezes" for i in range(1, 13)]
            parcelas_label_padrao = f"{parcelas_padrao} vez" if parcelas_padrao == 1 else f"{parcelas_padrao} vezes"
            if parcelas_label_padrao not in opcoes_parcelas:
                parcelas_label_padrao = "1 vez"
            parcelas_label = g3.selectbox(
                "Qnt. parcelas",
                opcoes_parcelas,
                index=opcoes_parcelas.index(parcelas_label_padrao),
                key=f"{chave_pagamento_base}_parcelas_qtd",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            parcelas = int(parcelas_label.split()[0])
            taxa_banco_percentual = g4.number_input(
                "Taxa banco (%)",
                value=taxa_banco_padrao,
                min_value=0.0,
                step=0.1,
                key=f"{chave_pagamento_base}_taxa_banco",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            data_primeira = g5.date_input(
                "Data 1ª parcela",
                value=data_primeira_padrao,
                key=f"{chave_pagamento_base}_data_primeira",
                disabled=visualizando,
                format="DD/MM/YYYY",
                label_visibility="collapsed",
            )

            gerar = g6.button(
                "🔄 Gerar",
                key=f"{chave_pagamento_base}_btn_gerar",
                disabled=visualizando,
                use_container_width=True,
            )

            if gerar:
                st.session_state[chave_lista_pag] = _gerar_parcelado(
                    total_geral,
                    forma_pagamento,
                    parcelas,
                    intervalo,
                    data_primeira,
                    taxa_banco_percentual,
                )
                st.rerun()

        else:
            c_forma, c_spacer, c_btn = st.columns([2.8, 3.5, 1.0])
            forma_pagamento = c_forma.selectbox(
                "Forma de pagamento",
                FORMAS_PAGAMENTO,
                index=FORMAS_PAGAMENTO.index(forma_atual),
                key=f"{chave_pagamento_base}_forma_avista",
                disabled=visualizando,
            )
            intervalo = 0
            parcelas = 2
            taxa_banco_percentual = 0.0
            data_primeira = date.today()
            c_spacer.markdown('<div class="orc-filter-button-spacer"></div>', unsafe_allow_html=True)
            alterar_condicao = c_btn.button(
                "Alterar condição",
                key=f"{chave_pagamento_base}_btn_avista_5050",
                disabled=visualizando,
                use_container_width=True,
            )
            controle_avista = f"À vista|{forma_pagamento}|{round(float(total_geral or 0), 2)}|{data_entrega_padrao.strftime('%d/%m/%Y')}"
            if alterar_condicao or st.session_state.get(f"{chave_pagamento_base}_controle_avista") != controle_avista:
                st.session_state[chave_lista_pag] = _gerar_avista_50_50(total_geral, forma_pagamento)
                st.session_state[f"{chave_pagamento_base}_controle_avista"] = controle_avista
                if alterar_condicao:
                    st.rerun()

        # Tabela das condições de pagamento.
        st.markdown('<div class="orc-item-row-spacer"></div>', unsafe_allow_html=True)
        lista_pagamentos = st.session_state.get(chave_lista_pag, [])
        if not isinstance(lista_pagamentos, list) or not lista_pagamentos:
            lista_pagamentos = _gerar_avista_50_50(total_geral, forma_pagamento) if tipo_pagamento == "À vista" else _gerar_parcelado(total_geral, forma_pagamento, parcelas, intervalo, data_primeira, taxa_banco_percentual)

        if tipo_pagamento == "À vista":
            st.markdown('<div class="orc-small-help"><b>Condição padrão:</b> À vista (50% sinal + 50% saldo na entrega)</div>', unsafe_allow_html=True)

        ph1, ph2, ph3, ph4, ph5, ph6 = st.columns([1.05, 1.55, 1.05, 1.85, 1.55, 0.40])
        titulos_pag = ['Vencimento<span class="req">*</span>', 'Descrição', 'Valor<span class="req">*</span>', 'Forma de pagamento', 'Observação', 'Ação']
        for col, titulo in zip([ph1, ph2, ph3, ph4, ph5, ph6], titulos_pag):
            col.markdown(f'<div class="orc-item-header">{titulo}</div>', unsafe_allow_html=True)

        condicoes_pagamento = []
        lista_atualizada = []
        for idx_pag, parcela_item in enumerate(lista_pagamentos):
            pc1, pc2, pc3, pc4, pc5, pc6 = st.columns([1.05, 1.55, 1.05, 1.85, 1.55, 0.40])

            vencimento_salvo = parcela_item.get("vencimento", date.today().strftime("%d/%m/%Y"))
            try:
                vencimento_data = datetime.strptime(str(vencimento_salvo), "%d/%m/%Y").date()
            except Exception:
                vencimento_data = date.today()

            vencimento = pc1.date_input(
                "Vencimento",
                value=vencimento_data,
                key=f"{chave_pagamento_base}_venc_{idx_pag}",
                disabled=visualizando,
                format="DD/MM/YYYY",
                label_visibility="collapsed",
            )
            descricao_parcela = pc2.text_input(
                "Descrição",
                value=str(parcela_item.get("descricao", "") or ("Sinal (50%)" if idx_pag == 0 and tipo_pagamento == "À vista" else "")),
                key=f"{chave_pagamento_base}_desc_{idx_pag}",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            valor_parcela = pc3.number_input(
                "Valor",
                value=float(parcela_item.get("valor", 0) or 0),
                min_value=0.0,
                step=1.0,
                key=f"{chave_pagamento_base}_valor_{idx_pag}",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            forma_item = str(parcela_item.get("forma_pagamento", forma_pagamento) or forma_pagamento).upper()
            if forma_item not in FORMAS_PAGAMENTO:
                forma_item = forma_pagamento if forma_pagamento in FORMAS_PAGAMENTO else FORMAS_PAGAMENTO[0]
            forma_parcela = pc4.selectbox(
                "Forma de pagamento",
                FORMAS_PAGAMENTO,
                index=FORMAS_PAGAMENTO.index(forma_item),
                key=f"{chave_pagamento_base}_forma_{idx_pag}",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            observacao_parcela = pc5.text_input(
                "Observação",
                value=str(parcela_item.get("observacao", "") or ""),
                key=f"{chave_pagamento_base}_obs_{idx_pag}",
                disabled=visualizando,
                label_visibility="collapsed",
            )
            pc6.markdown(
                """
                <div style="display:flex;align-items:center;justify-content:center;height:36px;">
                    <button type="button" style="width:36px;height:36px;min-width:36px;border-radius:4px;border:1px solid #dc3545;background:#dc3545;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;padding:0;margin:0;box-shadow:none;cursor:default;">×</button>
                </div>
                """,
                unsafe_allow_html=True,
            )

            nova_parcela = {
                "vencimento": vencimento.strftime("%d/%m/%Y"),
                "descricao": descricao_parcela,
                "valor": float(valor_parcela or 0),
                "forma_pagamento": forma_parcela,
                "observacao": observacao_parcela,
            }
            lista_atualizada.append(nova_parcela)
            condicoes_pagamento.append(nova_parcela)

        st.session_state[chave_lista_pag] = lista_atualizada

        st.markdown('<div class="orc-btn-add-row">', unsafe_allow_html=True)
        if st.button("✚ Adicionar parcela", key=f"{chave_pagamento_base}_add_parcela", disabled=visualizando):
            lista_atual = list(st.session_state.get(chave_lista_pag, []))
            lista_atual.append(_parcela_base(date.today().strftime("%d/%m/%Y"), 0.0, forma_pagamento, "", ""))
            st.session_state[chave_lista_pag] = lista_atual
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        forma_pagamento = forma_atual
        intervalo = intervalo_padrao
        parcelas = parcelas_padrao
        taxa_banco_percentual = 0.0
        data_primeira = data_primeira_padrao
        condicoes_pagamento = []
        st.info("Condições de pagamento desativadas para este orçamento.")

    st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # ANEXOS - padrão GestãoClick / SmartTec
    # =========================================================
    st.markdown('<div class="orc-card-title">📎 Anexos</div>', unsafe_allow_html=True)
    st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)
    st.warning("Utilize este espaço para anexar comprovantes e documentos. Tamanho máximo 5Mb.")
    st.markdown('<div class="orc-btn-add-row">', unsafe_allow_html=True)
    arquivo_anexo = st.file_uploader("Selecionar arquivo", disabled=visualizando, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col_obs1, col_obs2 = st.columns(2)
    with col_obs1:
        st.markdown('<div class="orc-card-title">📝 Observações</div>', unsafe_allow_html=True)
        st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)
        observacoes = st.text_area("Esta observação será impressa no pedido", value=orcamento.get("observacoes", ""), height=150, disabled=visualizando)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_obs2:
        st.markdown('<div class="orc-card-title">📝 Observações internas</div>', unsafe_allow_html=True)
        st.markdown('<div class="orc-card-body">', unsafe_allow_html=True)
        observacoes_internas = st.text_area("Esta observação é de uso interno", value=orcamento.get("observacoes_internas", ""), height=150, disabled=visualizando)
        st.markdown("</div>", unsafe_allow_html=True)

    b1, b2, b3 = st.columns([1, 1, 5])

    if not visualizando:
        if b1.button("Cadastrar" if modo == "adicionar" else "Salvar", type="primary", use_container_width=True):
            if not cliente.strip():
                st.error("Informe o cliente.")
                return

            registro_cliente = obter_registro_por_nome("cliente", cliente)
            cliente_id = registro_cliente.get("id") or orcamento.get("cliente_id")
            if not cliente_id:
                st.error("Selecione um cliente cadastrado para salvar no banco."); return
            itens_api = []
            for p in produtos:
                itens_api.append({"tipo_item":"PRODUTO", "produto_id":p.get("produto_id"), "descricao":p.get("produto") or p.get("produto_original") or "Item", "codigo_interno":p.get("codigo_interno"), "grupo_tecnico":p.get("grupo_tecnico"), "modelo_tecnico":p.get("modelo_tecnico"), "unidade":p.get("unidade") or "UN", "quantidade":p.get("quantidade", 1), "largura":p.get("largura", 0), "altura":p.get("altura", 0), "area":p.get("area_m2", 0), "preco_unitario":p.get("valor", 0), "desconto":p.get("desconto", 0), "subtotal":p.get("subtotal", 0), "observacao_item":p.get("detalhe"), "material":p.get("material"), "cor":p.get("cor"), "acionamento":p.get("acionamento"), "lado_comando":p.get("lado_comando"), "calculo_producao_status":p.get("calculo_producao_status")})
            for s in servicos:
                itens_api.append({"tipo_item":"SERVICO", "descricao":s.get("servico") or "Serviço", "unidade":"UN", "quantidade":s.get("quantidade", 1), "preco_unitario":s.get("valor", 0), "desconto":s.get("desconto", 0), "subtotal":s.get("subtotal", 0), "observacao_item":s.get("detalhe")})
            payload_api = {"cliente_id":int(cliente_id), "status":orcamento.get("situacao", "EM_ABERTO"), "validade":(date.today() + timedelta(days=10)).isoformat(), "observacao":observacoes, "desconto":float(desconto_total), "total":float(total_bruto), "total_final":float(total_geral), "itens":itens_api}
            try:
                resposta_api = atualizar_orcamento(orcamento.get("id"), payload_api) if editando else criar_orcamento(payload_api)
                if resposta_api is None or resposta_api.status_code not in [200, 201]:
                    st.error(f"Não foi possível salvar o orçamento: {resposta_api.text if resposta_api is not None else 'API indisponível'}"); return
                salvo = orcamento_api_para_tela(resposta_api.json())
            except Exception as exc:
                st.error(f"Não foi possível salvar o orçamento: {exc}"); return

            payload = {
                "id": orcamento.get("id", proximo_id()),
                "numero": int(numero),
                "cliente": cliente.strip().upper(),
                "cliente_final": cliente_final,
                "representante": representante,
                "data": data_orc.strftime("%d/%m/%Y"),
                "prazo_entrega": prazo_entrega.strftime("%d/%m/%Y"),
                "vendedor": vendedor,
                "canal_venda": canal_venda,
                "tipo_orcamento": tipo_orcamento,
                "situacao": orcamento.get("situacao", "Em aberto"),
                "valor_total": total_geral,
                "introducao": introducao,
                "produtos": produtos,
                "servicos": servicos,
                "frete": float(frete or 0),
                "transportadora": transportadora,
                "desconto_rs": float(desconto_rs or 0),
                "desconto_percentual": float(desconto_percentual or 0),
                "forma_pagamento": forma_pagamento,
                "tipo_pagamento": tipo_pagamento,
                "gerar_condicoes_pagamento": bool(gerar_condicoes),
                "intervalo": int(intervalo or 0),
                "parcelas": int(parcelas or 1),
                "taxa_banco_percentual": float(taxa_banco_percentual or 0),
                "condicoes_pagamento": condicoes_pagamento,
                "observacoes": observacoes,
                "observacoes_internas": observacoes_internas,
            }

            if editando:
                for i, item in enumerate(st.session_state.orcamentos_lista):
                    if int(item.get("id")) == int(orcamento.get("id")):
                        st.session_state.orcamentos_lista[i] = salvo
                        break
                st.success("Orçamento atualizado com sucesso.")
            else:
                st.session_state.orcamentos_lista.insert(0, salvo)
                st.success("Orçamento cadastrado com sucesso.")

            ir_listar()

    if b2.button("Cancelar" if not visualizando else "Voltar", use_container_width=True):
        ir_listar()


def tela_excluir_orcamento():
    orcamento = obter_orcamento_por_id(st.session_state.id_orcamento_editar)
    cabecalho("📋 Orçamentos", "Orçamentos", "Excluir")

    if not orcamento:
        st.error("Orçamento não encontrado.")
        if st.button("Voltar"):
            ir_listar()
        return

    st.warning(f"Tem certeza que deseja excluir o orçamento **{orcamento.get('numero')} - {orcamento.get('cliente')}**?")

    c1, c2, c3 = st.columns([1, 1, 4])
    if c1.button("Sim, excluir", type="primary", use_container_width=True):
        if deletar_orcamento:
            resposta = deletar_orcamento(orcamento.get("id"))
            if resposta.status_code not in [200, 204]:
                st.error("Não foi possível excluir o orçamento no banco."); return
        st.session_state.orcamentos_lista = [
            o for o in st.session_state.orcamentos_lista
            if int(o.get("id")) != int(orcamento.get("id"))
        ]
        st.success("Orçamento excluído com sucesso.")
        ir_listar()

    if c2.button("Cancelar", use_container_width=True):
        ir_listar()


def processar_parametros_url():
    try:
        params = st.query_params
        acao = params.get("acao_orcamento")
        oid = params.get("id_orcamento")
    except Exception:
        return

    busca_avancada = params.get("busca_avancada_orcamentos")
    if busca_avancada in ["0", "1"]:
        st.session_state.orcamentos_busca_avancada_aberta = busca_avancada == "1"
        try:
            del st.query_params["busca_avancada_orcamentos"]
        except Exception:
            pass

    if acao in ["visualizar", "editar", "excluir"] and oid:
        st.session_state.tela_orcamentos = acao
        st.session_state.id_orcamento_editar = int(oid)

        try:
            del st.query_params["acao_orcamento"]
            del st.query_params["id_orcamento"]
        except Exception:
            pass

    elif acao and oid:
        orcamento = obter_orcamento_por_id(int(oid))
        numero = orcamento.get("numero") if orcamento else oid

        mensagens = {
            "pdf_cliente": f"PDF Cliente do orçamento {numero}: próxima etapa será gerar o arquivo limpo, sem dados de parceiro/comissão.",
            "pdf_parceiro": f"PDF Parceiro do orçamento {numero}: próxima etapa será gerar o arquivo com comissão, taxa financeira e repasse previsto.",
            "pdf_interno": f"PDF Interno do orçamento {numero}: próxima etapa será gerar o arquivo completo para administração.",
            "email": f"Compartilhar por e-mail o orçamento {numero}: próxima etapa será abrir envio com PDF Cliente ou PDF Parceiro.",
            "whatsapp": f"Compartilhar por WhatsApp o orçamento {numero}: próxima etapa será montar mensagem e anexar PDF.",
            "alterar_situacao": f"Alterar situação do orçamento {numero}: próxima etapa será aprovar/reprovar/cancelar direto pelo menu.",
            "gerar_pedido": f"Gerar Pedido a partir do orçamento {numero}: próxima fase do desenvolvimento.",
            "gerar_os": f"Gerar O.S. a partir do orçamento {numero}: próxima fase do desenvolvimento.",
            "gerar_assinatura": f"Gerar e-Assinatura do orçamento {numero}: próxima fase do desenvolvimento.",
        }

        if acao == "gerar_copia" and orcamento:
            novo = clonar_dados_comerciais_orcamento(orcamento)
            novo["id"] = proximo_id()
            novo["numero"] = gerar_numero_orcamento()
            novo["situacao"] = "Em aberto"
            novo["data"] = date.today().strftime("%d/%m/%Y")
            novo["orcamento_origem"] = orcamento.get("numero")
            st.session_state.orcamentos_lista.append(novo)
            st.session_state.orcamento_acao_mensagem = {
                "tipo": "success",
                "texto": f"Cópia criada com sucesso a partir do orçamento {numero}.",
            }

        elif acao == "gerar_pedido" and orcamento:
            pedido = criar_pedido_a_partir_orcamento(orcamento)
            registrar_repasse_parceiro_previsto(orcamento, pedido)
            st.session_state.orcamento_acao_mensagem = {
                "tipo": "success",
                "texto": f"Pedido {pedido.get('numero')} gerado com sucesso a partir do orçamento {numero}.",
            }

        elif acao == "gerar_os" and orcamento:
            ordem = criar_os_a_partir_orcamento(orcamento)
            st.session_state.orcamento_acao_mensagem = {
                "tipo": "success",
                "texto": f"O.S. {ordem.get('numero')} gerada com sucesso a partir do orçamento {numero}.",
            }

        elif acao == "alterar_situacao" and orcamento:
            ordem_situacoes = ["Em aberto", "Aprovado", "Reprovado", "Cancelado"]
            atual = orcamento.get("situacao", "Em aberto")
            try:
                proxima = ordem_situacoes[(ordem_situacoes.index(atual) + 1) % len(ordem_situacoes)]
            except Exception:
                proxima = "Em aberto"
            orcamento["situacao"] = proxima
            st.session_state.orcamento_acao_mensagem = {
                "tipo": "success",
                "texto": f"Situação do orçamento {numero} alterada para {proxima}.",
            }

        else:
            st.session_state.orcamento_acao_mensagem = {
                "tipo": "info",
                "texto": mensagens.get(acao, f"Ação {acao} acionada para o orçamento {numero}."),
            }

        st.session_state.tela_orcamentos = "listar"
        st.session_state.id_orcamento_editar = None

        try:
            del st.query_params["acao_orcamento"]
            del st.query_params["id_orcamento"]
        except Exception:
            pass


def telaOrcamentos():
    carregar_css_orcamentos()
    inicializar_orcamentos()
    processar_parametros_url()

    tela = st.session_state.get("tela_orcamentos", "listar")

    if tela == "listar":
        tela_listar_orcamentos()

    elif tela == "adicionar":
        montar_formulario_orcamento(modo="adicionar")

    elif tela == "editar":
        orcamento = obter_orcamento_por_id(st.session_state.id_orcamento_editar)
        if orcamento:
            montar_formulario_orcamento(orcamento, modo="editar")
        else:
            st.error("Orçamento não encontrado.")

    elif tela == "visualizar":
        orcamento = obter_orcamento_por_id(st.session_state.id_orcamento_editar)
        if orcamento:
            montar_formulario_orcamento(orcamento, modo="visualizar")
        else:
            st.error("Orçamento não encontrado.")

    elif tela == "excluir":
        tela_excluir_orcamento()

    else:
        st.session_state.tela_orcamentos = "listar"
        st.rerun()


def tela_orcamentos():
    telaOrcamentos()
