import time
import math
import html
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote
import pandas as pd
import streamlit as st

from utils.ui import cabecalho
from utils.api_client import (
    get_produtos,
    criar_produto,
    atualizar_produto,
    deletar_produto,
    get_opcoes_auxiliares_por_categoria,
    criar_opcao_auxiliar,
)

try:
    from app.services.motor_calculo_produtos import calcular_produto_sob_medida
except Exception:
    try:
        from services.motor_calculo_produtos import calcular_produto_sob_medida
    except Exception:
        try:
            from modulos.motor_calculo_produtos import calcular_produto_sob_medida
        except Exception:
            calcular_produto_sob_medida = None

CATEGORIA_VALORES_VENDA = "valor_venda_produto"

# Baú inteligente de componentes compartilhados.
# Não altera o grupo técnico original; apenas marca o produto para também aparecer
# na busca do baú de componentes das receitas.
MARCADOR_BAU_COMPONENTES_PERSIANAS = "BAU_COMPONENTES_PERSIANAS=SIM"

# =========================================================
# SMARTTEC - NOVA ARQUITETURA TÉCNICA
# Decisão: abandonar Família Técnica como campo principal.
# O ERP passa a trabalhar com Modelo Técnico + Grupo Técnico.
# Mantemos algumas funções antigas internamente apenas para compatibilidade
# com receitas já salvas e cadastros antigos.
# =========================================================
MODELOS_TECNICOS_PADRAO = [
    "",
    "ROLO",
    "DOUBLE_VISION",
    "ROMANA",
    "PAINEL",
    "CORTINA",
    "TOLDO",
    "EXTERNA",
]

GRUPOS_TECNICOS_PADRAO = [
    "",
    # Tecidos / materiais principais
    "TECIDOS_ROLO_ROMANA_PAINEL",
    "TECIDOS_DOUBLE_VISION",
    "TECIDOS_SHANGRILA",
    "TECIDOS_PLISSADA",
    "TECIDOS_CELULAR",
    "TECIDOS_CORTINAS",
    "TECIDOS_TAPECARIA",
    "TECIDOS_TOLDO",
    "TECIDOS_EXTERNA",
    # Lâminas
    "LAMINAS_HORIZONTAL",
    "LAMINAS_VERTICAL",
    # Componentes por modelo
    "COMPONENTES_ROLO",
    "COMPONENTES_DOUBLE_VISION",
    "COMPONENTES_ROMANA",
    "COMPONENTES_PAINEL",
    "COMPONENTES_CORTINAS",
    "COMPONENTES_HORIZONTAL",
    "COMPONENTES_VERTICAL",
    "COMPONENTES_PLISSADA",
    "COMPONENTES_SHANGRILA",
    "COMPONENTES_CELULAR",
    "COMPONENTES_TOLDO",
    "COMPONENTES_EXTERNA",
    # Baús compartilhados por família técnica
    "BAU_PERSIANAS",
    "BAU_CORTINAS",
    "BAU_EXTERNA",
    "BAU_MOTORES",
    # Motorização global
    "MOTORES",
    "ACESSORIOS_MOTOR",
    # Produtos finais
    "PERSIANA_ROLO",
    "ROLO",  # legado/compatibilidade: saneamento novo converte para PERSIANA_ROLO
    "ROMANA",
    "PAINEL",
    "PERSIANA_DOUBLE_VISION",
    "PERSIANA_HORIZONTAL",
    "PERSIANA_VERTICAL",
    "PERSIANA_PLISSADA",
    "PERSIANA_SHANGRILA",
    "PERSIANA_CELULAR",
    "PERSIANA_EXTERNA",
    "CORTINA",
]

# Legado: usado apenas para receitas antigas e inferências internas.
FAMILIAS_TECNICAS_PADRAO = [
    "",
    "TECIDO",
    "TUBO_32",
    "TUBO_38",
    "FITA_TUBO",
    "BASE_AC133",
    "BASE_AC191",
    "FITA_BASE",
    "ESPAGUETE_3MM",
    "CORRENTE_BOLA10",
    "EMENDA_CORRENTE",
    "TAMPA_BASE",
    "COMANDO_32",
    "COMANDO_38",
    "MOTOR",
    "CONTROLE",
    "TRILHO",
    "SUPORTE",
    "SERVICO",
]

CORES_COMPONENTES_PADRAO = [
    "",
    "Branco",
    "Preto",
    "Cinza",
    "Marfim",
    "Bege",
    "Creme",
    "Off White",
    "Marrom",
    "Tabaco",
    "Natural",
    "Incolor",
]


def normalizar_percentual_valor_venda(valor):
    try:
        return float(str(valor or "0").replace("%", "").replace(",", ".").strip())
    except Exception:
        return 0.0


def normalizar_lista_api(dados):
    """
    Garante que a resposta da API vire uma lista de dicionários.
    Corrige casos em que o retorno vem como Response, bytes, string JSON ou dict.
    """
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


def carregar_tabelas_valores_venda():
    """
    Busca as tabelas de venda cadastradas em Produtos > Valores de venda.
    Enquanto não houver registros, usa os três padrões.
    """
    padroes = [
        {"nome": "Varejo", "lucro": 100.0, "ordem": 1},
        {"nome": "Consumidor final", "lucro": 150.0, "ordem": 2},
        {"nome": "Decorador", "lucro": 50.0, "ordem": 3},
    ]

    try:
        dados_api = get_opcoes_auxiliares_por_categoria(CATEGORIA_VALORES_VENDA)
        dados = normalizar_lista_api(dados_api)
    except Exception:
        dados = []

    tabelas = []

    for item in dados:
        if str(item.get("situacao", "Ativo")) == "Inativo":
            continue

        nome = str(item.get("nome", "")).strip()
        lucro = normalizar_percentual_valor_venda(item.get("descricao", 0))

        if nome:
            tabelas.append({
                "nome": nome,
                "lucro": lucro,
                "ordem": int(item.get("ordem") or 0),
            })

    if not tabelas:
        return padroes

    tabelas = sorted(tabelas, key=lambda x: (x.get("ordem", 0), x.get("nome", "")))
    return tabelas


def carregar_css_produtos():
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], .main {
            height: auto !important;
            min-height: 100vh !important;
            overflow-y: auto !important;
        }

        section.main > div {
            overflow: visible !important;
        }

        div[data-testid="stVerticalBlock"] {
            overflow: visible !important;
        }

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
            background-color: #6b7280 !important;
            border-color: #6b7280 !important;
            color: white !important;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            min-height: 40px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        textarea:focus {
            border: 2px solid #2563eb !important;
            outline: none !important;
            box-shadow: 0 0 0 1px #2563eb33 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 40px !important;
            height: 40px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
            box-shadow: none !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb33 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
            color: #111827 !important;
        }

        div[data-testid="stSelectbox"] input {
            color: #111827 !important;
        }

        div[data-testid="stNumberInput"] button {
            border-left: 1px solid #d1d5db !important;
            color: #111827 !important;
            background: #f9fafb !important;
        }

        .erp-form-page-title {
            font-size: 22px;
            font-weight: 600;
            color: #111827;
            margin: 4px 0 8px 0;
        }

        div[data-testid="stTabs"] {
            margin-top: 0 !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            gap: 6px !important;
            border-bottom: 1px solid #cfd6dd !important;
            margin-bottom: 10px !important;
        }

        div[data-testid="stTabs"] [role="tab"] {
            min-height: 36px !important;
            padding: 6px 13px !important;
            align-items: center !important;
            justify-content: center !important;
            border: 1px solid #d1d5db !important;
            border-bottom: 0 !important;
            border-radius: 6px 6px 0 0 !important;
            background: #f8fafc !important;
            color: #374151 !important;
        }

        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: #ffffff !important;
            border-color: #9ca3af !important;
            color: #111827 !important;
        }

        div[data-testid="stTabs"] [role="tab"] p {
            font-size: 13px !important;
            font-weight: 650 !important;
            text-align: center !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }

        div[data-testid="stTabs"] [role="tabpanel"] {
            padding-top: 0 !important;
        }

        .erp-section-title-clean {
            background: #ffffff;
            border: 1px solid #d9dee3;
            border-radius: 4px;
            padding: 9px 13px;
            font-size: 16px;
            font-weight: 600;
            color: #111827;
            margin-top: 10px;
            margin-bottom: 10px;
        }

        .erp-form-actions-spacer {
            border-top: 1px solid #e5e7eb;
            margin: 22px 0 14px 0;
            height: 1px;
        }

        .erp-blue-info {
            background-color: #d9edf7;
            border: 1px solid #bce8f1;
            color: #31708f;
            padding: 12px 14px;
            border-radius: 4px;
            font-size: 13px;
            margin: 8px 0 12px 0;
        }

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

        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            min-height: 38px !important;
            height: 38px !important;
            border-radius: 5px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
        }

        /* Campos do formulário bem visíveis */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            background-color: #ffffff !important;
            border: 1.5px solid #9ca3af !important;
            color: #111827 !important;
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
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb33 !important;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
            color: #111827 !important;
        }

        .erp-delete-confirm-box {
            background: #fff8db;
            border: 1px solid #f3e5a3;
            color: #7a5600;
            padding: 14px 16px;
            border-radius: 6px;
            margin: 14px 0 10px 0;
            font-size: 15px;
        }


        /* Ações da tabela no padrão Clientes */
        .erp-action-links-produtos {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        .erp-action-link-produto {
            width: 34px;
            height: 34px;
            border-radius: 4px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none !important;
            font-size: 15px;
            font-weight: 700;
            box-sizing: border-box;
        }

        .erp-action-view-produto {
            background: #ffffff;
            color: #111827 !important;
            border: 1px solid #d1d5db;
        }

        .erp-action-view-produto:hover {
            background: #f3f4f6;
            border-color: #9ca3af;
            color: #111827 !important;
        }

        .erp-action-edit-produto {
            background: #198754;
            color: #ffffff !important;
            border: 1px solid #198754;
        }

        .erp-action-edit-produto:hover {
            background: #157347;
            border-color: #157347;
            color: #ffffff !important;
        }

        .erp-action-delete-produto {
            background: #dc3545;
            color: #ffffff !important;
            border: 1px solid #dc3545;
        }

        .erp-action-delete-produto:hover {
            background: #bb2d3b;
            border-color: #bb2d3b;
            color: #ffffff !important;
        }

        .erp-action-clone-produto {
            background: #0d6efd;
            color: #ffffff !important;
            border: 1px solid #0d6efd;
        }

        .erp-action-clone-produto:hover {
            background: #0b5ed7;
            border-color: #0b5ed7;
            color: #ffffff !important;
        }


        /* Modal de confirmação de exclusão */
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
            width: min(600px, calc(100vw - 40px));
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
            font-size: 58px;
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

        .erp-modal-btn-nao:hover {
            background: #5c636a;
            border-color: #5c636a;
            color: #ffffff !important;
        }

        .erp-modal-btn-sim {
            background: #061523;
            color: #ffffff !important;
            border: 1px solid #061523;
        }

        .erp-modal-btn-sim:hover {
            background: #020911;
            border-color: #020911;
            color: #ffffff !important;
        }


        .erp-mais-acoes-link {
            display: flex;
            align-items: center;
            width: 100%;
            cursor: pointer;
            background: #ffffff;
            color: #212529 !important;
            text-decoration: none !important;
            border-radius: 0;
            padding: 9px 12px;
            margin-bottom: 0;
            font-size: 14px;
            font-weight: 500;
            text-align: left;
            box-sizing: border-box;
            border-bottom: 1px solid #f1f3f5;
        }

        .erp-mais-acoes-link:hover {
            background: #f5f5f5;
            color: #111827 !important;
            text-decoration: none !important;
        }


        /* Seleção em lote */
        div[data-testid="stCheckbox"] {
            display: flex !important;
            justify-content: center !important;
        }

        div[data-testid="stCheckbox"] label {
            margin-bottom: 0 !important;
        }

        div[data-testid="stCheckbox"] span {
            font-size: 13px !important;
        }

        /* Mais ações */
        div[data-testid="stPopover"] button {
            min-height: 40px !important;
            height: 40px !important;
            border-radius: 4px !important;
            background: #161616 !important;
            color: #ffffff !important;
            border-color: #161616 !important;
            font-weight: 700 !important;
        }


        /* Toolbar de Produtos alinhada no padrão GestãoClick */
        .erp-toolbar-spacer {
            min-height: 1px;
        }

        div[data-testid="stPopover"] > div > button {
            min-height: 40px !important;
            height: 40px !important;
            border-radius: 4px !important;
            background: #161616 !important;
            color: #ffffff !important;
            border: 1px solid #161616 !important;
            font-weight: 700 !important;
            margin-top: 0 !important;
        }

        div[data-testid="stPopover"] > div > button:hover {
            background: #0f0f0f !important;
            border-color: #0f0f0f !important;
            color: #ffffff !important;
        }


        .st-ajuste-actions div[data-testid="stButton"] button {
            min-height: 38px !important;
            height: 38px !important;
            border-radius: 4px !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            padding: 0 14px !important;
        }

        .ajuste-inline-card {
            border: 1px solid #e5e7eb;
            background: #ffffff;
            border-radius: 8px;
            padding: 18px;
            margin: 10px 0 14px 0;
        }

        .erp-busca-avancada-box {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: #ffffff;
            padding: 16px 20px;
            margin: 8px 0 10px 0;
        }


        /* Campos numéricos discretos: controles - e + neutros, sem vermelho */
        div[data-testid="stNumberInput"] button {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-width: 28px !important;
            width: 28px !important;
            min-height: 20px !important;
            height: 20px !important;
            padding: 0 !important;
            border: 1px solid #d1d5db !important;
            border-radius: 4px !important;
            background: #f3f4f6 !important;
            color: #374151 !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }

        div[data-testid="stNumberInput"] button:hover {
            background: #e5e7eb !important;
            border-color: #9ca3af !important;
            color: #111827 !important;
        }

        div[data-testid="stNumberInput"] input[type="number"]::-webkit-outer-spin-button,
        div[data-testid="stNumberInput"] input[type="number"]::-webkit-inner-spin-button {
            -webkit-appearance: none !important;
            margin: 0 !important;
        }

        div[data-testid="stNumberInput"] input[type="number"] {
            appearance: textfield !important;
            -moz-appearance: textfield !important;
        }

        div[data-testid="stNumberInput"] > div {
            width: 100% !important;
        }

        div[data-testid="stNumberInput"] input {
            border-radius: 4px !important;
            padding-right: 10px !important;
        }

        div[class*="st-key-produto_valor_custo_"] div[data-testid="stNumberInput"] button,
        div[class*="st-key-produto_despesas_acessorias_"] div[data-testid="stNumberInput"] button,
        div[class*="st-key-produto_outras_despesas_"] div[data-testid="stNumberInput"] button,
        div[class*="st-key-produto_lucro_"] div[data-testid="stNumberInput"] button,
        div[class*="st-key-produto_valor_"] div[data-testid="stNumberInput"] button,
        div[class*="st-key-produto_valor_custo_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_valor_custo_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_despesas_acessorias_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_despesas_acessorias_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_outras_despesas_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_outras_despesas_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_lucro_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_lucro_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_valor_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_valor_"] button[data-testid="stNumberInputStepDown"] {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-width: 26px !important;
            width: 26px !important;
            min-height: 20px !important;
            height: 20px !important;
            padding: 0 !important;
            border: 1px solid #d1d5db !important;
            border-radius: 4px !important;
            background: #f3f4f6 !important;
            background-color: #f3f4f6 !important;
            color: #374151 !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }

        div[class*="st-key-produto_valor_custo_"] div[data-testid="stNumberInput"] button:hover,
        div[class*="st-key-produto_despesas_acessorias_"] div[data-testid="stNumberInput"] button:hover,
        div[class*="st-key-produto_outras_despesas_"] div[data-testid="stNumberInput"] button:hover,
        div[class*="st-key-produto_lucro_"] div[data-testid="stNumberInput"] button:hover,
        div[class*="st-key-produto_valor_"] div[data-testid="stNumberInput"] button:hover,
        div[class*="st-key-produto_valor_custo_"] button[data-testid="stNumberInputStepUp"]:hover,
        div[class*="st-key-produto_valor_custo_"] button[data-testid="stNumberInputStepDown"]:hover,
        div[class*="st-key-produto_despesas_acessorias_"] button[data-testid="stNumberInputStepUp"]:hover,
        div[class*="st-key-produto_despesas_acessorias_"] button[data-testid="stNumberInputStepDown"]:hover,
        div[class*="st-key-produto_outras_despesas_"] button[data-testid="stNumberInputStepUp"]:hover,
        div[class*="st-key-produto_outras_despesas_"] button[data-testid="stNumberInputStepDown"]:hover,
        div[class*="st-key-produto_lucro_"] button[data-testid="stNumberInputStepUp"]:hover,
        div[class*="st-key-produto_lucro_"] button[data-testid="stNumberInputStepDown"]:hover,
        div[class*="st-key-produto_valor_"] button[data-testid="stNumberInputStepUp"]:hover,
        div[class*="st-key-produto_valor_"] button[data-testid="stNumberInputStepDown"]:hover {
            background: #e5e7eb !important;
            background-color: #e5e7eb !important;
            border-color: #9ca3af !important;
            color: #111827 !important;
        }

        div[data-testid="stForm"] div[data-testid="stButton"] button[kind="secondary"]:has(p) {
            border-radius: 4px !important;
        }


        </style>
        """,
        unsafe_allow_html=True,
    )


def texto_seguro(valor):
    if valor is None:
        return ""
    return html.escape(str(preservar_termos_comerciais(valor)))


def valor_str(produto, campo):
    valor = produto.get(campo, "")
    if valor is None:
        return ""
    return preservar_termos_comerciais(valor)


def valor_planilha_para_float(valor, padrao=0.0):
    """Converte valores vindos de Excel/CSV para float, aceitando vírgula brasileira."""
    try:
        if valor is None:
            return padrao
        if pd.isna(valor):
            return padrao
    except Exception:
        pass

    try:
        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()
        if not texto:
            return padrao

        texto = texto.replace("R$", "").replace("%", "").strip()

        # Se vier no padrão brasileiro: 1.234,56
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", ".")

        return float(texto)
    except Exception:
        return padrao


TERMOS_COMERCIAIS_PROTEGIDOS = {
    "visão dupla": "DOUBLE VISION",
    "visao dupla": "DOUBLE VISION",
    "dupla visão": "DOUBLE VISION",
    "dupla visao": "DOUBLE VISION",
    "doble vision": "DOUBLE VISION",
    "double visão": "DOUBLE VISION",
    "double visao": "DOUBLE VISION",
    "double vision": "DOUBLE VISION",
    "rastreio": "SCREEN",
}


def preservar_termos_comerciais(valor):
    """
    Corrige traduções automáticas indevidas em termos comerciais/técnicos.
    Regra: o SmartTec deve respeitar a linguagem do negócio do usuário.

    Exemplos:
    - VISÃO DUPLA BK. MÉXICO -> DOUBLE VISION BK. MÉXICO
    - TELA 3% IMPORTADO -> SCREEN 3% IMPORTADO
    - RASTREIO 3% -> SCREEN 3%

    Observação:
    Não troca toda palavra "tela" do sistema, porque "tela" pode existir em frases comuns.
    A troca de TELA -> SCREEN é aplicada em nomes comerciais quando vem com percentual/modelo.
    """
    if valor is None:
        return valor

    texto = str(valor)
    if not texto.strip():
        return texto

    resultado = texto

    # Termos comerciais diretos
    for termo_errado, termo_correto in TERMOS_COMERCIAIS_PROTEGIDOS.items():
        resultado = re.sub(
            re.escape(termo_errado),
            termo_correto,
            resultado,
            flags=re.IGNORECASE,
        )

    # Proteção específica para tecido SCREEN que entrou como TELA 1%, TELA 3%, TELA 5%...
    resultado = re.sub(
        r"\bTELA(\s+\d+(?:[,.]\d+)?\s*%)",
        r"SCREEN\1",
        resultado,
        flags=re.IGNORECASE,
    )

    # Proteção para variações comuns de cadastro/material
    resultado = re.sub(
        r"\bTELA(\s+(?:SCREEN|SOLAR|IMPORTADO|NACIONAL|BLACKOUT|BK\.?|NOBLETE|RÚSTICO|RUSTICO|MÉXICO|MEXICO))",
        r"SCREEN\1",
        resultado,
        flags=re.IGNORECASE,
    )

    # Proteção extra para materiais de tecido que vieram como TELA BK., TELA SOLAR, TELA NOBLETE etc.
    resultado = re.sub(
        r"\bTELA\b(?=\s+(?:BK\.?|BLACKOUT|NOBLETE|SCREEN|SOLAR|RÚSTICO|RUSTICO|MÉXICO|MEXICO|IMPORTADO|NACIONAL|\d))",
        "SCREEN",
        resultado,
        flags=re.IGNORECASE,
    )

    return resultado


def preservar_payload_termos_comerciais(payload):
    if not isinstance(payload, dict):
        return payload

    campos_texto = [
        "nome",
        "grupo_produto",
        "tipo_produto",
        "modelo_tecnico",
        "grupo_tecnico",
        "familia_tecnica",
        "cor_componente",
        "linha",
        "modelo",
        "tipo_cortina_persiana",
        "material_tecido",
        "cor",
        "descricao",
        "observacoes",
        "origem",
    ]

    for campo in campos_texto:
        if campo in payload and payload[campo] is not None:
            payload[campo] = preservar_termos_comerciais(payload[campo])

    return payload


def valor_planilha_para_texto(valor, padrao=None):
    """
    Importação deve respeitar exatamente o texto da planilha.
    Não traduzir, não trocar SCREEN por TELA, não trocar DOUBLE VISION por VISÃO DUPLA.
    Apenas remove vazio/nan/null.
    """
    try:
        if valor is None:
            return padrao
        if pd.isna(valor):
            return padrao
    except Exception:
        pass

    texto = str(valor).strip()
    if not texto or texto.lower() in ["nan", "none", "null"]:
        return padrao

    return texto


def detectar_largura_tecido_nome(nome):
    """
    Detecta largura do rolo de tecido no nome.
    Exemplos:
    - TECIDO BK. BRISK - 2,50M
    - BLACKOUT 100% DUPLA FACE BRANCO (CINZA / 2,80)
    - SCREEN 3% IMPORTADO 2,50
    """
    texto = str(nome or "").upper()

    padroes = [
        r"[/\-\s]\s*(2[,.]\d{1,2})\s*M?\b",
        r"\((?:[^)]*?)[/ ]\s*(2[,.]\d{1,2})\s*\)",
        r"\b(2[,.](?:50|80|60|40|20|00))\b",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto)
        if m:
            try:
                valor = float(m.group(1).replace(",", "."))
                if 1.0 <= valor <= 4.0:
                    return valor
            except Exception:
                pass

    return 0.0


def detectar_metragem_nome(nome):
    """
    Detecta metragem de embalagem/rolo/barra no nome.
    Exemplos:
    - C/ 250MT
    - 250M
    - 6MT
    """
    texto = str(nome or "").upper()

    padroes = [
        r"C/\s*(\d+(?:[,.]\d+)?)\s*(?:MTS|MT|M|ML)\b",
        r"ROLO\s+COM\s*(\d+(?:[,.]\d+)?)\s*(?:MTS|MT|M|ML)\b",
        r"\b(\d+(?:[,.]\d+)?)\s*(?:MTS|MT|ML)\b",
        r"X\s*(\d+(?:[,.]\d+)?)\s*(?:MTS|MT|M)\b",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto)
        if m:
            try:
                valor = float(m.group(1).replace(",", "."))
                if valor > 0:
                    return valor
            except Exception:
                pass

    return 0.0


def texto_importacao(row, campo):
    return str(valor_planilha_para_texto(row.get(campo), "") or "").strip()


def inferir_tipo_produto_importacao(row):
    """
    Classifica melhor os itens importados.
    Regra inicial:
    - insumos/componentes entram como Componente para o motor poder usar.
    - produtos finais sob medida entram como Produto fabricado.
    """
    nome = texto_importacao(row, "nome").upper()
    grupo = texto_importacao(row, "grupo_produto").upper()
    tipo_original = texto_importacao(row, "tipo_produto")

    texto = f"{nome} {grupo}"

    palavras_componente = [
        "TECIDO", "BLACKOUT", "SCREEN", "LINHO", "GASE", "VOIL", "LUGANO",
        "NOBLETE", "RÚSTICO", "RUSTICO", "WOOD", "DOUBLE VISION",
        "TUBO", "BASE", "PERFIL", "SUPORTE", "TAMPA", "PONTEIRA",
        "COMANDO", "CORRENTE", "CORR", "CORDÃO", "CORDAO", "VARETA",
        "TRILHO", "RODIZIO", "RODÍZIO", "CARRINHO", "KIT", "MOTOR",
        "CONTROLE", "RECEPTOR", "BATERIA", "FONTE", "LONA", "BRAÇO", "BRACO",
        "MANIVELA", "GUIA", "CAIXA",
    ]

    palavras_fabricado = [
        "ROLO ", "ROLÔ ", "PERSIANA ", "ROMANA ", "PAINEL ", "TOLDO ",
        "CORTINA DE TECIDO", "CORTINA TECIDO",
    ]

    # Se veio da planilha explicitamente como componente/insumo, respeita.
    if tipo_original and str(tipo_original).strip().lower() in ["componente", "insumo", "matéria-prima", "materia-prima", "material"]:
        return "Componente"

    # Produtos finais clássicos.
    if any(texto.startswith(p) for p in palavras_fabricado):
        return "Produto fabricado"

    # Todo material/peça técnica deve ficar disponível para o motor.
    if any(p in texto for p in palavras_componente):
        return "Componente"

    return tipo_original or "Componente"


def inferir_grupo_produto_importacao(row):
    nome = texto_importacao(row, "nome").upper()
    grupo_original = texto_importacao(row, "grupo_produto")

    if grupo_original:
        return grupo_original

    if "TUBO" in nome:
        return "TUBOS"
    if "TECIDO" in nome or "SCREEN" in nome or "BLACKOUT" in nome or "LINHO" in nome or "GASE" in nome or "DOUBLE VISION" in nome:
        return "TECIDOS"
    if "COMANDO" in nome or "CORRENTE" in nome or "KIT" in nome:
        return "COMPONENTES"
    if "MOTOR" in nome or "CONTROLE" in nome or "RECEPTOR" in nome:
        return "MOTORIZAÇÃO"
    if "TRILHO" in nome:
        return "TRILHOS"
    if "ROLO" in nome or "ROLÔ" in nome:
        return "ROLÔ"

    return grupo_original


def aplicar_conversao_importacao(row, valor_custo, unidade_venda, observacoes):
    """
    Converte o custo de compra para custo de saída usado no motor.
    Como o backend atual ainda não salva a regra completa de conversão, guardamos o custo já convertido
    em valor_custo/custo_final e deixamos uma observação técnica.

    Exemplos:
    - tecido comprado por metro linear 2,50m -> custo por m² = valor / 2,50
    - tubo comprado em barra 6m -> custo por ML = valor / 6
    - corrente C/250MT -> custo por ML = valor / 250
    """
    nome = texto_importacao(row, "nome")
    nome_upper = nome.upper()
    unidade_original = str(unidade_venda or "").strip()
    unidade_upper = unidade_original.upper()

    valor_custo = float(valor_custo or 0)
    obs = str(observacoes or "").strip()
    notas = []

    if valor_custo <= 0:
        return valor_custo, unidade_venda, obs

    obs_upper = obs.upper()
    grupo_tecnico_row = normalizar_grupo_tecnico(row.get("grupo_tecnico")) if isinstance(row, (dict, pd.Series)) else None
    categoria_row = normalizar_busca_motor(row.get("categoria_pdf") or row.get("linha") or "") if isinstance(row, (dict, pd.Series)) else ""
    eh_importacao_acao = "AÇÃO DISTRIBUIDORA" in obs_upper or "ACAO DISTRIBUIDORA" in obs_upper or "TABTECIDOS AÇÃO" in obs_upper or "TABTECIDOS ACAO" in obs_upper

    # Se já foi convertido na importação/planilha, o motor não pode converter de novo.
    # Ex.: corrente JUTA BOLA 10 já está em ML por R$ 0,29; não dividir novamente por 250MT.
    if any(marca in obs_upper for marca in [
        "CONVERSÃO AUTOMÁTICA IMPORTAÇÃO",
        "CONVERSAO AUTOMATICA IMPORTACAO",
        "CUSTO CONVERTIDO",
        "CUSTO DE SAÍDA",
        "CUSTO DE SAIDA",
    ]):
        return round(valor_custo, 4), unidade_venda, obs

    # Se a corrente já está cadastrada como ML com custo baixo, ela já é custo por metro.
    if any(p in nome_upper for p in ["CORRENTE", "CORR"]) and unidade_upper in ["ML", "METRO", "METRO LINEAR", "M"]:
        # Correção de base antiga: algumas correntes JUTA/BOLA 10 ficaram 0,0029
        # porque foram divididas indevidamente por causa do "250MT" no nome.
        if any(p in nome_upper for p in ["BOLA 10", "BOLA10", "JUTA"]) and 0 < valor_custo < 0.01:
            valor_corrigido = round(valor_custo * 100, 4)
            notas.append(
                f"Regra motor: corrente JUTA/BOLA 10 estava reconvertida indevidamente; custo corrigido para ML = {moeda_br(valor_corrigido)}."
            )
            return valor_corrigido, "ML", " | ".join([x for x in [obs] + notas if x])

        if valor_custo < 5:
            notas.append("Regra motor: corrente já está com custo por ML; não reconverter por metragem do nome.")
            return round(valor_custo, 4), "ML", " | ".join([x for x in [obs] + notas if x])

    # Se tecido já está cadastrado como M², não converter novamente por largura.
    # Importante SmartTec: muitos tecidos antigos já foram cadastrados com o custo
    # convertido por m², mesmo quando o nome ainda contém a largura do rolo
    # ou quando a unidade veio como ML/M por causa da planilha do fornecedor.
    # O motor NÃO pode dividir novamente por 2,50 / 2,80, senão o custo fica errado.
    eh_tecido_precheck = (
        any(p in nome_upper for p in [
            "TECIDO", "TEC ", "SCREEN", "BLACKOUT", "BK", "LINHO", "GASE", "VOIL",
            "LUGANO", "NOBLETE", "DOUBLE VISION", "RÚSTICO", "RUSTICO", "TRANSLUCIDO", "TRANSLÚCIDO"
        ])
        or str(grupo_tecnico_row or "").startswith("TECIDOS_")
        or "TECIDO" in categoria_row
    )

    if eh_tecido_precheck and unidade_upper in ["M²", "M2", "MT²", "METRO QUADRADO"]:
        notas.append("Regra SmartTec: tecido já está com custo por M²; não reconverter por largura.")
        return round(valor_custo, 4), "M²", " | ".join([x for x in [obs] + notas if x])

    largura_tecido_acao = valor_planilha_para_float(row.get("largura"), 0.0) if isinstance(row, (dict, pd.Series)) else 0.0
    if largura_tecido_acao <= 0:
        largura_tecido_acao = detectar_largura_tecido_nome(nome)
    if eh_importacao_acao and eh_tecido_precheck and largura_tecido_acao > 0 and unidade_upper in ["ML", "M", "MT", "METRO", "METRO LINEAR"]:
        custo_convertido = valor_custo / largura_tecido_acao
        notas.append(
            f"Conversão Ação Distribuidora: Tabela 1 {moeda_br(valor_custo)} por metro linear com largura {largura_tecido_acao:.2f}m; custo de saída m² = {moeda_br(custo_convertido)}."
        )
        return round(custo_convertido, 4), "M²", " | ".join([x for x in [obs] + notas if x])

    # Proteção contra reconversão de tecidos já convertidos.
    # Valores baixos/médios em tecido de persiana normalmente já representam custo de saída por m².
    # A conversão automática por largura fica reservada para casos claros de preço por metro linear alto.
    if eh_tecido_precheck and unidade_upper in ["ML", "M", "MT", "METRO", "METRO LINEAR", ""] and valor_custo <= 60:
        notas.append("Regra SmartTec: tecido com custo já compatível com m²; não reconverter por largura do nome.")
        return round(valor_custo, 4), "M²", " | ".join([x for x in [obs] + notas if x])

    # Regras específicas de componentes do Rolô.
    # Estas regras vêm antes das regras genéricas para não tratar "Tampa da base" como barra/base em ML.
    eh_emenda_corrente = ("EMENDA" in nome_upper or "CONECTOR" in nome_upper or "CONF" in nome_upper) and (
        "CORRENTE" in nome_upper or "CORR" in nome_upper
    )
    if eh_emenda_corrente:
        # No seu uso, emenda entra por peça/unidade. O valor importado já está correto.
        notas.append("Regra Rolô: emenda/conector da corrente tratado como UNIDADE.")
        return round(valor_custo, 4), "UN", " | ".join([x for x in [obs] + notas if x])

    eh_tampa_base = "TAMPA" in nome_upper and ("BASE" in nome_upper or "CHATA" in nome_upper)
    if eh_tampa_base:
        # No seu uso, tampa da base entra por unidade. Não converter por metro linear.
        notas.append("Regra Rolô: tampa da base tratada como UNIDADE.")
        return round(valor_custo, 4), "UN", " | ".join([x for x in [obs] + notas if x])

    eh_comando_rolo = (
        "COMANDO" in nome_upper
        or "MOLA ROLO" in nome_upper
        or "MOLA ROLÔ" in nome_upper
        or "ONE TOUCH" in nome_upper
    ) and not any(p in nome_upper for p in ["TRILHO", "ROMANA", "PAINEL", "TOLDO", "CORTINA"])

    if eh_comando_rolo:
        # No cadastro importado, alguns comandos aparecem como KIT, mas o valor é do pacote com 10 kits.
        # Regra prática inicial: valor alto de comando representa pacote/caixa com 10 kits.
        divisor_pacote = 10.0 if valor_custo >= 50 else 1.0
        custo_convertido = valor_custo / divisor_pacote

        if divisor_pacote > 1:
            notas.append(
                f"Regra Rolô: comando importado como pacote com 10 kits; custo por KIT = {moeda_br(custo_convertido)}."
            )
        else:
            notas.append("Regra Rolô: comando tratado como KIT.")

        return round(custo_convertido, 4), "KIT", " | ".join([x for x in [obs] + notas if x])

    # Tecido/lona por metro linear com largura fixa -> custo por m².
    # Só converte quando for claramente preço de COMPRA por metro linear.
    largura_tecido = detectar_largura_tecido_nome(nome)
    eh_tecido = eh_tecido_precheck

    unidade_indica_metro_linear = unidade_upper in ["ML", "M", "MT", "METRO", "METRO LINEAR"]
    unidade_indica_rolo = unidade_upper in ["RL", "ROLO", "PEÇA", "PECA"]

    if eh_tecido and largura_tecido > 0 and (unidade_indica_metro_linear or unidade_indica_rolo) and valor_custo > 60:
        custo_convertido = valor_custo / largura_tecido
        notas.append(
            f"Conversão automática importação: compra {moeda_br(valor_custo)} por metro linear com largura {largura_tecido:.2f}m; custo de saída m² = {moeda_br(custo_convertido)}."
        )
        return round(custo_convertido, 4), "M²", " | ".join([x for x in [obs] + notas if x])

    if eh_tecido:
        # Mantém tecido como m² para o motor usar largura x altura sem reconverter valor.
        notas.append("Regra SmartTec: tecido tratado como custo de saída por m², sem nova conversão automática.")
        return round(valor_custo, 4), "M²", " | ".join([x for x in [obs] + notas if x])

    # Rolos de fita/espaguete/macarrão comprados em RL/rolo, mas consumidos por metro linear.
    # Ex.: FTF 20MMX100MTS = valor do rolo / 100; ESPAGUETE 3,00MM ROLO COM 95MTS = valor / 95.
    eh_rolo_linear = any(p in nome_upper for p in [
        "FITA", "FTF", "ESPAGUETE", "MACARRAO", "MACARRÃO", "CORDÃO", "CORDAO"
    ])
    metragem_rolo = detectar_metragem_nome(nome)

    if eh_rolo_linear and metragem_rolo > 0 and unidade_upper not in ["ML", "METRO", "METRO LINEAR", "M"]:
        custo_convertido = valor_custo / metragem_rolo
        notas.append(
            f"Conversão automática motor: compra {moeda_br(valor_custo)} por rolo/embalagem de {metragem_rolo:.2f}m; custo de saída ML = {moeda_br(custo_convertido)}."
        )
        return round(custo_convertido, 4), "ML", " | ".join([x for x in [obs] + notas if x])

    # Algumas fitas/espaguetes vêm como RL mas sem metragem detectável; não converter no chute.
    # Melhor mostrar o custo original para o usuário corrigir no cadastro/conversão.

    # Barras/perfis/tubos comprados por barra. Sem metragem no nome, assume 6m.
    eh_barra = any(p in nome_upper for p in ["TUBO", "PERFIL", "BASE", "TRILHO", "GUIA"])
    unidade_barra = unidade_upper in ["BR", "BARRA", "BARRAS"]

    # SmartTec: muitos tubos/perfis antigos já vieram com custo por ML,
    # mesmo quando a unidade ficou como barra/UN na importação.
    # Ex.: TUBO P/ ROLÔ 38MM NATURAL com custo 9,02 já é custo por ML.
    # Nesse caso não pode dividir de novo por 6m.
    if eh_barra and valor_custo <= 30 and not detectar_metragem_nome(nome):
        notas.append("Regra SmartTec: tubo/perfil/base com custo baixo já tratado como ML; não reconverter por barra de 6m.")
        return round(valor_custo, 4), "ML", " | ".join([x for x in [obs] + notas if x])

    # Se já está cadastrado como ML, o custo já é de saída. Não converter de novo.
    if eh_barra and unidade_upper in ["ML", "METRO", "METRO LINEAR", "M"]:
        notas.append("Regra motor: barra/tubo/perfil já está com custo por ML; não reconverter por 6m.")
        return round(valor_custo, 4), "ML", " | ".join([x for x in [obs] + notas if x])

    if eh_barra or unidade_barra:
        metragem = detectar_metragem_nome(nome) or 6.0
        custo_convertido = valor_custo / metragem
        notas.append(
            f"Conversão automática importação: compra {moeda_br(valor_custo)} por barra de {metragem:.2f}m; custo de saída ML = {moeda_br(custo_convertido)}."
        )
        return round(custo_convertido, 4), "ML", " | ".join([x for x in [obs] + notas if x])

    # Corrente/cordão/correia vendidos por metro quando o nome informa embalagem.
    eh_metragem = any(p in nome_upper for p in ["CORRENTE", "CORR", "CORDÃO", "CORDAO", "CORREIA"])
    metragem = detectar_metragem_nome(nome)

    if eh_metragem and metragem > 0:
        custo_convertido = valor_custo / metragem
        notas.append(
            f"Conversão automática importação: compra {moeda_br(valor_custo)} para {metragem:.2f}m; custo de saída ML = {moeda_br(custo_convertido)}."
        )
        return round(custo_convertido, 4), "ML", " | ".join([x for x in [obs] + notas if x])

    return valor_custo, unidade_venda, obs


def montar_payload_produto_importacao(row):
    """Mapeia uma linha da planilha preparada para o schema ProdutoCreate da API."""
    nome = valor_planilha_para_texto(row.get("nome"), "")

    valor_custo_original = valor_planilha_para_float(row.get("valor_custo"), 0.0)
    despesas_acessorias = valor_planilha_para_float(row.get("despesas_acessorias"), 0.0)
    outras_despesas = valor_planilha_para_float(row.get("outras_despesas"), 0.0)

    tipo_produto = inferir_tipo_produto_importacao(row)
    tipo_produto_normalizado = str(tipo_produto or "").strip().lower()

    unidade_venda_importada = valor_planilha_para_texto(row.get("unidade_venda"), "UN")
    observacoes_importadas = valor_planilha_para_texto(row.get("observacoes"))

    valor_custo, unidade_venda_importada, observacoes_importadas = aplicar_conversao_importacao(
        row,
        valor_custo_original,
        unidade_venda_importada,
        observacoes_importadas,
    )

    custo_final_planilha = valor_planilha_para_float(row.get("custo_final"), 0.0)
    # Se houve conversão, custo_final deve acompanhar o custo convertido.
    custo_final = valor_custo + despesas_acessorias + outras_despesas
    if custo_final_planilha and abs(valor_custo - valor_custo_original) < 0.0001:
        custo_final = custo_final_planilha

    possui_composicao = "Sim" if "fabricado" in tipo_produto_normalizado else "Não"
    movimenta_estoque = "Não" if "serviço" in tipo_produto_normalizado or "servico" in tipo_produto_normalizado else "Sim"

    grupo_produto_importado = valor_planilha_para_texto(row.get("grupo_produto")) or inferir_grupo_produto_importacao(row)
    grupo_tecnico_importado = valor_planilha_para_texto(row.get("grupo_tecnico"))

    payload = {
        "nome": nome,
        "codigo_interno": normalizar_codigo_importacao(row.get("codigo_interno")),
        "codigo_barras": normalizar_codigo_importacao(row.get("codigo_barras")) or normalizar_codigo_importacao(row.get("codigo_interno")),
        "grupo_produto": grupo_produto_importado,
        "tipo_produto": tipo_produto,
        "modelo_tecnico": inferir_modelo_tecnico_produto({"nome": nome, "grupo_produto": grupo_produto_importado, "tipo_produto": tipo_produto}),
        "grupo_tecnico": normalizar_grupo_tecnico(grupo_tecnico_importado) or inferir_grupo_tecnico_produto({"nome": nome, "grupo_produto": grupo_produto_importado, "tipo_produto": tipo_produto}),
        # Legado interno: mantém compatibilidade com receitas antigas.
        "familia_tecnica": inferir_familia_tecnica_produto({"nome": nome, "grupo_produto": grupo_produto_importado, "tipo_produto": tipo_produto}),
        "varia_cor": inferir_varia_cor_componente({"nome": nome, "grupo_produto": grupo_produto_importado, "tipo_produto": tipo_produto}),
        "cor_componente": inferir_cor_componente_produto({"nome": nome}),
        "unidade_venda": unidade_venda_importada,
        "movimenta_estoque": movimenta_estoque,
        "habilitar_nota_fiscal": "Sim",
        "possui_variacoes": "Não",
        "possui_composicao": possui_composicao,
        "situacao": valor_planilha_para_texto(row.get("situacao"), "Ativo"),
        "linha": valor_planilha_para_texto(row.get("linha")),
        "modelo": valor_planilha_para_texto(row.get("modelo")),
        "tipo_cortina_persiana": valor_planilha_para_texto(row.get("tipo_cortina_persiana")),
        "material_tecido": valor_planilha_para_texto(row.get("material_tecido")),
        "cor": valor_planilha_para_texto(row.get("cor")),
        "largura": valor_planilha_para_float(row.get("largura"), 0.0),
        "altura": valor_planilha_para_float(row.get("altura"), 0.0),
        "comprimento": valor_planilha_para_float(row.get("comprimento"), 0.0),
        "peso": valor_planilha_para_float(row.get("peso"), 0.0),
        "descricao": valor_planilha_para_texto(row.get("descricao")),
        "observacoes": observacoes_importadas,
        "valor_custo": valor_custo,
        "despesas_acessorias": despesas_acessorias,
        "outras_despesas": outras_despesas,
        "custo_final": custo_final,
        "margem_lucro": valor_planilha_para_float(row.get("margem_lucro"), 0.0),
        "valor_venda": valor_planilha_para_float(row.get("valor_venda"), 0.0),
        "estoque_minimo": valor_planilha_para_float(row.get("estoque_minimo"), 0.0),
        "estoque_maximo": valor_planilha_para_float(row.get("estoque_maximo"), 0.0),
        "estoque_atual": valor_planilha_para_float(row.get("estoque_atual"), 0.0),
        "ncm": valor_planilha_para_texto(row.get("ncm")),
        "cest": valor_planilha_para_texto(row.get("cest")),
        "origem": valor_planilha_para_texto(row.get("arquivo_origem")),
    }

    return payload


def auditar_termos_importacao_dataframe(df):
    """
    Confere se a planilha já veio com termos comerciais indesejados.
    Não altera os dados; apenas informa.
    """
    colunas_texto = [
        c for c in [
            "nome",
            "grupo_produto",
            "tipo_produto",
            "unidade_venda",
            "material_tecido",
            "cor",
            "linha",
            "modelo",
            "tipo_cortina_persiana",
            "descricao",
            "observacoes",
        ]
        if c in df.columns
    ]

    termos_alerta = ["VISÃO DUPLA", "VISAO DUPLA", "RASTREIO"]
    achados = []

    for coluna in colunas_texto:
        serie = df[coluna].astype(str)
        for termo in termos_alerta:
            mask = serie.str.upper().str.contains(termo, na=False, regex=False)
            qtd = int(mask.sum())
            if qtd:
                exemplos = serie[mask].head(5).tolist()
                achados.append({
                    "coluna": coluna,
                    "termo": termo,
                    "qtd": qtd,
                    "exemplos": exemplos,
                })

    return achados


def payload_importacao_tem_traducao_indesejada(payload):
    texto = " ".join(str(payload.get(c) or "") for c in [
        "nome",
        "grupo_produto",
        "material_tecido",
        "linha",
        "modelo",
        "tipo_cortina_persiana",
        "descricao",
        "observacoes",
    ]).upper()

    return any(termo in texto for termo in ["VISÃO DUPLA", "VISAO DUPLA", "RASTREIO"])


def validar_dataframe_importacao_produtos(df):
    colunas_obrigatorias = ["nome"]
    faltando = [col for col in colunas_obrigatorias if col not in df.columns]

    if faltando:
        return False, f"Coluna obrigatória ausente: {', '.join(faltando)}"

    return True, ""


def valor_pdf_acao_para_float(valor, padrao=0.0):
    """Converte números da tabela Ação: 65,000 -> 65.0, 3,25% -> 3.25."""
    try:
        texto = str(valor or "").strip()
        if not texto or texto.upper() in ["SOB CONSULT", "SOB CONSULTA", "NAN", "NONE", "NULL"]:
            return padrao
        texto = texto.replace("R$", "").replace("%", "").strip()
        if "," in texto and "." in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", ".")
        return float(texto)
    except Exception:
        return padrao


def limpar_texto_pdf_acao(valor):
    texto = str(valor or "").replace("\n", " ").strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def detectar_categoria_pagina_pdf_acao(texto_pagina):
    texto = str(texto_pagina or "")
    m = re.search(r"\n(\d{3}\s*-\s*[^\n]+)", "\n" + texto)
    if m:
        return limpar_texto_pdf_acao(m.group(1))
    return ""


def extrair_linhas_pdf_acao(arquivo_importacao):
    """
    Extrai as tabelas oficiais da Ação Distribuidora em PDF.
    Mantém Cód. Produto, Descrição, Unidade, Tabela 1, Tabela 2, IPI e pacote mínimo.
    """
    try:
        import pdfplumber
    except Exception as erro:
        raise RuntimeError(
            "Para importar PDF da Ação, instale a dependência pdfplumber no ambiente do Streamlit: pip install pdfplumber"
        ) from erro

    arquivo_importacao.seek(0)
    linhas = []

    with pdfplumber.open(arquivo_importacao) as pdf:
        for numero_pagina, pagina in enumerate(pdf.pages, start=1):
            texto_pagina = pagina.extract_text() or ""
            categoria_pagina = detectar_categoria_pagina_pdf_acao(texto_pagina)
            tabelas = pagina.extract_tables() or []
            categoria_atual = categoria_pagina

            for tabela in tabelas:
                if not tabela:
                    continue

                for row in tabela:
                    if not row:
                        continue

                    cells = [limpar_texto_pdf_acao(c) for c in row]
                    while len(cells) < 8:
                        cells.append("")

                    primeira = cells[0]
                    segunda = cells[1] if len(cells) > 1 else ""

                    if re.match(r"^\d{3}\s*-\s*", primeira):
                        categoria_atual = primeira
                        continue

                    if primeira.upper().startswith("CÓD") or primeira.upper().startswith("COD") or segunda.upper().startswith("DESCRI"):
                        continue

                    codigo = normalizar_codigo_importacao(primeira)
                    descricao = segunda

                    # Linhas quebradas pelo PDF às vezes colocam parte da descrição em outras colunas.
                    if codigo and not descricao:
                        possiveis = [c for c in cells[1:4] if c and not re.match(r"^[0-9,.%]+$", c)]
                        descricao = " ".join(possiveis).strip()

                    if not codigo or not descricao:
                        continue

                    linhas.append({
                        "pagina_pdf": numero_pagina,
                        "categoria_pdf": categoria_atual or categoria_pagina,
                        "codigo_pdf": codigo,
                        "descricao_pdf": descricao,
                        "unidade_pdf": cells[2],
                        "tabela_1_pdf": cells[3],
                        "tabela_2_pdf": cells[4],
                        "ipi_pdf": cells[5],
                        "pacote_minimo_pdf": cells[6],
                        "qtd_caixa_pdf": cells[7],
                    })

    return pd.DataFrame(linhas)


def categoria_acao_para_grupo_tecnico(categoria, descricao):
    categoria_u = normalizar_busca_motor(categoria)
    descricao_u = normalizar_busca_motor(descricao)
    texto = f"{categoria_u} {descricao_u}"

    if "TECIDO DOUBLE VISION" in texto:
        return "Tecidos", "TECIDOS_DOUBLE_VISION"
    if "TECIDO ROLO" in texto or "ROLO BLACKOUT" in texto or "ROLO TRANSLUCIDO" in texto or "ROLO SCREEN" in texto:
        return "Tecidos", "TECIDOS_ROLO_ROMANA_PAINEL"
    if "TECIDO VERTICAL" in texto:
        return "Lâminas", "LAMINAS_VERTICAL"
    if "TECIDO PLISSADA" in texto:
        return "Tecidos", "TECIDOS_PLISSADA"
    if "TECIDO CELULAR" in texto:
        return "Tecidos", "TECIDOS_CELULAR"
    if "TECIDOS PARA TOLDOS" in texto or "TECIDO PARA TOLDO" in texto or "LONA" in texto:
        return "Tecidos", "TECIDOS_TOLDO"

    if any(t in texto for t in ["DOUB VISION", "DOUBLE VISION", "AC161", "AC162", "AC638"]):
        return "Componentes", "COMPONENTES_DOUBLE_VISION"
    if any(t in texto for t in ["ROMANA", "FITA PARA ROMANA", "CAVALETE ROMANA", "CABECEIRA DA ROMANA"]):
        return "Componentes", "COMPONENTES_ROMANA"
    if any(t in texto for t in ["VERTICAL"]):
        return "Componentes", "COMPONENTES_VERTICAL"
    if any(t in texto for t in ["PLISSADA", "CELULAR"]):
        if "CELULAR" in texto:
            return "Componentes", "COMPONENTES_CELULAR"
        return "Componentes", "COMPONENTES_PLISSADA"
    if "TOLDO" in texto:
        return "Componentes", "COMPONENTES_TOLDO"

    if any(t in texto for t in ["MOTOR", "CONTROLE", "RECEPTOR", "FONTE", "BATERIA", "CARREGADOR", "COROA", "PONTA OPOSTA"]):
        if "MOTOR" in texto and not any(a in texto for a in ["CONTROLE", "RECEPTOR", "FONTE", "BATERIA", "CARREGADOR", "COROA", "PONTA OPOSTA"]):
            return "Motorização", "MOTORES"
        return "Motorização", "ACESSORIOS_MOTOR"

    return "Componentes", "COMPONENTES_ROLO"


def detectar_largura_pdf_acao(descricao):
    texto = str(descricao or "").upper()
    texto = texto.replace("\n", " ")
    padroes = [
        r"-\s*(\d[,.]\d{1,2})\s*M\b",
        r"\b(\d[,.]\d{1,2})\s*M\b",
        r"\b(\d[,.](?:00|20|30|40|50|60|80))\b",
    ]
    for padrao in padroes:
        m = re.search(padrao, texto)
        if m:
            try:
                largura = float(m.group(1).replace(",", "."))
                if 0.3 <= largura <= 6.0:
                    return largura
            except Exception:
                pass
    return 0.0


def preparar_dataframe_pdf_acao(df_pdf, nome_arquivo=""):
    """
    Converte PDF da Ação no layout padrão já aceito pelo importador do SmartTec.
    Regra de custo:
    - valor_custo recebe Tabela 1.
    - Tabela 2, IPI e pacote mínimo ficam em observações.
    - tecidos vêm em metro linear; aplicar_conversao_importacao converte para M² quando necessário.
    - barras/perfis vêm como BR; aplicar_conversao_importacao converte para ML quando necessário.
    """
    registros = []
    nome_arquivo = str(nome_arquivo or "PDF Ação")

    if df_pdf is None:
        df_pdf = pd.DataFrame()

    for _, row in df_pdf.iterrows():
        categoria = limpar_texto_pdf_acao(row.get("categoria_pdf"))
        descricao = limpar_texto_pdf_acao(row.get("descricao_pdf"))
        codigo = normalizar_codigo_importacao(row.get("codigo_pdf"))
        unidade = limpar_texto_pdf_acao(row.get("unidade_pdf")) or "UN"
        tabela_1 = valor_pdf_acao_para_float(row.get("tabela_1_pdf"), 0.0)
        tabela_2 = valor_pdf_acao_para_float(row.get("tabela_2_pdf"), 0.0)
        ipi = limpar_texto_pdf_acao(row.get("ipi_pdf"))
        pacote = limpar_texto_pdf_acao(row.get("pacote_minimo_pdf"))
        qtd_caixa = limpar_texto_pdf_acao(row.get("qtd_caixa_pdf"))

        if not descricao or not codigo:
            continue

        grupo_produto, grupo_tecnico = categoria_acao_para_grupo_tecnico(categoria, descricao)
        largura = detectar_largura_pdf_acao(descricao)
        nome = descricao.replace("*", "").strip().upper()

        observacoes = (
            f"Fornecedor: Ação Distribuidora | Origem: {nome_arquivo} | Categoria PDF: {categoria} | "
            f"Tabela 1: {row.get('tabela_1_pdf','')} | Tabela 2/fracionado: {row.get('tabela_2_pdf','')} | "
            f"IPI: {ipi} | Pacote mínimo: {pacote} | Qtd. caixa: {qtd_caixa}"
        )

        registros.append({
            "nome": nome,
            "codigo_interno": codigo,
            "codigo_barras": codigo,
            "grupo_produto": grupo_produto,
            "grupo_tecnico": grupo_tecnico,
            "tipo_produto": "Componente",
            "unidade_venda": unidade,
            "valor_custo": tabela_1,
            "custo_final": tabela_1,
            "valor_venda": 0.0,
            "largura": largura,
            "altura": 0.0,
            "comprimento": 0.0,
            "peso": 0.0,
            "situacao": "Ativo",
            "linha": categoria,
            "modelo": "Ação Distribuidora",
            "descricao": descricao,
            "observacoes": observacoes,
            "arquivo_origem": nome_arquivo,
            "tipo_sugerido_status": "OK" if tabela_1 > 0 else "REVISAR",
        })

    return pd.DataFrame(registros)


def carregar_planilha_importacao_produtos(arquivo_importacao):
    nome = arquivo_importacao.name.lower()

    if nome.endswith(".pdf"):
        df_pdf = extrair_linhas_pdf_acao(arquivo_importacao)
        df_importacao = preparar_dataframe_pdf_acao(df_pdf, arquivo_importacao.name)
        return {"Ação PDF": df_importacao, "Extração bruta PDF": df_pdf}

    if nome.endswith(".csv"):
        try:
            return {"CSV": pd.read_csv(arquivo_importacao, sep=None, engine="python")}
        except Exception:
            arquivo_importacao.seek(0)
            return {"CSV": pd.read_csv(arquivo_importacao, sep=";")}

    return pd.read_excel(arquivo_importacao, sheet_name=None)


def normalizar_codigo_importacao(valor):
    """
    Normaliza código vindo do Excel/PDF.

    - Se for código alfanumérico, preserva o texto.
      Ex.: JPTEC-0001 continua JPTEC-0001.

    - Se for código somente numérico, remove separadores e recompõe zeros à esquerda.
      Ex.: 116,501,390 -> 00116501390
           100100020   -> 00100100020
    """
    texto = str(valor or "").strip()

    if texto.lower() in ["nan", "none", "null", ""]:
        return ""

    # Preserva códigos criados para fornecedores sem código original, como JPTEC-0001.
    if re.search(r"[A-Za-z]", texto):
        texto = texto.upper()
        texto = re.sub(r"\s+", "", texto)
        return texto

    # Quando o Excel converte código para número, pode vir com .0 ou vírgulas/pontos.
    digitos = re.sub(r"\D+", "", texto)

    if not digitos:
        return ""

    # Códigos numéricos de fornecedores costumam precisar manter zeros à esquerda.
    if len(digitos) < 11:
        digitos = digitos.zfill(11)

    return digitos


def normalizar_nome_importacao(valor):
    texto = str(valor or "").strip().upper()
    texto = (
        texto.replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    texto = re.sub(r"[^A-Z0-9%]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def normalizar_busca_texto_flexivel(valor):
    """Normaliza textos para busca livre.

    Permite que a busca por "persiana rolo" encontre "PERSIANA_ROLO"
    e que "rolo" encontre "ROLÔ". Também ajuda na edição em massa,
    onde o usuário costuma pesquisar pelo grupo técnico como texto.
    """
    texto = preservar_termos_comerciais(valor)
    texto = normalizar_nome_importacao(texto)
    texto = texto.replace("_", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def serie_contem_busca_flexivel(serie, termo):
    termo_norm = normalizar_busca_texto_flexivel(termo)
    if not termo_norm:
        return pd.Series([True] * len(serie), index=serie.index)

    return serie.astype(str).map(normalizar_busca_texto_flexivel).str.contains(
        termo_norm,
        na=False,
        regex=False,
    )


def preparar_payload_importacao_seguro(payload):
    payload = dict(payload or {})

    codigo_interno = normalizar_codigo_importacao(payload.get("codigo_interno"))
    codigo_barras = normalizar_codigo_importacao(payload.get("codigo_barras"))

    if codigo_interno:
        payload["codigo_interno"] = codigo_interno
    if codigo_barras:
        payload["codigo_barras"] = codigo_barras
    elif codigo_interno:
        payload["codigo_barras"] = codigo_interno

    return payload


def montar_indices_produtos_existentes(produtos):
    por_codigo_interno = {}
    por_codigo_barras = {}
    por_nome = {}

    for produto in produtos or []:
        try:
            pid = int(produto.get("id") or 0)
        except Exception:
            pid = 0

        if not pid:
            continue

        codigo_interno = normalizar_codigo_importacao(produto.get("codigo_interno"))
        codigo_barras = normalizar_codigo_importacao(produto.get("codigo_barras"))
        nome_norm = normalizar_nome_importacao(produto.get("nome"))

        if codigo_interno:
            por_codigo_interno[codigo_interno] = produto
        if codigo_barras:
            por_codigo_barras[codigo_barras] = produto
        if nome_norm:
            por_nome[nome_norm] = produto

    return por_codigo_interno, por_codigo_barras, por_nome


def encontrar_produto_existente_importacao(payload, por_codigo_interno, por_codigo_barras, por_nome, criterio="codigo_ou_nome"):
    codigo_interno = normalizar_codigo_importacao(payload.get("codigo_interno"))
    codigo_barras = normalizar_codigo_importacao(payload.get("codigo_barras"))
    nome_norm = normalizar_nome_importacao(payload.get("nome"))

    if criterio in ["codigo", "codigo_ou_nome"]:
        if codigo_interno and codigo_interno in por_codigo_interno:
            return por_codigo_interno[codigo_interno], "código interno"
        if codigo_barras and codigo_barras in por_codigo_barras:
            return por_codigo_barras[codigo_barras], "código de barras"

    if criterio in ["nome", "codigo_ou_nome"]:
        if nome_norm and nome_norm in por_nome:
            return por_nome[nome_norm], "nome"

    return None, ""


def calcular_resumo_importacao_produtos(df, somente_ok=True, limite=None, criterio="codigo_ou_nome"):
    df_importar = df.copy()

    if somente_ok and "tipo_sugerido_status" in df_importar.columns:
        df_importar = df_importar[
            df_importar["tipo_sugerido_status"].astype(str).str.strip().str.upper() == "OK"
        ].copy()

    if limite:
        df_importar = df_importar.head(int(limite)).copy()

    try:
        produtos_existentes = buscar_produtos_api()
    except Exception:
        produtos_existentes = []

    por_codigo_interno, por_codigo_barras, por_nome = montar_indices_produtos_existentes(produtos_existentes)

    novos = 0
    existentes = 0
    exemplos_existentes = []
    exemplos_novos = []

    for _, row in df_importar.iterrows():
        payload = preparar_payload_importacao_seguro(montar_payload_produto_importacao(row))
        existente, motivo = encontrar_produto_existente_importacao(
            payload,
            por_codigo_interno,
            por_codigo_barras,
            por_nome,
            criterio=criterio,
        )

        nome = str(payload.get("nome") or "").strip()
        codigo = str(payload.get("codigo_interno") or payload.get("codigo_barras") or "").strip()

        if existente:
            existentes += 1
            if len(exemplos_existentes) < 5:
                exemplos_existentes.append(f"{codigo} - {nome} ({motivo})")
        else:
            novos += 1
            if len(exemplos_novos) < 5:
                exemplos_novos.append(f"{codigo} - {nome}")

    return {
        "total": len(df_importar),
        "existentes": existentes,
        "novos": novos,
        "exemplos_existentes": exemplos_existentes,
        "exemplos_novos": exemplos_novos,
    }


def importar_produtos_dataframe(df, somente_ok=True, pular_existentes=True, limite=None, modo_existentes='pular', criterio='codigo_ou_nome'):
    df_importar = df.copy()

    if somente_ok and "tipo_sugerido_status" in df_importar.columns:
        df_importar = df_importar[
            df_importar["tipo_sugerido_status"].astype(str).str.strip().str.upper() == "OK"
        ].copy()

    if limite:
        df_importar = df_importar.head(int(limite)).copy()

    produtos_existentes = buscar_produtos_api()
    por_codigo_interno, por_codigo_barras, por_nome = montar_indices_produtos_existentes(produtos_existentes)

    total = len(df_importar)
    importados = 0
    atualizados = 0
    pulados = 0
    erros = []

    barra = st.progress(0)
    status = st.empty()

    for posicao, (_, row) in enumerate(df_importar.iterrows(), start=1):
        payload = preparar_payload_importacao_seguro(montar_payload_produto_importacao(row))

        nome = str(payload.get("nome") or "").strip()
        codigo_interno = str(payload.get("codigo_interno") or "").strip()
        codigo_barras = str(payload.get("codigo_barras") or "").strip()

        if not nome:
            pulados += 1
            erros.append("Linha sem nome foi ignorada.")
            continue

        produto_existente, motivo_existente = encontrar_produto_existente_importacao(
            payload,
            por_codigo_interno,
            por_codigo_barras,
            por_nome,
            criterio=criterio,
        )

        if produto_existente and modo_existentes == "pular":
            pulados += 1
            continue

        try:
            if payload_importacao_tem_traducao_indesejada(payload):
                erros.append(f"{nome}: importação bloqueada porque o payload contém termo traduzido indevido.")
                continue

            if produto_existente and modo_existentes == "atualizar":
                try:
                    produto_id_existente = int(produto_existente.get("id"))
                    resp = atualizar_produto(produto_id_existente, payload)
                except Exception as erro_update:
                    resp = None
                    erros.append(f"{nome}: erro ao atualizar produto existente encontrado por {motivo_existente}: {erro_update}")

                if resp is not None and hasattr(resp, "status_code") and resp.status_code in [200, 201, 204]:
                    atualizados += 1
                elif resp is not None and not hasattr(resp, "status_code"):
                    atualizados += 1
                elif resp is not None:
                    try:
                        detalhe = resp.json()
                    except Exception:
                        detalhe = getattr(resp, "text", "")
                    erros.append(f"{nome}: erro ao atualizar existente encontrado por {motivo_existente}: {detalhe}")
                else:
                    erros.append(f"{nome}: erro ao atualizar existente encontrado por {motivo_existente}: sem resposta da API.")

                continue

            resp = criar_produto(payload)

            if hasattr(resp, "status_code") and resp.status_code not in [200, 201]:
                try:
                    detalhe = resp.json()
                except Exception:
                    detalhe = getattr(resp, "text", "")
                erros.append(f"{nome}: {detalhe}")
            else:
                importados += 1

        except Exception as e:
            erros.append(f"{nome}: {str(e)}")

        if total:
            barra.progress(min(posicao / total, 1.0))
        status.caption(f"Importando {posicao} de {total} produto(s)...")

    barra.empty()
    status.empty()

    return {
        "total": total,
        "importados": importados,
        "atualizados": atualizados,
        "pulados": pulados,
        "erros": erros,
    }


def calcular_custo_unitario_saida(valor_entrada, qtd_saida):
    """Calcula custo da unidade de saída a partir do valor de compra/entrada."""
    try:
        valor_entrada = float(valor_entrada or 0)
        qtd_saida = float(qtd_saida or 0)
        if qtd_saida <= 0:
            return 0.0
        return valor_entrada / qtd_saida
    except Exception:
        return 0.0


def normalizar_unidade_label(unidade):
    texto = str(unidade or "").strip()
    mapa = {
        "M²": "m²",
        "MT²": "m²",
        "METRO QUADRADO": "m²",
        "M2": "m²",
        "ML": "metro linear",
        "MT": "metro",
        "METRO": "metro",
        "UN": "unidade",
        "UNID": "unidade",
        "UNIDADE": "unidade",
    }
    return mapa.get(texto.upper(), texto or "-")


def calcular_custo_motor_produto(produto):
    """
    Garante que o motor use custo na unidade de consumo/saída.
    Isso corrige produtos já importados antes da regra de conversão.
    """
    valor_base = float(produto.get("custo_final") or produto.get("valor_custo") or 0)
    unidade_base = str(produto.get("unidade_venda") or "UN").strip()
    observacoes = str(produto.get("observacoes") or "").strip()

    try:
        valor_convertido, unidade_convertida, _obs = aplicar_conversao_importacao(
            produto,
            valor_base,
            unidade_base,
            observacoes,
        )
        return float(valor_convertido or valor_base), str(unidade_convertida or unidade_base or "UN")
    except Exception:
        return valor_base, unidade_base or "UN"


def produto_para_item_catalogo_motor(produto):
    custo_unitario, unidade_motor = calcular_custo_motor_produto(produto)

    familia_tecnica = normalizar_familia_tecnica(produto.get("familia_tecnica")) or inferir_familia_tecnica_produto(produto)
    cor_componente = inferir_cor_componente_produto(produto)
    varia_cor = inferir_varia_cor_componente({**(produto or {}), "familia_tecnica": familia_tecnica})

    return {
        "codigo": str(produto.get("codigo_interno") or produto.get("codigo_barras") or produto.get("id") or "").strip(),
        "produto_id": produto.get("id"),
        "nome": str(produto.get("nome") or "").strip(),
        "unidade": unidade_motor,
        "custo_unitario": float(custo_unitario or 0),
        "familia_tecnica": familia_tecnica,
        "varia_cor": bool(varia_cor),
        "cor_componente": cor_componente,
    }


def normalizar_busca_motor(valor):
    texto = str(valor or "").upper()
    texto = (
        texto.replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    texto = re.sub(r"[^A-Z0-9% ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def texto_produto_motor(produto):
    return normalizar_busca_motor(
        " ".join(
            [
                str(produto.get("nome") or ""),
                str(produto.get("codigo_interno") or ""),
                str(produto.get("codigo_barras") or ""),
                str(produto.get("grupo_produto") or ""),
                str(produto.get("tipo_produto") or ""),
                str(produto.get("linha") or ""),
                str(produto.get("modelo") or ""),
                str(produto.get("tipo_cortina_persiana") or ""),
                str(produto.get("material_tecido") or ""),
                str(produto.get("cor") or ""),
                str(produto.get("observacoes") or ""),
            ]
        )
    )


def tokens_produto_base_motor(produto_base):
    texto = texto_produto_motor(produto_base or {})
    tokens = []

    # Cores e materiais ajudam muito a puxar o tecido correto.
    for campo in ["cor", "material_tecido", "linha", "modelo", "tipo_cortina_persiana"]:
        valor = normalizar_busca_motor((produto_base or {}).get(campo))
        if valor and valor not in ["SELECIONE", "SELECIONE..."]:
            tokens.extend([t for t in valor.split() if len(t) >= 3])

    # Também pega partes relevantes do nome do produto fabricado.
    for t in texto.split():
        if len(t) >= 4 and t not in ["ROLO", "ROLO", "PERSIANA", "PRODUTO", "FABRICADO", "MANUAL", "MOTORIZADA"]:
            tokens.append(t)

    # Remove duplicados preservando ordem.
    unicos = []
    for t in tokens:
        if t not in unicos:
            unicos.append(t)

    return unicos


def contem_algum(texto, termos):
    return any(normalizar_busca_motor(t) in texto for t in termos)


def contem_todos(texto, termos):
    return all(normalizar_busca_motor(t) in texto for t in termos)


def familia_material_tecido_motor(valor):
    texto = normalizar_busca_motor(valor)
    if not texto:
        return ""

    if "DOUBLE VISION" in texto or "VISION" in texto:
        return "DOUBLE VISION"
    if "SCREEN" in texto:
        return "SCREEN"
    if "BLACKOUT" in texto or texto.startswith("BK ") or " BK " in texto:
        return "BLACKOUT"
    if "TRANSLUCIDO" in texto or "TRANSLUCIDA" in texto:
        return "TRANSLUCIDO"
    if "ROMA" in texto:
        return "ROMA"
    if "NAPOLES" in texto:
        return "NAPOLES"
    if "BRISK" in texto:
        return "BRISK"
    if "LINHO" in texto:
        return "LINHO"
    return ""


def grupo_produto_motor(produto):
    return normalizar_busca_motor((produto or {}).get("grupo_produto"))


def eh_tecido_persiana_motor(produto):
    grupo = grupo_produto_motor(produto)
    texto = texto_produto_motor(produto or {})
    tipo = normalizar_busca_motor((produto or {}).get("tipo_produto"))

    if "FABRICADO" in tipo:
        return False

    if contem_algum(texto, [
        "GUIA DO TECIDO", "GUIA LATERAL", "SUPERIOR", "INFERIOR",
        "AC191", "AC133", "FITA", "BASE", "TUBO", "COMANDO",
        "CORRENTE", "TAMPA", "EMENDA", "ESPAGUETE", "MACARRAO", "MACARRÃO",
        "CONECTOR", "SUPORTE", "TRILHO", "VARETA"
    ]):
        return False

    if contem_algum(grupo, ["CORTINA", "CORTINAS", "SERVICO", "SERVIÇO"]):
        return False

    parece_tecido = contem_algum(texto, [
        "SCREEN", "BLACKOUT", "BK ", "TRANSLUCIDO", "TRANSLUCIDA",
        "TECIDO", "NOBLETE", "BRISK", "NAPOLES", "ROMA", "LINHO",
        "PRESTIGE", "TJ", "PIMPOINT", "VIENA", "SOLAR", "DOUBLE VISION"
    ])

    grupo_tecido = contem_algum(grupo, [
        "TECIDO PARA PERSIANAS", "TECIDOS PERSIANAS",
        "SCREEN", "BLACKOUT", "BK", "TRANSLUCIDO", "JP"
    ])

    return grupo_tecido or parece_tecido


def eh_tecido_cortina_motor(produto):
    grupo = grupo_produto_motor(produto)
    texto = texto_produto_motor(produto or {})
    return contem_algum(grupo, ["TECIDO CORTINA", "TECIDOS CORTINAS", "CORTINA"]) or contem_algum(texto, ["TECIDO CORTINA", "TECIDOS CORTINAS"])


def produto_tem_cor_compativel_motor(produto, cor_base):
    cor_base = normalizar_busca_motor(cor_base)
    if not cor_base or cor_base in ["SELECIONE", "SELECIONE..."]:
        return True

    texto = texto_produto_motor(produto or {})
    cor_produto = normalizar_busca_motor((produto or {}).get("cor"))

    if cor_produto:
        return cor_produto == cor_base

    return cor_base in texto


def categoria_tecido_persiana_motor(produto):
    """
    Classificação inicial para organizar tecidos:
    - Rolô/Romana/Painel: Screen, Translúcidos, Blackout
    - Double Vision: Translúcidos, Semi Blackout
    Isso será usado depois em Orçamentos/Pedidos para o vendedor não procurar no meio de tudo.
    """
    texto = texto_produto_motor(produto or {})

    if "DOUBLE VISION" in texto:
        if contem_algum(texto, ["SEMI BLACKOUT", "SEMI-BLACKOUT", "DIMOUT"]):
            return "DOUBLE VISION / SEMI BLACKOUT"
        return "DOUBLE VISION / TRANSLÚCIDOS"

    if "SCREEN" in texto:
        if "BLACKOUT" in texto:
            return "ROLÔ / SCREEN BLACKOUT"
        return "ROLÔ / SCREEN"

    if "BLACKOUT" in texto or texto.startswith("BK ") or " BK " in texto:
        return "ROLÔ / BLACKOUT"

    if contem_algum(texto, ["TRANSLUCIDO", "TRANSLUCIDA", "LINHO", "GAZE", "GASE", "VOIL"]):
        return "ROLÔ / TRANSLÚCIDOS"

    return "ROLÔ / OUTROS TECIDOS"


def produto_base_pede_jp_importada(produto_base):
    texto_base = texto_produto_motor(produto_base or {})
    return "IMPORTADA" in texto_base or "IMPORTADO" in texto_base or " JP " in f" {texto_base} "


def produto_candidato_eh_acao_ou_smart_antigo(produto):
    texto = texto_produto_motor(produto or {})
    codigo = normalizar_busca_motor((produto or {}).get("codigo") or (produto or {}).get("codigo_interno"))
    grupo = normalizar_busca_motor((produto or {}).get("grupo_produto"))
    fornecedor = normalizar_busca_motor((produto or {}).get("fornecedor") or (produto or {}).get("nome_fornecedor"))

    if "ACAO" in texto or "AÇÃO" in texto or "ACAO" in grupo or "AÇÃO" in grupo or "ACAO" in fornecedor or "AÇÃO" in fornecedor:
        return True
    if "TECIDO SC" in texto or "TECID SC" in texto or "TECRLSC" in texto or "TECRLBK" in texto:
        return True
    if "ALKENZ" in texto or "STANDARD" in texto:
        return True
    if codigo.startswith("000000") and not codigo.startswith("JPTEC"):
        return True
    if re.search(r"JP\d+", texto) and not codigo.startswith("JPTEC"):
        return True
    return False


def produto_candidato_eh_jp_novo(produto):
    texto = texto_produto_motor(produto or {})
    codigo = normalizar_busca_motor((produto or {}).get("codigo") or (produto or {}).get("codigo_interno"))
    grupo = normalizar_busca_motor((produto or {}).get("grupo_produto"))
    fornecedor = normalizar_busca_motor((produto or {}).get("fornecedor") or (produto or {}).get("nome_fornecedor"))

    return (
        codigo.startswith("JPTEC")
        or "JPTEC" in texto
        or "JP IMPORTADA" in texto
        or "JP IMPORTADO" in texto
        or "JP" in grupo
        or "JP" in fornecedor
    )


def tecido_candidato_bate_nome_base(produto, produto_base):
    """
    Trava de segurança antes da pontuação.
    Se o produto final diz IMPORTADA/JP, não aceita Ação/SC/Smart antigo.
    Se diz SCREEN 3%, só aceita SCREEN 3%.
    Se diz cor BRANCO, não aceita outra cor informada.
    """
    texto = texto_produto_motor(produto or {})
    texto_base = texto_produto_motor(produto_base or {})

    if produto_base_pede_jp_importada(produto_base):
        if produto_candidato_eh_acao_ou_smart_antigo(produto):
            return False
        # Se existe sinal de JP novo, ótimo. Se não existir, deixa passar só se não for antigo/ação,
        # mas a pontuação ainda vai preferir JPTEC.
        # Isso evita zerar lista em cadastros ainda incompletos.

    if "SCREEN" in texto_base:
        if "SCREEN" not in texto:
            return False

        pct_base = percentual_screen_produto_base(produto_base) if "percentual_screen_produto_base" in globals() else ""
        pct_produto = percentual_screen_produto(produto) if "percentual_screen_produto" in globals() else ""
        if pct_base and pct_produto != pct_base:
            return False

    cor_base = normalizar_busca_motor((produto_base or {}).get("cor"))
    if cor_base and cor_base not in ["SELECIONE", "SELECIONE..."]:
        cor_produto = cor_tecido_produto(produto) if "cor_tecido_produto" in globals() else ""
        if cor_produto and cor_produto != cor_base:
            return False

    return True


def tecido_compativel_com_produto_base(produto, produto_base):
    """
    Tecido do motor precisa respeitar a família principal.
    A cor ajuda no automático, mas não deve travar a lista manual quando o fornecedor não preencheu cor separada.
    """
    if not produto_base:
        return eh_tecido_persiana_motor(produto)

    texto_produto = texto_produto_motor(produto)
    texto_base = texto_produto_motor(produto_base or {})
    material_base = normalizar_busca_motor((produto_base or {}).get("material_tecido"))

    familia_base = familia_material_tecido_motor(material_base) or familia_material_tecido_motor(texto_base)

    if not eh_tecido_persiana_motor(produto):
        return False

    if not tecido_candidato_bate_nome_base(produto, produto_base):
        return False

    if ("SCREEN" in texto_base or familia_base == "SCREEN") and (
        "BLACKOUT" in texto_produto or texto_produto.startswith("BK ") or " BK " in texto_produto
    ):
        return False

    if familia_base == "SCREEN" and "SCREEN" not in texto_produto:
        return False

    # Se o nome do produto final informa o percentual do SCREEN, ele precisa bater.
    # Ex.: ROLÔ SCREEN 3% IMPORTADA não pode puxar SCREEN 1% ou SCREEN 5%.
    pct_base = percentual_screen_produto_base(produto_base)
    pct_produto = percentual_screen_produto(produto)
    if familia_base == "SCREEN" and pct_base:
        if pct_produto and pct_produto != pct_base:
            return False
        if not pct_produto:
            return False

    if familia_base == "BLACKOUT" and "SCREEN" in texto_produto and "BLACKOUT" not in texto_produto:
        return False

    # Cor escolhida nos detalhes técnicos precisa ser respeitada.
    # Ex.: produto final BRANCO não pode puxar tecido CINZA.
    if not cor_tecido_compativel_com_base(produto, produto_base):
        return False

    return True


def percentual_screen_produto_base(produto_base):
    texto_base = texto_produto_motor(produto_base or {})
    for pct in ["1%", "3%", "5%", "10%"]:
        pct_norm = normalizar_busca_motor(pct)
        if pct_norm in texto_base:
            return pct_norm
    return ""


def percentual_screen_produto(produto):
    texto = texto_produto_motor(produto or {})
    for pct in ["1%", "3%", "5%", "10%"]:
        pct_norm = normalizar_busca_motor(pct)
        if pct_norm in texto:
            return pct_norm
    return ""


def tokens_tecido_pelo_nome_produto_base(produto_base):
    """
    Usa o nome do produto final como endereço para o motor encontrar o tecido correto.
    Ex.: "ROLÔ SCREEN 3% IMPORTADA" aponta para tecido SCREEN 3% JP IMPORTADA.
    """
    texto_base = texto_produto_motor(produto_base or {})
    tokens = []

    for pct in ["1%", "3%", "5%", "10%"]:
        pct_norm = normalizar_busca_motor(pct)
        if pct_norm in texto_base:
            tokens.append(pct_norm)

    for termo in [
        "SCREEN", "BLACKOUT", "TRANSLUCIDO", "TRANSLUCIDA",
        "DOUBLE VISION", "LINHO", "BRISK", "NAPOLES", "ROMA",
        "VIENA", "PRESTIGE", "PIMPOINT", "TJ"
    ]:
        termo_norm = normalizar_busca_motor(termo)
        if termo_norm in texto_base:
            tokens.append(termo_norm)

    if "IMPORTADA" in texto_base or "IMPORTADO" in texto_base:
        tokens.extend(["IMPORTADA", "IMPORTADO", "JP"])

    if "JP" in texto_base:
        tokens.append("JP")

    if "ACAO" in texto_base or "AÇÃO" in texto_base:
        tokens.extend(["ACAO", "AÇÃO"])

    return list(dict.fromkeys(tokens))


def cor_tecido_produto(produto):
    """
    Lê a cor do tecido pelo campo cor ou pelo nome.
    Usado para impedir que ROLÔ branco puxe tecido cinza/bege etc.
    """
    texto = texto_produto_motor(produto or {})
    cor_campo = normalizar_busca_motor((produto or {}).get("cor"))
    if cor_campo and cor_campo not in ["SELECIONE", "SELECIONE..."]:
        return cor_campo

    cores = [
        "BRANCO", "CINZA", "BEGE", "MARROM", "PRETO", "BLACK",
        "FENDI", "PALHA", "CREME", "LINHO", "AMENDOA", "AMÊNDOA",
        "NATURAL", "OFF WHITE", "OFFWHITE", "IVORY", "CRU"
    ]

    for cor in cores:
        cor_norm = normalizar_busca_motor(cor)
        if cor_norm in texto:
            if cor_norm == "BLACK":
                return "PRETO"
            return cor_norm

    return ""


def cor_tecido_compativel_com_base(produto, produto_base):
    cor_base = normalizar_busca_motor((produto_base or {}).get("cor"))
    if not cor_base or cor_base in ["SELECIONE", "SELECIONE..."]:
        return True

    cor_produto = cor_tecido_produto(produto)

    # Se o produto candidato informa cor, precisa bater exatamente.
    if cor_produto:
        return cor_produto == cor_base

    # Se não informa cor, deixa passar apenas como último caso.
    return True


def pontuar_cor_tecido_pelo_produto_base(produto, produto_base):
    cor_base = normalizar_busca_motor((produto_base or {}).get("cor"))
    if not cor_base or cor_base in ["SELECIONE", "SELECIONE..."]:
        return 0

    cor_produto = cor_tecido_produto(produto)
    texto = texto_produto_motor(produto or {})

    score = 0

    if cor_produto == cor_base:
        score += 900
    elif cor_produto:
        score -= 3000

    # Reforço para o caso mais usado agora: branco.
    if cor_base == "BRANCO":
        if "BRANCO" in texto:
            score += 500
        if contem_algum(texto, ["CINZA", "BEGE", "MARROM", "PRETO", "BLACK", "FENDI", "PALHA", "CREME"]):
            score -= 3000

    return score


def pontuar_fornecedor_tecido_pelo_nome(produto, produto_base):
    """
    Direciona o tecido para a tabela/fornecedor correto pelo nome do produto final.
    Ex.: ROLÔ SCREEN 3% IMPORTADA deve preferir a tabela JP nova, não Ação/Smart antiga.
    """
    texto = texto_produto_motor(produto or {})
    texto_base = texto_produto_motor(produto_base or {})
    codigo = normalizar_busca_motor((produto or {}).get("codigo") or (produto or {}).get("codigo_interno"))
    grupo = normalizar_busca_motor((produto or {}).get("grupo_produto"))
    fornecedor = normalizar_busca_motor((produto or {}).get("fornecedor") or (produto or {}).get("nome_fornecedor"))

    score = 0

    base_importada = "IMPORTADA" in texto_base or "IMPORTADO" in texto_base
    base_jp = "JP" in texto_base or base_importada
    base_acao = "ACAO" in texto_base or "AÇÃO" in texto_base

    if base_jp:
        # Tabela JP nova: normalmente código JPTEC e/ou nome/grupo JP.
        if codigo.startswith("JPTEC"):
            score += 8000
        if "JPTEC" in texto:
            score += 6000
        if " JP " in f" {texto} ":
            score += 1500
        if "JP IMPORTADA" in texto or "JP IMPORTADO" in texto:
            score += 6000
        if "JP" in grupo or "JP" in fornecedor:
            score += 1800

        # Ação/Smart antiga precisa perder quando produto final fala IMPORTADA/JP.
        if "ACAO" in texto or "AÇÃO" in texto or "ACAO" in grupo or "AÇÃO" in grupo or "ACAO" in fornecedor or "AÇÃO" in fornecedor:
            score -= 9000
        if "TECIDO SC" in texto or "TECID SC" in texto or "TECRLSC" in texto or "TECRLBK" in texto:
            score -= 7000
        if "ALKENZ" in texto or "STANDARD" in texto:
            score -= 2500

        # Cadastro antigo da planilha Smart: JP01/JP06 no nome, mas não JPTEC no código.
        if re.search(r"JP\d+", texto) and not codigo.startswith("JPTEC"):
            score -= 2500
        if codigo.startswith("000000") and "JPTEC" not in texto:
            score -= 2200

    if base_acao:
        if "ACAO" in texto or "AÇÃO" in texto or "ACAO" in grupo or "AÇÃO" in grupo:
            score += 6000
        if codigo.startswith("JPTEC") or "JP IMPORTADA" in texto or "JP IMPORTADO" in texto:
            score -= 3000

    return score


def pontuar_tecido_pelo_nome_produto_base(produto, produto_base):
    """
    Pontuação para o tecido bater com o nome do produto final.
    Assim ROLÔ SCREEN 3% IMPORTADA não puxa SCREEN 5%, nem tecido de outro fornecedor.
    """
    if not produto_base:
        return 0

    texto = texto_produto_motor(produto or {})
    texto_base = texto_produto_motor(produto_base or {})
    score = 0

    for token in tokens_tecido_pelo_nome_produto_base(produto_base):
        if token and token in texto:
            score += 90

    # Screen por percentual: se o produto final fala 3%, só 3% pode ganhar.
    if "SCREEN" in texto_base:
        pct_base = percentual_screen_produto_base(produto_base)
        pct_produto = percentual_screen_produto(produto)

        if pct_base:
            if pct_produto == pct_base:
                score += 1000
            elif pct_produto:
                score -= 2000
            else:
                score -= 1000

    # Importado/importada: no cadastro atual aponta para JP nova.
    # Não deixar produto da Ação ganhar só por também ter SCREEN/3%/BRANCO.
    if "IMPORTADA" in texto_base or "IMPORTADO" in texto_base:
        codigo = normalizar_busca_motor((produto or {}).get("codigo") or (produto or {}).get("codigo_interno"))
        grupo = normalizar_busca_motor((produto or {}).get("grupo_produto"))
        fornecedor = normalizar_busca_motor((produto or {}).get("fornecedor") or (produto or {}).get("nome_fornecedor"))

        if codigo.startswith("JPTEC") or "JPTEC" in texto or "JP IMPORTADA" in texto or "JP IMPORTADO" in texto:
            score += 2200
        elif re.search(r"JP\d+", texto):
            score -= 1200
        elif "JP" in texto or "IMPORTADA" in texto or "IMPORTADO" in texto or "JP" in grupo or "JP" in fornecedor:
            score += 450

        if "ACAO" in texto or "AÇÃO" in texto or "ACAO" in grupo or "AÇÃO" in grupo or "TECID SC" in texto or "TECRLSC" in texto:
            score -= 2200

    if "JP" in texto_base:
        if "JP" in texto:
            score += 300
        if "ACAO" in texto or "AÇÃO" in texto:
            score -= 250

    if "ACAO" in texto_base or "AÇÃO" in texto_base:
        if "ACAO" in texto or "AÇÃO" in texto:
            score += 300
        if "JP" in texto:
            score -= 250

    return score


def cor_padrao_componente_motor(produto):
    """
    Componentes de Rolô devem priorizar branco por padrão.
    Também aceita neutro/incolor/natural quando não existe branco.
    """
    texto = texto_produto_motor(produto)
    if contem_algum(texto, ["BRANCO", "WHITE"]):
        return 40
    if contem_algum(texto, ["INCOLOR", "NEUTRO", "NATURAL"]):
        return 25
    if contem_algum(texto, ["PRETO", "BLACK", "CINZA", "BEGE", "MARROM", "FENDI", "PALHA"]):
        return -18
    return 0


def pontuar_receita_rolo_manual_smarttec(produto, chave):
    texto = texto_produto_motor(produto)
    score = 0

    if chave == "tubo_32":
        if contem_algum(texto, ["TUBO P ROLO 32MM", "TUBO P ROLÔ 32MM", "TUBO 32MM"]) and "NATURAL" in texto:
            score += 500
        if contem_algum(texto, ["38MM", "41MM"]):
            score -= 1000

    elif chave == "tubo_38":
        if contem_algum(texto, ["TUBO P ROLO 38MM", "TUBO P ROLÔ 38MM", "TUBO 38MM"]) and "NATURAL" in texto:
            score += 500
        if contem_algum(texto, ["32MM", "41MM"]):
            score -= 1000

    elif chave == "fita_tubo":
        if contem_algum(texto, ["FTF", "FITA DUPLA FACE"]) and contem_algum(texto, ["20MMX100MTS", "20MM 100MTS", "20MM"]):
            score += 500
        if "FPH" in texto or contem_algum(texto, [" PH ", "PERSIANA HORIZONTAL", "HORIZONTAL", "BASE ROLO", "COSTURA"]):
            score -= 1000

    elif chave == "base":
        if contem_algum(texto, ["BASE CHATA 02", "BASE CONICA", "BASE CÔNICA", "PDA BASE CONICA"]):
            score += 500
        if contem_algum(texto, ["TAMPA", "FITA", "ESPAGUETE", "TRILHO"]):
            score -= 1000

    elif chave == "fita_base":
        # Receita base SmartTec: fita plástica adesiva importada 15MMX100MTS.
        if contem_algum(texto, ["15MMX100MTS", "15MM 100MTS", "FITA DE PLASTICO ADESIVA IMPORTADA", "FITA DE PLÁSTICO ADESIVA IMPORTADA"]):
            score += 900

        # Segunda opção aceitável, mas não deve ganhar da 15MMX100MTS.
        if contem_algum(texto, ["FITA P COSTURA P BASE ROLO", "FITA PLASTICA ADESIVA FIXAR TECIDO BASE", "BASE ROLO"]):
            score += 250

        if contem_algum(texto, ["DUPLA FACE", "FTF"]) or "FPH" in texto:
            score -= 1000

    elif chave == "espaguete_base":
        if contem_algum(texto, ["ESPAGUETE", "MACARRAO", "MACARRÃO"]) and contem_algum(texto, ["3 00MM", "3MM", "3 0MM"]):
            score += 500
        if contem_algum(texto, ["2 50MM", "2 5MM", "3 50MM", "3 5MM"]):
            score -= 1000

    elif chave == "corrente":
        if contem_algum(texto, ["CORRENTE BOLA 10", "BOLA 10 JUTA", "CORR CORRENTE BOLA 10"]):
            score += 500
        if contem_algum(texto, ["TRACAO", "TRAÇÃO", "TETO", "TRILHO", "MOLA", "ONE TOUCH", "COMANDO"]):
            score -= 1000

    elif chave == "emenda_corrente":
        if contem_algum(texto, ["EMENDA DA CORRENTE", "EMENDA CORRENTE", "CONECTOR"]) and not contem_algum(texto, ["TRILHO", "TETO"]):
            score += 500

        # Receita base: emenda/conector branco unidade.
        if "2083484033809" in texto:
            score += 8000
        if "EMENDA DA CORRENTE" in texto and "CONECTOR" in texto:
            score += 1200
        if "BRANCO" in texto:
            score += 1200
        if contem_algum(texto, ["UNID", "UNIDADE", " UN "]):
            score += 700

        # Não usar metal/CSF como padrão da receita.
        if "METAL" in texto:
            score -= 7000
        if "CSF" in texto:
            score -= 2500

    elif chave == "tampa_base":
        if contem_algum(texto, ["TAMPA DA BASE CHATA 02", "TAMPA PARA BASE 5618"]):
            score += 500
        if contem_algum(texto, ["TRILHO", "TUBO"]):
            score -= 1000

    elif chave == "comando_32":
        if contem_algum(texto, ["COMANDO 32MM ACAO MAXI", "COMANDO 32MM AÇÃO MAXI", "COMANDO ROLO 32MM"]) and "BRANCO" in texto:
            score += 600
        if contem_algum(texto, ["PREMIUM", "JP", "38MM", "MOTOR"]):
            score -= 600

    elif chave == "comando_38":
        if contem_algum(texto, ["COMANDO 38MM ACAO MAXI", "COMANDO 38MM AÇÃO MAXI", "COMANDO ROLO 38MM"]) and "BRANCO" in texto:
            score += 600
        if contem_algum(texto, ["PREMIUM", "JP", "32MM", "MOTOR"]):
            score -= 600

    return score


def categorias_tecidos_persianas_smarttec():
    return {
        "Rolô / Romana / Painel": ["Screen", "Translúcidos", "Blackout"],
        "Double Vision": ["Translúcidos", "Semi Blackout"],
    }


def grupo_tecnico_produto_motor(produto):
    """Lê grupo técnico novo ou infere pelo cadastro antigo, sem depender de Família Técnica."""
    grupo = normalizar_busca_motor((produto or {}).get("grupo_tecnico"))
    if grupo:
        return grupo
    try:
        grupo_inferido = inferir_grupo_tecnico_produto(produto)
        return normalizar_busca_motor(grupo_inferido)
    except Exception:
        return ""


def produto_em_grupo_tecnico(produto, grupos):
    grupo = grupo_tecnico_produto_motor(produto)
    grupos_norm = [normalizar_busca_motor(g) for g in grupos]
    return bool(grupo and grupo in grupos_norm)


def produto_candidato_chave_motor(produto, chave, modelo_calculo, motorizada=False, produto_base=None):
    """
    Evita mistura grosseira.
    Ex.: Rolô não deve puxar suporte de varão/trilho/cortina, nem tecido de cortina pronta.
    """
    texto = texto_produto_motor(produto)
    modelo = normalizar_busca_motor(modelo_calculo)
    grupo_tecnico = grupo_tecnico_produto_motor(produto)

    if not texto:
        return False

    # Itens inativos não entram no automático.
    if not produto_ativo(produto.get("situacao", "Ativo")):
        return False

    # Produto fabricado não deve virar componente do motor, exceto se o cadastro antigo veio sem tipo.
    tipo = normalizar_busca_motor(produto.get("tipo_produto"))
    if "FABRICADO" in tipo and chave not in ["tecido", "lona"]:
        return False

    if chave == "tecido":
        termos_tecido = [
            "TECIDO", "SCREEN", "BLACKOUT", "LINHO", "GASE", "VOIL", "LUGANO",
            "NOBLETE", "TRANSLUCIDO", "DOUBLE VISION", "RUSTICO", "SOLAR"
        ]

        # Produto final/fabricado nunca deve ser usado como tecido do motor.
        # Ex.: "ROLÔ SCREEN 3% STANDARD 32MM CINZA" é produto fabricado, não tecido.
        tipo_produto = normalizar_busca_motor(produto.get("tipo_produto"))
        grupo_produto = normalizar_busca_motor(produto.get("grupo_produto"))
        nome_produto = normalizar_busca_motor(produto.get("nome"))

        if "FABRICADO" in tipo_produto:
            return False

        # Tecidos de toldo/lona não entram em Rolô/Romana/Painel.
        if grupo_tecnico == "TECIDOS_TOLDO" or contem_algum(texto, ["TOLDO", "LONA", "ACRILICA", "ACRÍLICA"]):
            return False

        # Bloqueia componentes que contêm a palavra tecido no nome,
        # como guia do tecido, roda niveladora, AC191, base, eixo etc.
        if not eh_tecido_persiana_motor(produto):
            return False

        if modelo in ["ROLO", "ROLO MOTORIZADA", "ROLO MOTORIZADO", "ROLÔ"]:
            if grupo_tecnico and grupo_tecnico != "TECIDOS_ROLO_ROMANA_PAINEL":
                return False
            # Para Rolô, tecido precisa ser tecido real de persiana.
            if eh_tecido_cortina_motor(produto):
                return False

            if not tecido_compativel_com_produto_base(produto, produto_base):
                return False

            return True

        if modelo in ["DOUBLE VISION", "DOUBLE_VISION"]:
            # Regra principal da arquitetura nova: tecido DV vem somente de TECIDOS_DOUBLE_VISION.
            if grupo_tecnico:
                return grupo_tecnico == "TECIDOS_DOUBLE_VISION"

            # Compatibilidade com cadastros antigos ainda sem grupo_tecnico.
            # Evita PDA, eixo, tampa, tubo, comando e demais componentes que também têm DOUBLE VISION no nome.
            if contem_algum(texto, [
                "PDA", "COMP", "COMPONENTE", "TUBO", "EIXO", "TAMPA", "SUPORTE",
                "PONTEIRA", "COMANDO", "MECANISMO", "CORRENTE", "MOTOR", "COROA",
                "PERFIL", "BASE", "FITA", "ESPAGUETE", "MACARRAO", "MACARRÃO"
            ]):
                return False

            unidade = normalizar_busca_motor(produto.get("unidade_venda"))
            parece_tecido_dv = "DOUBLE VISION" in texto and contem_algum(texto, ["TECIDO", "RUSTICO", "RÚSTICO", "WHITE", "BLACK", "IVORY", "M²", "M2"])
            return "FABRICADO" not in tipo_produto and parece_tecido_dv and unidade in ["M²", "M2", "MT²", "METRO QUADRADO", ""]

        if modelo == "ROMANA":
            if grupo_tecnico and grupo_tecnico != "TECIDOS_ROLO_ROMANA_PAINEL":
                return False
            return "FABRICADO" not in tipo_produto and ("ROMANA" in texto or contem_algum(texto, termos_tecido)) and "DOUBLE VISION" not in texto

        if modelo == "PAINEL":
            if grupo_tecnico and grupo_tecnico != "TECIDOS_ROLO_ROMANA_PAINEL":
                return False
            return "FABRICADO" not in tipo_produto and contem_algum(texto, termos_tecido) and "DOUBLE VISION" not in texto

        if modelo in ["CORTINA", "CORTINA DE TECIDO", "CORTINA/TRILHO"]:
            if grupo_tecnico and grupo_tecnico != "TECIDOS_CORTINAS":
                return False
            return "FABRICADO" not in tipo_produto and contem_algum(texto, termos_tecido)

        return "FABRICADO" not in tipo_produto and contem_algum(texto, termos_tecido)

    if chave == "lona":
        return "LONA" in texto

    if chave in ["tubo", "tubo_32", "tubo_38"]:
        if "TUBO" not in texto:
            return False

        # Tubo verdadeiro não pode misturar com tampa/suporte/comando/acessório de motor
        # que possuem a palavra TUBO no nome.
        if contem_algum(texto, [
            "TAMPA", "SUPORTE", "PONTEIRA", "COMANDO", "KIT", "CORRENTE",
            "EMENDA", "CONECTOR", "BASE", "FITA", "ESPAGUETE", "MACARRAO", "MACARRÃO",
            "MOTOR", "COROA", "PONTA OPOSTA", "ADAPTADOR", "ACESSORIO", "ACESSÓRIO"
        ]):
            return False

        if chave == "tubo_32":
            if not contem_algum(texto, ["32MM", "32 MM", " 32 "]):
                return False
            if contem_algum(texto, ["38MM", "38 MM", "41MM", "41 MM"]):
                return False

        if chave == "tubo_38":
            if not contem_algum(texto, ["38MM", "38 MM", " 38 "]):
                return False
            if contem_algum(texto, ["32MM", "32 MM", "41MM", "41 MM"]):
                return False

        if modelo in ["ROLO", "ROLÔ"]:
            if grupo_tecnico and grupo_tecnico not in ["COMPONENTES_ROLO", "BAU_PERSIANAS"]:
                return False
            return contem_algum(texto, ["ROLO", "ROLÔ"])
        if modelo in ["DOUBLE VISION", "DOUBLE_VISION"]:
            if grupo_tecnico and grupo_tecnico != "COMPONENTES_DOUBLE_VISION":
                return False
            # Double Vision manual: Tubos 32mm, 38mm e 41mm.
            # 56mm/70mm ficam fora do manual para não puxar tubo de motorizada/toldo.
            if not motorizada:
                if contem_algum(texto, ["56MM", "56 MM", "70MM", "70 MM"]):
                    return False
                return contem_algum(texto, ["32MM", "32 MM", " 32 ", "38MM", "38 MM", " 38 ", "41MM", "41 MM", " 41 "])

            return contem_algum(texto, ["DOUBLE", "DV", "ROLO", "ROLÔ", "32MM", "38MM", "41MM", "56MM", "70MM"])
        return True

    # Para componentes mecânicos, respeita o Grupo Técnico quando ele estiver preenchido.
    if grupo_tecnico:
        if modelo in ["ROLO", "ROLÔ"] and grupo_tecnico not in ["COMPONENTES_ROLO", "BAU_PERSIANAS", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False
        if modelo in ["DOUBLE VISION", "DOUBLE_VISION"] and grupo_tecnico not in ["COMPONENTES_DOUBLE_VISION", "BAU_PERSIANAS", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False
        if modelo == "ROMANA" and grupo_tecnico not in ["COMPONENTES_ROMANA", "BAU_PERSIANAS", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False
        if modelo == "PAINEL" and grupo_tecnico not in ["COMPONENTES_PAINEL", "BAU_PERSIANAS", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False
        if modelo in ["CORTINA", "CORTINA DE TECIDO", "CORTINA/TRILHO"] and grupo_tecnico not in ["COMPONENTES_CORTINAS", "BAU_CORTINAS", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False
        if modelo == "TOLDO" and grupo_tecnico not in ["COMPONENTES_TOLDO", "BAU_EXTERNA", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False
        if modelo == "EXTERNA" and grupo_tecnico not in ["COMPONENTES_EXTERNA", "BAU_EXTERNA", "MOTORES", "ACESSORIOS_MOTOR", "BAU_MOTORES"]:
            return False

    if chave == "fita_tubo":
        if not contem_algum(texto, ["FITA"]):
            return False
        # PH / persiana horizontal não entra na receita do Rolô.
        if "FPH" in texto or contem_algum(texto, [" PH ", "PERSIANA HORIZONTAL", "HORIZONTAL"]):
            return False
        if contem_algum(texto, ["BASE ROLO", "BASE ROLÔ", "COSTURA", "PLASTICA ADESIVA", "PLÁSTICA ADESIVA"]):
            return False
        return contem_algum(texto, ["DUPLA FACE", "20MM", "20X", "20MMX100", "2,5", "2.5", "25MM", "2,5MM", "TUBO"])

    if chave == "base":
        return contem_algum(texto, ["BASE", "PERFIL INFERIOR"]) and not contem_algum(texto, ["TRILHO", "VARAO", "VARÃO", "FITA", "ESPAGUETE", "TAMPA"])

    if chave == "fita_base":
        if not contem_algum(texto, ["FITA", "PLASTICA", "PLÁSTICA", "PLASTICO", "PLÁSTICO"]):
            return False
        if contem_algum(texto, ["DUPLA FACE", "FTF", "FPH", "PERSIANA HORIZONTAL", "HORIZONTAL"]):
            return False

        # Receita base: 15MMX100MTS COMP - FITA DE PLASTICO ADESIVA IMPORTADA.
        if contem_algum(texto, ["15MMX100MTS", "15MM 100MTS", "FITA DE PLASTICO ADESIVA IMPORTADA", "FITA DE PLÁSTICO ADESIVA IMPORTADA"]):
            return True

        return contem_algum(texto, ["1,5", "1.5", "15MM", "1,5MM", "BASE"])

    if chave == "espaguete_base":
        if not contem_algum(texto, ["ESPAGUETE", "ESPAG", "MACARRAO", "MACARRÃO"]):
            return False
        if contem_algum(texto, ["2,5MM", "2.5MM", "2 5MM", "3,50MM", "3.50MM", "3,5MM", "3.5MM"]):
            return False
        return contem_algum(texto, ["3MM", "3 MM", "3,00MM", "3.00MM", "3,0MM", "3.0MM"])

    if chave == "perfil":
        return "PERFIL" in texto and not contem_algum(texto, ["BASE CHATA", "TRILHO"])

    if chave == "suporte":
        if "SUPORTE" not in texto:
            return False
        if modelo in ["ROLO", "ROLÔ"]:
            return contem_algum(texto, ["ROLO", "ROLÔ"]) and not contem_algum(texto, ["VARAO", "VARÃO", "TRILHO", "CORTINA", "ROMANA", "TOLDO"])
        if modelo == "ROMANA":
            return "ROMANA" in texto or not contem_algum(texto, ["VARAO", "VARÃO", "TOLDO"])
        if modelo == "CORTINA DE TECIDO":
            return contem_algum(texto, ["CORTINA", "TRILHO", "SUPORTE"])
        return True

    if chave in ["comando", "comando_32", "comando_38"]:
        eh_comando = "COMANDO" in texto or "MOLA" in texto or "ONE TOUCH" in texto or "KIT" in texto
        if not eh_comando:
            return False

        if chave == "comando_32" and not contem_algum(texto, ["32MM", "32 MM", " 32 "]):
            return False
        if chave == "comando_38" and not contem_algum(texto, ["38MM", "38 MM", " 38 "]):
            return False

        if modelo in ["ROLO", "ROLÔ"]:
            return contem_algum(texto, ["ROLO", "ROLÔ"])
        if modelo == "ROMANA":
            return "ROMANA" in texto
        if modelo == "PAINEL":
            return "PAINEL" in texto
        return True

    if chave == "mecanismo":
        return contem_algum(texto, ["MECANISMO", "COMANDO"]) and ("DOUBLE" in texto if modelo == "DOUBLE VISION" else True)

    if chave == "corrente":
        if not contem_algum(texto, ["CORRENTE", "CORR "]):
            return False

        # Corrente de tração/teto/trilho não faz parte da receita de Rolô.
        if contem_algum(texto, [
            "TRACAO", "TRAÇÃO", "TETO", "TRILHO", "DESLIZANTE", "ROMANA", "PAINEL",
            "EMENDA", "CONF", "MOTOR", "MOLA", "ONE TOUCH", "S CORRENTE",
            "SEM CORRENTE", "COMANDO", "MECANISMO"
        ]):
            return False

        # Para Rolô, a receita padrão é corrente de bola 10 / juta / plástica.
        if modelo in ["ROLO", "ROLÔ", "ROLO MOTORIZADA", "ROLO MOTORIZADO"]:
            return contem_algum(texto, ["BOLA 10", "BOLA10", "JUTA", "PLASTICA", "PLÁSTICA"])

        return True

    if chave == "emenda_corrente":
        return contem_algum(texto, ["EMENDA", "CONF"]) and contem_algum(texto, ["CORRENTE", "CORR"])

    if chave == "tampa_base":
        return contem_algum(texto, ["TAMPA"]) and contem_algum(texto, ["BASE", "CHATA"])

    # Componentes específicos da Receita Base Romana SmartTec.
    if chave == "cabec_romana":
        return contem_algum(texto, ["CABECEIRA ROMANA", "CABECEIRA DA ROMANA"])

    if chave == "eixo_romana":
        return contem_algum(texto, ["EIXO ROMANA", "EIXO DA ROMANA", "EIXO P/ ROMANA"])

    if chave == "kit_comando_romana":
        return contem_algum(texto, ["KIT", "COMANDO"]) and "ROMANA" in texto

    if chave == "carretel_curto":
        return "CARRETEL" in texto and contem_algum(texto, ["CURTO", "PEQUENO", "ROMANA"]) and not contem_algum(texto, ["LONGO"])

    if chave == "carretel_longo":
        return "CARRETEL" in texto and contem_algum(texto, ["LONGO", "ALTO", "ROMANA"])

    if chave == "vareta_romana":
        return "VARETA" in texto and ("ROMANA" in texto or not contem_algum(texto, ["CORTINA", "VERTICAL", "HORIZONTAL"]))

    if chave == "tampa_vareta":
        return "TAMPA" in texto and "VARETA" in texto

    if chave == "espaguete_25":
        if not contem_algum(texto, ["ESPAGUETE", "MACARRAO", "MACARRÃO"]):
            return False
        return contem_algum(texto, ["2,5", "2.5", "2 5", "2,50", "2.50", "2 50"])

    if chave == "fita_plastica_15":
        if not contem_algum(texto, ["FITA", "PLASTICA", "PLÁSTICA", "PLASTICO", "PLÁSTICO"]):
            return False
        return contem_algum(texto, ["1,5", "1.5", "15MM", "1,50", "1.50"]) and not contem_algum(texto, ["DUPLA FACE", "FTF", "20MM", "25MM"])

    if chave == "guia_corda":
        return "GUIA" in texto and contem_algum(texto, ["CORDA", "CORDAO", "CORDÃO", "ROMANA"])

    if chave == "corda_horizontal":
        return contem_algum(texto, ["CORDA", "CORDAO", "CORDÃO"]) and contem_algum(texto, ["16", "25", "HORIZONTAL", "ROMANA"])

    if chave == "base_chata":
        return "BASE" in texto and "CHATA" in texto and not contem_algum(texto, ["TAMPA", "FITA", "GUIA", "EIXO"])

    if chave == "tampa_base_chata":
        return "TAMPA" in texto and "BASE" in texto and "CHATA" in texto

    if chave == "motor":
        if "MOTOR" not in texto:
            return False
        if modelo in ["ROLO", "ROLÔ", "ROMANA", "DOUBLE VISION", "TOLDO", "PERSIANA EXTERNA"]:
            return True
        return True

    if chave == "controle":
        return contem_algum(texto, ["CONTROLE", "RECEPTOR", "CENTRAL"])

    if chave == "trilho":
        if "TRILHO" not in texto:
            return False
        if modelo == "ROMANA":
            return "ROMANA" in texto or not contem_algum(texto, ["CORTINA", "VARAO", "VARÃO"])
        if modelo == "PAINEL":
            return "PAINEL" in texto
        if modelo in ["CORTINA DE TECIDO", "TRILHO MOTORIZADO"]:
            return contem_algum(texto, ["CORTINA", "TRILHO"])
        return True

    if chave == "correia":
        return "CORREIA" in texto

    if chave == "carrinho":
        return contem_algum(texto, ["CARRINHO", "RODIZIO", "RODÍZIO", "DESLIZANTE"])

    if chave == "vareta":
        return "VARETA" in texto

    if chave == "cordao":
        return contem_algum(texto, ["CORDAO", "CORDÃO"])

    if chave == "costura":
        return contem_algum(texto, ["COSTURA", "MAO DE OBRA", "MÃO DE OBRA"])

    if chave == "lamina":
        return contem_algum(texto, ["LAMINA", "LÂMINA", "TELA EXTERNA"])

    if chave == "guia":
        return "GUIA" in texto

    if chave == "caixa":
        return "CAIXA" in texto

    if chave == "tubo_frontal":
        return contem_todos(texto, ["TUBO", "FRONTAL"])

    if chave == "tubo_carga":
        return contem_todos(texto, ["TUBO", "CARGA"])

    if chave == "braco":
        return contem_algum(texto, ["BRACO", "BRAÇO"])

    if chave == "manivela":
        return "MANIVELA" in texto

    return False


def pontuar_produto_motor(produto, chave, modelo_calculo, produto_base=None, motorizada=False):
    texto = texto_produto_motor(produto)
    modelo = normalizar_busca_motor(modelo_calculo)
    score = 0
    if normalizar_busca_motor(modelo_calculo) in ["ROLO", "ROLÔ"]:
        score += pontuar_receita_rolo_manual_smarttec(produto, chave)

    if chave == "fita_tubo" and ("FPH" in texto or contem_algum(texto, [" PH ", "PERSIANA HORIZONTAL", "HORIZONTAL"])):
        score -= 1000

    if chave == "espaguete_base":
        if contem_algum(texto, ["ESPAGUETE", "ESPAG", "MACARRAO", "MACARRÃO"]):
            score += 90
        if contem_algum(texto, ["3MM", "3 MM", "3,00MM", "3.00MM"]):
            score += 80
        if contem_algum(texto, ["3,50MM", "3.50MM", "3,5MM", "3.5MM", "2,5MM", "2.5MM"]):
            score -= 300

    if chave == "tecido" and eh_tecido_persiana_motor(produto):
        score += 120

    if not produto_candidato_chave_motor(produto, chave, modelo_calculo, motorizada, produto_base=produto_base):
        return -9999

    # Produto final/fabricado não deve ganhar prioridade como componente técnico.
    tipo_score = normalizar_busca_motor(produto.get("tipo_produto"))
    nome_score = normalizar_busca_motor(produto.get("nome"))
    if "FABRICADO" in tipo_score:
        score -= 200
    if chave == "tecido" and (nome_score.startswith("ROLO ") or nome_score.startswith("ROLÔ ")):
        score -= 200

    # Custo válido é preferível, mas custo zero ainda pode aparecer para o usuário vincular manualmente.
    custo = float(produto.get("custo_final") or produto.get("valor_custo") or 0)
    if custo > 0:
        score += 12

    # Preferência por unidade coerente.
    unidade = normalizar_busca_motor(produto.get("unidade_venda"))
    if chave in ["tecido", "lona"] and unidade in ["M2", "M", "M²", "METRO QUADRADO"]:
        score += 10
    if chave in ["tubo", "tubo_32", "tubo_38", "fita_tubo", "base", "fita_base", "espaguete_base", "perfil", "trilho", "corrente", "cordao", "correia", "guia", "tubo_frontal", "tubo_carga"] and unidade in ["ML", "METRO", "METRO LINEAR", "M"]:
        score += 10
    if chave in ["suporte", "comando", "comando_32", "comando_38", "mecanismo", "motor", "controle", "carrinho", "vareta", "braco", "manivela"] and unidade in ["UN", "UNIDADE", "KIT", "PC", "PECA", "PEÇA"]:
        score += 10

    # Modelo correto.
    if modelo in ["ROLO", "ROLÔ"] and contem_algum(texto, ["ROLO", "ROLÔ"]):
        score += 20
    if modelo == "ROMANA" and "ROMANA" in texto:
        score += 20
    if modelo == "DOUBLE VISION" and "DOUBLE VISION" in texto:
        score += 25
    if modelo == "PAINEL" and "PAINEL" in texto:
        score += 20
    if modelo == "CORTINA DE TECIDO" and "CORTINA" in texto:
        score += 20
    if modelo == "TOLDO" and "TOLDO" in texto:
        score += 20

    # Penalidades fortes para misturas comuns.
    if modelo in ["ROLO", "ROLÔ"] and contem_algum(texto, ["CORTINA", "VARAO", "VARÃO", "ROMANA", "PAINEL", "TOLDO"]) and chave not in ["tecido"]:
        score -= 80
    if modelo in ["ROLO", "ROLÔ"] and chave == "tecido" and contem_algum(texto, ["CORTINA TECIDO", "ROMANA", "PAINEL", "DOUBLE VISION", "TOLDO", "LONA", "VERTICAL"]):
        score -= 200

    # Tecido precisa obedecer material/tecido e cor selecionados no produto final.
    if chave == "tecido" and produto_base:
        material_base = normalizar_busca_motor((produto_base or {}).get("material_tecido"))
        cor_base = normalizar_busca_motor((produto_base or {}).get("cor"))
        familia_base = familia_material_tecido_motor(material_base)

        if familia_base and familia_base in texto:
            score += 120
        if cor_base and cor_base not in ["SELECIONE", "SELECIONE..."] and cor_base in texto:
            score += 80

    # Componentes técnicos de Rolô: branco é o padrão inicial.
    if chave not in ["tecido", "lona"]:
        score += cor_padrao_componente_motor(produto)

    # Tokens do produto que está sendo fabricado: cor/material/nome.
    for token in tokens_produto_base_motor(produto_base):
        if token in texto:
            score += 6

    if chave == "tubo_38" and contem_algum(texto, ["41MM", "41 MM"]):
        score -= 500

    if chave == "tecido":
        texto_base = texto_produto_motor(produto_base or {})

        # Usa o nome do produto final como endereço do tecido.
        # Ex.: ROLÔ SCREEN 3% IMPORTADA -> JP / SCREEN / 3% / IMPORTADA.
        score += pontuar_tecido_pelo_nome_produto_base(produto, produto_base)

        # Direciona para a tabela/fornecedor correta.
        # Ex.: IMPORTADA prioriza JPTEC/JP nova, não cadastro antigo Smart.
        score += pontuar_fornecedor_tecido_pelo_nome(produto, produto_base)

        # Cor do tecido precisa seguir a cor do produto final.
        # Ex.: BRANCO não pode perder para CINZA só porque é importado.
        score += pontuar_cor_tecido_pelo_produto_base(produto, produto_base)

        if "SCREEN" in texto_base and "SCREEN" in texto:
            score += 500
        if "SCREEN" in texto_base and ("BLACKOUT" in texto or texto.startswith("BK ") or " BK " in texto):
            score -= 2000
        if "SCREEN" in texto_base and "SCREEN" not in texto:
            score -= 250
        if eh_tecido_persiana_motor(produto):
            score += 80

    if chave == "corrente" and contem_algum(texto, ["TRACAO", "TRAÇÃO", "TETO", "TRILHO"]):
        score -= 500

    # Palavras-chave específicas por chave.
    bonus_chave = {
        "tecido": ["TECIDO", "SCREEN", "BLACKOUT", "TRANSLUCIDO", "LUGANO"],
        "tubo": ["TUBO"],
        "tubo_32": ["TUBO", "32MM", "32"],
        "tubo_38": ["TUBO", "38MM", "38"],
        "fita_tubo": ["FITA", "DUPLA FACE", "20MM", "20X", "TUBO"],
        "base": ["BASE", "PERFIL INFERIOR", "CHATA", "CONICA", "CÔNICA"],
        "fita_base": ["FITA", "PLASTICA", "PLÁSTICA", "1,5", "BASE"],
        "espaguete_base": ["ESPAGUETE", "3MM", "BASE"],
        "suporte": ["SUPORTE"],
        "comando": ["COMANDO"],
        "comando_32": ["COMANDO", "KIT", "32MM", "32"],
        "comando_38": ["COMANDO", "KIT", "38MM", "38"],
        "corrente": ["CORRENTE", "CORR", "BOLA 10", "BOLA10", "JUTA", "PLASTICA", "PLÁSTICA"],
        "emenda_corrente": ["EMENDA", "CONECTOR", "CONF"],
        "tampa_base": ["TAMPA", "BASE", "CHATA"],
        "emenda_corrente": ["EMENDA", "CORRENTE"],
        "tampa_base": ["TAMPA", "BASE"],
        "motor": ["MOTOR"],
        "controle": ["CONTROLE"],
        "trilho": ["TRILHO"],
        "carrinho": ["CARRINHO", "RODIZIO"],
    }

    for termo in bonus_chave.get(chave, []):
        if termo in texto:
            score += 8

    return score


def receita_rolo_manual_base_smarttec():
    """
    Receita base validada pelo Warma para Rolô manual.
    Para Rolô manual, peças fixas não podem cair em Romana/Horizontal por nome parecido.
    """
    return {
        "tubo_32": {"preferir": ["2418293509764", "TUBO P ROLO 32MM NATURAL", "TUBO P ROLÔ 32MM NATURAL"], "obrigatorio": ["TUBO", "32MM"], "bloquear": ["38MM", "41MM", "ROMANA", "PAINEL", "HORIZONTAL", "TRILHO"]},
        "tubo_38": {"preferir": ["TUBO P ROLO 38MM NATURAL", "TUBO P ROLÔ 38MM NATURAL", "TUBO 38MM NATURAL"], "obrigatorio": ["TUBO", "38MM"], "bloquear": ["32MM", "41MM", "ROMANA", "PAINEL", "HORIZONTAL", "TRILHO"]},
        "fita_tubo": {"preferir": ["01908100920", "FTF FITA DUPLA FACE 20MMX100MTS INCOLOR", "FITA DUPLA FACE 20MMX100MTS INCOLOR"], "obrigatorio": ["FITA", "DUPLA", "FACE"], "bloquear": ["FPH", "PH ", "PERSIANA HORIZONTAL", "HORIZONTAL", "BASE ROLO", "COSTURA", "ROMANA", "GIRATORIO"]},
        "base": {"preferir": ["02711500171", "PDA BASE CONICA BRANCO AC133", "BASE CONICA BRANCO AC133", "BASE CÔNICA BRANCO AC133", "BASE CHATA 02 P ROLO BRANCO"], "obrigatorio": ["BASE"], "bloquear": ["CABECEIRA", "ROMANA", "GIRATORIO", "GIRATÓRIO", "HORIZONTAL", "TAMPA", "FITA", "ESPAGUETE", "TRILHO"]},
        "fita_base": {"preferir": ["02611300933", "15MMX100MTS COMP FITA DE PLASTICO ADESIVA IMPORTADA", "15MMX100MTS COMP FITA DE PLÁSTICO ADESIVA IMPORTADA", "FITA DE PLASTICO ADESIVA IMPORTADA"], "obrigatorio": ["FITA"], "bloquear": ["GIRATORIO", "GIRATÓRIO", "HASTE", "ROMANA", "HORIZONTAL", "DUPLA FACE", "FTF", "FPH", "PERSIANA HORIZONTAL"]},
        "espaguete_base": {"preferir": ["03615900930", "ESP ESPAGUETE MACARRAO 3 00MM", "ESPAGUETE MACARRAO 3 00MM", "ESPAGUETE MACARRÃO 3 00MM"], "obrigatorio": ["ESPAGUETE"], "bloquear": ["2 50MM", "2 5MM", "3 50MM", "3 5MM", "ROMANA", "HORIZONTAL"]},
        "corrente": {"preferir": ["022105001700", "CORR CORRENTE BOLA 10 JUNTA BRANCO", "CORRENTE BOLA 10 JUNTA BRANCO", "BOLA 10 JUNTA BRANCO"], "obrigatorio": ["CORRENTE", "BOLA"], "bloquear": ["TRACAO", "TRAÇÃO", "TETO", "TRILHO", "MOLA", "ONE TOUCH", "COMANDO", "ROMANA", "HORIZONTAL"]},
        "emenda_corrente": {"preferir": ["2083484033809", "EMENDA DA CORRENTE CONECTOR BRANCO", "EMENDA CORRENTE CONECTOR BRANCO"], "obrigatorio": ["EMENDA", "CORRENTE"], "bloquear": ["METAL", "CSF", "TRILHO", "TETO", "ROMANA", "HORIZONTAL"]},
        "tampa_base": {"preferir": ["2031868300009", "TAMPA DA BASE CHATA 02 BRANCO", "TAMPA BASE CHATA 02 BRANCO"], "obrigatorio": ["TAMPA", "BASE"], "bloquear": ["COM ABA", "ABA", "5618 COM ABA", "TRILHO", "TUBO", "ROMANA", "HORIZONTAL"]},
        "comando_32": {"preferir": ["02122500170", "COM COMANDO 32MM ACAO MAXI BRANCO", "COMANDO 32MM AÇÃO MAXI BRANCO", "COMANDO 32MM ACAO MAXI BRANCO"], "obrigatorio": ["COMANDO", "32MM"], "bloquear": ["PREMIUM", "JP", "38MM", "MOTOR", "ROMANA", "HORIZONTAL"]},
        "comando_38": {"preferir": ["02122600170", "COM COMANDO 38MM ACAO MAXI BRANCO", "COMANDO 38MM AÇÃO MAXI BRANCO", "COMANDO 38MM ACAO MAXI BRANCO"], "obrigatorio": ["COMANDO", "38MM"], "bloquear": ["PREMIUM", "JP", "32MM", "MOTOR", "ROMANA", "HORIZONTAL"]},
    }


def produto_bate_textos_receita(produto, regra):
    texto = texto_produto_motor(produto or {})
    if not texto:
        return False

    for termo in regra.get("bloquear", []):
        termo_norm = normalizar_busca_motor(termo)
        if termo_norm and termo_norm in texto:
            return False

    for termo in regra.get("preferir", []):
        termo_norm = normalizar_busca_motor(termo)
        if termo_norm and termo_norm in texto:
            return True

    obrigatorios = [normalizar_busca_motor(t) for t in regra.get("obrigatorio", []) if normalizar_busca_motor(t)]
    if obrigatorios and all(t in texto for t in obrigatorios):
        return True

    return False


def texto_identidade_tubo_32(produto):
    """Identidade estrutural do tubo 32, sem descrição ou observações."""
    produto = produto or {}
    return normalizar_busca_motor(
        " ".join(
            [
                str(produto.get("nome") or ""),
                str(produto.get("codigo") or ""),
                str(produto.get("codigo_interno") or ""),
                str(produto.get("codigo_barras") or ""),
                str(produto.get("tipo_produto") or ""),
                str(produto.get("grupo_produto") or ""),
                str(produto.get("grupo_tecnico") or ""),
                str(produto.get("modelo_tecnico") or ""),
                str(produto.get("produto_base") or ""),
                str(produto.get("unidade_venda") or ""),
                str(produto.get("situacao") or ""),
                str(produto.get("status_comercial") or ""),
                str(produto.get("material_tecido") or ""),
                str(produto.get("tubo_motor") or ""),
            ]
        )
    )


def produto_candidato_tubo_32_deterministico(produto):
    """Aceita somente tubo Rolô 32 mm estruturalmente identificado."""
    produto = produto or {}
    texto = texto_identidade_tubo_32(produto)
    nome = normalizar_busca_motor(produto.get("nome"))
    tipo = normalizar_busca_motor(produto.get("tipo_produto"))
    grupo = normalizar_busca_motor(produto.get("grupo_tecnico"))
    unidade = normalizar_busca_motor(produto.get("unidade_venda"))
    status = normalizar_busca_motor(produto.get("status_comercial"))

    if not produto_ativo(produto.get("situacao", "Ativo")):
        return False
    if status and contem_algum(status, ["INATIVO", "BLOQUEADO", "SUSPENSO", "EXCLUIDO"]):
        return False
    if "FABRICADO" in tipo:
        return False
    if grupo != "PERFIS PERSIANAS ROLO":
        return False
    if unidade not in ["ML", "M", "MT", "METRO", "METRO LINEAR"]:
        return False
    if "TUBO" not in nome or not contem_algum(nome, ["ROLO", "ROLÔ"]):
        return False
    if not re.search(r"(^| )32 ?MM($| )", nome):
        return False
    if re.search(r"(^| )(38|41|56|70|88) ?MM($| )", nome):
        return False
    if contem_algum(texto, [
        "TAMPA", "PONTEIRA", "SUPORTE", "COMANDO", "KIT", "MOTOR",
        "COROA", "ADAPTADOR", "ACESSORIO", "ACESSÓRIO",
    ]):
        return False
    return True


def pontuar_tubo_32_deterministico(produto):
    """Desempata tubos 32 válidos sem consultar observações."""
    if not produto_candidato_tubo_32_deterministico(produto):
        return -999999

    produto = produto or {}
    nome = normalizar_busca_motor(produto.get("nome"))
    codigo = normalizar_busca_motor(
        produto.get("codigo") or produto.get("codigo_interno") or produto.get("codigo_barras")
    )
    score = 100000

    if codigo == "2418293509764":
        score += 10000000
    if nome == "TUBO P ROLO 32MM NATURAL":
        score += 1000000
    if normalizar_busca_motor(produto.get("grupo_tecnico")) == "PERFIS PERSIANAS ROLO":
        score += 100000
    if normalizar_busca_motor(produto.get("unidade_venda")) in ["ML", "M", "MT", "METRO", "METRO LINEAR"]:
        score += 10000
    if str(produto.get("material_tecido") or "").strip():
        score += 1000
    if float(produto.get("custo_final") or produto.get("valor_custo") or 0) > 0:
        score += 100

    try:
        score += 1 / (int(produto.get("id") or 0) + 1)
    except Exception:
        pass
    return score


def produto_bate_tecido_receita_rolo(produto, produto_base):
    """
    Tecido é o único item dinâmico da receita.
    Regras:
    - segue material do nome/base: SCREEN, BLACKOUT etc.
    - segue percentual: 3% não pode puxar 1% ou 5%
    - segue cor: branco não pode puxar cinza
    - se o nome diz IMPORTADA/JP, aceita JP IMPORTADA mesmo que o código seja 000000,
      porque a tabela JP importada pode ter código interno assim.
    """
    if not eh_tecido_persiana_motor(produto):
        return False

    texto = texto_produto_motor(produto or {})

    # Não usar placeholder/genérico como tecido real.
    if texto.strip() in ["TECIDO PERSIANA", "TECIDO PARA PERSIANA", "TECIDO PARA PERSIANAS"]:
        return False
    if "TECIDO PERSIANA" in texto and not contem_algum(texto, ["SCREEN", "BLACKOUT", "TRANSLUCIDO", "TRANSLUCIDA", "BK "]):
        return False
    texto_base = texto_produto_motor(produto_base or {})
    codigo = normalizar_busca_motor((produto or {}).get("codigo") or (produto or {}).get("codigo_interno"))
    grupo = normalizar_busca_motor((produto or {}).get("grupo_produto"))
    fornecedor = normalizar_busca_motor((produto or {}).get("fornecedor") or (produto or {}).get("nome_fornecedor"))

    if "SCREEN" in texto_base:
        if "SCREEN" not in texto:
            return False

        pct_base = percentual_screen_produto_base(produto_base) if "percentual_screen_produto_base" in globals() else ""
        pct_produto = percentual_screen_produto(produto) if "percentual_screen_produto" in globals() else ""
        if pct_base and pct_produto != pct_base:
            return False

        if "BLACKOUT" in texto or texto.startswith("BK ") or " BK " in texto:
            return False

    cor_base = normalizar_busca_motor((produto_base or {}).get("cor"))
    if cor_base and cor_base not in ["SELECIONE", "SELECIONE..."]:
        cor_produto = cor_tecido_produto(produto) if "cor_tecido_produto" in globals() else ""
        if cor_produto and cor_produto != cor_base:
            return False

    base_importada = "IMPORTADA" in texto_base or "IMPORTADO" in texto_base or " JP " in f" {texto_base} "
    if base_importada:
        # Aqui está a correção principal: JP IMPORTADA é válido mesmo se o código for 000000.
        eh_jp = (
            codigo.startswith("JPTEC")
            or "JPTEC" in texto
            or "JP IMPORTADA" in texto
            or "JP IMPORTADO" in texto
            or " JP " in f" {texto} "
            or "JP" in grupo
            or "JP" in fornecedor
        )

        if not eh_jp:
            return False

        # Ação/SC só é bloqueado quando não tem marca clara de JP.
        if not ("JP IMPORTADA" in texto or "JP IMPORTADO" in texto or codigo.startswith("JPTEC") or "JPTEC" in texto):
            if "ACAO" in texto or "AÇÃO" in texto or "TECID SC" in texto or "TECRLSC" in texto or "ALKENZ" in texto or "STANDARD" in texto:
                return False

    return True


def pontuar_receita_deterministica(produto, chave, produto_base=None):
    if chave == "tubo_32":
        return pontuar_tubo_32_deterministico(produto)

    if chave == "tecido":
        if produto_bate_tecido_receita_rolo(produto, produto_base):
            texto = texto_produto_motor(produto or {})
            codigo = normalizar_busca_motor((produto or {}).get("codigo") or (produto or {}).get("codigo_interno"))
            score = 100000

            # Prioridades internas do tecido.
            if codigo.startswith("JPTEC"):
                score += 8000
            if "JP IMPORTADA" in texto or "JP IMPORTADO" in texto:
                score += 9000
            if "BRANCO" in texto:
                score += 2000
            if "ACAO" in texto or "AÇÃO" in texto or "TECID SC" in texto or "TECRLSC" in texto or "ALKENZ" in texto or "STANDARD" in texto:
                score -= 15000
            return score
        return -999999

    regra = receita_rolo_manual_base_smarttec().get(chave)
    if not regra:
        return 0

    if produto_bate_textos_receita(produto, regra):
        texto = texto_produto_motor(produto or {})
        score = 100000
        # branco/incolor/natural são as cores padrão da receita base
        if "BRANCO" in texto:
            score += 2000
        if "INCOLOR" in texto:
            score += 1500
        if "NATURAL" in texto:
            score += 1200
        return score

    return -999999


def encontrar_produto_receita_rolo_manual(produtos, chave, produto_base=None):
    candidatos = []
    for produto in produtos or []:
        if not produto_ativo(produto.get("situacao", "Ativo")):
            continue
        score = pontuar_receita_deterministica(produto, chave, produto_base=produto_base)
        if score > 0:
            candidatos.append((score, produto))

    if not candidatos:
        return None

    candidatos.sort(key=lambda item: item[0], reverse=True)
    return candidatos[0][1]


def chave_por_familia_tecnica_produto_global(produto, chave_padrao=None, chaves_validas=None):
    """Versão global usada por ações em massa da receita base."""
    familia = normalizar_familia_tecnica((produto or {}).get("familia_tecnica") or inferir_familia_tecnica_produto(produto))
    mapa = {
        "TECIDO": "tecido",
        "TUBO_32": "tubo_32",
        "TUBO_38": "tubo_38",
        "FITA_TUBO": "fita_tubo",
        "BASE_AC133": "base",
        "BASE_AC191": "base",
        "FITA_BASE": "fita_base",
        "ESPAGUETE_3MM": "espaguete_base",
        "CORRENTE_BOLA10": "corrente",
        "EMENDA_CORRENTE": "emenda_corrente",
        "TAMPA_BASE": "tampa_base",
        "COMANDO_32": "comando_32",
        "COMANDO_38": "comando_38",
    }
    chave = mapa.get(familia) or chave_padrao or "componente_livre"
    if chaves_validas and chave not in set(chaves_validas):
        return chave_padrao or "componente_livre"
    return chave


def item_catalogo_from_produto_receita_base(produto, chave, chaves_validas=None):
    """Monta item de receita fora da tela do carrinho, para aplicação plug and play em massa."""
    chave_real = chave_por_familia_tecnica_produto_global(produto, chave, chaves_validas=chaves_validas) if chave == "componente_livre" else chave
    item = produto_para_item_catalogo_motor(produto)
    familia = normalizar_familia_tecnica(item.get("familia_tecnica") or inferir_familia_tecnica_produto(produto))

    item["chave"] = chave_real
    item["categoria_tecnica"] = titulo_chave_tecnica(chave_real)
    item["familia_tecnica"] = familia

    if familia == "TECIDO" or chave_real == "tecido":
        item["varia_cor"] = False
        item["cor_componente"] = str((produto or {}).get("cor") or item.get("cor_componente") or "").strip()

    if familia in ["TUBO_32", "TUBO_38"]:
        item["varia_cor"] = False
        item["cor_componente"] = "Natural"
    elif familia == "ESPAGUETE_3MM":
        item["varia_cor"] = False
        item["cor_componente"] = "Incolor"
    elif familia in ["FITA_TUBO", "FITA_BASE"]:
        item["varia_cor"] = False

    return limpar_item_receita_para_salvar(item)


def montar_receita_base_rolo_manual_para_produto(produto_base, produtos_componentes):
    """
    Monta a receita base Rolô Manual para um produto final específico.
    Não altera banco; retorna carrinho e faltantes para prévia/aplicação em massa.
    """
    chaves_base = chaves_tecnicas_por_modelo("Rolô", False)
    chaves_base = chaves_rolo_manual_por_largura(chaves_base, produto_base)

    carrinho_novo = []
    faltantes = []

    for chave_receita in chaves_base:
        produto_receita = encontrar_produto_receita_rolo_manual(
            produtos_componentes,
            chave_receita,
            produto_base=produto_base,
        )
        if produto_receita:
            carrinho_novo.append(item_catalogo_from_produto_receita_base(produto_receita, chave_receita, chaves_validas=chaves_base))
        else:
            faltantes.append(titulo_chave_tecnica(chave_receita))

    return carrinho_novo, faltantes


def eh_produto_final_rolo_manual_para_receita(produto):
    """
    Identifica produto final Rolô manual para aplicação da receita base.

    Regra V26:
    - aceita o grupo técnico novo PERSIANA_ROLO e o legado ROLO;
    - aceita também produtos GestãoClick cujo nome começa com ROLÔ/ROLO;
    - para PERSIANA_ROLO, confirma modelo, tipo e Produto Base pelos campos estruturais;
    - separa a identidade do produto das receitas serializadas em observacoes;
    - nunca aplica em motorizada/motorizado nem em peças/comandos/tubos/bandôs.
    """
    produto = produto or {}
    nome = normalizar_busca_motor(produto.get("nome"))
    grupo_tecnico = normalizar_grupo_tecnico(produto.get("grupo_tecnico"))
    modelo_tecnico = normalizar_busca_motor(produto.get("modelo_tecnico"))
    produto_base = normalizar_busca_motor(produto.get("produto_base"))
    tipo = normalizar_busca_motor(produto.get("tipo_produto"))
    grupo_produto = normalizar_busca_motor(produto.get("grupo_produto"))

    # Identidade do produto: observacoes pode conter a receita técnica serializada
    # e, por isso, não pode decidir se o registro é produto final ou componente.
    texto_identidade = normalizar_busca_motor(
        " ".join(
            [
                str(produto.get("nome") or ""),
                str(produto.get("tipo_produto") or ""),
                str(produto.get("grupo_produto") or ""),
                str(produto.get("modelo") or ""),
                str(produto.get("grupo_tecnico") or ""),
                str(produto.get("modelo_tecnico") or ""),
                str(produto.get("produto_base") or ""),
            ]
        )
    )
    campos_motor = [
        "torque_motor",
        "voltagem_motor",
        "acionamento_motor",
        "uso_motor",
        "observacao_motor",
        "programacao_motor",
        "tubo_motor",
    ]
    possui_dado_motor = any(str(produto.get(campo) or "").strip() for campo in campos_motor)
    # Usa também o grupo técnico efetivo/inferido da listagem.
    # Alguns produtos do GestãoClick aparecem como PERSIANA_ROLO na tela,
    # mas ainda não têm o campo salvo de forma definitiva no banco.
    try:
        grupo_tecnico_efetivo = grupo_tecnico_label(produto)
    except Exception:
        grupo_tecnico_efetivo = grupo_tecnico
    if not produto_ativo(produto.get("situacao", "Ativo")):
        return False

    if possui_dado_motor:
        return False

    if any(t in texto_identidade for t in ["MOTOR", "MOTORIZADA", "MOTORIZADO"]):
        return False

    if contem_palavra_bloqueio_produto_final(texto_identidade) or any(
        termo in texto_identidade for termo in ["COMPONENTE", "TECIDO"]
    ):
        return False

    # Produto final canônico: todos os campos estruturais precisam concordar.
    if (
        grupo_tecnico == "PERSIANA_ROLO"
        and modelo_tecnico == "ROLO"
        and "PRODUTO FABRICADO" in tipo
        and not produto_base
    ):
        return True

    # Compatibilidade temporária com registros legados ainda não saneados.
    if grupo_tecnico == "ROLO" or grupo_tecnico_efetivo == "ROLO":
        return not produto_base

    # Fallback para produtos finais importados do GestãoClick ainda sem grupo técnico correto.
    if nome.startswith("ROLO ") or nome.startswith("ROLÔ "):
        if "PRODUTO FABRICADO" in tipo or "FABRICADO" in tipo or grupo_produto in ["ROLO", "ROLÔ", "PERSIANAS", "PERSIANA"]:
            return True

    return False


def montar_prev_aplicacao_receita_rolo_manual(produtos, ids_alvo=None):
    """Gera prévia plug and play da aplicação da receita Rolô manual.

    Se ids_alvo for informado, aplica somente nos produtos selecionados na lista.
    Se não houver seleção, usa todos os produtos finais PERSIANA_ROLO manuais encontrados.
    """
    produtos = produtos or []
    ids_set = set()
    for item in ids_alvo or []:
        try:
            ids_set.add(int(item))
        except Exception:
            pass

    if ids_set:
        base = [p for p in produtos if int(p.get("id") or 0) in ids_set]
    else:
        base = produtos

    produtos_finais = [p for p in base if eh_produto_final_rolo_manual_para_receita(p)]
    linhas = []

    for produto in produtos_finais:
        receita_atual = extrair_receita_tecnica_observacoes((produto or {}).get("observacoes"))
        carrinho, faltantes = montar_receita_base_rolo_manual_para_produto(produto, produtos)
        largura = largura_produto_base_motor(produto)
        try:
            from app.technical.rules.rolo import selecionar_tubo_rolo
            selecao = selecionar_tubo_rolo(largura, acionamento="manual") if largura > 0 else None
            tubo = selecao.diametro.value if selecao else "32mm"
        except Exception:
            tubo = "38mm" if largura > 1.80 else "32mm"
        linhas.append({
            "id": int(produto.get("id") or 0),
            "codigo": produto.get("codigo_interno") or produto.get("codigo_barras") or "",
            "nome": produto.get("nome") or "",
            "largura": largura,
            "tubo": tubo,
            "itens_receita": len(carrinho),
            "faltantes": ", ".join(faltantes),
            "ja_tem_receita": "Sim" if receita_atual else "Não",
            "carrinho": carrinho,
        })

    return linhas


def encontrar_produto_catalogo_contextual(produtos, chave, modelo_calculo, produto_base=None, motorizada=False):
    modelo_norm = normalizar_busca_motor(modelo_calculo)

    # 1º: receita base determinística do Rolô manual.
    # Isso evita ficar girando em tentativa por nome parecido.
    if modelo_norm in ["ROLO", "ROLÔ"] and not motorizada:
        produto_receita = encontrar_produto_receita_rolo_manual(produtos, chave, produto_base=produto_base)
        if produto_receita:
            return produto_receita

        # Para peças fixas da receita, NÃO usar fallback antigo,
        # pois ele puxa Romana/Horizontal por nome parecido.
        chaves_fixas_rolo = set(receita_rolo_manual_base_smarttec().keys()) - {"tecido"}
        if chave in chaves_fixas_rolo:
            return None

    # 2º: fallback antigo por pontuação, usado só quando não for peça fixa da receita.
    candidatos = []

    for produto in produtos or []:
        score = pontuar_produto_motor(produto, chave, modelo_calculo, produto_base, motorizada)
        if score > 0:
            candidatos.append((score, produto))

    if not candidatos:
        return None

    candidatos.sort(key=lambda item: item[0], reverse=True)
    return candidatos[0][1]


def filtrar_produtos_para_chave_motor(produtos, chave, modelo_calculo, motorizada=False, produto_base=None):
    filtrados = []

    for produto in produtos or []:
        if produto_candidato_chave_motor(produto, chave, modelo_calculo, motorizada, produto_base=produto_base):
            filtrados.append(produto)

    return filtrados


def montar_catalogo_motor_por_produtos(produtos_componentes, modelo_calculo=None, produto_base=None, motorizada=False):
    """
    Monta um catálogo contextual por modelo.
    Antes era uma busca genérica por nome e misturava item de cortina com rolô.
    Agora o automático só preenche quando o candidato parece compatível com modelo + chave técnica.
    """
    chaves = chaves_tecnicas_por_modelo(modelo_calculo or "Rolô", motorizada)
    catalogo = {}

    for chave in chaves:
        produto = encontrar_produto_catalogo_contextual(
            produtos_componentes,
            chave,
            modelo_calculo or "Rolô",
            produto_base=produto_base,
            motorizada=motorizada,
        )
        if produto:
            catalogo[chave] = produto_para_item_catalogo_motor(produto)

    return catalogo


def rotulo_produto_motor(produto):
    codigo = str(produto.get("codigo_interno") or produto.get("codigo_barras") or produto.get("id") or "").strip()
    nome = str(produto.get("nome") or "").strip()
    material = str(produto.get("material_tecido") or "").strip()
    cor = str(produto.get("cor") or "").strip()

    # Mostrar no carrinho/selectbox o custo já convertido para a unidade de saída do motor.
    # Assim rolo de fita 100m aparece por ML, não pelo valor do rolo inteiro.
    try:
        custo, unidade = calcular_custo_motor_produto(produto)
    except Exception:
        unidade = str(produto.get("unidade_venda") or "").strip()
        custo = float(produto.get("custo_final") or produto.get("valor_custo") or 0)

    detalhes = " • ".join([x for x in [material, cor, unidade, moeda_br(custo)] if x])
    rotulo = " - ".join([x for x in [codigo, nome] if x])
    if detalhes:
        rotulo = f"{rotulo} ({detalhes})"

    return rotulo or f"Produto #{produto.get('id')}"


def montar_opcoes_vinculo_motor(produtos_componentes, limite=80):
    # Renderizar milhares de opções no selectbox deixa o Streamlit pesado.
    # Mostramos só os primeiros resultados filtrados pela busca/categoria.
    opcoes = ["Selecione..."]
    mapa = {}

    for produto in list(produtos_componentes or [])[:limite]:
        rotulo = rotulo_produto_motor(produto)

        if rotulo in mapa:
            rotulo = f"{rotulo} #{produto.get('id')}"

        opcoes.append(rotulo)
        mapa[rotulo] = produto

    return opcoes, mapa


RECEITA_ROLO_MANUAL_SMARTTEC = {
    "tubo_32": "TUBO P/ ROLÔ 32MM NATURAL",
    "tubo_38": "TUBO P/ ROLÔ 38MM NATURAL",
    "fita_tubo": "FTF - FITA DUPLA FACE 20MMX100MTS - INCOLOR",
    "base": "BASE CHATA 02 / BASE CÔNICA",
    "fita_base": "15MMX100MTS COMP - FITA DE PLASTICO ADESIVA IMPORTADA",
    "espaguete_base": "ESP - ESPAGUETE / MACARRAO 3,00MM",
    "tecido": "TECIDO DE PERSIANA selecionado pelo material/cor",
    "corrente": "CORR - CORRENTE BOLA 10 JUTA",
    "emenda_corrente": "EMENDA DA CORRENTE / CONECTOR",
    "tampa_base": "TAMPA DA BASE CHATA 02",
    "comando_32": "COM - COMANDO 32MM AÇÃO MAXI - BRANCO",
    "comando_38": "COM - COMANDO 38MM AÇÃO MAXI - BRANCO",
}


def chaves_tecnicas_por_modelo(modelo_calculo, motorizada=False):
    modelo_original = str(modelo_calculo or "").strip()
    modelo = modelo_original.lower()
    modelo_norm = normalizar_busca_motor(modelo_original)

    # Modelos cadastráveis podem vir como "Rolô motorizada", "Rolo motor", etc.
    # Para decidir as chaves técnicas, separamos modelo base de acionamento.
    if any(t in modelo_norm for t in ["MOTORIZADA", "MOTORIZADO", "MOTOR"]):
        motorizada = True
    modelo_base = modelo_norm
    for termo in ["MOTORIZADA", "MOTORIZADO", "MOTOR", "MANUAL"]:
        modelo_base = modelo_base.replace(termo, "")
    modelo_base = re.sub(r"\s+", " ", modelo_base).strip()

    if modelo_base in ["ROLÔ", "ROLO", "ROL"] or modelo in ["rolô", "rolo"]:
        # Receita base Rolô manual: tecido troca por produto; peças padrão permanecem como base.
        # Suporte não entra separado porque já vem no kit/comando.
        # O motor escolhe automaticamente tubo/comando 32mm ou 38mm por largura.
        chaves = [
            "tecido",
            "tubo_32",
            "tubo_38",
            "fita_tubo",
            "base",
            "fita_base",
            "espaguete_base",
            "corrente",
            "emenda_corrente",
            "tampa_base",
        ]
        if motorizada:
            chaves += ["motor", "controle"]
        else:
            chaves += ["comando_32", "comando_38"]
        return chaves

    if modelo == "romana" or modelo_base == "ROMANA":
        chaves = [
            "tecido",
            "cabec_romana",
            "eixo_romana",
            "kit_comando_romana",
            "carretel_curto",
            "carretel_longo",
            "vareta_romana",
            "tampa_vareta",
            "espaguete_25",
            "fita_plastica_15",
            "guia_corda",
            "corda_horizontal",
            "base_chata",
            "tampa_base_chata",
        ]
        if motorizada:
            chaves += ["motor", "controle"]
        return chaves

    if modelo == "painel":
        return ["tecido", "trilho", "carrinho", "comando"]

    if modelo_base in ["DOUBLE VISION", "DOUBLE_VISION"] or modelo in ["double vision", "double_vision"]:
        # Double Vision: tecido e componentes ficam isolados pelos grupos técnicos.
        # Manual usa a categoria geral Tubos, permitindo 32mm, 38mm e 41mm.
        # 56mm/70mm ficam fora do manual para não misturar com motorizada/toldo.
        if motorizada:
            chaves = ["tecido", "tubo", "perfil", "suporte", "motor", "controle"]
        else:
            chaves = ["tecido", "tubo", "perfil", "suporte", "mecanismo", "corrente"]
        return chaves

    if modelo_base in ["CORTINA", "CORTINA DE TECIDO", "CORTINA/TRILHO", "TRILHO", "CORTINA TRILHO"] or modelo in ["cortina", "cortina de tecido", "cortina/trilho"]:
        chaves = ["tecido", "costura", "suporte", "trilho"]
        if motorizada:
            chaves += ["correia", "motor", "controle"]
        return chaves

    if modelo == "trilho motorizado":
        return ["trilho", "correia", "carrinho", "motor", "suporte", "controle"]

    if modelo == "persiana externa":
        chaves = ["lamina", "guia", "caixa", "suporte"]
        if motorizada:
            chaves += ["motor", "controle"]
        else:
            chaves += ["comando"]
        return chaves

    if modelo == "toldo":
        chaves = ["lona", "tubo_frontal", "tubo_carga", "braco", "suporte"]
        if motorizada:
            chaves += ["motor", "controle"]
        else:
            chaves += ["manivela"]
        return chaves

    return []


def titulo_chave_tecnica(chave):
    nomes = {
        "tecido": "Tecido / material",
        "lona": "Lona",
        "tubo": "Tubo",
        "tubo_32": "Tubo 32mm",
        "tubo_38": "Tubo 38mm",
        "fita_tubo": "Fita dupla face 2,5 para tubo",
        "base": "Base / perfil inferior",
        "fita_base": "Fita plástica 1,5 para base",
        "espaguete_base": "Espaguete 3mm para base",
        "perfil": "Perfil",
        "suporte": "Suporte",
        "comando": "Comando / mecanismo",
        "comando_32": "Comando / kit 32mm",
        "comando_38": "Comando / kit 38mm",
        "mecanismo": "Mecanismo",
        "corrente": "Corrente",
        "emenda_corrente": "Emenda da corrente",
        "tampa_base": "Tampa da base",
        "motor": "Motor",
        "controle": "Controle",
        "instalacao": "Instalação",
        "trilho": "Trilho",
        "correia": "Correia",
        "carrinho": "Carrinho",
        "vareta": "Vareta",
        "cordao": "Cordão",
        "costura": "Costura / mão de obra",
        "lamina": "Lâmina / tela",
        "guia": "Guia lateral",
        "caixa": "Caixa / perfil superior",
        "tubo_frontal": "Tubo frontal",
        "tubo_carga": "Tubo de carga",
        "braco": "Braço",
        "manivela": "Manivela",
    }
    return nomes.get(chave, chave)


def largura_produto_base_motor(produto_base):
    """Retorna a largura do produto final em metros para escolher tubo/comando do Rolô."""
    try:
        valor = (produto_base or {}).get("largura")
        if valor is None or str(valor).strip() == "":
            return 0.0
        if isinstance(valor, str):
            texto = valor.replace("R$", "").replace("%", "").strip()
            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", ".")
            valor = texto
        largura = float(valor or 0)
        # Se vier em centímetro, converte para metro.
        if largura > 10:
            largura = largura / 100.0
        return largura
    except Exception:
        return 0.0


def chaves_rolo_manual_por_largura(chaves, produto_base):
    """
    Rolô manual: seleciona apenas o tubo/comando adequado para a largura.
    Regra técnica central (app.technical.rules.rolo):
    - <= 1,80m: tubo 32mm
    - > 1,80m e <= 2,50m: tubo 38mm
    - > 2,50m e <= 3,20m: tubo 43mm
    - > 3,20m: manual proibido (motorização obrigatória)
    Se a largura ainda não estiver informada, começa com 32mm.
    """
    try:
        from app.technical.rules.rolo import selecionar_tubo_rolo, MotorObrigatorioErro
    except Exception:
        # Fallback compatível
        chaves = list(chaves or [])
        largura = largura_produto_base_motor(produto_base)
        if largura <= 0 or largura <= 1.80:
            remover = {"tubo_38", "comando_38", "tubo_43", "comando_43"}
        elif largura <= 2.50:
            remover = {"tubo_32", "comando_32", "tubo_43", "comando_43"}
        elif largura <= 3.20:
            remover = {"tubo_32", "comando_32", "tubo_38", "comando_38"}
        else:
            # > 3,20: manual proibido, remove todos os manuais
            remover = {"tubo_32", "comando_32", "tubo_38", "comando_38", "tubo_43", "comando_43"}
        return [ch for ch in chaves if ch not in remover]

    chaves = list(chaves or [])
    largura = largura_produto_base_motor(produto_base)

    if largura <= 0:
        # Sem largura: padrão 32mm
        remover = {"tubo_38", "comando_38", "tubo_43", "comando_43"}
        return [ch for ch in chaves if ch not in remover]

    try:
        selecao = selecionar_tubo_rolo(largura, acionamento="manual")
    except MotorObrigatorioErro:
        # Largura > 3,20: manual proibido, remove todos os tubos/comandos manuais
        remover = {"tubo_32", "comando_32", "tubo_38", "comando_38", "tubo_43", "comando_43"}
        return [ch for ch in chaves if ch not in remover]

    diametro = selecao.diametro.value
    # Remove os outros diâmetros
    todos_diametros = {"32mm", "38mm", "43mm", "65mm", "70mm"}
    remover_diametros = todos_diametros - {diametro}
    remover = set()
    for d in remover_diametros:
        d_sufixo = d.replace("mm", "")
        remover.add(f"tubo_{d_sufixo}")
        remover.add(f"comando_{d_sufixo}")

    return [ch for ch in chaves if ch not in remover]


def aplicar_vinculos_tecnicos_motor(catalogo_auto, produtos_componentes, modelo_calculo, motorizada, prefixo_key, disabled=False, produto_base=None):
    """
    Carrinho de receita técnica.

    Fluxo:
    - Detecta o modelo pelo produto final quando possível.
    - Busca separada por categoria técnica para ficar mais rápida e evitar mistura.
    - O cálculo final usa somente o carrinho manual; a busca automática por nome está desligada.
    - Só busca em todos os componentes quando a categoria for "Componente livre".
    """
    # IMPORTANTE: o cálculo agora usa somente o carrinho manual.
    # Não iniciamos mais com catalogo_auto, porque a busca automática por nome
    # misturava componentes de Rolô, Romana, Horizontal, Double Vision etc.
    catalogo = {}

    def inferir_modelo_carrinho_por_produto(produto):
        texto = texto_produto_motor(produto or {})
        modelo_campo = str((produto or {}).get("modelo") or "").strip()
        linha_campo = str((produto or {}).get("linha") or "").strip()

        # O campo modelo às vezes vem como MANUAL/MOTORIZADA.
        # Isso é tipo de acionamento, não modelo técnico da persiana.
        # Se devolver MANUAL aqui, o motor não encontra chaves e "não dá as caras".
        modelo_campo_norm = normalizar_busca_motor(modelo_campo)
        if modelo_campo and modelo_campo_norm not in ["SELECIONE", "SELECIONE", "MANUAL", "MOTORIZADA", "MOTORIZADO"]:
            return modelo_campo

        if "DOUBLE VISION" in texto or "DV" in texto:
            return "Double Vision"
        if "ROMANA" in texto:
            return "Romana"
        if "PAINEL" in texto:
            return "Painel"
        if "TRILHO" in texto or "CORTINA" in texto:
            return "Cortina/Trilho"
        if "TOLDO" in texto:
            return "Toldo"
        if "ROLO" in texto or "ROLÔ" in texto or "SCREEN" in texto or "BLACKOUT" in texto or "BK " in texto:
            return "Rolô"

        if linha_campo:
            return linha_campo

        return modelo_calculo or "Rolô"

    modelo_detectado = inferir_modelo_carrinho_por_produto(produto_base)
    modelo_usado = modelo_calculo or modelo_detectado

    chaves = chaves_tecnicas_por_modelo(modelo_usado, motorizada)
    if normalizar_busca_motor(modelo_usado) in ["ROLO", "ROLÔ"] and not motorizada:
        chaves = chaves_rolo_manual_por_largura(chaves, produto_base)
    if not chaves:
        return catalogo

    # Categoria baú/livre para casos especiais.
    # - Baú: busca apenas itens marcados como compartilhados, sem mudar o grupo técnico original.
    # - Livre: busca em todos os componentes, mas exige texto para não pesar a tela.
    chaves_carrinho = list(chaves) + ["bau_componentes", "componente_livre"]

    tenant_id_cache = st.session_state.get("tenant_empresa_id")
    carrinho_key = f"tenant_{tenant_id_cache}_{prefixo_key}_carrinho_receita_tecnica"
    if carrinho_key not in st.session_state:
        st.session_state[carrinho_key] = []

    # Carrega automaticamente a receita oficial salva no produto/clonado.
    # Assim o clone já abre pronto, sem o motor tentar montar nada sozinho.
    receita_salva_inicial = extrair_receita_tecnica_observacoes((produto_base or {}).get("observacoes"))
    if receita_salva_inicial and not st.session_state.get(carrinho_key):
        st.session_state[carrinho_key] = [limpar_item_receita_para_salvar(item) for item in receita_salva_inicial]
        st.session_state[f"{carrinho_key}_carregada_do_produto"] = True

    # Motor de descoberta desligado definitivamente.
    # O carrinho começa vazio, ou carrega a receita já salva/clonada no produto quando implementarmos persistência.
    # A partir de agora o motor só calcula o que está no carrinho/receita; ele não escolhe componente sozinho.

    # Limites para acelerar a tela. O selectbox não precisa carregar milhares de itens.
    MAX_RESULTADOS_BUSCA = 80
    MIN_CARACTERES_BUSCA_LIVRE = 2

    def texto_produto_carrinho(produto):
        # Cache local no dicionário do produto para evitar normalizar o mesmo texto toda hora.
        if isinstance(produto, dict) and "_texto_carrinho_motor" in produto:
            return produto.get("_texto_carrinho_motor") or ""
        texto = texto_produto_motor(produto)
        if isinstance(produto, dict):
            produto["_texto_carrinho_motor"] = texto
        return texto

    def item_catalogo_from_produto(produto, chave):
        # Se veio como livre, mas tem família técnica cadastrada, coloca na chave correta.
        # Se veio pelo Baú Inteligente, mantém como extra/livre para não substituir
        # uma categoria obrigatória da receita por engano.
        if chave == "bau_componentes":
            chave_real = "componente_livre"
            categoria_manual = "Baú de componentes"
        else:
            chave_real = chave_por_familia_tecnica_produto(produto, chave) if chave == "componente_livre" else chave
            categoria_manual = "Componente livre" if chave_real == "componente_livre" else titulo_chave_tecnica(chave_real)

        item = produto_para_item_catalogo_motor(produto)
        familia = normalizar_familia_tecnica(item.get("familia_tecnica") or inferir_familia_tecnica_produto(produto))

        item["chave"] = chave_real
        item["categoria_tecnica"] = categoria_manual
        item["familia_tecnica"] = familia

        # Tecido tem cor própria do campo técnico "cor". Ele NÃO participa da troca de cor dos componentes.
        if familia == "TECIDO" or chave_real == "tecido":
            item["varia_cor"] = False
            item["cor_componente"] = str((produto or {}).get("cor") or item.get("cor_componente") or "").strip()

        # Regras fixas da SmartTec: tubo natural, espaguete incolor, fitas não variam.
        if familia in ["TUBO_32", "TUBO_38"]:
            item["varia_cor"] = False
            item["cor_componente"] = "Natural"
        elif familia == "ESPAGUETE_3MM":
            item["varia_cor"] = False
            item["cor_componente"] = "Incolor"
        elif familia in ["FITA_TUBO", "FITA_BASE"]:
            item["varia_cor"] = False

        return item

    def rotulo_chave(chave):
        if chave == "bau_componentes":
            return "Baú de componentes [bau_componentes]"
        if chave == "componente_livre":
            return "Componente livre / extra [componente_livre]"

        modelo_contexto = normalizar_busca_motor(modelo_usado)
        if modelo_contexto in ["DOUBLE VISION", "DOUBLE_VISION"]:
            if chave == "tecido":
                return "Tecidos Double Vision [tecido]"
            if chave == "tubo":
                return "Tubos [tubo]"

        if modelo_contexto in ["CORTINA", "CORTINA DE TECIDO", "CORTINA/TRILHO", "TRILHO"]:
            if chave == "tecido":
                return "Tecidos Cortinas [tecido]"
            if chave in ["trilho", "suporte", "costura"]:
                return f"Componentes Cortinas - {titulo_chave_tecnica(chave)} [{chave}]"

        return f"{titulo_chave_tecnica(chave)} [{chave}]"

    def chave_por_familia_tecnica_produto(produto, chave_padrao=None):
        """
        Corrige o caso em que o usuário encontra o item pela busca livre.
        Ex.: se o produto escolhido tem família TECIDO, ele entra como chave "tecido"
        e não como "componente_livre". Sem isso o motor alerta que falta tecido.
        """
        familia = normalizar_familia_tecnica((produto or {}).get("familia_tecnica") or inferir_familia_tecnica_produto(produto))
        mapa = {
            "TECIDO": "tecido",
            "TUBO_32": "tubo_32",
            "TUBO_38": "tubo_38",
            "FITA_TUBO": "fita_tubo",
            "BASE_AC133": "base",
            "BASE_AC191": "base",
            "FITA_BASE": "fita_base",
            "ESPAGUETE_3MM": "espaguete_base",
            "CORRENTE_BOLA10": "corrente",
            "EMENDA_CORRENTE": "emenda_corrente",
            "TAMPA_BASE": "tampa_base",
            "COMANDO_32": "comando_32",
            "COMANDO_38": "comando_38",
        }
        chave = mapa.get(familia) or chave_padrao or "componente_livre"

        # Em Rolô manual, só existe um tubo/comando ativo conforme largura.
        # Se o produto escolhido não pertence às chaves do carrinho atual, mantém livre para não quebrar a receita.
        if chave not in chaves_carrinho:
            return chave_padrao or "componente_livre"
        return chave

    def produto_compativel_busca(produto, texto_busca):
        if not texto_busca:
            return True
        texto = texto_produto_carrinho(produto)
        termos = [normalizar_busca_motor(t) for t in str(texto_busca).split() if str(t).strip()]
        return all(t in texto for t in termos if t)

    def produtos_base_para_categoria(chave):
        # Cache por categoria técnica: evita refazer a filtragem pesada a cada tecla digitada.
        cache_key = f"tenant_{tenant_id_cache}_{prefixo_key}_cache_carrinho_v47_{modelo_usado}_{motorizada}_{chave}"

        if cache_key in st.session_state:
            return st.session_state[cache_key]

        if chave == "bau_componentes":
            base = []
            for produto in produtos_componentes or []:
                tipo = normalizar_busca_motor(produto.get("tipo_produto"))
                if "FABRICADO" in tipo or "SERVICO" in tipo or "SERVIÇO" in tipo:
                    continue
                if produto_disponivel_no_bau_componentes(produto):
                    base.append(produto)
            st.session_state[cache_key] = base
            return base

        if chave == "componente_livre":
            base = []
            for produto in produtos_componentes or []:
                tipo = normalizar_busca_motor(produto.get("tipo_produto"))
                if "FABRICADO" in tipo or "SERVICO" in tipo or "SERVIÇO" in tipo:
                    continue
                base.append(produto)
            st.session_state[cache_key] = base
            return base

        # Busca separada por categoria técnica.
        # Ex.: se categoria é Tecido, não mostra Tubo; se é Tubo, não mostra tecido.
        base = filtrar_produtos_para_chave_motor(
            produtos_componentes,
            chave,
            modelo_usado,
            motorizada,
            produto_base=produto_base,
        )
        st.session_state[cache_key] = base
        return base

    def produtos_para_carrinho(chave, texto_busca):
        base = produtos_base_para_categoria(chave)
        busca_norm = normalizar_busca_motor(texto_busca)

        # Para busca livre/baú, não carregar tudo sem texto porque isso deixa a tela pesada.
        if chave in ["componente_livre", "bau_componentes"] and len(busca_norm) < MIN_CARACTERES_BUSCA_LIVRE:
            return []

        # Sem busca digitada, mostra uma amostra curta da categoria.
        if not busca_norm:
            return list(base or [])[:MAX_RESULTADOS_BUSCA]

        resultado = []
        for produto in base or []:
            tipo = normalizar_busca_motor(produto.get("tipo_produto"))
            if "FABRICADO" in tipo or "SERVICO" in tipo or "SERVIÇO" in tipo:
                continue
            if produto_compativel_busca(produto, texto_busca):
                resultado.append(produto)
                if len(resultado) >= MAX_RESULTADOS_BUSCA:
                    break

        return resultado

    def produto_parece_categoria_errada(produto, chave):
        if not produto or chave in ["componente_livre", "bau_componentes"]:
            return False

        texto = texto_produto_motor(produto)

        if chave == "tecido":
            return not eh_tecido_persiana_motor(produto)
        if chave.startswith("tubo") or chave == "tubo":
            if "TUBO" not in texto:
                return True
            return contem_algum(texto, [
                "TAMPA", "SUPORTE", "PONTEIRA", "COMANDO", "KIT", "CORRENTE",
                "EMENDA", "CONECTOR", "BASE", "FITA", "ESPAGUETE", "MACARRAO", "MACARRÃO"
            ])
        if chave in ["base", "perfil_base"]:
            return "BASE" not in texto
        if chave == "corrente":
            return "CORRENTE" not in texto
        if chave == "emenda_corrente":
            return not ("EMENDA" in texto or "CONECTOR" in texto)
        if chave == "tampa_base":
            return "TAMPA" not in texto
        if chave.startswith("comando"):
            return "COMANDO" not in texto

        return False

    # Aplica itens já salvos no carrinho ao catálogo do motor.
    for item in st.session_state.get(carrinho_key, []):
        chave_item = item.get("chave")
        if chave_item and chave_item != "componente_livre":
            catalogo[chave_item] = {
                "codigo": item.get("codigo"),
                "produto_id": item.get("produto_id"),
                "nome": item.get("nome"),
                "unidade": item.get("unidade"),
                "custo_unitario": item.get("custo_unitario", 0),
                "familia_tecnica": item.get("familia_tecnica"),
                "varia_cor": item.get("varia_cor"),
                "cor_componente": item.get("cor_componente"),
            }

    with st.expander("Carrinho da receita técnica", expanded=True):
        st.caption(
            "Monte a receita como uma compra online: escolha a categoria, busque o componente, "
            "adicione ao carrinho e use no cálculo. O motor NÃO escolhe mais componentes automaticamente."
        )

        c_info1, c_info2, c_info3 = st.columns(3)
        with c_info1:
            st.metric("Itens no carrinho", len(st.session_state.get(carrinho_key, [])))
        with c_info2:
            st.write("**Modelo detectado:**", modelo_detectado or "-")
        with c_info3:
            st.write("**Tipo:**", "Motorizado" if motorizada else "Manual")

        if modelo_detectado and str(modelo_detectado).strip().lower() != str(modelo_calculo or "").strip().lower():
            st.info(f"O carrinho identificou o modelo como **{modelo_detectado}** pelo produto final. Confira se o modelo selecionado acima está correto antes de calcular.")

        receita_salva_produto = extrair_receita_tecnica_observacoes((produto_base or {}).get("observacoes"))
        ultima_receita_sessao = st.session_state.get("smarttec_ultima_receita_tecnica") or []
        carrinho_atual = list(st.session_state.get(carrinho_key, []))
        mensagem_receita_key = f"{prefixo_key}_mensagem_receita_temp"

        # Painel único e limpo da receita pronta.
        # Agora fica separado em 3 ações diferentes:
        # 1) Restaurar receita oficial salva no produto/clonado.
        # 2) Atualizar somente o tecido conforme material/cor do produto.
        # 3) Trocar somente a cor dos componentes que variam por cor.
        st.markdown('<div style="font-size:16px;font-weight:700;color:#111827;margin:4px 0 6px 0;">Receita Base</div>', unsafe_allow_html=True)

        tem_receita_salva = bool(receita_salva_produto)
        tem_carrinho = bool(carrinho_atual)

        mensagem_receita_temp = st.session_state.pop(mensagem_receita_key, "")
        if mensagem_receita_temp:
            st.success(mensagem_receita_temp)

        if tem_receita_salva and not tem_carrinho:
            st.info("Existe receita gravada neste produto/clonado. Clique abaixo para inserir a receita no carrinho.")
        elif ultima_receita_sessao and not tem_carrinho:
            st.warning("Este produto ainda não tem receita gravada. Você pode recuperar a última receita montada nesta sessão.")
        elif not tem_carrinho:
            st.warning("Nenhuma receita pronta encontrada. Monte o carrinho uma vez e salve o produto para gravar a receita.")

        # Autoajuste de tecido quando o produto clonado tem material/cor preenchidos.
        # Não troca componentes; só o item TECIDO da receita.
        def atualizar_tecido_receita_por_produto(mostrar_mensagem=True):
            """
            Atualiza somente o item TECIDO usando os campos técnicos do produto final:
            - Nome do produto clonado/original para manter a mesma família comercial do tecido
              Ex.: BK NAPOLES Branco -> BK NAPOLES Bege, e não BK BRISK Bege.
            - Material / tecido
            - Cor

            Importante: isso não usa cor_componente. Tecido tem cor própria.
            """
            nome_ref = str((produto_base or {}).get("nome") or "").strip()
            material_ref = str((produto_base or {}).get("material_tecido") or "").strip()
            cor_ref = str((produto_base or {}).get("cor") or "").strip()

            if not nome_ref and not material_ref and not cor_ref:
                if mostrar_mensagem:
                    st.error("Informe Nome, Material / tecido e Cor nos detalhes técnicos do produto para atualizar o tecido.")
                return False

            material_norm = normalizar_busca_motor(material_ref)
            cor_norm = normalizar_busca_motor(cor_ref)
            nome_norm = normalizar_busca_motor(nome_ref)

            def tokens_nome_tecido_referencia():
                """
                Pega os tokens comerciais do nome do produto para manter a mesma linha/família.
                Remove cor, medidas e termos genéricos.

                Exemplo:
                BK NAPOLES - BEGE - 2,60M -> [BK, NAPOLES]
                SCREEN 3% JP IMPORTADA - BRANCO - 2,50M -> [SCREEN, 3%, JP, IMPORTADA]
                """
                ignorar = set([
                    "ROLO", "ROLÔ", "PERSIANA", "MANUAL", "MOTORIZADA", "MOTOR", "PRODUTO",
                    "FABRICADO", "TECIDO", "MATERIAL", "COR", "BRANCO", "BRANCA", "PRETO", "PRETA",
                    "BEGE", "CINZA", "MARFIM", "NATURAL", "INCOLOR", "M", "MM", "CM", "ML", "M2",
                    "BLACKOUT", "TRANSLUCIDO", "TRANSLUCIDA", "TELA", "PARA", "COM", "SEM"
                ])
                if cor_norm:
                    ignorar.update(cor_norm.split())
                if material_norm:
                    # Material é usado como filtro separado; não deve decidir entre NAPOLES/BRISK.
                    ignorar.update([t for t in material_norm.split() if t not in ["SCREEN", "BK"]])

                tokens = []
                for token in nome_norm.split():
                    token_limpo = token.strip()
                    if not token_limpo:
                        continue
                    if token_limpo in ignorar:
                        continue
                    if re.fullmatch(r"\d+(?:[.,]\d+)?", token_limpo):
                        continue
                    if re.fullmatch(r"\d+(?:[.,]\d+)?M", token_limpo):
                        continue
                    if len(token_limpo) < 2 and token_limpo not in ["%"]:
                        continue
                    tokens.append(token_limpo)

                # Remove duplicados preservando ordem.
                unicos = []
                for token in tokens:
                    if token not in unicos:
                        unicos.append(token)
                return unicos

            tokens_ref = tokens_nome_tecido_referencia()

            candidatos = []
            for produto in produtos_componentes or []:
                familia = normalizar_familia_tecnica(produto.get("familia_tecnica") or inferir_familia_tecnica_produto(produto))
                if familia != "TECIDO" and not eh_tecido_persiana_motor(produto):
                    continue

                texto = texto_produto_motor(produto)
                nome_prod = normalizar_busca_motor(produto.get("nome"))
                material_prod = normalizar_busca_motor(produto.get("material_tecido"))
                cor_prod = normalizar_busca_motor(produto.get("cor"))

                pontos = 0

                # Material precisa bater quando informado. Aceita BK como BLACKOUT.
                if material_norm:
                    material_bate = (
                        material_prod == material_norm
                        or material_norm in texto
                        or (material_norm == "BLACKOUT" and ("BLACKOUT" in texto or " BK " in f" {texto} " or texto.startswith("BK ")))
                    )
                    if not material_bate:
                        continue
                    pontos += 8 if material_prod == material_norm else 5

                # Cor precisa bater quando informada. Primeiro campo técnico, depois nome/texto.
                if cor_norm:
                    cor_bate = cor_prod == cor_norm or cor_norm in texto
                    if not cor_bate:
                        continue
                    pontos += 20 if cor_prod == cor_norm else 10

                # Mantém a mesma linha/nome comercial do produto que está sendo clonado.
                # Isso evita BLACKOUT BEGE escolher BK BRISK quando o clone é BK NAPOLES BEGE.
                if tokens_ref:
                    bateu_tokens = [t for t in tokens_ref if t in nome_prod or t in texto]
                    # Se há tokens fortes do nome, exige pelo menos um deles para não fugir da família.
                    tokens_fortes = [t for t in tokens_ref if len(t) >= 4 or t in ["BK", "JP", "3%", "5%", "1%"]]
                    bateu_fortes = [t for t in tokens_fortes if t in nome_prod or t in texto]
                    if tokens_fortes and not bateu_fortes:
                        continue
                    pontos += len(bateu_tokens) * 12

                    # Bônus quando o prefixo comercial principal bate.
                    if len(tokens_ref) >= 2:
                        frase_ref = " ".join(tokens_ref[:2])
                        if frase_ref and frase_ref in texto:
                            pontos += 30

                # Preferir produtos ativos e códigos novos/organizados.
                if str(produto.get("situacao") or "Ativo") == "Ativo":
                    pontos += 2
                if str(produto.get("codigo_interno") or "").upper().startswith("JPTEC"):
                    pontos += 1

                candidatos.append((pontos, produto))

            if not candidatos:
                if mostrar_mensagem:
                    st.error(
                        "Não encontrei tecido mantendo o nome/família do produto clonado junto com Material/tecido e Cor. "
                        "Confira se o tecido cadastrado está com Família Técnica = TECIDO, Material/tecido e Cor preenchidos. "
                        "Se for uma linha nova do fornecedor, cadastre a cor/material nas opções auxiliares e salve o tecido."
                    )
                return False

            candidatos.sort(key=lambda x: (-x[0], len(str(x[1].get("nome") or ""))))
            produto_tecido = candidatos[0][1]
            novo_tecido = item_catalogo_from_produto(produto_tecido, "tecido")

            carrinho_base = list(st.session_state.get(carrinho_key, []))
            # Remove tecido antigo, inclusive se ele entrou errado como componente livre.
            carrinho_novo = []
            for item in carrinho_base:
                familia_item = normalizar_familia_tecnica(item.get("familia_tecnica"))
                if item.get("chave") == "tecido" or familia_item == "TECIDO":
                    continue
                carrinho_novo.append(item)

            carrinho_novo.insert(0, novo_tecido)
            st.session_state[carrinho_key] = carrinho_novo
            if mostrar_mensagem:
                st.session_state[mensagem_receita_key] = f"Tecido atualizado pela família do produto + cor: {novo_tecido.get('nome')}"
            return True

        def trocar_cor_componentes_receita(cor_destino):
            carrinho_base = list(st.session_state.get(carrinho_key, []))
            alterados = 0
            nao_encontrados = []
            carrinho_novo = []

            for item in carrinho_base:
                # Tecido, tubo natural, espaguete incolor e fitas não trocam cor.
                if item.get("varia_cor"):
                    substituto = procurar_substituto_mesma_familia_cor(produtos_componentes, item, cor_destino)
                    if substituto:
                        carrinho_novo.append(item_catalogo_from_produto(substituto, item.get("chave")))
                        alterados += 1
                    else:
                        carrinho_novo.append(item)
                        nao_encontrados.append(item.get("categoria_tecnica") or item.get("nome") or "item")
                else:
                    carrinho_novo.append(item)

            st.session_state[carrinho_key] = carrinho_novo
            return alterados, nao_encontrados

        def montar_receita_base_rolo_manual_smarttec():
            """
            Carrega uma receita base Rolô Manual no carrinho usando as regras determinísticas
            validadas durante o saneamento da base.
            Não salva automaticamente no produto: o usuário revisa, calcula e salva o produto.
            """
            chaves_base = chaves_tecnicas_por_modelo("Rolô", False)
            chaves_base = chaves_rolo_manual_por_largura(chaves_base, produto_base)

            carrinho_novo = []
            faltantes = []

            for chave_receita in chaves_base:
                produto_receita = encontrar_produto_receita_rolo_manual(
                    produtos_componentes,
                    chave_receita,
                    produto_base=produto_base,
                )
                if produto_receita:
                    carrinho_novo.append(limpar_item_receita_para_salvar(item_catalogo_from_produto(produto_receita, chave_receita)))
                else:
                    faltantes.append(titulo_chave_tecnica(chave_receita))

            return carrinho_novo, faltantes

        base_restaurar_col, base_select_col, base_carregar_col, _ = st.columns([1.35, 1.7, 1.35, 0.6])

        with base_restaurar_col:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            if tem_receita_salva:
                if st.button("Restaurar receita salva", key=f"{prefixo_key}_restaurar_receita_salva", disabled=disabled, use_container_width=True):
                    st.session_state[carrinho_key] = [limpar_item_receita_para_salvar(item) for item in receita_salva_produto]
                    st.session_state[mensagem_receita_key] = "Receita salva restaurada no carrinho."
                    st.rerun()
            elif ultima_receita_sessao:
                if st.button("Recuperar última montada", key=f"{prefixo_key}_recuperar_ultima_receita", disabled=disabled, use_container_width=True):
                    st.session_state[carrinho_key] = [limpar_item_receita_para_salvar(item) for item in ultima_receita_sessao]
                    st.session_state[mensagem_receita_key] = "Última receita montada recuperada."
                    st.rerun()
            else:
                st.button("Restaurar receita salva", key=f"{prefixo_key}_restaurar_receita_sem_receita", disabled=True, use_container_width=True)

        with base_select_col:
            opcoes_receita_base = ["Rolô manual"]
            receita_base_escolhida = st.selectbox(
                "Receita base",
                opcoes_receita_base,
                index=0,
                disabled=disabled,
                key=f"{prefixo_key}_receita_base_escolhida",
            )

        with base_carregar_col:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            modelo_para_base = normalizar_busca_motor(modelo_usado)
            if receita_base_escolhida == "Rolô manual" and modelo_para_base in ["ROLO", "ROLÔ"] and not motorizada:
                if st.button("Carregar receita base", key=f"{prefixo_key}_carregar_base_rolo_manual", disabled=disabled, use_container_width=True, type="primary"):
                    carrinho_base_rolo, faltantes_base_rolo = montar_receita_base_rolo_manual_smarttec()
                    if carrinho_base_rolo:
                        st.session_state[carrinho_key] = carrinho_base_rolo
                        if faltantes_base_rolo:
                            st.warning("Receita base carregada, mas faltaram: " + ", ".join(faltantes_base_rolo))
                        else:
                            st.session_state[mensagem_receita_key] = "Receita base Rolô manual carregada no carrinho."
                        st.rerun()
                    else:
                        st.error("Não encontrei itens suficientes para montar a Receita Base Rolô manual. Revise os grupos técnicos e nomes dos componentes.")
            else:
                st.button("Carregar receita base", key=f"{prefixo_key}_carregar_base_indisponivel", disabled=True, use_container_width=True)

        st.markdown('<div style="border-top:1px solid #e5e7eb;margin:10px 0 8px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:16px;font-weight:700;color:#111827;margin:4px 0 6px 0;">Atualizações rápidas</div>', unsafe_allow_html=True)

        col_tecido, col_cor, col_trocar, _ = st.columns([1.05, 1.7, 0.95, 1.3])

        with col_tecido:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            if st.button("Atualizar tecido", key=f"{prefixo_key}_atualizar_tecido_receita", disabled=disabled or not st.session_state.get(carrinho_key), use_container_width=False, type="primary"):
                if atualizar_tecido_receita_por_produto(mostrar_mensagem=True):
                    st.rerun()

        with col_cor:
            cor_componentes_tela = str((produto_base or {}).get("cor_componente") or "").strip()
            opcoes_cor_componentes_receita = list(CORES_COMPONENTES_PADRAO)
            for cor_extra in carregar_opcoes_categoria("cor_produto", incluir_vazio=False):
                if cor_extra and cor_extra not in opcoes_cor_componentes_receita and cor_extra != "Selecione...":
                    opcoes_cor_componentes_receita.append(cor_extra)
            cor_componentes_orc = st.selectbox(
                "Cor dos componentes",
                opcoes_cor_componentes_receita,
                index=indice_select(opcoes_cor_componentes_receita, cor_componentes_tela or "Branco"),
                disabled=disabled,
                key=f"{prefixo_key}_cor_componentes_receita",
            )

        with col_trocar:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            st.markdown(
                """
                <span id="smarttec-trocar-cor-receita-anchor"></span>
                <style>
                div:has(#smarttec-trocar-cor-receita-anchor) + div button {
                    background-color: #F59E0B !important;
                    border-color: #D97706 !important;
                    color: #ffffff !important;
                }
                div:has(#smarttec-trocar-cor-receita-anchor) + div button:hover {
                    background-color: #D97706 !important;
                    border-color: #B45309 !important;
                    color: #ffffff !important;
                }
                div:has(#smarttec-trocar-cor-receita-anchor) + div button:disabled {
                    background-color: #FCD34D !important;
                    border-color: #FBBF24 !important;
                    color: #78350F !important;
                    opacity: 0.65 !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Trocar cor", key=f"{prefixo_key}_trocar_cor_componentes", disabled=disabled or not st.session_state.get(carrinho_key), use_container_width=False):
                alterados, nao_encontrados = trocar_cor_componentes_receita(cor_componentes_orc)
                if nao_encontrados:
                    st.warning(f"Cor alterada em {alterados} item(ns). Não encontrei substituto para: {', '.join(nao_encontrados)}.")
                else:
                    st.session_state[mensagem_receita_key] = f"Cor dos componentes atualizada. Itens alterados: {alterados}."
                st.rerun()

        carrinho_atual = list(st.session_state.get(carrinho_key, []))

        # Autoatualização discreta do tecido ao trocar material/cor no clone.
        if carrinho_atual:
            termo_tecido_auto = " ".join([
                str((produto_base or {}).get("material_tecido") or ""),
                str((produto_base or {}).get("cor") or ""),
            ]).strip()
            auto_key_tecido = f"{prefixo_key}_ultimo_termo_tecido_auto"
            if termo_tecido_auto and st.session_state.get(auto_key_tecido) != termo_tecido_auto:
                atualizar_tecido_receita_por_produto(mostrar_mensagem=False)
                st.session_state[auto_key_tecido] = termo_tecido_auto
                st.rerun()

        st.markdown('<div style="border-top:1px solid #e5e7eb;margin:10px 0 8px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:16px;font-weight:700;color:#111827;margin:4px 0 6px 0;">Adicionar Item</div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1.2, 2.2])
        with c1:
            rotulos_chave = [rotulo_chave(ch) for ch in chaves_carrinho]
            chave_escolhida_rotulo = st.selectbox(
                "Categoria técnica",
                rotulos_chave,
                index=0,
                disabled=disabled,
                key=f"{prefixo_key}_carrinho_chave",
            )
            chave_escolhida = chaves_carrinho[rotulos_chave.index(chave_escolhida_rotulo)]

        with c2:
            busca = st.text_input(
                "Buscar produto/componente",
                value=st.session_state.get(f"{prefixo_key}_carrinho_busca", ""),
                placeholder="Ex.: branco, JPTEC, comando 32mm ação maxi, tubo 32mm natural...",
                disabled=disabled,
                key=f"{prefixo_key}_carrinho_busca",
            )

        produtos_opcao = produtos_para_carrinho(chave_escolhida, busca)
        opcoes, mapa = montar_opcoes_vinculo_motor(produtos_opcao, limite=MAX_RESULTADOS_BUSCA)
        busca_norm_carrinho = normalizar_busca_motor(busca)

        if busca_norm_carrinho and not produtos_opcao:
            if chave_escolhida == "bau_componentes":
                st.warning("Nenhum item encontrado no Baú. Digite ao menos 2 caracteres e confira se o componente foi copiado para o Baú.")
            elif chave_escolhida == "componente_livre":
                st.warning("Nenhum componente encontrado na busca livre.")
            else:
                st.warning("Nenhum item encontrado nesta categoria. Tente simplificar a busca, use o Baú ou use 'Componente livre / extra'.")

            c_cad_rapido, c_limpar_busca, _ = st.columns([1.15, 1.0, 3.2])
            with c_cad_rapido:
                if st.button("Cadastrar +", key=f"{prefixo_key}_carrinho_cadastrar_novo", disabled=disabled, use_container_width=True):
                    # Atalho global: qualquer busca sem resultado pode abrir cadastro de produto.
                    # O usuário cadastra o item e depois volta para a receita/listagem.
                    st.session_state.tela_produtos = "adicionar"
                    st.session_state.id_produto_editar = None
                    st.rerun()
            with c_limpar_busca:
                if st.button("Limpar busca", key=f"{prefixo_key}_carrinho_limpar_busca", disabled=disabled, use_container_width=True):
                    st.session_state[f"{prefixo_key}_carrinho_busca"] = ""
                    st.rerun()

        indice_padrao_produto = 1 if len(opcoes) > 1 else 0
        produto_col, add_col, _ = st.columns([2.7, 1.15, 1.25])
        with produto_col:
            escolha_produto = st.selectbox(
                "Produto encontrado",
                opcoes,
                index=indice_padrao_produto,
                disabled=disabled,
                key=f"{prefixo_key}_carrinho_produto",
            )

        produto_escolhido = mapa.get(escolha_produto) if escolha_produto != "Selecione..." else None

        if produto_escolhido and produto_parece_categoria_errada(produto_escolhido, chave_escolhida):
            st.error("Este produto parece não pertencer à categoria escolhida. Troque a categoria ou use 'Componente livre / extra'.")

        with add_col:
            st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
            adicionar = st.button(
                "+ Adicionar ao carrinho",
                disabled=disabled or escolha_produto == "Selecione..." or produto_parece_categoria_errada(produto_escolhido, chave_escolhida),
                key=f"{prefixo_key}_carrinho_add",
                use_container_width=True,
                type="primary",
            )

        if adicionar and escolha_produto != "Selecione...":
            produto = mapa[escolha_produto]
            novo_item = item_catalogo_from_produto(produto, chave_escolhida)
            chave_real_item = novo_item.get("chave") or chave_escolhida

            carrinho = list(st.session_state.get(carrinho_key, []))

            if chave_real_item == "componente_livre":
                carrinho.append(novo_item)
            else:
                # Substitui item da mesma categoria real, para não duplicar tecido/tubo/base/comando.
                carrinho = [i for i in carrinho if i.get("chave") != chave_real_item and normalizar_familia_tecnica(i.get("familia_tecnica")) != normalizar_familia_tecnica(novo_item.get("familia_tecnica"))]
                carrinho.append(novo_item)

            st.session_state[carrinho_key] = carrinho
            st.success(f"Adicionado: {novo_item.get('categoria_tecnica')} → {novo_item.get('nome')}")
            st.rerun()

        st.markdown('<div style="border-top:1px solid #e5e7eb;margin:10px 0 8px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:16px;font-weight:700;color:#111827;margin:4px 0 6px 0;">Receita montada</div>', unsafe_allow_html=True)

        carrinho = st.session_state.get(carrinho_key, [])
        if not carrinho:
            st.info("Carrinho vazio. Adicione os componentes da receita acima.")
        else:
            h_categoria, h_produto, h_cor, h_qtd, h_unidade, h_valor, h_acoes = st.columns([1.15, 3.1, 0.95, 0.7, 0.8, 0.9, 0.85])
            with h_categoria:
                st.markdown("**Categoria**")
            with h_produto:
                st.markdown("**Componente**")
            with h_cor:
                st.markdown("**Cor**")
            with h_qtd:
                st.markdown("**Qtd.**")
            with h_unidade:
                st.markdown("**Unidade**")
            with h_valor:
                st.markdown("**Valor**")
            with h_acoes:
                st.markdown("**Ações**")

            for idx_item, item in enumerate(carrinho):
                custo = float(item.get("custo_unitario") or 0)

                cols = st.columns([1.15, 3.1, 0.95, 0.7, 0.8, 0.9, 0.85])
                with cols[0]:
                    st.write(item.get("categoria_tecnica") or item.get("chave") or "-")
                with cols[1]:
                    st.write(item.get("nome") or "-")
                    st.caption(item.get("codigo") or "")
                with cols[2]:
                    st.write(item.get("cor_componente") or "-")
                with cols[3]:
                    st.write("-")
                with cols[4]:
                    st.write(item.get("unidade") or "-")
                with cols[5]:
                    st.write(moeda_br(custo))
                with cols[6]:
                    st.markdown(
                        f"""
                        <span id="smarttec-remover-receita-anchor-{idx_item}"></span>
                        <style>
                        div:has(#smarttec-remover-receita-anchor-{idx_item}) + div button {{
                            width: 32px !important;
                            min-width: 32px !important;
                            height: 32px !important;
                            min-height: 32px !important;
                            padding: 0 !important;
                            background-color: #dc3545 !important;
                            border-color: #dc3545 !important;
                            color: #ffffff !important;
                            border-radius: 4px !important;
                            display: inline-flex !important;
                            align-items: center !important;
                            justify-content: center !important;
                        }}
                        div:has(#smarttec-remover-receita-anchor-{idx_item}) + div button p {{
                            font-size: 16px !important;
                            font-weight: 800 !important;
                            line-height: 1 !important;
                        }}
                        div:has(#smarttec-remover-receita-anchor-{idx_item}) + div button:hover {{
                            background-color: #bb2d3b !important;
                            border-color: #bb2d3b !important;
                            color: #ffffff !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("×", key=f"{prefixo_key}_remove_carrinho_{idx_item}", disabled=disabled):
                        carrinho_novo = list(carrinho)
                        carrinho_novo.pop(idx_item)
                        st.session_state[carrinho_key] = carrinho_novo
                        st.rerun()

        st.markdown('<div style="border-top:1px solid #e5e7eb;margin:10px 0 8px 0;"></div>', unsafe_allow_html=True)

        st.markdown('<div style="font-size:16px;font-weight:700;color:#111827;margin:4px 0 6px 0;">Resultado da composição</div>', unsafe_allow_html=True)
        custo_motor_atual = float(st.session_state.get(f"{prefixo_key}_custo_motor_resultado", 0) or 0)
        st.markdown(
            f"""
            <div style="border:1px solid #bfdbfe;background:#eff6ff;border-radius:6px;padding:12px 14px;margin-bottom:8px;">
                <div style="font-size:13px;font-weight:700;color:#1e40af;margin-bottom:4px;">Custo da composição</div>
                <div style="font-size:24px;font-weight:800;color:#111827;">{moeda_br(custo_motor_atual)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <style>
            div:has(#smarttec-atualizar-calculo-receita-anchor) + div button,
            div:has(#smarttec-limpar-carrinho-receita-anchor) + div button {
                width: 100% !important;
                min-height: 38px !important;
                border-radius: 0.5rem !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 0.45rem 0.75rem !important;
            }
            div:has(#smarttec-limpar-carrinho-receita-anchor) + div button {
                background-color: #dc3545 !important;
                border-color: #dc3545 !important;
                color: #ffffff !important;
            }
            div:has(#smarttec-limpar-carrinho-receita-anchor) + div button:hover {
                background-color: #bb2d3b !important;
                border-color: #bb2d3b !important;
                color: #ffffff !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        l1, l2, _ = st.columns([1.1, 1.1, 3.2], gap="small")
        with l1:
            st.markdown('<span id="smarttec-atualizar-calculo-receita-anchor"></span>', unsafe_allow_html=True)
            if st.button("Atualizar cálculo", key=f"{prefixo_key}_carrinho_usar", disabled=disabled, use_container_width=True, type="primary"):
                st.session_state[mensagem_receita_key] = "Cálculo atualizado usando somente os itens do carrinho."
                st.rerun()

        with l2:
            st.markdown('<span id="smarttec-limpar-carrinho-receita-anchor"></span>', unsafe_allow_html=True)
            if st.button("Limpar carrinho", key=f"{prefixo_key}_carrinho_limpar", disabled=disabled, use_container_width=True):
                st.session_state[carrinho_key] = []
                # Limpa cache de busca do carrinho para atualizar a lista depois de importações/correções.
                for chave_sessao in list(st.session_state.keys()):
                    if str(chave_sessao).startswith(f"{prefixo_key}_cache_carrinho_"):
                        del st.session_state[chave_sessao]
                st.session_state[mensagem_receita_key] = "Carrinho da receita esvaziado."
                st.rerun()

    # Aplica novamente depois das alterações da tela.
    for item in st.session_state.get(carrinho_key, []):
        chave_item = item.get("chave")
        if chave_item and chave_item != "componente_livre":
            catalogo[chave_item] = {
                "codigo": item.get("codigo"),
                "produto_id": item.get("produto_id"),
                "nome": item.get("nome"),
                "unidade": item.get("unidade"),
                "custo_unitario": item.get("custo_unitario", 0),
                "familia_tecnica": item.get("familia_tecnica"),
                "varia_cor": item.get("varia_cor"),
                "cor_componente": item.get("cor_componente"),
            }

    carrinho_final_receita = list(st.session_state.get(carrinho_key, []))
    if carrinho_final_receita:
        st.session_state["smarttec_ultima_receita_tecnica"] = [limpar_item_receita_para_salvar(i) for i in carrinho_final_receita]

    if not catalogo:
        st.info("Receita técnica vazia. Insira a receita pronta ou monte o carrinho manual para calcular o custo.")

    return catalogo


def renderizar_componentes_adicionais_motor(
    produtos_componentes,
    modo,
    id_produto,
    disabled=False,
):
    """
    Permite acrescentar componentes extras ao cálculo do motor.
    Isso não substitui o motor: soma itens adicionais quando a receita padrão ainda não cobre tudo.
    """
    opcoes_componentes = ["Selecione..."]
    mapa_componentes = {}

    for comp_produto in produtos_componentes or []:
        nome_comp = str(comp_produto.get("nome") or "").strip()
        if not nome_comp:
            continue

        codigo_comp = str(comp_produto.get("codigo_interno") or comp_produto.get("codigo_barras") or comp_produto.get("id") or "").strip()
        material_comp = str(comp_produto.get("material_tecido") or "").strip()
        cor_comp = str(comp_produto.get("cor") or "").strip()
        unidade_comp = str(comp_produto.get("unidade_venda") or "").strip()
        custo_comp, unidade_motor = calcular_custo_motor_produto(comp_produto)
        detalhes = " • ".join([x for x in [material_comp, cor_comp, unidade_motor or unidade_comp, moeda_br(custo_comp)] if x])

        rotulo = f"{codigo_comp} - {nome_comp}" if codigo_comp else nome_comp
        if detalhes:
            rotulo += f" ({detalhes})"

        if rotulo in mapa_componentes:
            rotulo = f"{rotulo} #{comp_produto.get('id')}"

        opcoes_componentes.append(rotulo)
        mapa_componentes[rotulo] = comp_produto

    opcoes_componentes.append("Outro / manual")

    componentes_extras = []
    custo_extra_total = 0.0

    with st.expander("➕ Componentes extras da receita", expanded=False):
        st.caption(
            "Use para acrescentar peças extras somente quando a receita oficial precisar de algum item adicional. "
            "Ex.: tampa, ponteira, suporte especial, instalação, embalagem, mão de obra etc."
        )

        qtd_extras = st.number_input(
            "Qtd. de componentes adicionais",
            min_value=0,
            max_value=20,
            value=int(st.session_state.get(f"qtd_componentes_extras_motor_{modo}_{id_produto}", 0)),
            step=1,
            disabled=disabled,
            key=f"qtd_componentes_extras_motor_{modo}_{id_produto}",
        )

        if int(qtd_extras or 0) <= 0:
            st.info("Nenhum componente extra informado.")
            return componentes_extras, custo_extra_total

        cab1, cab2, cab3, cab4, cab5, cab6 = st.columns([2.8, 0.9, 0.85, 1.15, 0.9, 1.15])
        with cab1:
            st.markdown("**Componente adicional**")
        with cab2:
            st.markdown("**Qtd.**")
        with cab3:
            st.markdown("**Unid.**")
        with cab4:
            st.markdown("**Custo unit.**")
        with cab5:
            st.markdown("**Perda %**")
        with cab6:
            st.markdown("**Total**")

        for i in range(int(qtd_extras or 0)):
            c1, c2, c3, c4, c5, c6 = st.columns([2.8, 0.9, 0.85, 1.15, 0.9, 1.15])

            with c1:
                escolha = st.selectbox(
                    f"Componente adicional {i + 1}",
                    opcoes_componentes,
                    index=0,
                    label_visibility="collapsed",
                    disabled=disabled,
                    key=f"motor_extra_comp_{modo}_{id_produto}_{i}",
                )

            produto_extra = mapa_componentes.get(escolha)

            with c2:
                qtd = st.number_input(
                    f"Qtd. adicional {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    label_visibility="collapsed",
                    disabled=disabled,
                    key=f"motor_extra_qtd_{modo}_{id_produto}_{i}",
                )

            if escolha == "Outro / manual":
                with c3:
                    unidade = st.text_input(
                        f"Unid. adicional {i + 1}",
                        value="UN",
                        label_visibility="collapsed",
                        disabled=disabled,
                        key=f"motor_extra_unidade_manual_{modo}_{id_produto}_{i}",
                    )
                with c4:
                    custo_unit = st.number_input(
                        f"Custo adicional {i + 1}",
                        min_value=0.0,
                        value=0.0,
                        step=1.0,
                        format="%.2f",
                        label_visibility="collapsed",
                        disabled=disabled,
                        key=f"motor_extra_custo_manual_{modo}_{id_produto}_{i}",
                    )
                nome = "Componente manual"
            elif produto_extra:
                item_catalogo = produto_para_item_catalogo_motor(produto_extra)
                nome = item_catalogo.get("nome") or "Componente adicional"
                unidade = item_catalogo.get("unidade") or "UN"
                custo_unit = float(item_catalogo.get("custo_unitario") or 0)

                with c3:
                    st.markdown(f"<div style='height:38px;display:flex;align-items:center;'>{html.escape(str(unidade))}</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown(f"<div style='height:38px;display:flex;align-items:center;font-weight:600;'>{moeda_br(custo_unit)}</div>", unsafe_allow_html=True)
            else:
                nome = ""
                unidade = ""
                custo_unit = 0.0
                with c3:
                    st.markdown("<div style='height:38px;display:flex;align-items:center;color:#9ca3af;'>-</div>", unsafe_allow_html=True)
                with c4:
                    st.markdown("<div style='height:38px;display:flex;align-items:center;color:#9ca3af;'>-</div>", unsafe_allow_html=True)

            with c5:
                perda = st.number_input(
                    f"Perda adicional {i + 1}",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    format="%.2f",
                    label_visibility="collapsed",
                    disabled=disabled,
                    key=f"motor_extra_perda_{modo}_{id_produto}_{i}",
                )

            subtotal = float(qtd or 0) * float(custo_unit or 0)
            total = subtotal + (subtotal * (float(perda or 0) / 100))
            custo_extra_total += total

            with c6:
                st.markdown(
                    f"<div style='height:38px;display:flex;align-items:center;font-weight:700;'>{moeda_br(total)}</div>",
                    unsafe_allow_html=True,
                )

            if nome and float(qtd or 0) > 0:
                componentes_extras.append({
                    "Componente": nome,
                    "Categoria": "Adicional",
                    "Regra": "Manual",
                    "Qtd.": float(qtd or 0),
                    "Unid.": unidade,
                    "Custo unit.": float(custo_unit or 0),
                    "Perda %": float(perda or 0),
                    "Total": float(total or 0),
                })

        st.markdown(
            f"""
            <div style="margin-top:10px;background:#ecfdf5;border:1px solid #bbf7d0;color:#166534;border-radius:6px;padding:10px 12px;font-weight:700;">
                Total de componentes adicionais: {moeda_br(custo_extra_total)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    return componentes_extras, custo_extra_total


def nome_modelo_para_motor(modelo_calc, motorizada=False):
    modelo = str(modelo_calc or "").strip()
    modelo_norm = normalizar_busca_motor(modelo)

    if any(t in modelo_norm for t in ["MOTORIZADA", "MOTORIZADO", "MOTOR"]):
        motorizada = True

    modelo_base = modelo_norm
    for termo in ["MOTORIZADA", "MOTORIZADO", "MOTOR", "MANUAL"]:
        modelo_base = modelo_base.replace(termo, "")
    modelo_base = re.sub(r"\s+", " ", modelo_base).strip()

    if modelo_base in ["ROLÔ", "ROLO", "ROL"]:
        return "Rolô motorizada" if motorizada else "Rolô"
    if modelo_base == "ROMANA":
        return "Romana motorizada" if motorizada else "Romana"
    if modelo_base == "DOUBLE VISION":
        return "Double Vision motorizada" if motorizada else "Double Vision"
    if modelo_base == "CORTINA DE TECIDO":
        return "Cortina de tecido motorizada" if motorizada else "Cortina de tecido"
    if modelo_base == "PERSIANA EXTERNA":
        return "Persiana externa motorizada" if motorizada else "Persiana externa"
    if modelo_base == "TOLDO":
        return "Toldo motorizado" if motorizada else "Toldo"
    if modelo_base == "TRILHO" or modelo_base == "TRILHO MOTORIZADO":
        return "Trilho motorizado"

    return modelo


def produto_ativo(valor):
    valor = str(valor).strip().lower()
    return valor in ["ativo", "true", "1", "sim", "active"]


def buscar_produtos_api(skip=0, limit=500, todos=False, max_paginas=20):
    """
    Busca produtos no backend com paginação.

    - Uso normal da tela: busca um lote leve.
    - Ferramentas em massa/exportações: use todos=True para varrer todos os lotes.
    """
    try:
        if todos:
            produtos = []
            pagina_skip = int(skip or 0)
            lote = int(limit or 500)

            for _ in range(int(max_paginas or 20)):
                resp = get_produtos(skip=pagina_skip, limit=lote)

                if resp is None or resp.status_code != 200:
                    status = resp.status_code if resp is not None else "sem resposta"
                    st.error(f"Erro ao buscar produtos. Status: {status}")
                    break

                dados = resp.json()
                if not isinstance(dados, list) or not dados:
                    break

                produtos.extend(dados)

                if len(dados) < lote:
                    break

                pagina_skip += lote

            return lista_produtos_com_termos_preservados(produtos)

        resp = get_produtos(skip=skip, limit=limit)

        if resp is not None and resp.status_code == 200:
            return lista_produtos_com_termos_preservados(resp.json())

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar produtos. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


def _somente_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def gerar_codigo_interno_automatico(produtos=None, prefixo="PRD"):
    """
    Gera um código interno simples e profissional.
    Exemplo: PRD-000010

    Usa o maior ID/código já existente como referência.
    """
    if produtos is None:
        produtos = buscar_produtos_api()

    maior_numero = 0

    for produto in produtos or []:
        try:
            maior_numero = max(maior_numero, int(produto.get("id") or 0))
        except Exception:
            pass

        codigo = str(produto.get("codigo_interno") or "").strip()
        numeros = re.findall(r"\d+", codigo)
        if numeros:
            try:
                maior_numero = max(maior_numero, int(numeros[-1]))
            except Exception:
                pass

    return f"{prefixo}-{maior_numero + 1:06d}"


def _digito_verificador_ean13(doze_digitos):
    """
    Calcula o dígito verificador EAN-13.
    Recebe 12 dígitos e retorna o 13º.
    """
    digitos = [int(d) for d in doze_digitos]
    soma = sum(digitos[::2]) + sum(d * 3 for d in digitos[1::2])
    return str((10 - (soma % 10)) % 10)


def gerar_codigo_barras_automatico(produtos=None):
    """
    Gera um código de barras EAN-13 interno.
    Prefixo 789 + sequência baseada nos produtos existentes + dígito verificador.
    """
    if produtos is None:
        produtos = buscar_produtos_api()

    maior_seq = 0

    for produto in produtos or []:
        codigo = _somente_digitos(produto.get("codigo_barras"))
        if len(codigo) >= 4:
            try:
                # Pega a parte central do código. Funciona bem para códigos gerados pelo sistema.
                maior_seq = max(maior_seq, int(codigo[3:12]))
            except Exception:
                pass

        try:
            maior_seq = max(maior_seq, int(produto.get("id") or 0))
        except Exception:
            pass

    sequencia = maior_seq + 1
    base12 = f"789{sequencia:09d}"[-12:]
    return base12 + _digito_verificador_ean13(base12)


def preparar_codigos_automaticos_produto(produto_atual, modo):
    """
    Preenche código interno e código de barras automaticamente ao adicionar/clonar e também ao editar quando estiver vazio.
    Não sobrescreve código existente.
    """
    if modo not in ["adicionar", "clonar", "editar"]:
        return produto_atual

    produto_atual = dict(produto_atual or {})
    produtos = buscar_produtos_api()

    if not str(produto_atual.get("codigo_interno") or "").strip():
        produto_atual["codigo_interno"] = gerar_codigo_interno_automatico(produtos)

    if not str(produto_atual.get("codigo_barras") or "").strip():
        produto_atual["codigo_barras"] = gerar_codigo_barras_automatico(produtos)

    return produto_atual


def produto_disponivel_no_bau_componentes(produto):
    """Retorna True quando o produto está liberado no Baú de Componentes.

    Compatível com as duas fases do SmartTec:
    - marcador antigo nas observações;
    - novo Grupo Técnico BAU_PERSIANAS.
    """
    obs = normalizar_busca_motor((produto or {}).get("observacoes"))
    grupo = normalizar_grupo_tecnico((produto or {}).get("grupo_tecnico")) or ""
    return (
        grupo == "BAU_PERSIANAS"
        or "BAU_COMPONENTES_PERSIANAS=SIM" in obs
        or "DISPONIVEL_NO_BAU_COMPONENTES=SIM" in obs
    )


def aplicar_marcador_bau_componentes_no_payload(payload, ativo=True):
    """Marca/remove o produto do Baú sem mudar grupo técnico.

    O item continua em COMPONENTES_ROLO, COMPONENTES_ROMANA, COMPONENTES_DOUBLE_VISION etc.
    O baú é apenas uma camada de busca compartilhada.
    """
    payload = dict(payload or {})
    obs = str(payload.get("observacoes") or "").strip()
    padrao = re.compile(r"\s*\|?\s*(BAU_COMPONENTES_PERSIANAS=SIM|DISPONIVEL_NO_BAU_COMPONENTES=SIM)\s*", re.IGNORECASE)
    obs_limpa = padrao.sub("", obs).strip(" |")

    if ativo:
        if obs_limpa:
            obs_nova = f"{obs_limpa} | {MARCADOR_BAU_COMPONENTES_PERSIANAS}"
        else:
            obs_nova = MARCADOR_BAU_COMPONENTES_PERSIANAS
    else:
        obs_nova = obs_limpa

    payload["observacoes"] = obs_nova
    return payload


def produto_pode_ir_para_bau_componentes(produto):
    """Trava de segurança: baú é só para componentes.

    Não libera produto final, tecido, lâmina, motor puro ou item inativo por engano.
    """
    grupo = grupo_tecnico_filtro_produto(produto)
    tipo = normalizar_busca_motor((produto or {}).get("tipo_produto"))
    texto = texto_produto_motor(produto or {})

    if "PRODUTO FABRICADO" in tipo:
        return False
    if str(grupo or "").startswith("TECIDOS_") or str(grupo or "").startswith("LAMINAS_"):
        return False
    if grupo in ["MOTORES"]:
        return False
    if any(p in texto for p in ["TECIDO", "SCREEN", "BLACKOUT", "DOUBLE VISION", "LAMINA", "LÂMINA"]):
        return False
    return str(grupo or "").startswith("COMPONENTES_") or grupo in ["ACESSORIOS_MOTOR"]


def gerar_csv_produtos(produtos):
    """
    Gera CSV simples para exportar cadastros.
    Usa separador ; para abrir melhor no Excel em pt-BR.
    """
    if not produtos:
        return ""

    produtos_preservados = lista_produtos_com_termos_preservados(produtos)
    df_export = pd.DataFrame(produtos_preservados).fillna("")

    # Coluna auxiliar para exportação/análise.
    # Ela mostra exatamente o mesmo valor usado no filtro da tela, inclusive SEM_GRUPO_TECNICO.
    if "grupo_tecnico_filtro" not in df_export.columns:
        try:
            df_export["grupo_tecnico_filtro"] = [grupo_tecnico_filtro_produto(p) for p in produtos_preservados]
        except Exception:
            df_export["grupo_tecnico_filtro"] = ""

    # Coluna auxiliar do Baú de Componentes Compartilhados.
    try:
        df_export["disponivel_no_bau_componentes"] = ["Sim" if produto_disponivel_no_bau_componentes(p) else "Não" for p in produtos_preservados]
    except Exception:
        df_export["disponivel_no_bau_componentes"] = "Não"

    colunas_preferidas = [
        "id",
        "codigo_interno",
        "codigo_barras",
        "nome",
        "grupo_produto",
        "tipo_produto",
        "modelo_tecnico",
        "grupo_tecnico",
        "grupo_tecnico_filtro",
        "disponivel_no_bau_componentes",
        "familia_tecnica",
        "cor_componente",
        "linha",
        "modelo",
        "tipo_cortina_persiana",
        "material_tecido",
        "cor",
        "unidade_venda",
        "valor_custo",
        "custo_final",
        "margem_lucro",
        "valor_venda",
        "estoque_atual",
        "estoque_minimo",
        "estoque_maximo",
        "situacao",
        "ativo",
    ]

    colunas_existentes = [c for c in colunas_preferidas if c in df_export.columns]
    outras_colunas = [c for c in df_export.columns if c not in colunas_existentes]
    df_export = df_export[colunas_existentes + outras_colunas]

    return df_export.to_csv(index=False, sep=";", encoding="utf-8-sig")


def produto_com_termos_preservados(produto):
    if not isinstance(produto, dict):
        return produto
    return preservar_payload_termos_comerciais(dict(produto))


def lista_produtos_com_termos_preservados(produtos):
    return [produto_com_termos_preservados(p) for p in (produtos or [])]


def buscar_produto_por_id(id_produto):
    produtos = buscar_produtos_api()

    for produto in produtos:
        if int(produto.get("id", 0)) == int(id_produto):
            return produto

    return {}


def carregar_opcoes_categoria(categoria, incluir_vazio=True, padrao=None):
    """
    Carrega nomes das opções auxiliares por categoria.
    Retorna uma lista pronta para usar em st.selectbox.
    """
    opcoes = []

    if incluir_vazio:
        opcoes.append("Selecione...")

    try:
        resp = get_opcoes_auxiliares_por_categoria(categoria)

        if resp is not None and resp.status_code == 200:
            dados = resp.json()

            if isinstance(dados, list):
                # Ordena pela coluna ordem e depois por nome, quando existir
                dados = sorted(
                    dados,
                    key=lambda item: (
                        int(item.get("ordem") or 0),
                        str(item.get("nome") or "").lower(),
                    ),
                )

                for item in dados:
                    if str(item.get("situacao", "Ativo")).strip().lower() == "ativo":
                        nome = str(item.get("nome") or "").strip()
                        if nome and nome not in opcoes:
                            opcoes.append(nome)

    except Exception:
        pass

    if padrao and padrao not in opcoes:
        opcoes.append(padrao)

    return opcoes


def selectbox_opcao_auxiliar_com_novo(
    label,
    categoria,
    valor_atual="",
    incluir_vazio=True,
    padrao=None,
    disabled=False,
    key_base="",
):
    """
    Selectbox padrão com cadastro rápido de nova opção auxiliar.
    A opção nova entra na categoria informada e já pode ser usada após o cadastro.

    Exemplo:
    grupo_produto = selectbox_opcao_auxiliar_com_novo(
        "Grupo do produto",
        "grupo_produto",
        valor_atual=produto_atual.get("grupo_produto"),
        key_base="grupo_produto_adicionar"
    )
    """
    opcoes = carregar_opcoes_categoria(categoria, incluir_vazio=incluir_vazio, padrao=padrao)

    marcador_novo = "➕ Adicionar novo..."
    if not disabled and marcador_novo not in opcoes:
        opcoes.append(marcador_novo)

    valor = str(valor_atual or "").strip()

    if not valor and padrao:
        valor = str(padrao).strip()

    if valor and valor not in opcoes:
        opcoes.append(valor)

    indice = opcoes.index(valor) if valor in opcoes else 0

    escolha = st.selectbox(
        label,
        opcoes,
        index=indice,
        disabled=disabled,
        key=f"{key_base}_{categoria}_select",
    )

    if escolha != marcador_novo:
        return escolha

    with st.container():
        st.markdown(
            """
            <div style="border:1px solid #d1d5db;background:#ffffff;border-radius:6px;padding:12px;margin-top:8px;margin-bottom:10px;">
                <div style="font-weight:700;color:#111827;margin-bottom:8px;">➕ Adicionar novo</div>
            """,
            unsafe_allow_html=True,
        )

        novo_nome = st.text_input(
            "Nome da nova opção",
            key=f"{key_base}_{categoria}_novo_nome",
            placeholder=f"Digite o novo {label.lower()}",
        )

        salvar_novo = st.button(
            "Cadastrar",
            type="primary",
            key=f"{key_base}_{categoria}_salvar_novo",
            use_container_width=True,
        )

        cancelar_novo = st.button(
            "Cancelar",
            key=f"{key_base}_{categoria}_cancelar_novo",
            use_container_width=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        if cancelar_novo:
            st.rerun()

        if salvar_novo:
            nome_limpo = str(novo_nome or "").strip()

            if not nome_limpo:
                st.warning("Digite o nome da nova opção.")
                st.stop()

            payload = {
                "categoria": categoria,
                "nome": nome_limpo,
                "descricao": "",
                "tipo_campo": "Texto",
                "obrigatorio": "Não",
                "situacao": "Ativo",
                "ordem": 0,
            }

            try:
                resp = criar_opcao_auxiliar(payload)

                if resp is not None and resp.status_code in [200, 201, 204]:
                    st.session_state.mensagem_acao_produtos = f"✅ Nova opção '{nome_limpo}' cadastrada com sucesso."
                    st.rerun()

                status = resp.status_code if resp is not None else "sem resposta"
                st.error(f"Não foi possível cadastrar a nova opção. Status: {status}")
                try:
                    st.code(resp.text)
                except Exception:
                    pass
                st.stop()

            except Exception as erro:
                st.error(f"Erro ao cadastrar nova opção: {erro}")
                st.stop()

    return "Selecione..."


def indice_select(opcoes, valor_atual, padrao=None):
    """
    Retorna o índice seguro para selectbox.
    Se o valor atual não existir na lista, adiciona no final para não perder dado antigo.
    """
    valor = str(valor_atual or "").strip()

    if not valor and padrao:
        valor = str(padrao).strip()

    if valor and valor not in opcoes:
        opcoes.append(valor)

    if valor in opcoes:
        return opcoes.index(valor)

    return 0


def valor_select_payload(valor):
    """
    Converte o placeholder visual do select em None antes de salvar no banco.
    """
    valor = str(valor or "").strip()
    if not valor or valor == "Selecione...":
        return None
    return valor


def normalizar_bool_varia_cor(valor):
    texto = str(valor or "").strip().lower()
    return texto in ["sim", "s", "true", "1", "yes", "y"]


def normalizar_familia_tecnica(valor):
    texto = normalizar_busca_motor(valor)
    texto = texto.replace(" ", "_")
    return texto if texto and texto not in ["SELECIONE", "SELECIONE..."] else None


def normalizar_modelo_tecnico(valor):
    texto = normalizar_busca_motor(valor)
    texto = texto.replace(" ", "_")
    return texto if texto and texto not in ["SELECIONE", "SELECIONE..."] else None


def normalizar_grupo_tecnico(valor):
    texto = normalizar_busca_motor(valor)
    texto = texto.replace(" ", "_")

    # SmartTec v15:
    # SEM_GRUPO_TECNICO não é um grupo real; é apenas marcador visual/filtro.
    # Se esse texto ficou salvo no banco em alguma rodada anterior, tratamos como vazio
    # para permitir que as regras automáticas infiram o grupo correto.
    if texto in [
        "", "SELECIONE", "SELECIONE...", "SEM_GRUPO", "SEM_GRUPO_TECNICO",
        "SEM_GRUPO_TÉCNICO", "SEM_GRUPO_TECN", "NENHUM", "NAO_INFORMADO", "NÃO_INFORMADO"
    ]:
        return None

    # Produto final Rolô: padronizar como PERSIANA_ROLO para aparecer claramente nos filtros.
    # Mantemos suporte a ROLO como legado em funções antigas.
    if texto in ["ROLO", "ROLÔ", "PERSIANA_ROLO", "PERSIANA_ROLÔ"]:
        return "PERSIANA_ROLO"

    # Unificação decidida: o mesmo tecido atende Rolô, Romana e Painel.
    if texto in ["TECIDOS_ROLO", "TECIDOS_ROMANA", "TECIDOS_PAINEL"]:
        return "TECIDOS_ROLO_ROMANA_PAINEL"

    # Correção conceitual: vertical/horizontal usam lâminas, não tecido.
    if texto in ["LAMINAS_VERTICAL", "TECIDOS_PERSIANA_VERTICAL"]:
        return "LAMINAS_VERTICAL"
    if texto in ["TECIDOS_HORIZONTAL", "TECIDOS_PERSIANA_HORIZONTAL"]:
        return "LAMINAS_HORIZONTAL"

    # Baús compartilhados: continuam sendo Grupo Técnico para não criar mais um campo no banco.
    if texto in [
        "BAU_COMPONENTES", "BAU_COMPONENTES_PERSIANAS", "BAU_PERSIANA",
        "COMPONENTES_COMPARTILHADOS_PERSIANAS", "COMPARTILHADOS_PERSIANAS"
    ]:
        return "BAU_PERSIANAS"

    if texto in ["BAU_COMPONENTES_CORTINAS", "BAU_CORTINA", "COMPARTILHADOS_CORTINAS"]:
        return "BAU_CORTINAS"

    if texto in [
        "BAU_COMPONENTES_EXTERNA", "BAU_EXTERNA", "BAU_TOLDO", "BAU_TOLDOS",
        "COMPARTILHADOS_EXTERNA", "COMPARTILHADOS_TOLDOS"
    ]:
        return "BAU_EXTERNA"

    if texto in ["BAU_MOTOR", "BAU_MOTORES", "COMPARTILHADOS_MOTORES"]:
        return "BAU_MOTORES"

    return texto


def inferir_modelo_tecnico_produto(produto):
    """Define o modelo técnico do produto sem depender de família técnica."""
    texto = texto_produto_motor(produto or {})

    if any(t in texto for t in ["DOUBLE VISION", "DUPLA VISAO", "DUPLA VISÃO", "VISION", "DV "]):
        return "DOUBLE_VISION"
    if any(t in texto for t in ["ROLO", "ROLÔ", "ROLO ", "ROLÔ "]):
        return "ROLO"
    if "ROMANA" in texto:
        return "ROMANA"
    if "PAINEL" in texto:
        return "PAINEL"
    if "TOLDO" in texto:
        return "TOLDO"
    if "EXTERNA" in texto:
        return "EXTERNA"
    if "CORTINA" in texto or "TRILHO" in texto:
        return "CORTINA"

    return None


def inferir_grupo_tecnico_produto(produto):
    """
    Agrupa o cadastro para evitar mistura entre modelos.

    Regras SmartTec:
    - Tecidos de Rolô/Romana/Painel ficam unificados em TECIDOS_ROLO_ROMANA_PAINEL.
    - Componentes mecânicos continuam separados por modelo.
    - Tecidos de cortina ficam em TECIDOS_CORTINAS.
    - Componentes de cortina ficam em COMPONENTES_CORTINAS.
    - Motores e acessórios de motor continuam globais.
    """
    produto = produto or {}
    grupo_salvo = normalizar_grupo_tecnico(produto.get("grupo_tecnico"))
    if grupo_salvo:
        return grupo_salvo

    texto = texto_produto_motor(produto)
    tipo = normalizar_busca_motor(produto.get("tipo_produto"))
    modelo = normalizar_modelo_tecnico(produto.get("modelo_tecnico")) or inferir_modelo_tecnico_produto(produto)

    # Produto final padronizado.
    if "CORTINA DOUBLE VISION" in texto or texto.strip().startswith("PERSIANA DOUBLE VISION"):
        return "PERSIANA_DOUBLE_VISION"

    # Produto final Rolô: não deixar cair como COMPONENTES_ROLO.
    if (texto.strip().startswith("ROLO") or texto.strip().startswith("ROLÔ") or texto.strip().startswith("PERSIANA ROLO") or texto.strip().startswith("PERSIANA ROLÔ")) and "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto):
        return "PERSIANA_ROLO"

    # Persiana Horizontal: material principal é lâmina, não tecido.
    if any(t in texto for t in PALAVRAS_LAMINAS_HORIZONTAL):
        if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto):
            return "PERSIANA_HORIZONTAL"
        return "LAMINAS_HORIZONTAL"

    if any(t in texto for t in PALAVRAS_COMPONENTES_HORIZONTAL):
        return "COMPONENTES_HORIZONTAL"

    # Plissada, Celular e Shangri-lá: material principal é tecido.
    if any(t in texto for t in PALAVRAS_TECIDO_PLISSADA):
        if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto):
            return "PERSIANA_PLISSADA"
        return "TECIDOS_PLISSADA"

    if any(t in texto for t in PALAVRAS_TECIDO_CELULAR):
        if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto):
            return "PERSIANA_CELULAR"
        return "TECIDOS_CELULAR"

    if any(t in texto for t in PALAVRAS_TECIDO_SHANGRILA):
        if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto):
            return "PERSIANA_SHANGRILA"
        return "TECIDOS_SHANGRILA"

    if any(t in texto for t in PALAVRAS_COMPONENTES_EXTERNA):
        if "PERSIANA EXTERNA" in texto and "PRODUTO FABRICADO" in tipo:
            return "PERSIANA_EXTERNA"
        return "COMPONENTES_EXTERNA"

    # Regras cirúrgicas v18 vindas da revisão manual dos órfãos.
    if any(t in texto for t in PALAVRAS_COMPONENTES_VERTICAL):
        return "COMPONENTES_VERTICAL"

    if any(t in texto for t in PALAVRAS_COMPONENTES_HORIZONTAL):
        return "COMPONENTES_HORIZONTAL"

    if any(t in texto for t in PALAVRAS_COMPONENTES_CORTINA):
        return "COMPONENTES_CORTINAS"

    if any(t in texto for t in PALAVRAS_COMPONENTES_ROLO_ESPECIFICAS):
        return "COMPONENTES_ROLO"

    # Tapeçaria / Movelaria.
    if any(t in texto for t in ["ACQUABLOCK", "AQUABLOCK", "ACQUA BLOCK", "NAUTICO", "NÁUTICO", "COURVIN", "CORINO", "COURO", "SINTETICO", "SINTÉTICO", "VELUDO", "CHENILLE", "JACQUARD", "TAPEÇARIA", "TAPECARIA", "ESTOFADO", "MOVELARIA"]):
        return "TECIDOS_TAPECARIA"

    # Motores e acessórios são globais.
    if "MOTOR" in texto and not any(t in texto for t in [
        "CONTROLE", "RECEPTOR", "FONTE", "BATERIA", "CARREGADOR", "HUB", "WIFI",
        "CENTRAL", "MODULO", "MÓDULO", "COROA", "PONTA OPOSTA", "ADAPTADOR"
    ]):
        return "MOTORES"

    if any(t in texto for t in [
        "CONTROLE", "RECEPTOR", "FONTE", "BATERIA", "CARREGADOR", "HUB", "WIFI",
        "CENTRAL", "MODULO", "MÓDULO", "PONTE WIFI", "RF", "COROA MOTOR", "PONTA OPOSTA MOTOR",
        "ADAPTADOR MOTOR", "ACESSORIO MOTOR", "ACESSÓRIO MOTOR"
    ]):
        return "ACESSORIOS_MOTOR"

    # Regra v15: se o cadastro comercial já diz que é tecido de persiana,
    # classifica como tecido unificado para Rolô/Romana/Painel, mesmo quando
    # o nome não contém uma palavra-chave conhecida.
    grupo_comercial = normalizar_busca_motor(produto.get("grupo_produto"))
    material_cadastro = normalizar_busca_motor(produto.get("material_tecido"))
    tipo_cortina_persiana = normalizar_busca_motor(produto.get("tipo_cortina_persiana"))

    if any(t in grupo_comercial for t in ["TECIDO", "TECIDOS"]) or "TECIDO PARA PERSIANA" in texto or "TECIDO PARA PERSIANA" in tipo_cortina_persiana:
        if "DOUBLE VISION" in texto:
            return "TECIDOS_DOUBLE_VISION"
        if any(t in texto for t in ["VOIL", "VOILE", "GASE", "GAZE", "FORRO", "CORTINA"]):
            return "TECIDOS_CORTINAS"
        if any(t in texto for t in ["LAMINA", "LÂMINA", "VERTICAL"]):
            return "LAMINAS_VERTICAL"
        if any(t in texto for t in ["TOLDO", "LONA"]):
            return "TECIDOS_TOLDO"
        return "TECIDOS_ROLO_ROMANA_PAINEL"

    # Tecidos reais. Bloqueia componentes que têm o nome do modelo no cadastro.
    eh_tecido = any(t in texto for t in [
        "TECIDO", "SCREEN", "BLACKOUT", "LINHO", "NOBLETE", "GAZE", "GASE", "VOIL",
        "LUGANO", "NAPOLES", "NÁPOLES", "BRISK", "PRESTIGE", "SOLAR", "DOUBLE VISION", "RUSTICO", "RÚSTICO", "TRANSLUCIDO", "TRANSLÚCIDO", "LONA"
    ])
    eh_componente = any(t in texto for t in [
        "TUBO", "BASE", "COMANDO", "CORRENTE", "TAMPA", "SUPORTE", "PONTEIRA", "KIT", "TRILHO",
        "PERFIL", "EIXO", "PDA", "COMP", "COMPONENTE", "RODIZIO", "RODÍZIO", "CARRINHO",
        "VARETA", "CORDÃO", "CORDAO", "FITA", "ESPAGUETE", "MACARRAO", "MACARRÃO", "VARAO", "VARÃO"
    ])

    if eh_tecido and not eh_componente:
        if modelo == "DOUBLE_VISION" or "DOUBLE VISION" in texto:
            return "TECIDOS_DOUBLE_VISION"
        if "LAMINA" in texto or "LÂMINA" in texto or "TECIDO VERTICAL" in texto:
            return "LAMINAS_VERTICAL"
        if modelo == "CORTINA" or "CORTINA" in texto or "VOIL" in texto or "GAZE" in texto or "GASE" in texto or "FORRO" in texto:
            return "TECIDOS_CORTINAS"
        if modelo == "TOLDO" or "TOLDO" in texto or "LONA" in texto:
            return "TECIDOS_TOLDO"
        if modelo == "EXTERNA" or "EXTERNA" in texto:
            return "TECIDOS_EXTERNA"
        # SmartTec: Screen, BK, Blackout, Translúcido, Nápoles, Brisk, Prestige etc.
        # servem para Rolô, Romana e Painel. Mantemos uma fonte única para o motor.
        return "TECIDOS_ROLO_ROMANA_PAINEL"

    # Componentes mecânicos por modelo.
    if modelo == "DOUBLE_VISION" or "DOUBLE VISION" in texto:
        return "COMPONENTES_DOUBLE_VISION"
    if modelo == "ROMANA" or "ROMANA" in texto:
        return "COMPONENTES_ROMANA"
    if modelo == "PAINEL" or "PAINEL" in texto:
        return "COMPONENTES_PAINEL"
    if modelo == "CORTINA" or "CORTINA" in texto or "TRILHO" in texto or "VARAO" in texto or "VARÃO" in texto:
        return "COMPONENTES_CORTINAS"
    if modelo == "TOLDO" or "TOLDO" in texto:
        return "COMPONENTES_TOLDO"
    if modelo == "EXTERNA" or "EXTERNA" in texto:
        return "COMPONENTES_EXTERNA"
    if modelo == "ROLO" or any(t in texto for t in ["ROLO", "ROLÔ"]):
        return "COMPONENTES_ROLO"

    return None


def grupo_tecnico_label(produto):
    return normalizar_grupo_tecnico((produto or {}).get("grupo_tecnico")) or inferir_grupo_tecnico_produto(produto) or ""


def grupo_tecnico_filtro_produto(produto):
    """Valor usado nos filtros e relatórios da listagem.

    Importante: quando o produto não tem grupo técnico salvo nem inferido,
    mostramos SEM_GRUPO_TECNICO. Assim o usuário consegue filtrar e tratar
    exatamente os itens que aparecem no resumo do saneamento.
    """
    grupo = normalizar_grupo_tecnico((produto or {}).get("grupo_tecnico"))
    if grupo:
        return grupo

    grupo = grupo_tecnico_label(produto)
    if grupo:
        return grupo

    return "SEM_GRUPO_TECNICO"


def montar_opcoes_grupo_tecnico_filtro(produtos=None):
    """Monta opções dinâmicas de Grupo Técnico para filtros.

    Sempre inclui SEM_GRUPO_TECNICO quando houver registros vazios/não inferidos.
    Isso evita o problema de o resumo mostrar pendências, mas a busca não permitir abrir a lista.
    """
    if produtos is None:
        try:
            produtos = buscar_produtos_api()
        except Exception:
            produtos = []

    grupos = set()
    tem_sem_grupo = False

    for produto in produtos or []:
        if not isinstance(produto, dict):
            continue
        grupo = grupo_tecnico_filtro_produto(produto)
        if grupo == "SEM_GRUPO_TECNICO":
            tem_sem_grupo = True
        elif grupo:
            grupos.add(grupo)

    opcoes = ["Todos"]
    if tem_sem_grupo:
        opcoes.append("SEM_GRUPO_TECNICO")

    opcoes.extend(sorted(grupos))

    # Segurança: remove duplicados mantendo ordem.
    finais = []
    for item in opcoes:
        if item not in finais:
            finais.append(item)
    return finais


def modelo_tecnico_label(produto):
    return normalizar_modelo_tecnico((produto or {}).get("modelo_tecnico")) or inferir_modelo_tecnico_produto(produto) or ""


# =========================================================
# SANEAMENTO SMARTTEC - CLASSIFICAÇÃO AUTOMÁTICA SEGURA
# Fonte única para limpeza da base antes de aplicar receitas.
# Regra comercial definida com o Warma:
# - DOUBLE VISION sem prefixo é tecido.
# - CORTINA DOUBLE VISION vira PERSIANA DOUBLE VISION.
# - PERSIANA DOUBLE VISION é produto final.
# - Produtos finais importados do GestãoClick recebem grupo técnico de produto final,
#   mas componentes/tecidos nunca recebem receita.
# =========================================================
PALAVRAS_BLOQUEIO_PRODUTO_FINAL = [
    "BANDO", "TUBO", "SUPORTE", "COMANDO", "CORRENTE", "TAMPA", "PONTEIRA",
    "BASE", "PERFIL", "KIT", "MOTOR", "CONTROLE", "RECEPTOR", "FONTE",
    "BATERIA", "CARREGADOR", "TRILHO", "CARRINHO", "RODIZIO", "RODÍZIO",
    "CORDÃO", "CORDAO", "FITA", "ESPAGUETE", "MACARRAO", "MACARRÃO",
]

PALAVRAS_TAPECARIA = [
    "ACQUABLOCK", "AQUABLOCK", "ACQUA BLOCK", "NÁUTICO", "NAUTICO", "COURVIN",
    "CORINO", "COURO", "SINTETICO", "SINTÉTICO", "VELUDO", "CHENILLE", "JACQUARD",
    "SUEDE", "LINHO RÚSTICO", "LINHO RUSTICO", "TAPEÇARIA", "TAPECARIA", "ESTOFADO",
    "ESTOFADOS", "MOVELARIA", "MOVELEIRO", "DECORATIVO", "DECORAÇÃO", "DECORACAO",
]

PALAVRAS_TECIDO_CORTINA = [
    "VOIL", "VOILE", "GASE", "GAZE", "FORRO", "BLACKOUT CORTINA", "LINHO CORTINA",
    "BOREAL", "BAHAMAS", "ECLIPSE", "BÉLGICA", "BELGICA", "FILIPINAS", "COZUMEL",
    "GRÉCIA", "GRECIA", "HORIZONTE", "INFINITE", "IRLANDA", "LISBOA", "MADRI",
    "MIRAGE", "PETRA", "SANTORINI", "TÓQUIO", "TOQUIO", "TOSCANA", "CORTINA TECIDO",
]

PALAVRAS_TECIDO_ROLO = [
    # Tecidos comuns para Rolô/Romana/Painel
    "SCREEN", "BLACKOUT", "BK", "TRANSLUCIDO", "TRANSLÚCIDO", "SOLAR",
    "NÁPOLES", "NAPOLES", "BRISK", "PRESTIGE", "NOBLETE", "LUGANO",
    "RÚSTICO", "RUSTICO", "SHANTUNG", "HOUSTON", "EGITO", "FLORENÇA",
    "FLORENCA", "LISBOA BK", "MYSTIC", "VENICE", "VIENA", "ARUBA",
    "DENVER", "FIGUEIRA", "SIDNEY", "XADREZ", "NATURAL BK",
    "PIMPOINT", "TJ ", "TJ-", "JPTEC", "TECNO", "PARIS", "DUBAI", "MÔNACO", "MONACO",
    # Códigos/nomes internos importados JPTEC e fornecedor Ação
    "TEC ", "TECIDO ROLO", "TECIDO SCREEN", "TECIDO BLACKOUT", "TEC BK",
    "TEC BRISK", "TEC PRESTIGE", "TEC LUGANO", "TEC NAPOLES", "TEC NÁPOLES",
]

PALAVRAS_LAMINAS_HORIZONTAL = [
    "PH 16", "PH16", "PH 25", "PH25", "PH 50", "PH50",
    "HORIZONTAL", "LAMINA HORIZONTAL", "LÂMINA HORIZONTAL",
    "LAMINA ALUMINIO", "LÂMINA ALUMINIO", "LAMINA ALUMÍNIO", "LÂMINA ALUMÍNIO",
    "LAMINA PVC 16", "LAMINA PVC 25", "LAMINA PVC 50",
    "LÂMINA PVC 16", "LÂMINA PVC 25", "LÂMINA PVC 50",
    "LAMINA MADEIRA", "LÂMINA MADEIRA", "LAMINA BAMBOO", "LÂMINA BAMBOO", "BAMBOO",
]

PALAVRAS_COMPONENTES_HORIZONTAL = [
    "BOTAO ENTRE VIDROS", "BOTÃO ENTRE VIDROS", "ENTRE VIDROS",
    "BASTAO", "BASTÃO", "ESCADINHA", "CADARCO", "CADARÇO",
    "FREIO", "COMANDO HORIZONTAL", "SUPORTE HORIZONTAL",
    "SUPORTE LATERAL", "SUPORTE LATERAL DE 50MM",
    "PONTEIRA HORIZONTAL", "BOTAO PH", "BOTÃO PH", "PH ", "PH16", "PH25", "PH50",
    "GIRATORIO", "GIRATÓRIO", "CAVALETE", "16/25MM", "16/25", "25MM", "50MM",
    "TRAVA DA FITA", "PARADA 3 PINOS", "PARADA 50MM", "TAMPA DA CABECEIRA", "TAMPA DO CAVALETE",
]

PALAVRAS_TECIDO_PLISSADA = [
    "PLISSADA", "PLISSADO", "TECIDO PLISSADA", "TECIDO PLISSADO",
]

PALAVRAS_TECIDO_CELULAR = [
    "CELULAR", "HONEYCOMB", "HONEY COMB", "CELLULAR",
]

PALAVRAS_TECIDO_SHANGRILA = [
    "SHANGRILLA", "SHANGRI-LA", "SHANGRI LA", "SHANGRILÁ", "SHANGRI-LÁ",
]

PALAVRAS_COMPONENTES_PLISSADA = [
    "PERFIL PLISSADA", "PERFIL PLISSADO", "COMPONENTE PLISSADA", "COMPONENTE PLISSADO",
    "SUPORTE PLISSADA", "SUPORTE PLISSADO", "CORDÃO PLISSADA", "CORDAO PLISSADA",
]

PALAVRAS_COMPONENTES_CELULAR = [
    "PERFIL CELULAR", "COMPONENTE CELULAR", "SUPORTE CELULAR", "CORDÃO CELULAR", "CORDAO CELULAR",
]

PALAVRAS_COMPONENTES_SHANGRILA = [
    "PERFIL SHANGRILLA", "COMPONENTE SHANGRILLA", "SUPORTE SHANGRILLA",
    "SHANGRILLA", "SHANGRI-LA", "SHANGRI LA",
]

PALAVRAS_COMPONENTES_EXTERNA = [
    "OCTAGONAL", "SEXTAVADO", "TUBO OCT", "TUBO SEXT",
    "PONTA OPOSTA OCTAGONAL", "PONTA OPOSTA SEXTAVADO",
    "COROA OCTAGONAL", "COROA SEXTAVADO", "MANCAL", "REDUTOR",
    "PERSIANA EXTERNA", "EXTERNA",
]

PALAVRAS_LAMINAS_VERTICAL = [
    "LAMINA 89", "LÂMINA 89", "LAMINA 90", "LÂMINA 90",
    "LAMINA VERTICAL", "LÂMINA VERTICAL", "LAMINA PVC VERTICAL", "LÂMINA PVC VERTICAL",
    "LAMINA TECIDO VERTICAL", "LÂMINA TECIDO VERTICAL", "TECIDO VERTICAL",
]

PALAVRAS_COMPONENTES_VERTICAL = [
    "BASTAO VERTICAL", "BASTÃO VERTICAL", "CARRINHO VERTICAL", "TRILHO VERTICAL", "PESO VERTICAL",
    "CORRENTE VERTICAL", "COMANDO VERTICAL", "SUPORTE VERTICAL", "GANCHO VERTICAL",
    "PENDULO PARA VERTICAL", "PÊNDULO PARA VERTICAL", "PENDULO VERTICAL", "PÊNDULO VERTICAL",
    "PESO BALASTRO", "LAMELA DO CARRINHO PARA VERTICAL", "CORDA P/ PERSIANA VERTICAL",
    "CORDA PARA PERSIANA VERTICAL", "CORDAS VERTICAL", "CORDA VERTICAL",
]

PALAVRAS_COMPONENTES_CORTINA = [
    "TRILHO", "CARRINHO", "RODIZIO", "RODÍZIO", "ILHOS", "ILHÓS",
    "ARGOLA", "VARÃO", "VARAO", "PONTEIRA VARAO", "SUPORTE VARAO", "GANCHO", "FRANZIDOR",
    "ABRAÇADEIRA", "ABRACADEIRA", "ACESSÓRIO CORTINA", "ACESSORIO CORTINA",
    "VELCRO",
]

PALAVRAS_COMPONENTES_ROLO_ESPECIFICAS = [
    "TAMPA BANDO", "TAMPA P/ BANDO", "TAMPA DO BANDO",
    "PENDULO CRISTAL", "PÊNDULO CRISTAL",
    "PENDULO TOP", "PÊNDULO TOP", "PENDULO", "PÊNDULO",
    "PESTANA PARA GUIA", "PESTANA GUIA", "PESTANA",
    "FITA PLASTICA", "FITA PLÁSTICA", "FITA P/ BASE",
    "DESLIZANTE P/ BARRA ESTABILIZADORA", "DESLIZANTE PARA BARRA ESTABILIZADORA",
    "BARRA ESTABILIZADORA",
    "CONECTOR PLASTICO", "CONECTOR PLÁSTICO", "CONECTOR",
    "TAMPA P/ FITA", "TAMPA PARA FITA",
    "CLIP X DE FIXACAO P/ GUIA LATERAL", "CLIP X DE FIXAÇÃO P/ GUIA LATERAL",
]


def texto_produto_saneamento(produto):
    produto = produto or {}
    partes = [
        produto.get("nome"), produto.get("grupo_produto"), produto.get("tipo_produto"),
        produto.get("linha"), produto.get("modelo"), produto.get("material_tecido"),
        produto.get("descricao"), produto.get("observacoes"), produto.get("grupo_tecnico"),
    ]
    return normalizar_busca_motor(" ".join(str(p or "") for p in partes))


def nome_comeca_com_modelo_final(texto):
    texto = normalizar_busca_motor(texto)
    return any(texto.startswith(prefixo) for prefixo in [
        "ROLO", "ROLÔ", "ROMANA", "PAINEL", "PERSIANA DOUBLE VISION", "CORTINA",
    ])


def contem_palavra_bloqueio_produto_final(texto):
    texto = normalizar_busca_motor(texto)
    return any(p in texto for p in PALAVRAS_BLOQUEIO_PRODUTO_FINAL)


def parece_produto_final_gestaoclick(produto):
    """Identifica produtos finais vindos do GestãoClick sem aplicar receita em componentes."""
    produto = produto or {}
    nome = normalizar_busca_motor(produto.get("nome"))
    grupo = normalizar_busca_motor(produto.get("grupo_produto"))
    tipo = normalizar_busca_motor(produto.get("tipo_produto"))

    if contem_palavra_bloqueio_produto_final(nome):
        return False

    if "PRODUTO FABRICADO" in tipo:
        if nome_comeca_com_modelo_final(nome):
            return True
        if grupo in ["ROLO", "ROLÔ", "ROMANA", "PAINEL", "PERSIANAS", "PERSIANA", "CORTINA"]:
            return True

    return False


def classificar_saneamento_produto(produto):
    """
    Retorna (updates, motivos) para saneamento seguro da base.
    Não altera banco sozinho; a tela de saneamento mostra prévia antes de aplicar.
    """
    produto = dict(produto or {})
    updates = {}
    motivos = []

    nome_original = str(produto.get("nome") or "").strip()
    nome = normalizar_busca_motor(nome_original)
    texto = texto_produto_saneamento(produto)
    tipo = normalizar_busca_motor(produto.get("tipo_produto"))
    grupo_atual = str(produto.get("grupo_produto") or "").strip()
    grupo_tecnico_atual = normalizar_grupo_tecnico(produto.get("grupo_tecnico"))

    # 1) Padronização comercial: CORTINA DOUBLE VISION = PERSIANA DOUBLE VISION.
    if "CORTINA DOUBLE VISION" in nome:
        novo_nome = re.sub(r"(?i)\bCORTINA\s+DOUBLE\s+VISION\b", "PERSIANA DOUBLE VISION", nome_original).strip()
        if novo_nome and novo_nome != nome_original:
            updates["nome"] = novo_nome
            motivos.append("Renomear CORTINA DOUBLE VISION para PERSIANA DOUBLE VISION")
        updates["grupo_produto"] = "Persianas"
        updates["grupo_tecnico"] = "PERSIANA_DOUBLE_VISION"
        updates["tipo_produto"] = "Produto fabricado"
        return updates, motivos or ["Produto final Persiana Double Vision"]

    # 2) Produto final Persiana Double Vision.
    if nome.startswith("PERSIANA DOUBLE VISION"):
        updates["grupo_produto"] = "Persianas"
        updates["grupo_tecnico"] = "PERSIANA_DOUBLE_VISION"
        updates["tipo_produto"] = "Produto fabricado"
        motivos.append("Produto final Persiana Double Vision")
        return updates, motivos

    # 3) DOUBLE VISION sem prefixo é tecido, desde que não seja componente mecânico.
    if "DOUBLE VISION" in nome and not nome.startswith("PERSIANA DOUBLE VISION"):
        if not any(p in texto for p in ["TUBO", "COMANDO", "SUPORTE", "TAMPA", "PONTEIRA", "KIT", "BASE", "PERFIL", "CORRENTE"]):
            updates["grupo_produto"] = "Tecidos"
            updates["grupo_tecnico"] = "TECIDOS_DOUBLE_VISION"
            if "PRODUTO FABRICADO" not in tipo:
                updates["tipo_produto"] = "Componente"
            motivos.append("Tecido Double Vision")
            return updates, motivos
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_DOUBLE_VISION"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Double Vision")
        return updates, motivos

    # 4) Produtos finais clássicos do GestãoClick: não mexer no nome, só preparar para receita futura.
    if parece_produto_final_gestaoclick(produto):
        if nome.startswith(("ROLO", "ROLÔ", "PERSIANA ROLO", "PERSIANA ROLÔ")):
            updates["grupo_tecnico"] = "PERSIANA_ROLO"
            updates["grupo_produto"] = grupo_atual or "Persianas"
            motivos.append("Produto final Rolô")
        elif nome.startswith("ROMANA"):
            updates["grupo_tecnico"] = "ROMANA"
            updates["grupo_produto"] = grupo_atual or "Persianas"
            motivos.append("Produto final Romana")
        elif nome.startswith("PAINEL"):
            updates["grupo_tecnico"] = "PAINEL"
            updates["grupo_produto"] = grupo_atual or "Persianas"
            motivos.append("Produto final Painel")
        elif nome.startswith("CORTINA"):
            updates["grupo_tecnico"] = "CORTINA"
            updates["grupo_produto"] = grupo_atual or "Cortinas"
            motivos.append("Produto final Cortina")
        if updates:
            updates["tipo_produto"] = "Produto fabricado"
            return updates, motivos

    # 4.5) Novas famílias de persianas identificadas nos órfãos.
    # Horizontal usa LÂMINAS; Plissada/Celular/Shangri-lá usam TECIDO.
    if any(p in texto for p in PALAVRAS_LAMINAS_HORIZONTAL):
        updates["grupo_produto"] = "Persianas" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "Lâminas"
        updates["grupo_tecnico"] = "PERSIANA_HORIZONTAL" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "LAMINAS_HORIZONTAL"
        updates["tipo_produto"] = "Produto fabricado" if updates["grupo_tecnico"] == "PERSIANA_HORIZONTAL" else "Componente"
        motivos.append("Persiana Horizontal / Lâminas Horizontal")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_HORIZONTAL):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_HORIZONTAL"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Persiana Horizontal")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_TECIDO_PLISSADA):
        updates["grupo_produto"] = "Persianas" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "Tecidos"
        updates["grupo_tecnico"] = "PERSIANA_PLISSADA" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "TECIDOS_PLISSADA"
        updates["tipo_produto"] = "Produto fabricado" if updates["grupo_tecnico"] == "PERSIANA_PLISSADA" else "Componente"
        motivos.append("Persiana/Tecido Plissada")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_TECIDO_CELULAR):
        updates["grupo_produto"] = "Persianas" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "Tecidos"
        updates["grupo_tecnico"] = "PERSIANA_CELULAR" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "TECIDOS_CELULAR"
        updates["tipo_produto"] = "Produto fabricado" if updates["grupo_tecnico"] == "PERSIANA_CELULAR" else "Componente"
        motivos.append("Persiana/Tecido Celular")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_TECIDO_SHANGRILA):
        updates["grupo_produto"] = "Persianas" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "Tecidos"
        updates["grupo_tecnico"] = "PERSIANA_SHANGRILA" if "PRODUTO FABRICADO" in tipo and not contem_palavra_bloqueio_produto_final(texto) else "TECIDOS_SHANGRILA"
        updates["tipo_produto"] = "Produto fabricado" if updates["grupo_tecnico"] == "PERSIANA_SHANGRILA" else "Componente"
        motivos.append("Persiana/Tecido Shangri-lá")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_PLISSADA):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_PLISSADA"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Plissada")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_CELULAR):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_CELULAR"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Celular")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_SHANGRILA) and not any(p in texto for p in PALAVRAS_TECIDO_SHANGRILA):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_SHANGRILA"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Shangri-lá")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_EXTERNA):
        updates["grupo_produto"] = "Persianas" if "PERSIANA EXTERNA" in texto and "PRODUTO FABRICADO" in tipo else "Componentes"
        updates["grupo_tecnico"] = "PERSIANA_EXTERNA" if updates["grupo_produto"] == "Persianas" else "COMPONENTES_EXTERNA"
        updates["tipo_produto"] = "Produto fabricado" if updates["grupo_tecnico"] == "PERSIANA_EXTERNA" else "Componente"
        motivos.append("Persiana Externa / Componente Externa")
        return updates, motivos

    # 4.5) Regras cirúrgicas v18 vindas da revisão manual dos 76 órfãos.
    if any(p in texto for p in PALAVRAS_COMPONENTES_VERTICAL):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_VERTICAL"
        updates["tipo_produto"] = "Componente"
        updates["situacao"] = "Inativo"
        motivos.append("Componente Vertical inativo - regra v18")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_HORIZONTAL):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_HORIZONTAL"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Horizontal - regra v18")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_CORTINA):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_CORTINAS"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Cortinas - regra v18")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_ROLO_ESPECIFICAS):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_ROLO"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Rolô - regra v18")
        return updates, motivos

    # 5) Persiana Vertical: manter classificada, mas Inativa por baixa saída.
    if any(p in texto for p in PALAVRAS_LAMINAS_VERTICAL):
        updates["grupo_produto"] = "Tecidos"
        updates["grupo_tecnico"] = "LAMINAS_VERTICAL"
        updates["tipo_produto"] = "Componente"
        updates["situacao"] = "Inativo"
        motivos.append("Lâmina Vertical inativa")
        return updates, motivos

    if any(p in texto for p in PALAVRAS_COMPONENTES_VERTICAL):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_VERTICAL"
        updates["tipo_produto"] = "Componente"
        updates["situacao"] = "Inativo"
        motivos.append("Componente Vertical inativo")
        return updates, motivos

    # 6) Tapeçaria / Movelaria Wiler.
    if any(p in texto for p in PALAVRAS_TAPECARIA):
        updates["grupo_produto"] = "Tecidos"
        updates["grupo_tecnico"] = "TECIDOS_TAPECARIA"
        updates["tipo_produto"] = "Componente"
        motivos.append("Tecido Tapeçaria/Movelaria")
        return updates, motivos

    # 6) Tecidos de cortina.
    if any(p in texto for p in PALAVRAS_TECIDO_CORTINA):
        if not any(p in texto for p in PALAVRAS_COMPONENTES_CORTINA):
            updates["grupo_produto"] = "Tecidos"
            updates["grupo_tecnico"] = "TECIDOS_CORTINAS"
            updates["tipo_produto"] = "Componente"
            motivos.append("Tecido Cortinas")
            return updates, motivos

    # 7) Componentes de cortina.
    if any(p in texto for p in PALAVRAS_COMPONENTES_CORTINA):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = "COMPONENTES_CORTINAS"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Cortinas")
        return updates, motivos

    # 7.5) Regra v15 por grupo comercial: derruba órfãos que já vêm com grupo
    # Tecidos/Componentes no cadastro, mas ainda ficaram SEM_GRUPO_TECNICO.
    grupo_cadastro_norm = normalizar_busca_motor(grupo_atual)

    if any(g in grupo_cadastro_norm for g in ["TECIDO", "TECIDOS"]) or "TECIDO PARA PERSIANA" in texto:
        updates["grupo_produto"] = "Tecidos"
        updates["grupo_tecnico"] = "TECIDOS_ROLO_ROMANA_PAINEL"
        updates["tipo_produto"] = "Componente"
        motivos.append("Tecido Rolô/Romana/Painel por grupo comercial")
        return updates, motivos

    if "COMPONENTE" in grupo_cadastro_norm or "COMPONENTES" in grupo_cadastro_norm or "026 - COMPONENTES" in texto or "021 - COMANDOS" in texto or "024 - CLIPS E SUPORTES" in texto:
        updates["grupo_produto"] = "Componentes"
        updates["tipo_produto"] = "Componente"
        if any(p in texto for p in ["ENTRE VIDROS", "DOUBLE VISION", "DOUB VISION", "AC161", "AC162", "AC638"]):
            updates["grupo_tecnico"] = "COMPONENTES_DOUBLE_VISION"
            motivos.append("Componente Double Vision por grupo comercial")
        elif any(p in texto for p in PALAVRAS_COMPONENTES_HORIZONTAL):
            updates["grupo_tecnico"] = "COMPONENTES_HORIZONTAL"
            motivos.append("Componente Horizontal por grupo comercial")
        elif any(p in texto for p in PALAVRAS_COMPONENTES_EXTERNA):
            updates["grupo_tecnico"] = "COMPONENTES_EXTERNA"
            motivos.append("Componente Externa por grupo comercial")
        elif any(p in texto for p in ["BASTAO VERTICAL", "BASTÃO VERTICAL", "LAMINA", "LÂMINA", "VERTICAL"]):
            updates["grupo_tecnico"] = "COMPONENTES_VERTICAL"
            updates["situacao"] = "Inativo"
            motivos.append("Componente Vertical inativo por grupo comercial")
        elif "ROMANA" in texto:
            updates["grupo_tecnico"] = "COMPONENTES_ROMANA"
            motivos.append("Componente Romana por grupo comercial")
        elif "PAINEL" in texto:
            updates["grupo_tecnico"] = "COMPONENTES_PAINEL"
            motivos.append("Componente Painel por grupo comercial")
        elif "TOLDO" in texto:
            updates["grupo_tecnico"] = "COMPONENTES_TOLDO"
            motivos.append("Componente Toldo por grupo comercial")
        elif "EXTERNA" in texto:
            updates["grupo_tecnico"] = "COMPONENTES_EXTERNA"
            motivos.append("Componente Externa por grupo comercial")
        else:
            updates["grupo_tecnico"] = "COMPONENTES_ROLO"
            motivos.append("Componente Rolô/Geral por grupo comercial")
        return updates, motivos

    # 8) Motores e acessórios de motor.
    if "MOTOR" in texto and not any(p in texto for p in ["CONTROLE", "RECEPTOR", "FONTE", "BATERIA", "CARREGADOR", "HUB", "WIFI", "COROA", "PONTA OPOSTA"]):
        updates["grupo_produto"] = "Motorização"
        updates["grupo_tecnico"] = "MOTORES"
        updates["tipo_produto"] = "Componente"
        motivos.append("Motor")
        return updates, motivos

    if any(p in texto for p in ["CONTROLE", "RECEPTOR", "FONTE", "BATERIA", "CARREGADOR", "HUB", "WIFI", "COROA MOTOR", "PONTA OPOSTA MOTOR"]):
        updates["grupo_produto"] = "Motorização"
        updates["grupo_tecnico"] = "ACESSORIOS_MOTOR"
        updates["tipo_produto"] = "Componente"
        motivos.append("Acessório de motor")
        return updates, motivos

    # 9) Tecidos de Rolô, incluindo translúcidos.
    if any(p in texto for p in PALAVRAS_TECIDO_ROLO) and not contem_palavra_bloqueio_produto_final(texto):
        updates["grupo_produto"] = "Tecidos"
        updates["grupo_tecnico"] = "TECIDOS_ROLO_ROMANA_PAINEL"
        updates["tipo_produto"] = "Componente"
        motivos.append("Tecido Rolô/Romana/Painel")
        return updates, motivos

    # 10) Componentes Rolô/gerais.
    if any(p in texto for p in ["TUBO", "COMANDO", "CORRENTE", "SUPORTE", "TAMPA", "PONTEIRA", "BASE", "PERFIL", "KIT", "ESPAGUETE", "FITA"]):
        updates["grupo_produto"] = "Componentes"
        updates["grupo_tecnico"] = grupo_tecnico_atual or "COMPONENTES_ROLO"
        updates["tipo_produto"] = "Componente"
        motivos.append("Componente Rolô/Geral")
        return updates, motivos

    return updates, motivos


def saneamento_precisa_atualizar(produto, updates):
    for campo, novo in (updates or {}).items():
        atual = produto.get(campo)
        if normalizar_busca_motor(atual) != normalizar_busca_motor(novo):
            return True
    return False


def montar_relatorio_saneamento(produtos):
    linhas = []
    resumo = {}
    for produto in produtos or []:
        updates, motivos = classificar_saneamento_produto(produto)
        grupo_tecnico_final = updates.get("grupo_tecnico") or grupo_tecnico_label(produto) or "SEM_GRUPO_TECNICO"
        resumo[grupo_tecnico_final] = resumo.get(grupo_tecnico_final, 0) + 1
        if updates and saneamento_precisa_atualizar(produto, updates):
            linhas.append({
                "id": produto.get("id"),
                "codigo": produto.get("codigo_interno") or produto.get("codigo_barras") or produto.get("id"),
                "nome_atual": produto.get("nome"),
                "novo_nome": updates.get("nome", produto.get("nome")),
                "grupo_atual": produto.get("grupo_produto"),
                "novo_grupo": updates.get("grupo_produto", produto.get("grupo_produto")),
                "grupo_tecnico_atual": produto.get("grupo_tecnico") or grupo_tecnico_label(produto),
                "novo_grupo_tecnico": updates.get("grupo_tecnico", produto.get("grupo_tecnico") or grupo_tecnico_label(produto)),
                "tipo_atual": produto.get("tipo_produto"),
                "novo_tipo": updates.get("tipo_produto", produto.get("tipo_produto")),
                "motivo": "; ".join(motivos),
                "updates": updates,
            })
    return linhas, resumo


def inferir_familia_tecnica_produto(produto):
    """Sugestão segura para preencher família técnica em importações/itens antigos.
    A receita oficial ainda deve ser definida pelo usuário no carrinho.
    """
    texto = texto_produto_motor(produto or {})

    if any(t in texto for t in ["SCREEN", "BLACKOUT", "TECIDO", "DOUBLE VISION", "NOBLETE", "LINHO", "GAZE", "GASE"]):
        if not any(t in texto for t in ["FITA", "BASE", "TUBO", "COMANDO", "CORRENTE", "TAMPA", "EMENDA", "ESPAGUETE"]):
            return "TECIDO"
    if "TUBO" in texto and "38" in texto:
        return "TUBO_38"
    if "TUBO" in texto and "32" in texto:
        return "TUBO_32"
    if any(t in texto for t in ["FITA DUPLA", "FTF", "FITA 20", "FITA 25", "FITA 2 5", "FITA 2,5"]):
        return "FITA_TUBO"
    if "BASE" in texto and any(t in texto for t in ["AC133", "AC 133", "PH 50", "50MM"]):
        return "BASE_AC133"
    if "BASE" in texto and any(t in texto for t in ["AC191", "AC 191"]):
        return "BASE_AC191"
    if "FITA" in texto and "BASE" in texto:
        return "FITA_BASE"
    if any(t in texto for t in ["ESPAGUETE", "MACARRAO", "MACARRÃO"]):
        return "ESPAGUETE_3MM"
    if "CORRENTE" in texto or "CORR" in texto:
        if "EMENDA" in texto or "CONECTOR" in texto:
            return "EMENDA_CORRENTE"
        return "CORRENTE_BOLA10"
    if "TAMPA" in texto and "BASE" in texto:
        return "TAMPA_BASE"
    if "COMANDO" in texto and "38" in texto:
        return "COMANDO_38"
    if "COMANDO" in texto and "32" in texto:
        return "COMANDO_32"
    if "MOTOR" in texto:
        return "MOTOR"
    if "CONTROLE" in texto:
        return "CONTROLE"
    if "TRILHO" in texto:
        return "TRILHO"
    if "SUPORTE" in texto:
        return "SUPORTE"

    return None


def inferir_cor_componente_produto(produto):
    cor_salva = str((produto or {}).get("cor_componente") or "").strip()
    if cor_salva:
        return cor_salva

    texto = texto_produto_motor(produto or {})
    if "PRETO" in texto or "PT" in texto:
        return "Preto"
    if "BRANCO" in texto or "BR " in f" {texto} ":
        return "Branco"
    if "CINZA" in texto:
        return "Cinza"
    if "MARFIM" in texto or "BEGE" in texto:
        return "Marfim"
    if "TUBO" in texto:
        return "Natural"
    if any(t in texto for t in ["ESPAGUETE", "MACARRAO", "MACARRÃO"]):
        return "Incolor"
    return ""


def inferir_varia_cor_componente(produto):
    if "varia_cor" in (produto or {}) and produto.get("varia_cor") is not None:
        return normalizar_bool_varia_cor(produto.get("varia_cor"))

    familia = normalizar_familia_tecnica((produto or {}).get("familia_tecnica")) or inferir_familia_tecnica_produto(produto)
    # Tubo é natural, espaguete é incolor e fitas não variam por cor.
    if familia in ["TUBO_32", "TUBO_38", "ESPAGUETE_3MM", "FITA_TUBO", "FITA_BASE", "TECIDO"]:
        return False
    # Itens aparentes que podem acompanhar a cor escolhida no pedido/orçamento.
    if familia in ["BASE_AC133", "BASE_AC191", "CORRENTE_BOLA10", "EMENDA_CORRENTE", "TAMPA_BASE", "COMANDO_32", "COMANDO_38"]:
        return True
    return False


def moeda_br(valor):
    """
    Formata número no padrão brasileiro.
    """
    try:
        valor = float(valor or 0)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


# =========================================================
# RECEITA TÉCNICA OFICIAL EMBUTIDA NO PRODUTO
# Temporário até criarmos as tabelas próprias no backend.
# Salva a receita em observações com marcador oculto para o clone herdar.
# =========================================================
RECEITA_TECNICA_INICIO = "[[SMARTTEC_RECEITA_TECNICA_JSON]]"
RECEITA_TECNICA_FIM = "[[/SMARTTEC_RECEITA_TECNICA_JSON]]"


def extrair_receita_tecnica_observacoes(observacoes):
    texto = str(observacoes or "")
    if RECEITA_TECNICA_INICIO not in texto or RECEITA_TECNICA_FIM not in texto:
        return []

    try:
        bloco = texto.split(RECEITA_TECNICA_INICIO, 1)[1].split(RECEITA_TECNICA_FIM, 1)[0].strip()
        dados = json.loads(bloco)
        if isinstance(dados, dict):
            dados = dados.get("itens", [])
        if not isinstance(dados, list):
            return []
        return [item for item in dados if isinstance(item, dict)]
    except Exception:
        return []


def remover_receita_tecnica_observacoes(observacoes):
    texto = str(observacoes or "")
    if RECEITA_TECNICA_INICIO not in texto or RECEITA_TECNICA_FIM not in texto:
        return texto.strip()

    antes = texto.split(RECEITA_TECNICA_INICIO, 1)[0]
    depois = texto.split(RECEITA_TECNICA_FIM, 1)[1] if RECEITA_TECNICA_FIM in texto else ""
    return (antes + depois).strip()


def limpar_item_receita_para_salvar(item):
    return {
        "chave": item.get("chave"),
        "categoria_tecnica": item.get("categoria_tecnica"),
        "produto_id": item.get("produto_id"),
        "codigo": item.get("codigo"),
        "nome": item.get("nome"),
        "unidade": item.get("unidade"),
        "custo_unitario": float(item.get("custo_unitario") or 0),
        "familia_tecnica": item.get("familia_tecnica"),
        "varia_cor": bool(item.get("varia_cor")),
        "cor_componente": item.get("cor_componente"),
    }


def embutir_receita_tecnica_observacoes(observacoes, carrinho):
    texto_limpo = remover_receita_tecnica_observacoes(observacoes)
    itens = [limpar_item_receita_para_salvar(item) for item in (carrinho or []) if isinstance(item, dict)]

    if not itens:
        return texto_limpo or None

    payload = {
        "versao": 1,
        "tipo": "receita_tecnica_produto",
        "itens": itens,
    }
    bloco = f"{RECEITA_TECNICA_INICIO}\n{json.dumps(payload, ensure_ascii=False)}\n{RECEITA_TECNICA_FIM}"

    if texto_limpo:
        return f"{texto_limpo}\n\n{bloco}"
    return bloco


def obter_carrinho_receita_session(modo, id_produto):
    """
    Recupera o carrinho/receita da tela atual.

    Correção SmartTec:
    o prefixo do carrinho inclui modo, id, modelo e tipo; em clonagem/edição esse id pode
    variar entre o produto original e o novo registro. Por segurança, só usa carrinhos
    do contexto atual; a última receita da sessão fica apenas como último recurso.
    """
    prefixo = f"{modo}_{id_produto}_"
    chaves = [
        chave for chave in st.session_state.keys()
        if str(chave).startswith(prefixo) and str(chave).endswith("_carrinho_receita_tecnica")
    ]

    if not chaves:
        ultima = st.session_state.get("smarttec_ultima_receita_tecnica")
        return list(ultima or []) if isinstance(ultima, list) else []

    preenchidos = [chave for chave in chaves if st.session_state.get(chave)]
    if preenchidos:
        chave_final = preenchidos[-1]
        carrinho = list(st.session_state.get(chave_final, []))
        if carrinho:
            st.session_state["smarttec_ultima_receita_tecnica"] = [limpar_item_receita_para_salvar(i) for i in carrinho]
        return carrinho

    return []


def produto_mesma_familia_cor(produto, familia_tecnica, cor_componente):
    if not produto:
        return False
    familia_prod = normalizar_familia_tecnica(produto.get("familia_tecnica") or inferir_familia_tecnica_produto(produto))
    familia_ref = normalizar_familia_tecnica(familia_tecnica)
    if familia_ref and familia_prod != familia_ref:
        return False
    cor_ref = normalizar_busca_motor(cor_componente)
    if not cor_ref:
        return True
    cor_prod = normalizar_busca_motor(produto.get("cor_componente") or inferir_cor_componente_produto(produto))
    texto = texto_produto_motor(produto)
    return cor_prod == cor_ref or cor_ref in texto


def procurar_substituto_mesma_familia_cor(produtos, item, cor_componentes):
    if not item or not item.get("varia_cor") or not cor_componentes:
        return None

    familia = item.get("familia_tecnica")
    cor_ref = str(cor_componentes or "").strip()

    candidatos = []
    for produto in produtos or []:
        try:
            if int(produto.get("id") or 0) == int(item.get("produto_id") or 0):
                continue
        except Exception:
            pass

        if produto_mesma_familia_cor(produto, familia, cor_ref):
            candidatos.append(produto)

    if not candidatos:
        return None

    candidatos.sort(key=lambda p: (
        0 if normalizar_busca_motor(p.get("cor_componente") or inferir_cor_componente_produto(p)) == normalizar_busca_motor(cor_ref) else 1,
        len(str(p.get("nome") or "")),
    ))
    return candidatos[0]


def montar_payload_produto(
    nome,
    codigo_interno,
    codigo_barras,
    grupo_produto,
    tipo_produto,
    modelo_tecnico,
    grupo_tecnico,
    familia_tecnica,
    varia_cor,
    cor_componente,
    unidade_venda,
    movimenta_estoque,
    habilitar_nota_fiscal,
    possui_variacoes,
    possui_composicao,
    situacao,
    linha,
    modelo,
    tipo_cortina_persiana,
    material_tecido,
    cor,
    largura,
    altura,
    comprimento,
    peso,
    descricao,
    observacoes,
    valor_custo,
    despesas_acessorias,
    outras_despesas,
    margem_lucro,
    valor_venda,
    estoque_minimo,
    estoque_maximo,
    estoque_atual,
    ncm,
    cest,
    origem,
):
    custo_final = float(valor_custo or 0) + float(despesas_acessorias or 0) + float(outras_despesas or 0)
    valor_venda_calculado = float(valor_venda or 0)

    if valor_venda_calculado <= 0 and custo_final > 0:
        valor_venda_calculado = custo_final + (custo_final * (float(margem_lucro or 0) / 100))

    return {
        "nome": str(nome).strip(),
        "codigo_interno": str(codigo_interno).strip() if str(codigo_interno).strip() else None,
        "codigo_barras": str(codigo_barras).strip() if str(codigo_barras).strip() else None,
        "grupo_produto": valor_select_payload(grupo_produto),
        "tipo_produto": valor_select_payload(tipo_produto),
        "modelo_tecnico": normalizar_modelo_tecnico(modelo_tecnico),
        "grupo_tecnico": normalizar_grupo_tecnico(grupo_tecnico),
        # Legado: mantém receitas antigas funcionando enquanto migramos o motor.
        "familia_tecnica": normalizar_familia_tecnica(familia_tecnica),
        "varia_cor": bool(normalizar_bool_varia_cor(varia_cor)),
        "cor_componente": valor_select_payload(cor_componente),
        "unidade_venda": valor_select_payload(unidade_venda),
        "movimenta_estoque": str(movimenta_estoque),
        "habilitar_nota_fiscal": str(habilitar_nota_fiscal),
        "possui_variacoes": str(possui_variacoes),
        "possui_composicao": str(possui_composicao),
        "situacao": str(situacao),
        "linha": valor_select_payload(linha),
        "modelo": valor_select_payload(modelo),
        "tipo_cortina_persiana": valor_select_payload(tipo_cortina_persiana),
        "material_tecido": valor_select_payload(material_tecido),
        "cor": valor_select_payload(cor),
        "largura": float(largura or 0),
        "altura": float(altura or 0),
        "comprimento": float(comprimento or 0),
        "peso": float(peso or 0),
        "descricao": str(descricao).strip() if str(descricao).strip() else None,
        "observacoes": str(observacoes).strip() if str(observacoes).strip() else None,
        "valor_custo": float(valor_custo or 0),
        "despesas_acessorias": float(despesas_acessorias or 0),
        "outras_despesas": float(outras_despesas or 0),
        "custo_final": custo_final,
        "margem_lucro": float(margem_lucro or 0),
        "valor_venda": float(valor_venda_calculado or 0),
        "estoque_minimo": float(estoque_minimo or 0),
        "estoque_maximo": float(estoque_maximo or 0),
        "estoque_atual": float(estoque_atual or 0),
        "ncm": str(ncm).strip() if str(ncm).strip() else None,
        "cest": str(cest).strip() if str(cest).strip() else None,
        "origem": str(origem).strip() if str(origem).strip() else None,
    }


def montar_payload_produto_massa(produto, campo_alterado=None, novo_valor=None, nova_margem=None, novo_valor_venda=None):
    produto = dict(produto or {})

    for chave in ["created_at", "updated_at", "data_criacao", "data_atualizacao"]:
        produto.pop(chave, None)

    valor_custo = float(produto.get("valor_custo") or 0)
    despesas_acessorias = float(produto.get("despesas_acessorias") or 0)
    outras_despesas = float(produto.get("outras_despesas") or 0)
    custo_final = valor_custo + despesas_acessorias + outras_despesas

    produto["valor_custo"] = valor_custo
    produto["despesas_acessorias"] = despesas_acessorias
    produto["outras_despesas"] = outras_despesas
    produto["custo_final"] = custo_final

    if campo_alterado == "valor_custo":
        valor_custo = float(novo_valor or 0)
        custo_final = valor_custo + despesas_acessorias + outras_despesas
        produto["valor_custo"] = valor_custo
        produto["custo_final"] = custo_final

    if nova_margem is not None:
        produto["margem_lucro"] = float(nova_margem or 0)

    if novo_valor_venda is not None:
        produto["valor_venda"] = float(novo_valor_venda or 0)

    if campo_alterado == "valor_venda" and novo_valor is not None and novo_valor_venda is None:
        produto["valor_venda"] = float(novo_valor or 0)

    produto["nome"] = str(produto.get("nome") or "").strip()
    produto["situacao"] = str(produto.get("situacao") or "Ativo")
    produto["margem_lucro"] = float(produto.get("margem_lucro") or 0)
    produto["valor_venda"] = float(produto.get("valor_venda") or 0)
    produto["estoque_minimo"] = float(produto.get("estoque_minimo") or 0)
    produto["estoque_maximo"] = float(produto.get("estoque_maximo") or 0)
    produto["estoque_atual"] = float(produto.get("estoque_atual") or 0)

    return produto


# =========================================================
# EDIÇÃO EM MASSA DE PRODUTOS - CONFIGURAÇÃO POR CAMPO
# =========================================================
CAMPOS_EDICAO_MASSA_PRODUTOS = {
    "Selecione o campo para alteração": {
        "api": None,
        "tipo": "placeholder",
    },
    "Código de barras": {
        "api": "codigo_barras",
        "tipo": "texto",
    },
    "Grupo": {
        "api": "grupo_produto",
        "tipo": "opcao_categoria",
        "categoria": "grupo_produto",
        "label_vazio": "Sem grupo",
    },
    "Grupo técnico": {
        "api": "grupo_tecnico",
        "tipo": "select",
        "opcoes": GRUPOS_TECNICOS_PADRAO,
    },
    "Peso": {
        "api": "peso",
        "tipo": "numero",
        "step": 0.01,
        "format": "%.2f",
    },
    "Largura": {
        "api": "largura",
        "tipo": "numero",
        "step": 0.01,
        "format": "%.2f",
    },
    "Altura": {
        "api": "altura",
        "tipo": "numero",
        "step": 0.01,
        "format": "%.2f",
    },
    "Comprimento": {
        "api": "comprimento",
        "tipo": "numero",
        "step": 0.01,
        "format": "%.2f",
    },
    "Movimenta estoque": {
        "api": "movimenta_estoque",
        "tipo": "select",
        "opcoes": ["Sim", "Não"],
    },
    "Possui NF": {
        "api": "habilitar_nota_fiscal",
        "tipo": "select",
        "opcoes": ["Sim", "Não"],
    },
    "Produto Ativo": {
        "api": "situacao",
        "tipo": "select",
        "opcoes": ["Sim", "Não"],
    },
    "Comissão (%)": {
        "api": None,
        "tipo": "indisponivel",
        "mensagem": "Comissão (%) está preparada, mas ainda precisa ser liberada no backend.",
    },
    "NCM": {
        "api": "ncm",
        "tipo": "texto",
    },
    "Cód. benefício": {
        "api": None,
        "tipo": "indisponivel",
        "mensagem": "Cód. benefício está preparado, mas ainda precisa ser liberado no backend.",
    },
}


def opcoes_campo_edicao_massa_produtos(cfg):
    if cfg.get("tipo") == "opcao_categoria":
        opcoes = carregar_opcoes_categoria(cfg.get("categoria"), incluir_vazio=False)
        opcoes = [x for x in opcoes if x and x != "Selecione..."]
        label_vazio = cfg.get("label_vazio", "Sem grupo")
        return [label_vazio] + opcoes

    return list(cfg.get("opcoes", []))


def valor_inicial_campo_edicao_massa_produtos(produto, cfg):
    api = cfg.get("api")
    tipo = cfg.get("tipo")
    valor = produto.get(api) if api else None

    if tipo == "numero":
        try:
            return float(valor or 0)
        except Exception:
            return 0.0

    if api == "situacao":
        return "Sim" if str(valor or "Ativo").strip().lower() == "ativo" else "Não"

    # Ajuste SmartTec v8:
    # - Grupo continua sendo comercial/estoque (grupo_produto).
    # - Grupo técnico é a fonte do motor/cálculo.
    # Quando o produto antigo ainda está vazio, a tela sugere automaticamente
    # o grupo correto em vez de mostrar tudo como "Sem grupo".
    if api == "grupo_tecnico":
        texto = normalizar_grupo_tecnico(valor) or grupo_tecnico_label(produto)
        return texto or ""

    if api == "grupo_produto":
        label_vazio = cfg.get("label_vazio", "Sem grupo")
        texto = str(valor or "").strip()
        if not texto:
            try:
                texto = inferir_grupo_produto_importacao(produto) or ""
            except Exception:
                texto = ""
        return texto if texto else label_vazio

    if tipo == "opcao_categoria":
        label_vazio = cfg.get("label_vazio", "Sem grupo")
        texto = str(valor or "").strip()
        return texto if texto else label_vazio

    return str(valor or "")


def converter_valor_edicao_massa_produtos_para_api(valor_ui, cfg):
    api = cfg.get("api")
    tipo = cfg.get("tipo")

    if tipo == "numero":
        try:
            return float(valor_ui or 0)
        except Exception:
            return 0.0

    if api == "situacao":
        return "Ativo" if str(valor_ui) == "Sim" else "Inativo"

    if tipo == "opcao_categoria":
        label_vazio = cfg.get("label_vazio", "Sem grupo")
        return None if str(valor_ui).strip() == label_vazio else str(valor_ui).strip()

    texto = str(valor_ui or "").strip()
    return texto if texto else None


def calcular_novo_valor_massa(valor_atual, tipo_ajuste, operacao, valor_ajuste):
    valor_atual = float(valor_atual or 0)
    valor_ajuste = float(valor_ajuste or 0)

    if tipo_ajuste == "Percentual":
        delta = valor_atual * (valor_ajuste / 100)
    else:
        delta = valor_ajuste

    if operacao == "Aumentar":
        return max(valor_atual + delta, 0)

    if operacao == "Reduzir":
        return max(valor_atual - delta, 0)

    if operacao == "Definir valor":
        return max(valor_ajuste, 0)

    return valor_atual


def calcular_margem_por_valor_venda(custo_final, valor_venda):
    custo_final = float(custo_final or 0)
    valor_venda = float(valor_venda or 0)

    if custo_final <= 0:
        return 0

    return max(((valor_venda - custo_final) / custo_final) * 100, 0)


def calcular_valor_venda_por_margem(custo_final, margem_lucro):
    custo_final = float(custo_final or 0)
    margem_lucro = float(margem_lucro or 0)

    return max(custo_final * (1 + (margem_lucro / 100)), 0)


def filtrar_produtos_ajuste_massa(produtos, config):
    produtos = produtos or []

    grupo = str(config.get("grupo") or "Todos").strip().lower()
    nome = str(config.get("nome") or "").strip().lower()
    codigo = str(config.get("codigo") or "").strip().lower()
    situacao = str(config.get("situacao") or "Todos").strip().lower()
    modelo = str(config.get("modelo") or "").strip().lower()
    motor = str(config.get("motor") or "").strip().lower()
    largura = str(config.get("largura") or "").strip().lower()

    filtrados = []

    for produto in produtos:
        if grupo and grupo != "todos":
            grupo_produto = str(produto.get("grupo_produto") or produto.get("grupo") or "").strip().lower()
            if grupo not in grupo_produto:
                continue

        if nome and nome not in str(produto.get("nome") or "").strip().lower():
            continue

        if codigo:
            codigos = " ".join([
                str(produto.get("codigo_interno") or ""),
                str(produto.get("codigo_barras") or ""),
                str(produto.get("id") or ""),
            ]).lower()
            if codigo not in codigos:
                continue

        if situacao != "todos" and situacao != "independe":
            situacao_produto = str(produto.get("situacao") or "Ativo").strip().lower()
            if situacao_produto != situacao:
                continue

        if modelo and modelo not in str(produto.get("modelo") or "").strip().lower():
            continue

        if motor and motor not in str(produto.get("motor") or produto.get("acionamento") or "").strip().lower():
            continue

        if largura and largura not in str(produto.get("largura") or "").strip().lower():
            continue

        filtrados.append(produto)

    return filtrados


def executar_ajuste_valores_massa(mudar_tela):
    config = st.session_state.get("config_ajuste_valores_massa", {}) or {}
    produtos = buscar_produtos_api()
    produtos_filtrados = filtrar_produtos_ajuste_massa(produtos, config)

    if not produtos_filtrados:
        st.warning("Nenhum produto encontrado para aplicar o ajuste.")
        st.session_state.confirmar_ajuste_valores_massa = False
        return

    tipo_valor = config.get("tipo_valor", "Lucro utilizado")
    tipo_ajuste = config.get("tipo", "Percentual")
    operacao = config.get("operacao", "Aumentar")
    valor_ajuste = float(config.get("valor", 0) or 0)

    atualizados = 0
    erros = []

    for produto in produtos_filtrados:
        produto_id = produto.get("id")

        if produto_id is None:
            continue

        custo_final = float(produto.get("custo_final") or 0)
        if custo_final <= 0:
            custo_final = (
                float(produto.get("valor_custo") or 0)
                +float(produto.get("despesas_acessorias") or 0)
                +float(produto.get("outras_despesas") or 0)
            )

        margem_atual = float(produto.get("margem_lucro") or 0)
        valor_venda_atual = float(produto.get("valor_venda") or 0)

        if valor_venda_atual <= 0:
            valor_venda_atual = calcular_valor_venda_por_margem(custo_final, margem_atual)

        if tipo_valor == "Lucro utilizado":
            nova_margem = calcular_novo_valor_massa(margem_atual, tipo_ajuste, operacao, valor_ajuste)
            novo_valor_venda = calcular_valor_venda_por_margem(custo_final, nova_margem)
        else:
            novo_valor_venda = calcular_novo_valor_massa(valor_venda_atual, tipo_ajuste, operacao, valor_ajuste)
            nova_margem = calcular_margem_por_valor_venda(custo_final, novo_valor_venda)

        payload = montar_payload_produto_massa(
            produto,
            nova_margem=nova_margem,
            novo_valor_venda=novo_valor_venda,
        )

        try:
            resp = atualizar_produto(int(produto_id), preservar_payload_termos_comerciais(payload))

            if resp is not None and resp.status_code in [200, 201, 204]:
                atualizados += 1
            else:
                status = resp.status_code if resp is not None else "sem resposta"
                texto_erro = ""
                try:
                    texto_erro = resp.text
                except Exception:
                    pass
                erros.append(f"Produto {produto_id}: status {status} {texto_erro}")

        except Exception as erro:
            erros.append(f"Produto {produto_id}: {erro}")

    if atualizados:
        tipo_msg = "lucro utilizado" if tipo_valor == "Lucro utilizado" else "valor de venda"
        st.success(f"✅ {atualizados} produto(s) atualizado(s) com sucesso!")
        st.session_state.mensagem_acao_produtos = f"✅ {atualizados} produto(s) atualizado(s) com sucesso no ajuste em massa de {tipo_msg}."

    if erros:
        st.error("Alguns produtos não foram atualizados:")
        for erro in erros[:8]:
            st.write(f"- {erro}")
        if not st.session_state.get("mensagem_acao_produtos"):
            st.session_state.mensagem_acao_produtos = "⚠️ Ajuste concluído com alguns erros. Confira os produtos."

    st.session_state.confirmar_ajuste_valores_massa = False
    st.session_state.config_ajuste_valores_massa = {}
    st.session_state.acao_mais_produtos = ""

    time.sleep(0.6)
    mudar_tela("listar")
    st.query_params.clear()
    st.rerun()


def renderizar_confirmacao_ajuste_valores_massa(mudar_tela):
    if not st.session_state.get("confirmar_ajuste_valores_massa", False):
        return

    config = st.session_state.get("config_ajuste_valores_massa", {}) or {}
    produtos = buscar_produtos_api()
    produtos_filtrados = filtrar_produtos_ajuste_massa(produtos, config)

    tipo_valor = config.get("tipo_valor", "Lucro utilizado")
    tipo = config.get("tipo", "Percentual")
    operacao = config.get("operacao", "Aumentar")
    valor = float(config.get("valor", 0) or 0)

    sufixo = "%" if tipo == "Percentual" else "R$"
    valor_txt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    config_url = quote(json.dumps(config, ensure_ascii=False), safe="")
    link_nao = f"?go_to=produtos&acao_mais_produtos=ajustar_valores&confirmar_ajuste_valores_massa=nao&ajuste_config={config_url}"
    link_sim = f"?go_to=produtos&acao_mais_produtos=ajustar_valores&confirmar_ajuste_valores_massa=sim&ajuste_config={config_url}"

    st.markdown(
        f"""
        <div class="erp-modal-backdrop">
            <div class="erp-modal-card">
                <div class="erp-modal-body">
                    <div class="erp-modal-icon">💲</div>
                    <div class="erp-modal-text">
                        <strong>{operacao} {tipo_valor.lower()}</strong><br>
                        Deseja aplicar em <strong>{len(produtos_filtrados)} produto(s)</strong>?
                    </div>
                    <div style="margin-top:12px;font-size:14px;color:#374151;border:1px solid #e5e7eb;background:#f9fafb;padding:10px;border-radius:6px;text-align:left;">
                        <strong>Tipo:</strong> {tipo_valor}<br>
                        <strong>Ação:</strong> {operacao} {valor_txt}{sufixo if tipo == "Percentual" else ""}<br>
                        <strong>Formato:</strong> {tipo}
                    </div>
                </div>
                <div class="erp-modal-footer">
                    <a class="erp-modal-btn erp-modal-btn-no" href="{link_nao}" target="_self">Não</a>
                    <a class="erp-modal-btn erp-modal-btn-yes" href="{link_sim}" target="_self">Sim</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def normalizar_ids_selecionados_produtos():
    ids = st.session_state.get("produtos_selecionados_lote", [])
    normalizados = []

    for item in ids:
        try:
            normalizados.append(int(item))
        except Exception:
            pass

    st.session_state.produtos_selecionados_lote = list(dict.fromkeys(normalizados))
    return st.session_state.produtos_selecionados_lote


def selecionar_produto_lote(produto_id, selecionado):
    ids = normalizar_ids_selecionados_produtos()

    try:
        produto_id = int(produto_id)
    except Exception:
        return

    if selecionado and produto_id not in ids:
        ids.append(produto_id)

    if not selecionado and produto_id in ids:
        ids.remove(produto_id)

    st.session_state.produtos_selecionados_lote = ids


def limpar_selecao_produtos_lote():
    st.session_state.produtos_selecionados_lote = []


COLUNAS_GERENCIAVEIS_PRODUTOS = {
    "valor_venda": {"label": "Vr. venda", "largura": 1.15, "tipo": "moeda"},
    "estoque_atual": {"label": "Estoque", "largura": 1.05, "tipo": "numero"},
    "situacao": {"label": "Situação", "largura": 0.9, "tipo": "situacao"},
    "grupo_produto": {"label": "Grupo", "largura": 1.45, "tipo": "texto"},
    "modelo_tecnico": {"label": "Modelo técnico", "largura": 1.35, "tipo": "texto"},
    "grupo_tecnico": {"label": "Grupo técnico", "largura": 1.75, "tipo": "texto"},
    "linha": {"label": "Linha", "largura": 1.1, "tipo": "texto"},
    "modelo": {"label": "Modelo", "largura": 1.2, "tipo": "texto"},
    "tipo_cortina_persiana": {"label": "Tipo", "largura": 1.55, "tipo": "texto"},
    "material_tecido": {"label": "Material/Tecido", "largura": 1.75, "tipo": "texto"},
    "cor": {"label": "Cor", "largura": 1.05, "tipo": "texto"},
    "unidade_venda": {"label": "Unid.", "largura": 0.85, "tipo": "texto"},
    "valor_custo": {"label": "Vr. custo", "largura": 1.1, "tipo": "moeda"},
    "custo_final": {"label": "Custo final", "largura": 1.15, "tipo": "moeda"},
    "margem_lucro": {"label": "Margem %", "largura": 1.0, "tipo": "percentual"},
    "codigo_barras": {"label": "Cód. barras", "largura": 1.35, "tipo": "texto"},
    "tipo_produto": {"label": "Tipo produto", "largura": 1.45, "tipo": "texto"},
}

COLUNAS_PADRAO_LISTAGEM_PRODUTOS = [
    "valor_venda",
    "estoque_atual",
    "situacao",
    "grupo_tecnico",
    "cor",
]

ARQUIVO_COLUNAS_PRODUTOS = Path("config") / "colunas_visiveis_produtos.json"


def carregar_colunas_visiveis_produtos_salvas():
    try:
        if ARQUIVO_COLUNAS_PRODUTOS.exists():
            dados = json.loads(ARQUIVO_COLUNAS_PRODUTOS.read_text(encoding="utf-8"))
            colunas = dados.get("colunas_visiveis_produtos", [])
            if isinstance(colunas, list):
                return [
                    campo for campo in colunas
                    if campo in COLUNAS_GERENCIAVEIS_PRODUTOS
                ]
    except Exception:
        pass

    return []


def salvar_colunas_visiveis_produtos(colunas):
    try:
        ARQUIVO_COLUNAS_PRODUTOS.parent.mkdir(parents=True, exist_ok=True)
        colunas_limpas = []
        for campo in colunas or []:
            if campo in COLUNAS_GERENCIAVEIS_PRODUTOS and campo not in colunas_limpas:
                colunas_limpas.append(campo)

        ARQUIVO_COLUNAS_PRODUTOS.write_text(
            json.dumps(
                {"colunas_visiveis_produtos": colunas_limpas},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def obter_colunas_visiveis_produtos():
    if "colunas_visiveis_produtos" not in st.session_state:
        colunas_salvas = carregar_colunas_visiveis_produtos_salvas()
        if colunas_salvas:
            st.session_state.colunas_visiveis_produtos = colunas_salvas
        else:
            st.session_state.colunas_visiveis_produtos = COLUNAS_PADRAO_LISTAGEM_PRODUTOS.copy()
            salvar_colunas_visiveis_produtos(st.session_state.colunas_visiveis_produtos)

    colunas = []
    for campo in st.session_state.colunas_visiveis_produtos:
        if campo in COLUNAS_GERENCIAVEIS_PRODUTOS and campo not in colunas:
            colunas.append(campo)

    if not colunas:
        colunas = COLUNAS_PADRAO_LISTAGEM_PRODUTOS.copy()
        st.session_state.colunas_visiveis_produtos = colunas
        salvar_colunas_visiveis_produtos(colunas)

    return colunas


def formatar_valor_coluna_produto(row, campo):
    cfg = COLUNAS_GERENCIAVEIS_PRODUTOS.get(campo, {})
    tipo = cfg.get("tipo", "texto")

    if tipo == "situacao":
        ativo = produto_ativo(row.get("situacao", "Ativo"))
        status = "✓" if ativo else "×"
        cor = "#00a65a" if ativo else "#ff0019"
        return f'<span style="color:{cor};font-size:22px;font-weight:800;">{status}</span>'

    valor = row.get(campo, "")

    if tipo == "moeda":
        try:
            return f'{float(valor or 0):,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00"

    if tipo == "numero":
        try:
            return f'{float(valor or 0):,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00"

    if tipo == "percentual":
        try:
            return f'{float(valor or 0):,.2f}%'.replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00%"

    return texto_seguro(valor)


def corrigir_termos_comerciais_produtos_banco():
    """
    Corrige definitivamente no banco os produtos já salvos/importados com tradução indevida.

    Importante:
    Aqui lemos o retorno cru do get_produtos(), mas o get_produtos pode retornar:
    - lista de produtos
    - Response do requests
    - dicionário com chave "produtos", "data", "items" ou "results"
    Por isso normalizamos antes de percorrer.
    """
    try:
        resposta_produtos = get_produtos()
    except Exception as erro:
        return 0, [f"Erro ao buscar produtos: {erro}"]

    produtos = []

    try:
        if hasattr(resposta_produtos, "json"):
            dados = resposta_produtos.json()
        else:
            dados = resposta_produtos

        if isinstance(dados, list):
            produtos = dados
        elif isinstance(dados, dict):
            for chave in ["produtos", "data", "items", "results"]:
                if isinstance(dados.get(chave), list):
                    produtos = dados.get(chave)
                    break

            if not produtos and all(k in dados for k in ["id", "nome"]):
                produtos = [dados]
        else:
            produtos = []

    except Exception as erro:
        return 0, [f"Erro ao interpretar lista de produtos: {erro}"]

    atualizados = 0
    erros = []

    for produto in produtos or []:
        if not isinstance(produto, dict):
            continue

        original = dict(produto or {})
        corrigido = preservar_payload_termos_comerciais(dict(produto or {}))

        mudou = False
        for campo in [
            "nome",
            "grupo_produto",
            "linha",
            "modelo",
            "tipo_cortina_persiana",
            "material_tecido",
            "descricao",
            "observacoes",
        ]:
            if str(original.get(campo) or "") != str(corrigido.get(campo) or ""):
                mudou = True
                break

        if not mudou:
            continue

        try:
            pid = int(original.get("id"))
            payload = montar_payload_produto_massa(corrigido)
            payload = preservar_payload_termos_comerciais(payload)
            resp = atualizar_produto(pid, payload)

            if resp is not None and resp.status_code in [200, 201, 204]:
                atualizados += 1
            else:
                status = resp.status_code if resp is not None else "sem resposta"
                detalhe = ""
                try:
                    detalhe = resp.text
                except Exception:
                    pass
                erros.append(f"Produto {pid}: status {status} {detalhe}")

        except Exception as erro:
            erros.append(f"Produto {original.get('id')}: {erro}")

    return atualizados, erros


def renderizar_gerenciador_colunas_produtos():
    colunas_visiveis = obter_colunas_visiveis_produtos()

    if hasattr(st, "popover"):
        with st.popover("☷", use_container_width=True):
            st.markdown("#### Gerenciar colunas")
            st.caption("As colunas escolhidas ficam salvas até você alterar novamente.")

            novas_colunas = []
            houve_mudanca = False

            for campo, cfg in COLUNAS_GERENCIAVEIS_PRODUTOS.items():
                valor_atual = campo in colunas_visiveis
                marcado = st.checkbox(
                    cfg["label"],
                    value=valor_atual,
                    key=f"chk_coluna_produtos_{campo}",
                )

                if marcado:
                    novas_colunas.append(campo)

                if marcado != valor_atual:
                    houve_mudanca = True

            if houve_mudanca:
                st.session_state.colunas_visiveis_produtos = novas_colunas
                salvar_colunas_visiveis_produtos(novas_colunas)
                st.rerun()

            if st.button("Restaurar padrão", key="btn_restaurar_colunas_produtos", use_container_width=True):
                st.session_state.colunas_visiveis_produtos = COLUNAS_PADRAO_LISTAGEM_PRODUTOS.copy()
                salvar_colunas_visiveis_produtos(COLUNAS_PADRAO_LISTAGEM_PRODUTOS.copy())
                st.rerun()
    else:
        st.caption("Gerenciar colunas indisponível nesta versão do Streamlit.")


def renderizar_tabela_produtos(df, mudar_tela):
    ids_selecionados = normalizar_ids_selecionados_produtos()
    modo_selecao_lote = st.session_state.get("acao_mais_produtos") in ["ferramentas_massa", "excluir_selecionados", "inativar_selecionados", "reativar_selecionados", "copiar_para_bau_componentes", "remover_do_bau_componentes", "aplicar_receita_rolo_manual"]
    colunas_visiveis = obter_colunas_visiveis_produtos()

    larguras = []
    if modo_selecao_lote:
        larguras.append(0.45)

    larguras.extend([1.05, 3.35])

    for campo in colunas_visiveis:
        larguras.append(float(COLUNAS_GERENCIAVEIS_PRODUTOS[campo].get("largura", 1.2)))

    larguras.append(1.65)

    headers = st.columns(larguras)

    idx_col = 0

    if modo_selecao_lote:
        with headers[idx_col]:
            st.markdown('<div class="erp-list-header" style="text-align:center;">☑</div>', unsafe_allow_html=True)
        idx_col += 1

    with headers[idx_col]:
        st.markdown('<div class="erp-list-header">Código</div>', unsafe_allow_html=True)
    idx_col += 1

    with headers[idx_col]:
        st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
    idx_col += 1

    for campo in colunas_visiveis:
        cfg = COLUNAS_GERENCIAVEIS_PRODUTOS[campo]
        alinhamento = "center" if cfg.get("tipo") == "situacao" else "left"
        with headers[idx_col]:
            st.markdown(
                f'<div class="erp-list-header" style="text-align:{alinhamento};">{cfg["label"]}</div>',
                unsafe_allow_html=True,
            )
        idx_col += 1

    with headers[idx_col]:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

    for index, row in df.reset_index(drop=True).iterrows():
        produto_id = int(row.get("id", 0))
        codigo = texto_seguro(preservar_termos_comerciais(row.get("codigo_interno", "") or row.get("id", "")))
        nome = texto_seguro(preservar_termos_comerciais(row.get("nome", "")))
        cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

        cols = st.columns(larguras)
        idx_col = 0

        if modo_selecao_lote:
            with cols[idx_col]:
                st.markdown(f'<div class="{cell_class}" style="justify-content:center;">', unsafe_allow_html=True)
                selecionado = st.checkbox(
                    "Selecionar produto",
                    value=produto_id in ids_selecionados,
                    key=f"selecionar_produto_lote_{produto_id}",
                    label_visibility="collapsed",
                )
                selecionar_produto_lote(produto_id, selecionado)
                st.markdown('</div>', unsafe_allow_html=True)
            idx_col += 1

        with cols[idx_col]:
            st.markdown(f'<div class="{cell_class}">{codigo}</div>', unsafe_allow_html=True)
        idx_col += 1

        with cols[idx_col]:
            st.markdown(f'<div class="{cell_class}">{nome}</div>', unsafe_allow_html=True)
        idx_col += 1

        for campo in colunas_visiveis:
            cfg = COLUNAS_GERENCIAVEIS_PRODUTOS[campo]
            alinhamento_css = "justify-content:center;text-align:center;" if cfg.get("tipo") == "situacao" else ""
            valor_formatado = formatar_valor_coluna_produto(row, campo)

            with cols[idx_col]:
                st.markdown(
                    f'<div class="{cell_class}" style="{alinhamento_css}">{valor_formatado}</div>',
                    unsafe_allow_html=True,
                )
            idx_col += 1

        with cols[idx_col]:
            nome_url = texto_seguro(preservar_termos_comerciais(row.get("nome", "")))
            st.markdown(
                f"""
                <div class="erp-action-links-produtos">
                    <a class="erp-action-link-produto erp-action-view-produto" href="?go_to=produtos&acao_produto=visualizar&id_produto={produto_id}" target="_self" title="Visualizar">🔍</a>
                    <a class="erp-action-link-produto erp-action-edit-produto" href="?go_to=produtos&acao_produto=editar&id_produto={produto_id}" target="_self" title="Editar">✎</a>
                    <a class="erp-action-link-produto erp-action-delete-produto" href="?go_to=produtos&acao_produto=excluir&id_produto={produto_id}&nome_produto={nome_url}" target="_self" title="Excluir">×</a>
                    <a class="erp-action-link-produto erp-action-clone-produto" href="?go_to=produtos&acao_produto=clonar&id_produto={produto_id}" target="_self" title="Clonar produto">⧉</a>
                </div>
                """,
                unsafe_allow_html=True,
            )


def executar_exclusao_produto(produto_id, mudar_tela):
    try:
        resp = deletar_produto(produto_id)

        if resp is not None and resp.status_code in [200, 204]:
            st.success("✅ Produto excluído com sucesso!")
            st.session_state.confirmar_exclusao_produto = None
            st.session_state.confirmar_exclusao_produto_nome = ""
            mudar_tela("listar")
            time.sleep(0.3)
            st.query_params.clear()
            st.rerun()

        else:
            status = resp.status_code if resp is not None else "sem resposta"
            st.error(f"Não foi possível excluir este produto. Status: {status}")

    except Exception as erro:
        st.error(f"Erro ao excluir produto: {erro}")


def executar_exclusao_produtos_lote(ids_produtos, mudar_tela):
    ids_produtos = [int(x) for x in ids_produtos if str(x).strip()]

    if not ids_produtos:
        st.warning("Nenhum produto selecionado para excluir.")
        return

    excluidos = 0
    erros = []

    for produto_id in ids_produtos:
        try:
            resp = deletar_produto(produto_id)

            if resp is not None and resp.status_code in [200, 204]:
                excluidos += 1
            else:
                status = resp.status_code if resp is not None else "sem resposta"
                erros.append(f"Produto {produto_id}: status {status}")

        except Exception as erro:
            erros.append(f"Produto {produto_id}: {erro}")

    if excluidos:
        st.success(f"✅ {excluidos} produto(s) excluído(s) com sucesso!")

    if erros:
        st.error("Alguns produtos não foram excluídos:")
        for erro in erros[:8]:
            st.write(f"- {erro}")

    st.session_state.produtos_selecionados_lote = []
    st.session_state.confirmar_exclusao_produtos_lote = False
    st.session_state.acao_mais_produtos = ""

    time.sleep(0.4)
    mudar_tela("listar")
    st.query_params.clear()
    st.rerun()


def renderizar_confirmacao_exclusao_lote_produtos(produtos_por_id, mudar_tela):
    ids = normalizar_ids_selecionados_produtos()

    if not st.session_state.get("confirmar_exclusao_produtos_lote", False):
        return

    nomes = []
    for produto_id in ids:
        produto = produtos_por_id.get(int(produto_id), {})
        nome = produto.get("nome") or produto.get("codigo_interno") or produto_id
        nomes.append(str(nome))

    # Mostra só alguns nomes para manter o popup limpo.
    lista_nomes = "<br>".join(texto_seguro(nome) for nome in nomes[:8])
    if len(nomes) > 8:
        lista_nomes += f"<br>... e mais {len(nomes) - 8} produto(s)"

    link_nao = "?go_to=produtos&acao_mais_produtos=excluir_selecionados&confirmar_exclusao_lote_produtos=nao"
    link_sim = "?go_to=produtos&acao_mais_produtos=excluir_selecionados&confirmar_exclusao_lote_produtos=sim"

    st.markdown(
        f"""
        <div class="erp-modal-backdrop">
            <div class="erp-modal-card">
                <div class="erp-modal-body">
                    <div class="erp-modal-icon">🗑️</div>
                    <div class="erp-modal-text">
                        Deseja realmente excluir <strong>{len(ids)} produto(s) selecionado(s)</strong>?
                    </div>
                    <div style="
                        margin-top:12px;
                        font-size:13px;
                        color:#374151;
                        max-height:100px;
                        overflow:auto;
                        border:1px solid #e5e7eb;
                        background:#f9fafb;
                        padding:8px 10px;
                        border-radius:6px;
                        text-align:left;
                    ">
                        {lista_nomes}
                    </div>
                </div>
                <div class="erp-modal-footer">
                    <a class="erp-modal-btn erp-modal-btn-no" href="{link_nao}" target="_self">Não</a>
                    <a class="erp-modal-btn erp-modal-btn-yes" href="{link_sim}" target="_self">Sim</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_confirmacao_exclusao_produto(mudar_tela):
    produto_id = st.session_state.get("confirmar_exclusao_produto")
    produto_nome = st.session_state.get("confirmar_exclusao_produto_nome", "")

    if not produto_id:
        return

    nome_exibir = texto_seguro(produto_nome or produto_id)

    link_nao = "?go_to=produtos&confirmar_exclusao_produto=nao"
    link_sim = f"?go_to=produtos&confirmar_exclusao_produto=sim&id_produto={produto_id}"

    st.markdown(
        f"""
        <div class="erp-modal-backdrop">
            <div class="erp-modal-card">
                <div class="erp-modal-body">
                    <div class="erp-modal-icon">🗑️</div>
                    <div class="erp-modal-text">
                        Deseja realmente excluir o produto <strong>{nome_exibir}</strong>?
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


def valor_filtro_produto(valor):
    valor = str(valor or "").strip()
    if not valor or valor in ["Todos", "Independe", "Selecione..."]:
        return ""
    return valor


def aplicar_filtros_produtos(df):
    filtros = st.session_state.get("filtros_busca_avancada_produtos", {})

    if df is None or df.empty:
        return df

    def contem(campo, texto):
        texto = str(texto or "").strip().lower()
        if not texto or campo not in df.columns:
            return pd.Series([True] * len(df), index=df.index)
        return df[campo].astype(str).str.lower().str.contains(texto, na=False, regex=False)

    grupo = valor_filtro_produto(filtros.get("grupo_produto"))
    grupo_tecnico = valor_filtro_produto(filtros.get("grupo_tecnico"))
    nome = valor_filtro_produto(filtros.get("nome"))
    codigo = valor_filtro_produto(filtros.get("codigo"))
    situacao = valor_filtro_produto(filtros.get("situacao"))
    linha = valor_filtro_produto(filtros.get("linha"))
    modelo = valor_filtro_produto(filtros.get("modelo"))
    tipo = valor_filtro_produto(filtros.get("tipo_cortina_persiana"))
    material = valor_filtro_produto(filtros.get("material_tecido"))
    cor = valor_filtro_produto(filtros.get("cor"))

    if grupo and "grupo_produto" in df.columns:
        df = df[df["grupo_produto"].astype(str).str.lower() == grupo.lower()]

    if grupo_tecnico and "grupo_tecnico_filtro" in df.columns:
        df = df[df["grupo_tecnico_filtro"].astype(str).str.lower() == grupo_tecnico.lower()]
    elif grupo_tecnico and "grupo_tecnico" in df.columns:
        df = df[df["grupo_tecnico"].astype(str).str.lower() == grupo_tecnico.lower()]

    if nome:
        df = df[contem("nome", nome)]

    if codigo:
        mask_codigo = pd.Series([False] * len(df), index=df.index)
        if "codigo_interno" in df.columns:
            mask_codigo = mask_codigo | df["codigo_interno"].astype(str).str.lower().str.contains(codigo.lower(), na=False, regex=False)
        if "codigo_barras" in df.columns:
            mask_codigo = mask_codigo | df["codigo_barras"].astype(str).str.lower().str.contains(codigo.lower(), na=False, regex=False)
        if "id" in df.columns:
            mask_codigo = mask_codigo | df["id"].astype(str).str.lower().str.contains(codigo.lower(), na=False, regex=False)
        df = df[mask_codigo]

    if situacao and "situacao" in df.columns:
        df = df[df["situacao"].astype(str).str.lower() == situacao.lower()]

    if linha and "linha" in df.columns:
        df = df[df["linha"].astype(str).str.lower() == linha.lower()]

    if modelo and "modelo" in df.columns:
        df = df[df["modelo"].astype(str).str.lower().str.contains(modelo.lower(), na=False, regex=False)]

    if tipo and "tipo_cortina_persiana" in df.columns:
        df = df[df["tipo_cortina_persiana"].astype(str).str.lower() == tipo.lower()]

    if material and "material_tecido" in df.columns:
        df = df[df["material_tecido"].astype(str).str.lower() == material.lower()]

    if cor and "cor" in df.columns:
        df = df[df["cor"].astype(str).str.lower() == cor.lower()]

    return df


def renderizar_busca_avancada_produtos():
    filtros = st.session_state.get("filtros_busca_avancada_produtos", {})

    opcoes_grupo = ["Todos"] + [x for x in carregar_opcoes_categoria("grupo_produto", incluir_vazio=False) if x != "Selecione..."]
    opcoes_grupo_tecnico = montar_opcoes_grupo_tecnico_filtro()
    opcoes_linha = ["Todos"] + [x for x in carregar_opcoes_categoria("linha_produto", incluir_vazio=False) if x != "Selecione..."]
    opcoes_tipo = ["Todos"] + [x for x in carregar_opcoes_categoria("tipo_cortina_persiana", incluir_vazio=False) if x != "Selecione..."]
    opcoes_material = ["Todos"] + [x for x in carregar_opcoes_categoria("material_tecido", incluir_vazio=False) if x != "Selecione..."]
    opcoes_cor = ["Todos"] + [x for x in carregar_opcoes_categoria("cor_produto", incluir_vazio=False) if x != "Selecione..."]

    def idx_seguro(lista, valor):
        valor = str(valor or "").strip()
        if valor in lista:
            return lista.index(valor)
        return 0

    with st.form("form_busca_avancada_produtos"):
        st.markdown('<div class="erp-busca-avancada-box">', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            grupo_produto = st.selectbox(
                "Grupo",
                opcoes_grupo,
                index=idx_seguro(opcoes_grupo, filtros.get("grupo_produto", "Todos")),
            )

        with c2:
            nome = st.text_input("Nome", value=str(filtros.get("nome", "")))

        with c3:
            codigo = st.text_input("Código", value=str(filtros.get("codigo", "")))

        with c4:
            situacao = st.selectbox(
                "Ativo",
                ["Todos", "Ativo", "Inativo"],
                index=idx_seguro(["Todos", "Ativo", "Inativo"], filtros.get("situacao", "Todos")),
            )

        c5, c6, c7, c8 = st.columns(4)

        with c5:
            linha = st.selectbox(
                "Linha",
                opcoes_linha,
                index=idx_seguro(opcoes_linha, filtros.get("linha", "Todos")),
            )

        with c6:
            tipo_cortina_persiana = st.selectbox(
                "Tipo cortina/persiana",
                opcoes_tipo,
                index=idx_seguro(opcoes_tipo, filtros.get("tipo_cortina_persiana", "Todos")),
            )

        with c7:
            material_tecido = st.selectbox(
                "Material / tecido",
                opcoes_material,
                index=idx_seguro(opcoes_material, filtros.get("material_tecido", "Todos")),
            )

        with c8:
            modelo = st.text_input("Modelo", value=str(filtros.get("modelo", "")))

        c9, c10, c11, c12 = st.columns(4)

        with c9:
            cor = st.selectbox(
                "Cor",
                opcoes_cor,
                index=idx_seguro(opcoes_cor, filtros.get("cor", "Todos")),
            )

        with c10:
            grupo_tecnico = st.selectbox(
                "Grupo técnico",
                opcoes_grupo_tecnico,
                index=idx_seguro(opcoes_grupo_tecnico, filtros.get("grupo_tecnico", "Todos")),
            )

        with c11:
            st.text_input("Marca", value="", disabled=True)

        with c12:
            st.text_input("Largura", value="", disabled=True)

        b1, b2, _ = st.columns([1, 1, 6])

        with b1:
            buscar = st.form_submit_button("Buscar", type="primary", use_container_width=True)

        with b2:
            limpar = st.form_submit_button("Limpar", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if buscar:
            st.session_state.filtros_busca_avancada_produtos = {
                "grupo_produto": grupo_produto,
                "grupo_tecnico": grupo_tecnico,
                "nome": nome,
                "codigo": codigo,
                "situacao": situacao,
                "linha": linha,
                "tipo_cortina_persiana": tipo_cortina_persiana,
                "material_tecido": material_tecido,
                "cor": cor,
                "modelo": modelo,
            }
            st.rerun()

        if limpar:
            st.session_state.filtros_busca_avancada_produtos = {}
            st.rerun()


def renderizar_aba_geral(produto_atual, is_visualizar, modo, id_produto_editar):
    """Renderiza os dados principais do formulario de produto."""
    st.markdown('<div class="erp-section-title-clean">Dados</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        nome = st.text_input("Nome*", value=valor_str(produto_atual, "nome"), disabled=is_visualizar)
    with col2:
        codigo_interno = st.text_input("Código interno", value=valor_str(produto_atual, "codigo_interno"), help="Gerado automaticamente ao adicionar/clonar, mas você pode editar.", disabled=is_visualizar)
    with col3:
        codigo_barras = st.text_input("Código de barra", value=valor_str(produto_atual, "codigo_barras"), help="Gerado automaticamente ao adicionar/clonar, mas você pode editar.", disabled=is_visualizar)
    with col4:
        grupo_produto = selectbox_opcao_auxiliar_com_novo(
            "Grupo do produto",
            "grupo_produto",
            valor_atual=valor_str(produto_atual, "grupo_produto"),
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_grupo_{modo}_{id_produto_editar}",
        )

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        tipo_produto = selectbox_opcao_auxiliar_com_novo(
            "Tipo do produto",
            "tipo_produto",
            valor_atual=valor_str(produto_atual, "tipo_produto"),
            incluir_vazio=True,
            padrao="Produto simples",
            disabled=is_visualizar,
            key_base=f"produto_tipo_{modo}_{id_produto_editar}",
        )
    with col6:
        unidade_venda = selectbox_opcao_auxiliar_com_novo(
            "Unidade de venda",
            "unidade_medida",
            valor_atual=valor_str(produto_atual, "unidade_venda"),
            incluir_vazio=True,
            padrao="Unidade",
            disabled=is_visualizar,
            key_base=f"produto_unidade_{modo}_{id_produto_editar}",
        )
    with col7:
        movimenta_estoque = st.selectbox(
            "Movimenta estoque?",
            ["Sim", "Não"],
            index=0 if valor_str(produto_atual, "movimenta_estoque") != "Não" else 1,
            disabled=is_visualizar,
        )
    with col8:
        possui_composicao = st.selectbox(
            "Possui composição?",
            ["Não", "Sim"],
            index=1 if valor_str(produto_atual, "possui_composicao") == "Sim" else 0,
            disabled=is_visualizar,
        )

    col9, col10, col11 = st.columns(3)
    with col9:
        habilitar_nota_fiscal = st.selectbox(
            "Habilitar nota fiscal?",
            ["Sim", "Não"],
            index=0 if valor_str(produto_atual, "habilitar_nota_fiscal") != "Não" else 1,
            disabled=is_visualizar,
        )
    with col10:
        possui_variacoes = st.selectbox(
            "Possui variações?",
            ["Não", "Sim"],
            index=1 if valor_str(produto_atual, "possui_variacoes") == "Sim" else 0,
            disabled=is_visualizar,
        )
    with col11:
        situacao = st.selectbox(
            "Situação",
            ["Ativo", "Inativo"],
            index=0 if valor_str(produto_atual, "situacao") != "Inativo" else 1,
            disabled=is_visualizar,
        )

    return (
        nome,
        codigo_interno,
        codigo_barras,
        grupo_produto,
        tipo_produto,
        unidade_venda,
        movimenta_estoque,
        possui_composicao,
        habilitar_nota_fiscal,
        possui_variacoes,
        situacao,
    )



def renderizar_aba_tecnico(produto_atual, is_visualizar, modo, id_produto_editar, unidade_venda):
    """Renderiza os dados tecnicos, conversao e medidas do produto."""
    st.markdown('<div class="erp-section-title-clean">Dados técnicos do produto</div>', unsafe_allow_html=True)

    ct1, ct2, ct3, ct4 = st.columns(4)
    with ct1:
        modelo_atual = valor_str(produto_atual, "modelo_tecnico") or inferir_modelo_tecnico_produto(produto_atual) or ""
        opcoes_modelo = list(MODELOS_TECNICOS_PADRAO)
        if modelo_atual and modelo_atual not in opcoes_modelo:
            opcoes_modelo.append(modelo_atual)
        modelo_tecnico = st.selectbox(
            "Modelo técnico",
            opcoes_modelo,
            index=indice_select(opcoes_modelo, modelo_atual),
            disabled=is_visualizar,
            key=f"produto_modelo_tecnico_{modo}_{id_produto_editar}",
            help="Define o modelo do produto. Ex.: ROLO ou DOUBLE_VISION.",
        )

    with ct2:
        produto_tmp_grupo = {**dict(produto_atual or {}), "modelo_tecnico": modelo_tecnico}
        grupo_atual = valor_str(produto_atual, "grupo_tecnico") or inferir_grupo_tecnico_produto(produto_tmp_grupo) or ""
        opcoes_grupo = list(GRUPOS_TECNICOS_PADRAO)
        if grupo_atual and grupo_atual not in opcoes_grupo:
            opcoes_grupo.append(grupo_atual)
        grupo_tecnico = st.selectbox(
            "Grupo técnico",
            opcoes_grupo,
            index=indice_select(opcoes_grupo, grupo_atual),
            disabled=is_visualizar,
            key=f"produto_grupo_tecnico_{modo}_{id_produto_editar}",
            help="Isola tecidos/componentes por modelo. Motores e acessórios ficam globais.",
        )

    # Família técnica fica oculta e inferida apenas para compatibilidade das receitas antigas.
    familia_tecnica = inferir_familia_tecnica_produto({**dict(produto_atual or {}), "modelo_tecnico": modelo_tecnico, "grupo_tecnico": grupo_tecnico}) or valor_str(produto_atual, "familia_tecnica") or ""

    with ct3:
        varia_cor_atual = normalizar_bool_varia_cor(produto_atual.get("varia_cor"))
        if not produto_atual.get("varia_cor") and familia_tecnica:
            varia_cor_atual = inferir_varia_cor_componente({**dict(produto_atual or {}), "familia_tecnica": familia_tecnica})
        varia_cor = st.selectbox(
            "Varia por cor?",
            ["Não", "Sim"],
            index=1 if varia_cor_atual else 0,
            disabled=is_visualizar,
            key=f"produto_varia_cor_{modo}_{id_produto_editar}",
            help="Marque Sim para base, comando, corrente, tampa e emenda. Tubo fica Natural e espaguete fica Incolor.",
        )

    with ct4:
        cor_comp_atual = valor_str(produto_atual, "cor_componente") or inferir_cor_componente_produto({**dict(produto_atual or {}), "familia_tecnica": familia_tecnica})
        cor_componente = selectbox_opcao_auxiliar_com_novo(
            "Cor do componente",
            "cor_produto",
            valor_atual=cor_comp_atual,
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_cor_componente_{modo}_{id_produto_editar}",
        )

    if grupo_tecnico in ["TECIDOS_ROLO_ROMANA_PAINEL", "TECIDOS_DOUBLE_VISION"] or familia_tecnica == "TECIDO":
        varia_cor = "Não"
        st.caption("Regra SmartTec: tecido não troca junto com componentes; a cor dele vem de Detalhes técnicos > Cor.")
    elif familia_tecnica in ["TUBO_32", "TUBO_38"]:
        varia_cor = "Não"
        cor_componente = "Natural"
        st.caption("Regra SmartTec: tubo não troca cor; considerar Natural.")
    elif familia_tecnica == "ESPAGUETE_3MM":
        varia_cor = "Não"
        cor_componente = "Incolor"
        st.caption("Regra SmartTec: espaguete não troca cor; considerar Incolor.")

    st.markdown('<div class="erp-section-title-clean">Conversão de unidade</div>', unsafe_allow_html=True)

    usar_conversao_custo = st.checkbox(
        "Usar conversão para calcular o custo pela unidade de saída",
        value=False,
        disabled=is_visualizar,
        key=f"usar_conversao_custo_{modo}_{id_produto_editar}",
    )

    custo_unitario_saida = 0.0

    if usar_conversao_custo:
        st.info(
            "Use quando você compra em uma unidade e vende/consome em outra. "
            "Ex.: tubo comprado em barra de 6 m e usado por metro linear; tecido comprado em 1 metro linear com 2,50 m² de saída."
        )

        conv1, conv2, conv3 = st.columns([1.1, 1.35, 1.25])
        with conv1:
            conversao_qtd_entrada = st.number_input(
                "Entrada",
                min_value=0.0,
                value=1.0,
                step=1.0,
                format="%.2f",
                disabled=is_visualizar,
                key=f"conversao_qtd_entrada_{modo}_{id_produto_editar}",
            )
        with conv2:
            conversao_unidade_entrada = selectbox_opcao_auxiliar_com_novo(
                "Unidade de entrada",
                "unidade_medida",
                valor_atual="Unidade",
                incluir_vazio=True,
                padrao="Unidade",
                disabled=is_visualizar,
                key_base=f"conversao_unidade_entrada_{modo}_{id_produto_editar}",
            )
        with conv3:
            conversao_valor_entrada = st.number_input(
                "Valor da entrada / compra",
                min_value=0.0,
                value=float(produto_atual.get("valor_custo") or 0),
                step=1.0,
                format="%.2f",
                disabled=is_visualizar,
                key=f"conversao_valor_entrada_{modo}_{id_produto_editar}",
            )

        conv4, conv5, conv6 = st.columns([1.1, 1.35, 1.25])
        with conv4:
            conversao_qtd_saida = st.number_input(
                "Saída equivalente",
                min_value=0.01,
                value=1.0,
                step=0.01,
                format="%.2f",
                disabled=is_visualizar,
                key=f"conversao_qtd_saida_{modo}_{id_produto_editar}",
            )
        with conv5:
            conversao_unidade_saida = selectbox_opcao_auxiliar_com_novo(
                "Unidade de saída",
                "unidade_medida",
                valor_atual=unidade_venda or "Unidade",
                incluir_vazio=True,
                padrao=unidade_venda or "Unidade",
                disabled=is_visualizar,
                key_base=f"conversao_unidade_saida_{modo}_{id_produto_editar}",
            )
        with conv6:
            custo_unitario_saida = calcular_custo_unitario_saida(
                conversao_valor_entrada,
                conversao_qtd_saida,
            )
            st.markdown(
                f"""
                <div style="margin-top:25px;background:#ecfdf5;border:1px solid #bbf7d0;color:#166534;border-radius:6px;padding:10px 12px;font-weight:700;">
                    Custo por {html.escape(normalizar_unidade_label(conversao_unidade_saida))}: {moeda_br(custo_unitario_saida)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(
            f"Regra: {conversao_qtd_entrada:g} {normalizar_unidade_label(conversao_unidade_entrada)} "
            f"entra por {moeda_br(conversao_valor_entrada)} e equivale a "
            f"{conversao_qtd_saida:g} {normalizar_unidade_label(conversao_unidade_saida)} na saída."
        )

        unidade_venda = conversao_unidade_saida

    st.markdown('<div class="erp-section-title-clean">Detalhes técnicos</div>', unsafe_allow_html=True)

    col12, col13, col14, col15 = st.columns(4)
    with col12:
        linha = selectbox_opcao_auxiliar_com_novo(
            "Linha",
            "linha_produto",
            valor_atual=valor_str(produto_atual, "linha"),
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_linha_{modo}_{id_produto_editar}",
        )
    with col13:
        modelo = selectbox_opcao_auxiliar_com_novo(
            "Modelo / variação",
            "modelo_produto",
            valor_atual=valor_str(produto_atual, "modelo"),
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_modelo_{modo}_{id_produto_editar}",
        )
    with col14:
        tipo_cortina_persiana = selectbox_opcao_auxiliar_com_novo(
            "Tipo cortina/persiana",
            "tipo_cortina_persiana",
            valor_atual=valor_str(produto_atual, "tipo_cortina_persiana"),
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_tipo_cortina_{modo}_{id_produto_editar}",
        )
    with col15:
        material_tecido = selectbox_opcao_auxiliar_com_novo(
            "Material / tecido",
            "material_tecido",
            valor_atual=valor_str(produto_atual, "material_tecido"),
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_material_{modo}_{id_produto_editar}",
        )

    col16, col17, col18, col19 = st.columns(4)
    with col16:
        cor = selectbox_opcao_auxiliar_com_novo(
            "Cor",
            "cor_produto",
            valor_atual=valor_str(produto_atual, "cor"),
            incluir_vazio=True,
            disabled=is_visualizar,
            key_base=f"produto_cor_{modo}_{id_produto_editar}",
        )
    with col17:
        largura = st.number_input("Largura", min_value=0.0, value=float(produto_atual.get("largura") or 0), step=0.01, disabled=is_visualizar)
    with col18:
        altura = st.number_input("Altura", min_value=0.0, value=float(produto_atual.get("altura") or 0), step=0.01, disabled=is_visualizar)
    with col19:
        comprimento = st.number_input("Comprimento", min_value=0.0, value=float(produto_atual.get("comprimento") or 0), step=0.01, disabled=is_visualizar)

    peso = st.number_input("Peso", min_value=0.0, value=float(produto_atual.get("peso") or 0), step=0.01, disabled=is_visualizar)

    return (
        modelo_tecnico,
        grupo_tecnico,
        familia_tecnica,
        varia_cor,
        cor_componente,
        usar_conversao_custo,
        custo_unitario_saida,
        unidade_venda,
        linha,
        modelo,
        tipo_cortina_persiana,
        material_tecido,
        cor,
        largura,
        altura,
        comprimento,
        peso,
    )


def renderizar_aba_estoque(produto_atual, is_visualizar):
    """Renderiza os campos de controle de estoque do produto."""
    st.markdown('<div class="erp-section-title-clean">Estoque</div>', unsafe_allow_html=True)

    col25, col26, col27 = st.columns(3)
    with col25:
        estoque_minimo = st.number_input(
            "Estoque mínimo",
            min_value=0.0,
            value=max(0.0, float(produto_atual.get("estoque_minimo") or 0)),
            step=1.0,
            disabled=is_visualizar,
        )
    with col26:
        estoque_maximo = st.number_input(
            "Estoque máximo",
            min_value=0.0,
            value=max(0.0, float(produto_atual.get("estoque_maximo") or 0)),
            step=1.0,
            disabled=is_visualizar,
        )
    with col27:
        # O GestãoClick pode trazer estoque negativo. O SmartTec precisa abrir o produto
        # sem quebrar e permitir corrigir o saldo depois no módulo de estoque.
        estoque_atual_valor = float(produto_atual.get("estoque_atual") or 0)
        estoque_atual = st.number_input(
            "Quantidade atual",
            min_value=None,
            value=estoque_atual_valor,
            step=1.0,
            disabled=is_visualizar,
        )

    return estoque_minimo, estoque_maximo, estoque_atual


def renderizar_aba_fiscal(produto_atual, is_visualizar):
    """Renderiza os campos fiscais basicos do produto."""
    st.markdown('<div class="erp-section-title-clean">Fiscal</div>', unsafe_allow_html=True)

    col28, col29, col30 = st.columns(3)
    with col28:
        ncm = st.text_input("NCM", value=valor_str(produto_atual, "ncm"), disabled=is_visualizar)
    with col29:
        cest = st.text_input("CEST", value=valor_str(produto_atual, "cest"), disabled=is_visualizar)
    with col30:
        origem = st.text_input("Origem", value=valor_str(produto_atual, "origem"), disabled=is_visualizar)

    return ncm, cest, origem


def renderizar_aba_descricao(produto_atual, is_visualizar):
    """Renderiza descricao e observacoes do produto."""
    st.markdown('<div class="erp-section-title-clean">Descrição / Observações</div>', unsafe_allow_html=True)

    descricao = st.text_area(
        "Descrição do produto",
        value=valor_str(produto_atual, "descricao"),
        height=90,
        disabled=is_visualizar,
    )

    observacoes_visiveis = remover_receita_tecnica_observacoes(valor_str(produto_atual, "observacoes"))
    receita_salva_produto_atual = extrair_receita_tecnica_observacoes(produto_atual.get("observacoes"))

    if receita_salva_produto_atual:
        st.info(f"Este produto possui receita técnica oficial salva com {len(receita_salva_produto_atual)} item(ns). Ao clonar, ela pode ser reaproveitada sem refazer a busca.")

    observacoes = st.text_area(
        "Observações",
        value=observacoes_visiveis,
        height=90,
        disabled=is_visualizar,
    )

    return descricao, observacoes


def renderizar_aba_valores(
    produto_atual,
    is_visualizar,
    modo,
    id_produto_editar,
    possui_composicao,
    usar_custo_composicao,
    custo_composicao_final,
    usar_conversao_custo,
    custo_unitario_saida,
):
    """Renderiza custos, margens e valores de venda do produto."""
    st.markdown('<div class="erp-section-title-clean">Valores</div>', unsafe_allow_html=True)

    def formatar_valor_texto(valor):
        return f"{valor_planilha_para_float(valor, 0.0):.2f}".replace(".", ",")

    def valor_texto_para_float(valor):
        return valor_planilha_para_float(valor, 0.0)

    def valor_inicial_texto(chave, valor_padrao):
        if chave in st.session_state and not isinstance(st.session_state.get(chave), str):
            st.session_state[chave] = formatar_valor_texto(st.session_state.get(chave))
        return formatar_valor_texto(valor_padrao)

    col_custo_box, col_venda_box = st.columns([1.15, 3.0])

    with col_custo_box:
        st.markdown(
            """
            <div style="border:1px solid #d1d5db;border-radius:4px;background:#fff;margin-bottom:10px;">
                <div style="padding:12px 14px;border-bottom:1px solid #e5e7eb;font-size:18px;font-weight:600;color:#111827;">
                    Valores de custo
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        chave_valor_custo_produto = f"produto_valor_custo_{modo}_{id_produto_editar}"

        if possui_composicao == "Sim" and usar_custo_composicao and float(custo_composicao_final or 0) > 0 and not is_visualizar:
            st.session_state[chave_valor_custo_produto] = formatar_valor_texto(custo_composicao_final)

        if usar_conversao_custo and float(custo_unitario_saida or 0) > 0 and not is_visualizar:
            st.session_state[chave_valor_custo_produto] = formatar_valor_texto(custo_unitario_saida)

        valor_custo = valor_texto_para_float(st.text_input(
            "Valor de custo *",
            value=valor_inicial_texto(chave_valor_custo_produto, produto_atual.get("valor_custo") or 0),
            disabled=is_visualizar,
            key=chave_valor_custo_produto,
        ))

        despesas_acessorias = valor_texto_para_float(st.text_input(
            "Despesas acessórias",
            value=valor_inicial_texto(f"produto_despesas_acessorias_{modo}_{id_produto_editar}", produto_atual.get("despesas_acessorias") or 0),
            disabled=is_visualizar,
            key=f"produto_despesas_acessorias_{modo}_{id_produto_editar}",
        ))

        outras_despesas = valor_texto_para_float(st.text_input(
            "Outras despesas",
            value=valor_inicial_texto(f"produto_outras_despesas_{modo}_{id_produto_editar}", produto_atual.get("outras_despesas") or 0),
            disabled=is_visualizar,
            key=f"produto_outras_despesas_{modo}_{id_produto_editar}",
        ))

        custo_final_calculado = float(valor_custo or 0) + float(despesas_acessorias or 0) + float(outras_despesas or 0)

        chave_custo_final_calculado = f"produto_custo_final_calculado_{modo}_{id_produto_editar}"
        st.session_state[chave_custo_final_calculado] = formatar_valor_texto(custo_final_calculado)
        st.text_input(
            "Custo final *",
            value=formatar_valor_texto(custo_final_calculado),
            disabled=True,
            key=chave_custo_final_calculado,
        )

    with col_venda_box:
        st.markdown(
            """
            <div style="border:1px solid #d1d5db;border-radius:4px;background:#fff;margin-bottom:10px;">
                <div style="padding:12px 14px;border-bottom:1px solid #e5e7eb;font-size:18px;font-weight:600;color:#111827;">
                    Valores de venda
                </div>
                <div style="margin:14px;background:#d9edf7;border:1px solid #bce8f1;color:#286090;border-radius:4px;padding:12px 14px;font-size:14px;">
                    O valor de venda é recalculado automaticamente ao alterar os campos de custo ou lucro.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        calcular_valores = True
        versao_calculo_valores = st.session_state._versao_calculo_valores_produto

        tipo_col, sugerido_col, utilizado_pct_col, sugerido_rs_col, utilizado_rs_col = st.columns([1.2, 1.25, 1.7, 1.7, 1.7])

        with tipo_col:
            st.markdown("**Tipo**")
        with sugerido_col:
            st.markdown("**Lucro sugerido (%)**")
        with utilizado_pct_col:
            st.markdown("**Lucro utilizado (%)**")
        with sugerido_rs_col:
            st.markdown("**Valor sugerido (R$)**")
        with utilizado_rs_col:
            st.markdown("**Valor utilizado (R$)**")

        tabelas_valores_venda = carregar_tabelas_valores_venda()

        valor_venda_atual = float(produto_atual.get("valor_venda") or 0)
        margem_lucro_atual = float(produto_atual.get("margem_lucro") or 0)

        if tabelas_valores_venda:
            lucro_padrao = float(tabelas_valores_venda[0].get("lucro") or 0)
        else:
            lucro_padrao = 150.0

        if margem_lucro_atual <= 0:
            margem_lucro_atual = lucro_padrao

        if valor_venda_atual <= 0:
            valor_venda_atual = custo_final_calculado + (custo_final_calculado * (margem_lucro_atual / 100))

        def linha_valor_venda(nome_tipo, lucro_sugerido, margem_default, valor_default, chave):
            c_tipo, c_sug, c_pct, c_v_sug, c_v_util = st.columns([1.2, 1.25, 1.7, 1.7, 1.7])

            with c_tipo:
                st.write(nome_tipo)

            with c_sug:
                st.write(f"{float(lucro_sugerido or 0):.2f}%".replace(".", ","))

            with c_pct:
                lucro_utilizado = valor_texto_para_float(st.text_input(
                    f"Lucro utilizado {nome_tipo}",
                    value=valor_inicial_texto(f"produto_lucro_{chave}_{modo}_{id_produto_editar}", margem_default or 0),
                    label_visibility="collapsed",
                    disabled=is_visualizar,
                    key=f"produto_lucro_{chave}_{modo}_{id_produto_editar}",
                ))

            valor_sugerido_por_lucro = custo_final_calculado + (custo_final_calculado * (float(lucro_utilizado or 0) / 100))

            with c_v_sug:
                st.write(moeda_br(valor_sugerido_por_lucro))

            valor_padrao_utilizado = valor_sugerido_por_lucro if calcular_valores else (valor_default or valor_sugerido_por_lucro or 0)

            with c_v_util:
                valor_utilizado = valor_texto_para_float(st.text_input(
                    f"Valor utilizado {nome_tipo}",
                    value=valor_inicial_texto(f"produto_valor_{chave}_{modo}_{id_produto_editar}_{versao_calculo_valores}", valor_padrao_utilizado or 0),
                    label_visibility="collapsed",
                    disabled=is_visualizar,
                    key=f"produto_valor_{chave}_{modo}_{id_produto_editar}_{versao_calculo_valores}",
                ))

            return lucro_utilizado, valor_utilizado

        margem_lucro = margem_lucro_atual
        valor_venda = valor_venda_atual

        for indice, tabela in enumerate(tabelas_valores_venda):
            nome_tabela = str(tabela.get("nome", f"Tabela {indice + 1}"))
            lucro_tabela = float(tabela.get("lucro") or 0)
            chave_tabela = nome_tabela.lower().replace(" ", "_").replace("/", "_").replace("-", "_")

            if indice == 0:
                margem_lucro, valor_venda = linha_valor_venda(
                    nome_tabela,
                    lucro_tabela,
                    margem_lucro_atual,
                    valor_venda_atual,
                    f"principal_{chave_tabela}",
                )
            else:
                valor_padrao = custo_final_calculado + (custo_final_calculado * (lucro_tabela / 100))
                linha_valor_venda(
                    nome_tabela,
                    lucro_tabela,
                    lucro_tabela,
                    valor_padrao,
                    f"extra_{indice}_{chave_tabela}",
                )

        st.markdown(
            """
            <div style="display:flex;justify-content:flex-end;margin-top:8px;">
                <a href="?go_to=produtos_valores" target="_self" style="display:inline-flex;align-items:center;gap:6px;border:1px solid #d1d5db;border-radius:4px;background:#ffffff;color:#198754;text-decoration:none;padding:9px 14px;font-weight:700;font-size:14px;">
                    Cadastrar novo valor de venda
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("O valor principal salvo no produto é a primeira tabela ativa em Produtos > Valores de venda.")

    st.markdown(
        """
        <style>
        div[class*="st-key-produto_valor_custo_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_valor_custo_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_despesas_acessorias_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_despesas_acessorias_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_outras_despesas_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_outras_despesas_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_lucro_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_lucro_"] button[data-testid="stNumberInputStepDown"],
        div[class*="st-key-produto_valor_"] button[data-testid="stNumberInputStepUp"],
        div[class*="st-key-produto_valor_"] button[data-testid="stNumberInputStepDown"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            min-width: 0 !important;
            padding: 0 !important;
            border: 0 !important;
        }

        div[class*="st-key-produto_valor_custo_"] div[data-testid="stNumberInput"] input,
        div[class*="st-key-produto_despesas_acessorias_"] div[data-testid="stNumberInput"] input,
        div[class*="st-key-produto_outras_despesas_"] div[data-testid="stNumberInput"] input,
        div[class*="st-key-produto_lucro_"] div[data-testid="stNumberInput"] input,
        div[class*="st-key-produto_valor_"] div[data-testid="stNumberInput"] input {
            width: 100% !important;
            padding-right: 10px !important;
            border-radius: 4px !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    return valor_custo, despesas_acessorias, outras_despesas, margem_lucro, valor_venda


def renderizar_aba_composicao(
    produto_atual,
    is_visualizar,
    modo,
    id_produto_editar,
    possui_composicao,
    nome,
    linha,
    modelo,
    tipo_cortina_persiana,
    material_tecido,
    cor,
    largura,
    altura,
    comprimento,
    tipo_produto,
    grupo_produto,
):
    """Renderiza composicao, receita tecnica e carrinho de componentes."""
    st.markdown('<div class="erp-section-title-clean">Componentes / Composição</div>', unsafe_allow_html=True)

    custo_composicao_final = 0.0
    usar_custo_composicao = False

    if possui_composicao == "Sim":
        st.markdown(
            """
            <div class="erp-blue-info">
                Informe os componentes usados neste produto. O sistema calcula o custo da composição
                e pode levar este valor automaticamente para a etapa de Valores.
            </div>
            """,
            unsafe_allow_html=True,
        )

        produtos_componentes_base = buscar_produtos_api()

        tipos_permitidos = [
            "insumo",
            "componente",
            "matéria-prima",
            "materia-prima",
            "matéria prima",
            "materia prima",
            "material",
            "acessório",
            "acessorio",
        ]

        produtos_componentes_filtrados = []
        produto_atual_id = None
        try:
            produto_atual_id = int(produto_atual.get("id") or 0)
        except Exception:
            produto_atual_id = None

        for item_prod in produtos_componentes_base:
            try:
                item_id = int(item_prod.get("id") or 0)
            except Exception:
                item_id = 0

            if produto_atual_id and item_id == produto_atual_id:
                continue

            tipo_item = str(item_prod.get("tipo_produto") or "").strip().lower()

            # SmartTec: tecidos de persiana podem ter vindo do GestãoClick/Ação
            # com tipo diferente de Componente/Insumo. Mesmo assim precisam
            # entrar na base do carrinho para a categoria Tecido / material.
            if tipo_item in tipos_permitidos or eh_tecido_persiana_motor(item_prod):
                produtos_componentes_filtrados.append(item_prod)

        usar_motor_inteligente = st.checkbox(
            "Usar receita técnica oficial no cálculo",
            value=True,
            disabled=is_visualizar,
            key=f"usar_motor_inteligente_{modo}_{id_produto_editar}",
        )

        if usar_motor_inteligente:
            # Motor inteligente também deve alimentar a etapa de Valores.
            usar_custo_composicao = True

            if calcular_produto_sob_medida is None:
                st.error("Motor de cálculo não encontrado. Confirme se o arquivo está em app/services/motor_calculo_produtos.py ou services/motor_calculo_produtos.py.")
            else:
                m1, m2, m3, m4 = st.columns([1.4, 1.0, 1.0, 1.0])

                with m1:
                    modelos_calculo_padrao = [
                        "Rolô",
                        "Rolô motorizada",
                        "Romana",
                        "Romana motorizada",
                        "Painel",
                        "Double Vision",
                        "Double Vision motorizada",
                        "Cortina de tecido",
                        "Trilho motorizado",
                        "Persiana externa",
                        "Toldo",
                    ]
                    opcoes_modelo_calculo = []
                    for opc in modelos_calculo_padrao + carregar_opcoes_categoria("modelo_calculo_produto", incluir_vazio=False):
                        if opc and opc != "Selecione..." and opc not in opcoes_modelo_calculo:
                            opcoes_modelo_calculo.append(opc)
                    marcador_novo_modelo = "➕ Cadastrar novo modelo..."
                    if not is_visualizar:
                        opcoes_modelo_calculo.append(marcador_novo_modelo)

                    valor_modelo_calculo = modelo or "Rolô"
                    # Se o campo Modelo/variação for MANUAL/MOTORIZADA, usa Rolô como base.
                    if normalizar_busca_motor(valor_modelo_calculo) in ["MANUAL", "MOTORIZADA", "MOTORIZADO"]:
                        valor_modelo_calculo = "Rolô motorizada" if normalizar_busca_motor(valor_modelo_calculo) in ["MOTORIZADA", "MOTORIZADO"] else "Rolô"
                    idx_modelo_calc = indice_select(opcoes_modelo_calculo, valor_modelo_calculo, "Rolô")
                    modelo_calculo = st.selectbox(
                        "Modelo de cálculo",
                        opcoes_modelo_calculo,
                        index=idx_modelo_calc,
                        disabled=is_visualizar,
                        key=f"modelo_calculo_motor_{modo}_{id_produto_editar}",
                    )
                    if modelo_calculo == marcador_novo_modelo:
                        novo_modelo_calc = st.text_input(
                            "Novo modelo de cálculo",
                            placeholder="Ex.: Rolô motorizada 41mm",
                            key=f"novo_modelo_calculo_{modo}_{id_produto_editar}",
                        )
                        if st.button("Cadastrar modelo de cálculo", key=f"salvar_modelo_calculo_{modo}_{id_produto_editar}", type="primary"):
                            nome_limpo_modelo = str(novo_modelo_calc or "").strip()
                            if nome_limpo_modelo:
                                payload_modelo = {
                                    "categoria": "modelo_calculo_produto",
                                    "nome": nome_limpo_modelo,
                                    "descricao": "",
                                    "tipo_campo": "Texto",
                                    "obrigatorio": "Não",
                                    "situacao": "Ativo",
                                    "ordem": 0,
                                }
                                resp_modelo = criar_opcao_auxiliar(payload_modelo)
                                if resp_modelo is not None and getattr(resp_modelo, "status_code", 0) in [200, 201, 204]:
                                    st.session_state.mensagem_acao_produtos = f"✅ Modelo de cálculo '{nome_limpo_modelo}' cadastrado."
                                    st.rerun()
                            st.warning("Digite o nome do modelo de cálculo.")
                        modelo_calculo = "Rolô"

                with m2:
                    modelo_calculo_norm = normalizar_busca_motor(modelo_calculo)
                    motorizada_sugerida = any(t in modelo_calculo_norm for t in ["MOTORIZADA", "MOTORIZADO", "MOTOR"])
                    motorizada_calc = st.checkbox(
                        "Motorizada",
                        value=bool(motorizada_sugerida),
                        disabled=is_visualizar or modelo_calculo in ["Painel", "Trilho motorizado"] or motorizada_sugerida,
                        key=f"motorizada_calc_{modo}_{id_produto_editar}",
                    )
                    if motorizada_sugerida:
                        motorizada_calc = True

                with m3:
                    qtd_produto_calc = st.number_input(
                        "Qtd. produto",
                        min_value=1.0,
                        value=1.0,
                        step=1.0,
                        format="%.2f",
                        disabled=is_visualizar,
                        key=f"qtd_produto_calc_{modo}_{id_produto_editar}",
                    )

                with m4:
                    perda_motor_calc = st.number_input(
                        "Perda tecido/lona %",
                        min_value=0.0,
                        value=5.0,
                        step=1.0,
                        format="%.2f",
                        disabled=is_visualizar,
                        key=f"perda_motor_calc_{modo}_{id_produto_editar}",
                    )

                produto_base_motor_tela = dict(produto_atual or {})
                produto_base_motor_tela.update(
                    {
                        "nome": nome,
                        "linha": linha,
                        "modelo": modelo,
                        "tipo_cortina_persiana": tipo_cortina_persiana,
                        "material_tecido": material_tecido,
                        "cor": cor,
                        "largura": largura,
                        "altura": altura,
                        "comprimento": comprimento,
                        "tipo_produto": tipo_produto,
                        "grupo_produto": grupo_produto,
                    }
                )

                # Busca automática por nome DESLIGADA.
                # O motor agora deve usar somente o carrinho/receita técnica escolhida pelo usuário.
                catalogo_motor_auto = {}
                prefixo_motor_receita = f"{modo}_{id_produto_editar}_{modelo_calculo}_{'mot' if motorizada_calc else 'manual'}"
                catalogo_motor = aplicar_vinculos_tecnicos_motor(
                    catalogo_motor_auto,
                    produtos_componentes_filtrados,
                    modelo_calculo,
                    motorizada_calc,
                    prefixo_key=prefixo_motor_receita,
                    disabled=is_visualizar,
                    produto_base=produto_base_motor_tela,
                )
                modelo_motor = nome_modelo_para_motor(modelo_calculo, motorizada_calc)

                opcoes_motor = {}

                if modelo_motor.lower().startswith("rol"):
                    opcoes_motor["perda_tecido_percentual"] = perda_motor_calc
                    # Na persiana Rolô, o suporte já vem no kit/comando. Não lançar suporte separado.
                    opcoes_motor["incluir_suporte"] = False
                    # Regras técnicas SmartTec do Rolô.
                    opcoes_motor["desconto_largura_tubo_base"] = 0.025
                    opcoes_motor["desconto_largura_tecido"] = 0.03
                    opcoes_motor["sobra_altura_tecido"] = 0.15
                    opcoes_motor["altura_padrao_corrente"] = 1.50
                elif modelo_motor.lower().startswith("romana"):
                    opcoes_motor["perda_tecido_percentual"] = perda_motor_calc
                elif modelo_motor.lower().startswith("double"):
                    opcoes_motor["perda_tecido_percentual"] = perda_motor_calc
                elif "cortina" in modelo_motor.lower():
                    opcoes_motor["perda_tecido_percentual"] = perda_motor_calc
                elif "externa" in modelo_motor.lower():
                    opcoes_motor["perda_percentual"] = perda_motor_calc
                elif "toldo" in modelo_motor.lower():
                    opcoes_motor["perda_lona_percentual"] = perda_motor_calc

                try:
                    resultado_motor = calcular_produto_sob_medida(
                        modelo=modelo_motor,
                        largura=float(largura or 0),
                        altura=float(altura or 0),
                        quantidade=float(qtd_produto_calc or 1),
                        catalogo=catalogo_motor,
                        opcoes=opcoes_motor,
                    )

                    custo_motor_base = float(resultado_motor.custo_total or 0)

                    # Receita oficial não usa mais componentes extras automáticos.
                    # Tudo que entra no cálculo precisa estar no carrinho/receita técnica.
                    componentes_extras_motor = []
                    custo_extras_motor = 0.0

                    custo_composicao_final = float(custo_motor_base or 0)
                    st.session_state[f"{prefixo_motor_receita}_custo_motor_resultado"] = custo_composicao_final

                    # Receita técnica oficial: não mostrar alertas de componentes obrigatórios
                    # que não fazem parte da receita montada. Na SmartTec, quem define o que entra é a receita.
                    # Ex.: Rolô motorizada não precisa avisar Comando 38 se a receita usa motor/kit.

                    st.markdown(
                        f"""
                        <div style="border:1px solid #bfdbfe;background:#eff6ff;border-radius:6px;padding:12px 14px;margin:10px 0;">
                            <div style="font-size:13px;font-weight:700;color:#1e40af;margin-bottom:4px;">Custo calculado pelo motor</div>
                            <div style="font-size:24px;font-weight:800;color:#111827;">{moeda_br(custo_composicao_final)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    dados_componentes_motor = []
                    for componente in resultado_motor.componentes:
                        dados_componentes_motor.append({
                            "Componente": componente.nome,
                            "Categoria": componente.categoria,
                            "Regra": componente.regra,
                            "Qtd.": componente.quantidade,
                            "Unid.": componente.unidade,
                            "Custo unit.": componente.custo_unitario,
                            "Perda %": componente.perda_percentual,
                            "Total": componente.custo_total,
                        })

                    dados_componentes_motor.extend(componentes_extras_motor)

                    if dados_componentes_motor:
                        df_motor = pd.DataFrame(dados_componentes_motor)
                        st.dataframe(df_motor, use_container_width=True, hide_index=True)

                    # Receita técnica oficial: não avisar sobre componentes não vinculados automaticamente.
                    # O SmartTec agora calcula somente os itens existentes no carrinho/receita salva.
                    # Ex.: se a receita tem Tubo 32mm, não precisa alertar Tubo 38mm/Comando 38mm.

                except Exception as erro_motor:
                    st.error(f"Erro ao calcular pelo motor: {erro_motor}")

        else:
            col_comp_a, col_comp_b, col_comp_c = st.columns([1, 1, 2])
            with col_comp_a:
                qtd_linhas_composicao = st.number_input(
                    "Qtd. de componentes",
                    min_value=1,
                    max_value=20,
                    value=int(st.session_state.get(f"qtd_componentes_produto_{modo}_{id_produto_editar}", 3)),
                    step=1,
                    disabled=is_visualizar,
                    key=f"qtd_componentes_produto_{modo}_{id_produto_editar}",
                )
            with col_comp_b:
                perda_padrao_composicao = st.number_input(
                    "Perda técnica padrão (%)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    format="%.2f",
                    disabled=is_visualizar,
                    key=f"perda_padrao_comp_produto_{modo}_{id_produto_editar}",
                )
            with col_comp_c:
                usar_custo_composicao = st.checkbox(
                    "Usar custo da composição nos valores",
                    value=True,
                    disabled=is_visualizar,
                    key=f"usar_custo_comp_produto_{modo}_{id_produto_editar}",
                )

            opcoes_componentes = ["Selecione..."]
            mapa_componentes = {}

            for comp_produto in produtos_componentes_filtrados:
                try:
                    comp_id = int(comp_produto.get("id") or 0)
                except Exception:
                    comp_id = 0

                nome_comp = str(comp_produto.get("nome") or "").strip()
                if not nome_comp:
                    continue

                codigo_comp = str(comp_produto.get("codigo_interno") or comp_produto.get("codigo_barras") or comp_id).strip()
                material_comp = str(comp_produto.get("material_tecido") or "").strip()
                cor_comp = str(comp_produto.get("cor") or "").strip()
                tipo_comp_label = str(comp_produto.get("tipo_produto") or "").strip()
                custo_comp_convertido, unidade_comp_convertida = calcular_custo_motor_produto(comp_produto)

                detalhes = " • ".join([x for x in [tipo_comp_label, material_comp, cor_comp, unidade_comp_convertida, moeda_br(custo_comp_convertido)] if x])
                rotulo = f"{codigo_comp} - {nome_comp}"
                if detalhes:
                    rotulo += f" ({detalhes})"

                if rotulo in mapa_componentes:
                    rotulo = f"{rotulo} #{comp_id}"

                opcoes_componentes.append(rotulo)
                mapa_componentes[rotulo] = comp_produto

            if len(opcoes_componentes) == 1:
                st.warning("Nenhum insumo/componente encontrado. Cadastre produtos com Tipo do produto = Insumo ou Componente para usar na composição.")

            opcoes_componentes.append("Outro / manual")

            cab1, cab2, cab3, cab4, cab5, cab6 = st.columns([2.8, 0.9, 0.85, 1.15, 0.9, 1.15])
            with cab1:
                st.markdown("**Produto componente**")
            with cab2:
                st.markdown("**Qtd.**")
            with cab3:
                st.markdown("**Unid.**")
            with cab4:
                st.markdown("**Custo unit.**")
            with cab5:
                st.markdown("**Perda %**")
            with cab6:
                st.markdown("**Total**")

            totais_componentes = []

            for i in range(int(qtd_linhas_composicao)):
                comp1, comp2, comp3, comp4, comp5, comp6 = st.columns([2.8, 0.9, 0.85, 1.15, 0.9, 1.15])

                with comp1:
                    componente_escolhido = st.selectbox(
                        f"Componente {i + 1}",
                        opcoes_componentes,
                        index=0,
                        label_visibility="collapsed",
                        disabled=is_visualizar,
                        key=f"comp_produto_sel_{modo}_{id_produto_editar}_{i}",
                    )

                produto_componente = mapa_componentes.get(componente_escolhido, {})

                with comp2:
                    componente_qtd = st.number_input(
                        f"Qtd. {i + 1}",
                        min_value=0.0,
                        value=0.0,
                        step=0.01,
                        format="%.2f",
                        label_visibility="collapsed",
                        disabled=is_visualizar,
                        key=f"comp_qtd_{modo}_{id_produto_editar}_{i}",
                    )

                if componente_escolhido == "Outro / manual":
                    with comp3:
                        componente_unidade = st.text_input(
                            f"Unid. {i + 1}",
                            value="",
                            placeholder="m², ml, un",
                            label_visibility="collapsed",
                            disabled=is_visualizar,
                            key=f"comp_unidade_manual_{modo}_{id_produto_editar}_{i}",
                        )

                    with comp4:
                        componente_custo = st.number_input(
                            f"Custo unit. {i + 1}",
                            min_value=0.0,
                            value=0.0,
                            step=1.0,
                            format="%.2f",
                            label_visibility="collapsed",
                            disabled=is_visualizar,
                            key=f"comp_custo_manual_{modo}_{id_produto_editar}_{i}",
                        )
                else:
                    if produto_componente:
                        item_catalogo_manual = produto_para_item_catalogo_motor(produto_componente)
                        componente_unidade = str(item_catalogo_manual.get("unidade") or "un").strip()
                        componente_custo = float(item_catalogo_manual.get("custo_unitario") or 0)
                    else:
                        componente_unidade = ""
                        componente_custo = 0.0

                    with comp3:
                        st.markdown(
                            f"""
                            <div style="height:38px;display:flex;align-items:center;color:#374151;">
                                {html.escape(componente_unidade or "-")}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with comp4:
                        st.markdown(
                            f"""
                            <div style="height:38px;display:flex;align-items:center;color:#374151;font-weight:600;">
                                {moeda_br(componente_custo)}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                with comp5:
                    componente_perda = st.number_input(
                        f"Perda {i + 1}",
                        min_value=0.0,
                        value=float(perda_padrao_composicao or 0),
                        step=1.0,
                        format="%.2f",
                        label_visibility="collapsed",
                        disabled=is_visualizar,
                        key=f"comp_perda_{modo}_{id_produto_editar}_{i}",
                    )

                subtotal_componente = float(componente_qtd or 0) * float(componente_custo or 0)
                total_componente = subtotal_componente + (subtotal_componente * (float(componente_perda or 0) / 100))
                totais_componentes.append(total_componente)

                with comp6:
                    st.markdown(
                        f"""
                        <div style="height:38px;display:flex;align-items:center;font-weight:700;color:#111827;">
                            {moeda_br(total_componente)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            custo_composicao_final = sum(totais_componentes)

            st.markdown(
                f"""
                <div style="margin-top:10px;background:#ecfdf5;border:1px solid #bbf7d0;color:#166534;border-radius:6px;padding:12px 14px;font-weight:700;">
                    Custo calculado da composição: {moeda_br(custo_composicao_final)}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption("Modo manual: os componentes são puxados dos produtos cadastrados. O motor inteligente fica disponível acima.")
    else:
        st.markdown(
            """
            <div class="erp-blue-info">
                Para habilitar componentes, selecione <b>Possui composição? Sim</b> na seção Dados.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return custo_composicao_final, usar_custo_composicao

def telaProdutos():
    carregar_css_produtos()

    if "tela_produtos" not in st.session_state:
        st.session_state.tela_produtos = "listar"

    if "id_produto_editar" not in st.session_state:
        st.session_state.id_produto_editar = None

    if "confirmar_exclusao_produto" not in st.session_state:
        st.session_state.confirmar_exclusao_produto = None

    if "confirmar_exclusao_produto_nome" not in st.session_state:
        st.session_state.confirmar_exclusao_produto_nome = ""

    if "_ultima_acao_produto_url_processada" not in st.session_state:
        st.session_state._ultima_acao_produto_url_processada = ""

    if "_ultima_confirmacao_exclusao_url_processada" not in st.session_state:
        st.session_state._ultima_confirmacao_exclusao_url_processada = ""

    if "mostrar_busca_avancada_produtos" not in st.session_state:
        st.session_state.mostrar_busca_avancada_produtos = False

    if "filtros_busca_avancada_produtos" not in st.session_state:
        st.session_state.filtros_busca_avancada_produtos = {}

    if "_versao_calculo_valores_produto" not in st.session_state:
        st.session_state._versao_calculo_valores_produto = 0

    if "mensagem_acao_produtos" not in st.session_state:
        st.session_state.mensagem_acao_produtos = ""

    if "acao_mais_produtos" not in st.session_state:
        st.session_state.acao_mais_produtos = ""

    if "produtos_selecionados_lote" not in st.session_state:
        st.session_state.produtos_selecionados_lote = []

    if "confirmar_exclusao_produtos_lote" not in st.session_state:
        st.session_state.confirmar_exclusao_produtos_lote = False

    if "confirmar_ajuste_valores_massa" not in st.session_state:
        st.session_state.confirmar_ajuste_valores_massa = False

    if "config_ajuste_valores_massa" not in st.session_state:
        st.session_state.config_ajuste_valores_massa = {}

    def mudar_tela(tela, id_produto=None):
        st.session_state.tela_produtos = tela
        st.session_state.id_produto_editar = id_produto

    params = st.query_params

    # IMPORTANTE:
    # Processar confirmações ANTES de tratar acao_mais_produtos.
    # Se apagar acao_mais_produtos primeiro, o Streamlit pode rerodar a tela
    # e o clique do "Sim" pode não executar a ação.
    if "confirmar_ajuste_valores_massa" in params:
        decisao_ajuste = params.get("confirmar_ajuste_valores_massa", "")

        if isinstance(decisao_ajuste, (list, tuple)):
            decisao_ajuste = decisao_ajuste[0]

        config_url = params.get("ajuste_config", "")
        if isinstance(config_url, (list, tuple)):
            config_url = config_url[0]

        if config_url:
            try:
                st.session_state.config_ajuste_valores_massa = json.loads(unquote(str(config_url)))
            except Exception:
                pass

        if decisao_ajuste == "nao":
            st.session_state.confirmar_ajuste_valores_massa = False
            st.session_state.acao_mais_produtos = "ajustar_valores"
            try:
                del st.query_params["confirmar_ajuste_valores_massa"]
                del st.query_params["ajuste_config"]
            except Exception:
                pass

        elif decisao_ajuste == "sim":
            # Executa com a configuração restaurada da URL para não perder filtro/valor no clique do popup.
            executar_ajuste_valores_massa(mudar_tela)

    if "confirmar_exclusao_lote_produtos" in params:
        decisao_lote = params.get("confirmar_exclusao_lote_produtos", "")

        if isinstance(decisao_lote, (list, tuple)):
            decisao_lote = decisao_lote[0]

        if decisao_lote == "nao":
            st.session_state.confirmar_exclusao_produtos_lote = False
            st.session_state.acao_mais_produtos = "excluir_selecionados"
            try:
                del st.query_params["confirmar_exclusao_lote_produtos"]
            except Exception:
                pass

        elif decisao_lote == "sim":
            ids_lote = normalizar_ids_selecionados_produtos()
            executar_exclusao_produtos_lote(ids_lote, mudar_tela)

    if "acao_mais_produtos" in params:
        acao_url = params.get("acao_mais_produtos", "")

        if isinstance(acao_url, (list, tuple)):
            acao_url = acao_url[0]

        if acao_url:
            st.session_state.acao_mais_produtos = acao_url
            try:
                del st.query_params["acao_mais_produtos"]
            except Exception:
                pass

    if "confirmar_exclusao_produto" in params:
        decisao_exclusao = params.get("confirmar_exclusao_produto", "")
        id_excluir = params.get("id_produto", st.session_state.get("confirmar_exclusao_produto"))

        if isinstance(decisao_exclusao, (list, tuple)):
            decisao_exclusao = decisao_exclusao[0]

        if isinstance(id_excluir, (list, tuple)):
            id_excluir = id_excluir[0]

        chave_confirmacao_url = f"{decisao_exclusao}|{id_excluir}"

        # IMPORTANTE:
        # Não usar st.rerun() no "Não", senão qualquer clique seguinte parece só piscar.
        # A URL pode continuar no navegador, mas a ação não fica travando os botões.
        if st.session_state._ultima_confirmacao_exclusao_url_processada != chave_confirmacao_url:
            st.session_state._ultima_confirmacao_exclusao_url_processada = chave_confirmacao_url

            if decisao_exclusao == "nao":
                st.session_state.confirmar_exclusao_produto = None
                st.session_state.confirmar_exclusao_produto_nome = ""

            elif decisao_exclusao == "sim" and id_excluir:
                executar_exclusao_produto(int(id_excluir), mudar_tela)

    if "acao_produto" in params and "id_produto" in params:
        acao = params["acao_produto"]
        id_param = params["id_produto"]
        nome_param = params.get("nome_produto", "")

        if isinstance(acao, (list, tuple)):
            acao = acao[0]

        if isinstance(id_param, (list, tuple)):
            id_param = id_param[0]

        if isinstance(nome_param, (list, tuple)):
            nome_param = nome_param[0]

        chave_acao_url = f"{acao}|{id_param}|{nome_param}"

        # Processa link antigo da URL apenas uma vez.
        # Se não fizer isso, a URL antiga fica repetindo a ação em todo rerun.
        if st.session_state._ultima_acao_produto_url_processada != chave_acao_url:
            st.session_state._ultima_acao_produto_url_processada = chave_acao_url
            id_alvo = int(id_param)

            if acao == "visualizar":
                mudar_tela("visualizar", id_alvo)
                st.rerun()

            elif acao == "editar":
                mudar_tela("editar", id_alvo)
                st.rerun()

            elif acao == "excluir":
                st.session_state.confirmar_exclusao_produto = id_alvo
                st.session_state.confirmar_exclusao_produto_nome = str(nome_param or id_alvo)
                mudar_tela("listar")
                st.rerun()

            elif acao == "clonar":
                mudar_tela("clonar", id_alvo)
                st.rerun()

    tela_atual = st.session_state.tela_produtos

    tela_nome = {
        "listar": "Listar",
        "adicionar": "Adicionar",
        "editar": "Editar",
        "visualizar": "Visualizar",
        "clonar": "Clonar",
    }.get(tela_atual, "Listar")

    cabecalho(titulo="Produtos", modulo="Produtos", tela_atual=tela_nome)

    if tela_atual == "listar":
        col_add, col_more, col_columns, col_space, col_search, col_btn, col_advanced = st.columns(
            [1.25, 1.45, 0.45, 1.25, 2.6, 0.35, 1.55]
        )

        with col_add:
            if st.button("Adicionar +", type="primary", use_container_width=True):
                st.session_state.confirmar_exclusao_produto = None
                st.session_state.confirmar_exclusao_produto_nome = ""
                st.session_state._ultima_confirmacao_exclusao_url_processada = ""
                mudar_tela("adicionar")
                st.rerun()

        with col_more:
            if hasattr(st, "popover"):
                with st.popover("⚙️ Mais ações", use_container_width=True):
                    st.markdown("#### Mais ações")

                    if st.button("Corrigir termos comerciais", key="btn_corrigir_termos_comerciais", use_container_width=True):
                        with st.spinner("Corrigindo termos comerciais já gravados..."):
                            atualizados_termos, erros_termos = corrigir_termos_comerciais_produtos_banco()

                        if atualizados_termos:
                            st.session_state.mensagem_acao_produtos = f"✅ {atualizados_termos} produto(s) corrigido(s): DOUBLE VISION / SCREEN."
                            st.success(st.session_state.mensagem_acao_produtos)
                            time.sleep(0.4)
                            st.rerun()
                        elif erros_termos:
                            st.error("Não foi possível corrigir alguns produtos.")
                            for erro in erros_termos[:10]:
                                st.caption(erro)
                        else:
                            st.info("Nenhum produto precisou de correção.")

                    st.markdown(
                        """
                        <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=importar_planilha" target="_self">📥 Importar planilha/PDF fornecedor</a>
                        <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=importar_nfe" target="_self">🧾 Importar notas fiscais de vendas</a>
                        <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=exportar_cadastros" target="_self">📤 Exportar cadastros</a>
                        <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=ferramentas_massa" target="_self">🧰 Ferramentas em massa</a>
                        <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=ajustar_valores" target="_self">Ajustar valores em massa</a>
                        <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=aplicar_receita_rolo_manual" target="_self">⚙️ Aplicar receita base Rolô manual</a>
                        <a class="erp-mais-acoes-link" href="?go_to=produtos_etiquetas" target="_self">Etiquetas</a>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.caption("Itens liberados como links internos para evitar cursor bloqueado.")
            else:
                st.markdown(
                    """
                    <a class="erp-mais-acoes-link" href="?go_to=produtos&acao_mais_produtos=exportar_cadastros" target="_self">📤 Exportar cadastros</a>
                    <a class="erp-mais-acoes-link" href="?go_to=produtos_etiquetas" target="_self">Etiquetas</a>
                    """,
                    unsafe_allow_html=True,
                )

        with col_columns:
            renderizar_gerenciador_colunas_produtos()

        with col_space:
            st.markdown('<div class="erp-toolbar-spacer"></div>', unsafe_allow_html=True)

        with col_search:
            busca_texto = st.text_input("Buscar", placeholder="Buscar", label_visibility="collapsed")

        with col_btn:
            st.button("Buscar", use_container_width=True)

        with col_advanced:
            texto_busca_avancada = "Busca avançada" if not st.session_state.mostrar_busca_avancada_produtos else "Ocultar busca"
            if st.button(texto_busca_avancada, use_container_width=True):
                st.session_state.confirmar_exclusao_produto = None
                st.session_state.confirmar_exclusao_produto_nome = ""
                st.session_state._ultima_confirmacao_exclusao_url_processada = ""
                st.session_state.mostrar_busca_avancada_produtos = not st.session_state.mostrar_busca_avancada_produtos
                st.rerun()

        if st.session_state.get("mensagem_acao_produtos"):
            mensagem_temp = st.session_state.mensagem_acao_produtos
            st.success(mensagem_temp)
            st.session_state.mensagem_acao_produtos = ""

        if st.session_state.acao_mais_produtos:
            acao = st.session_state.acao_mais_produtos

            st.markdown('<div class="erp-busca-avancada-box">', unsafe_allow_html=True)

            if acao == "exportar_cadastros":
                st.subheader("Exportar cadastros de produtos")
                st.info("Agora você pode exportar todos os produtos ou somente um Grupo Técnico, incluindo SEM_GRUPO_TECNICO para revisão assistida.")

                produtos_base_exportar = buscar_produtos_api()
                opcoes_grupos_exportar = montar_opcoes_grupo_tecnico_filtro(produtos_base_exportar)

                col_exp_1, col_exp_2 = st.columns([2.2, 1])

                with col_exp_1:
                    grupo_tecnico_exportar = st.selectbox(
                        "Exportar por Grupo Técnico",
                        opcoes_grupos_exportar,
                        key="produtos_exportar_grupo_tecnico",
                        help="Use SEM_GRUPO_TECNICO para baixar somente os itens pendentes e mandar para análise/correção.",
                    )

                with col_exp_2:
                    formato_exportar = st.selectbox(
                        "Formato",
                        ["CSV"],
                        key="produtos_exportar_formato",
                    )

                if grupo_tecnico_exportar == "Todos":
                    produtos_para_exportar = produtos_base_exportar
                    sufixo_arquivo = "todos"
                else:
                    produtos_para_exportar = [
                        p for p in produtos_base_exportar
                        if grupo_tecnico_filtro_produto(p) == grupo_tecnico_exportar
                    ]
                    sufixo_arquivo = grupo_tecnico_exportar.lower()

                csv_produtos = gerar_csv_produtos(produtos_para_exportar)

                if csv_produtos:
                    st.success(f"Arquivo pronto com {len(produtos_para_exportar)} produto(s) em {grupo_tecnico_exportar}.")
                    st.download_button(
                        f"Baixar produtos_smarttec_{sufixo_arquivo}.csv",
                        data=csv_produtos.encode("utf-8-sig"),
                        file_name=f"produtos_smarttec_{sufixo_arquivo}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        type="primary",
                    )

                    if grupo_tecnico_exportar == "SEM_GRUPO_TECNICO":
                        st.caption("Me envie esse CSV e eu preparo as regras/ajustes para derrubarmos os pendentes em lote.")
                else:
                    st.warning("Nenhum produto disponível para exportar com esse filtro.")

            elif acao == "importar_planilha":
                st.subheader("Importar produtos de uma planilha")
                st.info("Faça upload de CSV, Excel ou PDF da Ação Distribuidora. O sistema valida, mostra uma prévia e só grava no banco quando você clicar em Importar.")

                arquivo_importacao = st.file_uploader(
                    "Selecione a planilha ou PDF",
                    type=["csv", "xlsx", "xls", "pdf"],
                    key="upload_importar_produtos",
                )

                if arquivo_importacao is not None:
                    st.success(f"Arquivo recebido: {arquivo_importacao.name}")

                    try:
                        abas_importacao = carregar_planilha_importacao_produtos(arquivo_importacao)
                        nomes_abas = list(abas_importacao.keys())

                        aba_escolhida = nomes_abas[0]
                        if len(nomes_abas) > 1:
                            prioridade_abas = ["Ação PDF", "Importar Agora", "SmartTec Importação", "Produtos Tratados"]
                            for aba_prioritaria in prioridade_abas:
                                if aba_prioritaria in nomes_abas:
                                    aba_escolhida = aba_prioritaria
                                    break

                            aba_escolhida = st.selectbox(
                                "Aba da planilha",
                                nomes_abas,
                                index=nomes_abas.index(aba_escolhida),
                                key="aba_importacao_produtos",
                            )

                        df_importacao = abas_importacao[aba_escolhida].copy()
                        df_importacao.columns = [str(c).strip() for c in df_importacao.columns]
                        df_importacao = df_importacao.dropna(how="all")

                        valido, mensagem_validacao = validar_dataframe_importacao_produtos(df_importacao)

                        if not valido:
                            st.error(mensagem_validacao)
                        else:
                            total_linhas = len(df_importacao)
                            total_ok = total_linhas
                            if "tipo_sugerido_status" in df_importacao.columns:
                                total_ok = len(
                                    df_importacao[
                                        df_importacao["tipo_sugerido_status"].astype(str).str.strip().str.upper() == "OK"
                                    ]
                                )

                            r1, r2, r3 = st.columns(3)
                            with r1:
                                st.metric("Linhas na aba", total_linhas)
                            with r2:
                                st.metric("Liberadas para importar", total_ok)
                            with r3:
                                st.metric("Aba selecionada", aba_escolhida)

                            achados_termos = auditar_termos_importacao_dataframe(df_importacao)
                            if achados_termos:
                                st.error("Atenção: a planilha contém termos já traduzidos que não devem ser importados.")
                                for achado in achados_termos:
                                    st.caption(f"{achado['coluna']}: {achado['qtd']} ocorrência(s) de {achado['termo']}. Exemplos: {', '.join(achado['exemplos'][:3])}")
                            else:
                                st.success("✅ Conferência de termos: planilha sem VISÃO DUPLA/RASTREIO. Importador vai salvar os nomes como estão e aplicar conversão inteligente inicial de custo quando detectar tecido/barra/rolo.")

                            st.markdown("#### Prévia")
                            colunas_previas = [
                                c for c in [
                                    "codigo_interno",
                                    "codigo_barras",
                                    "nome",
                                    "grupo_produto",
                                    "tipo_produto",
                                    "unidade_venda",
                                    "material_tecido",
                                    "cor",
                                    "valor_custo",
                                    "valor_venda",
                                    "estoque_atual",
                                    "situacao",
                                    "tipo_sugerido_status",
                                ]
                                if c in df_importacao.columns
                            ]
                            st.dataframe(df_importacao[colunas_previas].head(20), use_container_width=True, hide_index=True)

                            somente_ok = True
                            if "tipo_sugerido_status" in df_importacao.columns:
                                somente_ok = st.checkbox(
                                    "Importar somente linhas com status OK",
                                    value=True,
                                    key="importar_produtos_somente_ok",
                                )

                            modo_existentes_importacao = st.radio(
                                "Quando encontrar produto existente:",
                                [
                                    "Pular produto existente",
                                    "Atualizar/substituir produto existente",
                                ],
                                index=0,
                                horizontal=True,
                                key="modo_existentes_importacao_produtos",
                            )
                            modo_existentes_importacao_valor = "atualizar" if modo_existentes_importacao.startswith("Atualizar") else "pular"
                            pular_existentes = modo_existentes_importacao_valor == "pular"

                            criterio_importacao_label = st.radio(
                                "Como detectar duplicidade:",
                                [
                                    "Código interno/código de barras OU nome",
                                    "Somente código interno/código de barras",
                                    "Somente nome",
                                ],
                                index=0,
                                horizontal=False,
                                key="criterio_duplicidade_importacao_produtos",
                            )

                            if criterio_importacao_label.startswith("Somente código"):
                                criterio_importacao_valor = "codigo"
                            elif criterio_importacao_label.startswith("Somente nome"):
                                criterio_importacao_valor = "nome"
                            else:
                                criterio_importacao_valor = "codigo_ou_nome"

                            usar_limite_teste = st.checkbox(
                                "Importar apenas uma quantidade para teste",
                                value=True,
                                key="importar_produtos_usar_limite_teste",
                            )

                            limite_importacao = None
                            if usar_limite_teste:
                                limite_importacao = st.number_input(
                                    "Quantidade para teste",
                                    min_value=1,
                                    max_value=max(1, int(total_ok or total_linhas or 1)),
                                    value=min(50, max(1, int(total_ok or total_linhas or 1))),
                                    step=10,
                                    key="importar_produtos_limite_teste",
                                )

                            try:
                                resumo_importacao = calcular_resumo_importacao_produtos(
                                    df_importacao,
                                    somente_ok=somente_ok,
                                    limite=limite_importacao,
                                    criterio=criterio_importacao_valor,
                                )

                                st.info(
                                    f"Pré-conferência: {resumo_importacao['existentes']} produto(s) existente(s) serão "
                                    f"{'atualizados' if modo_existentes_importacao_valor == 'atualizar' else 'pulados'} e "
                                    f"{resumo_importacao['novos']} produto(s) novo(s) serão criados. "
                                    f"Total processado: {resumo_importacao['total']}."
                                )

                                if resumo_importacao["exemplos_existentes"]:
                                    with st.expander("Exemplos de produtos existentes detectados"):
                                        for exemplo in resumo_importacao["exemplos_existentes"]:
                                            st.caption(exemplo)

                                if resumo_importacao["exemplos_novos"]:
                                    with st.expander("Exemplos de produtos novos"):
                                        for exemplo in resumo_importacao["exemplos_novos"]:
                                            st.caption(exemplo)

                            except Exception as erro_resumo:
                                st.warning(f"Não foi possível calcular a pré-conferência de duplicidade: {erro_resumo}")

                            st.warning("Antes de importar tudo, faça um teste com 20 a 50 produtos. Depois confira Listar, Visualizar, Editar e Composição.")

                            c_imp1, c_imp2 = st.columns([0.9, 4])
                            with c_imp1:
                                if st.button("Importar", key="btn_confirmar_importacao_produtos", type="primary"):
                                    resultado = importar_produtos_dataframe(
                                            df_importacao,
                                            somente_ok=somente_ok,
                                            pular_existentes=pular_existentes,
                                            limite=limite_importacao,
                                            modo_existentes=modo_existentes_importacao_valor,
                                            criterio=criterio_importacao_valor,
                                        )

                                    total_importados = int(resultado.get("importados", 0) or 0)
                                    total_atualizados = int(resultado.get("atualizados", 0) or 0)
                                    total_pulados = int(resultado.get("pulados", 0) or 0)
                                    total_erros = len(resultado.get("erros", []) or [])

                                    if total_importados > 0 or total_atualizados > 0:
                                        st.session_state.mensagem_acao_produtos = (
                                            f"✅ Importação concluída. "
                                            f"Criados: {total_importados}. "
                                            f"Atualizados: {total_atualizados}. "
                                            f"Pulados: {total_pulados}. "
                                            f"Erros: {total_erros}."
                                        )
                                        st.session_state.acao_mais_produtos = ""
                                        st.rerun()
                                    else:
                                        st.warning(
                                            f"Nenhum produto criado ou atualizado. "
                                            f"Criados: {total_importados}. "
                                            f"Atualizados: {total_atualizados}. "
                                            f"Pulados: {total_pulados}. "
                                            f"Erros: {total_erros}."
                                        )

                                    if resultado.get("erros"):
                                        st.error("Alguns itens não foram importados/atualizados. Veja os primeiros erros abaixo:")
                                        for erro in resultado["erros"][:10]:
                                            st.write(f"- {erro}")

                            with c_imp2:
                                st.caption("O importador usa os campos da planilha preparada para o SmartTec e mantém os termos exatamente como estão cadastrados, incluindo SCREEN.")

                    except Exception as e:
                        st.error(f"Erro ao ler a planilha: {e}")

            elif acao == "importar_nfe":
                st.subheader("Importar notas fiscais de vendas")
                st.info("Área preparada para importar XML de NF-e/NFC-e depois. Ela ficará ligada ao módulo Fiscal/Notas.")

            elif acao == "saneamento_base":
                st.subheader("Saneamento da base")
                st.info("Classifica Grupo, Grupo Técnico e Tipo Produto com regras seguras. Nada é alterado sem clicar em Aplicar saneamento.")

                produtos_saneamento = buscar_produtos_api()
                linhas_saneamento, resumo_saneamento = montar_relatorio_saneamento(produtos_saneamento)

                if resumo_saneamento:
                    st.markdown("### Resumo por Grupo Técnico")
                    df_resumo = pd.DataFrame([
                        {"Grupo Técnico": k, "Quantidade": v}
                        for k, v in sorted(resumo_saneamento.items(), key=lambda item: item[0])
                    ])
                    st.dataframe(df_resumo, use_container_width=True, hide_index=True)

                st.markdown("### Prévia das correções")
                if not linhas_saneamento:
                    st.success("Nenhuma correção automática pendente encontrada.")
                else:
                    st.warning(f"{len(linhas_saneamento)} produto(s) com correção automática sugerida.")
                    df_prev = pd.DataFrame([{k: v for k, v in linha.items() if k != "updates"} for linha in linhas_saneamento])
                    st.dataframe(df_prev.head(300), use_container_width=True, hide_index=True)
                    if len(df_prev) > 300:
                        st.caption("Mostrando os primeiros 300 itens para não pesar a tela. A aplicação considera todos os itens listados.")

                    st.markdown("#### Regras principais aplicadas")
                    st.markdown("""
                    - **CORTINA DOUBLE VISION** vira **PERSIANA DOUBLE VISION**.
                    - **DOUBLE VISION** sem prefixo vira **TECIDOS_DOUBLE_VISION**.
                    - **Tecidos de persiana** viram **TECIDOS_ROLO_ROMANA_PAINEL**.
                    - **Componentes genéricos da Ação/SmartTec** são enviados para o grupo técnico mais provável.
                    - **Vertical** usa **LAMINAS_VERTICAL** / **COMPONENTES_VERTICAL** e continua inativo.
                    - **Horizontal** usa **LAMINAS_HORIZONTAL** / **COMPONENTES_HORIZONTAL**.
                    - **Plissada, Shangri-lá e Celular** entram como tecidos próprios.
                    - Tabela Wiler Movelaria entra em **TECIDOS_TAPECARIA**.
                    - Cortinas Wiler entram em **TECIDOS_CORTINAS** ou **COMPONENTES_CORTINAS**.
                    - Motores e acessórios ficam globais em **MOTORES** e **ACESSORIOS_MOTOR**.
                    """)

                    confirmar = st.checkbox(
                        "Conferi a prévia e quero aplicar o saneamento automático.",
                        key="confirmar_saneamento_base_produtos",
                    )

                    c_aplicar, c_cancelar, _ = st.columns([1.2, 1.0, 3.8])
                    with c_aplicar:
                        if st.button("Aplicar saneamento", key="aplicar_saneamento_base_produtos", type="primary", disabled=not confirmar, use_container_width=True):
                            atualizados = 0
                            erros = []
                            for linha in linhas_saneamento:
                                pid = int(linha.get("id") or 0)
                                produto_original = next((p for p in produtos_saneamento if int(p.get("id") or 0) == pid), None)
                                if not produto_original:
                                    continue
                                payload = montar_payload_produto_massa(produto_original)
                                payload.update(linha.get("updates") or {})
                                try:
                                    resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                    if resp is not None and resp.status_code in [200, 201, 204]:
                                        atualizados += 1
                                    else:
                                        status = getattr(resp, "status_code", "sem resposta")
                                        erros.append(f"Produto {pid}: status {status}")
                                except Exception as e:
                                    erros.append(f"Produto {pid}: {e}")

                            if atualizados:
                                st.session_state.mensagem_acao_produtos = f"✅ Saneamento aplicado em {atualizados} produto(s)."
                            if erros:
                                st.error("Alguns produtos não puderam ser atualizados:")
                                for erro in erros[:15]:
                                    st.caption(erro)
                            if atualizados and not erros:
                                st.rerun()

                    with c_cancelar:
                        if st.button("Fechar", key="fechar_saneamento_base_produtos", use_container_width=True):
                            st.session_state.acao_mais_produtos = ""
                            st.rerun()

            elif acao == "aplicar_receita_rolo_manual":
                st.subheader("Aplicar receita base Rolô manual")
                st.info(
                    "Modo plug and play: o sistema cria a receita técnica oficial nos produtos finais PERSIANA_ROLO manuais, "
                    "sem mexer nos componentes cadastrados e sem aplicar em motorizadas. Marque itens na lista abaixo para aplicar só nos selecionados, ou deixe sem seleção para aplicar em todos. Confira a prévia antes de gravar."
                )

                produtos_base_receita = buscar_produtos_api()

                candidatos_receita_rolo = [
                    p for p in produtos_base_receita
                    if eh_produto_final_rolo_manual_para_receita(p)
                ]

                st.markdown("#### Selecionar produtos para aplicar")
                st.caption(
                    "Para não pesar o sistema, esta etapa agora é fragmentada: filtre por nome/cor e carregue uma página pequena por vez. "
                    "Motorizadas, componentes e peças continuam bloqueados automaticamente."
                )

                c_filtro_receita, c_por_pagina_receita, c_pagina_receita = st.columns([3.2, 1.0, 1.0])
                with c_filtro_receita:
                    termo_selecao_receita = st.text_input(
                        "Filtrar candidatos",
                        value=st.session_state.get("filtro_receita_rolo_manual", ""),
                        key="filtro_receita_rolo_manual",
                        placeholder="Ex.: Nápoles, BK, screen, translúcida, branco...",
                    )
                with c_por_pagina_receita:
                    qtd_pagina_receita = st.selectbox(
                        "Itens por página",
                        [10, 25, 50],
                        index=1,
                        key="qtd_pagina_receita_rolo_manual",
                    )
                termo_norm_receita = normalizar_busca_motor(termo_selecao_receita)

                candidatos_filtrados_receita = []
                for prod_cand in candidatos_receita_rolo:
                    texto_cand = normalizar_busca_motor(
                        f"{prod_cand.get('codigo_interno','')} {prod_cand.get('codigo_barras','')} {prod_cand.get('nome','')} {prod_cand.get('cor','')} {grupo_tecnico_label(prod_cand)}"
                    )
                    if not termo_norm_receita or termo_norm_receita in texto_cand:
                        candidatos_filtrados_receita.append(prod_cand)

                total_filtrado_receita = len(candidatos_filtrados_receita)
                total_paginas_receita = max(1, math.ceil(total_filtrado_receita / int(qtd_pagina_receita or 25)))
                pagina_atual_receita = int(st.session_state.get("pagina_receita_rolo_manual", 1) or 1)
                pagina_atual_receita = max(1, min(pagina_atual_receita, total_paginas_receita))
                with c_pagina_receita:
                    pagina_atual_receita = st.number_input(
                        "Página",
                        min_value=1,
                        max_value=total_paginas_receita,
                        value=pagina_atual_receita,
                        step=1,
                        key="pagina_receita_rolo_manual_input",
                    )

                # Guarda a página atual em uma chave separada do widget.
                # Isso evita o erro do Streamlit:
                # "cannot be modified after the widget with key ... is instantiated".
                st.session_state.pagina_receita_rolo_manual = int(pagina_atual_receita)

                inicio_receita = (int(pagina_atual_receita) - 1) * int(qtd_pagina_receita)
                fim_receita = inicio_receita + int(qtd_pagina_receita)
                candidatos_pagina_receita = candidatos_filtrados_receita[inicio_receita:fim_receita]

                st.caption(
                    f"Encontrados: {total_filtrado_receita} de {len(candidatos_receita_rolo)} candidato(s) PERSIANA_ROLO manual. "
                    f"Exibindo {inicio_receita + 1 if total_filtrado_receita else 0}-{min(fim_receita, total_filtrado_receita)}."
                )

                c_sel_todos, c_limpar_sel, c_ant, c_prox = st.columns([1.5, 1.2, 1.0, 1.0])
                with c_sel_todos:
                    if st.button("Selecionar página", key="selecionar_pagina_receita_rolo_manual", use_container_width=True, disabled=not candidatos_pagina_receita):
                        ids_atuais = set(normalizar_ids_selecionados_produtos())
                        for prod_cand in candidatos_pagina_receita:
                            try:
                                ids_atuais.add(int(prod_cand.get("id") or 0))
                            except Exception:
                                pass
                        st.session_state.produtos_selecionados_lote = list(ids_atuais)
                        st.rerun()
                with c_limpar_sel:
                    if st.button("Limpar seleção", key="limpar_selecao_receita_rolo_manual", use_container_width=True):
                        st.session_state.produtos_selecionados_lote = []
                        st.rerun()
                with c_ant:
                    if st.button("Anterior", key="pagina_receita_rolo_manual_ant", use_container_width=True, disabled=pagina_atual_receita <= 1):
                        st.session_state.pagina_receita_rolo_manual = max(1, int(pagina_atual_receita) - 1)
                        st.rerun()
                with c_prox:
                    if st.button("Próxima", key="pagina_receita_rolo_manual_prox", use_container_width=True, disabled=pagina_atual_receita >= total_paginas_receita):
                        st.session_state.pagina_receita_rolo_manual = min(total_paginas_receita, int(pagina_atual_receita) + 1)
                        st.rerun()

                ids_receita_selecionados = normalizar_ids_selecionados_produtos()

                if candidatos_pagina_receita:
                    st.markdown("##### Lista de seleção")
                    h_cols = st.columns([0.45, 1.0, 3.0, 0.9, 1.2])
                    h_cols[0].markdown("**☑**")
                    h_cols[1].markdown("**Código**")
                    h_cols[2].markdown("**Produto**")
                    h_cols[3].markdown("**Cor**")
                    h_cols[4].markdown("**Grupo técnico**")

                    for prod_cand in candidatos_pagina_receita:
                        pid_cand = int(prod_cand.get("id") or 0)
                        r_cols = st.columns([0.45, 1.0, 3.0, 0.9, 1.2])
                        with r_cols[0]:
                            marcado = st.checkbox(
                                "Selecionar para receita",
                                value=pid_cand in ids_receita_selecionados,
                                key=f"selecionar_receita_rolo_manual_{pid_cand}",
                                label_visibility="collapsed",
                            )
                            selecionar_produto_lote(pid_cand, marcado)
                        r_cols[1].caption(str(prod_cand.get("codigo_interno") or prod_cand.get("codigo_barras") or ""))
                        r_cols[2].caption(str(prod_cand.get("nome") or ""))
                        r_cols[3].caption(str(prod_cand.get("cor") or ""))
                        try:
                            grupo_cand = grupo_tecnico_label(prod_cand)
                        except Exception:
                            grupo_cand = prod_cand.get("grupo_tecnico") or ""
                        r_cols[4].caption(str(grupo_cand))
                elif termo_norm_receita:
                    st.warning("Nenhum candidato encontrado com esse filtro.")
                else:
                    st.info("Digite um filtro ou use as páginas para selecionar os produtos Rolô manuais.")

                ids_receita_selecionados = normalizar_ids_selecionados_produtos()
                aplicar_todos_sem_selecao = st.checkbox(
                    "Se nada estiver marcado, aplicar em todos os candidatos PERSIANA_ROLO manuais.",
                    key="aplicar_receita_rolo_manual_todos_sem_selecao",
                    value=False,
                )
                ids_para_previa = ids_receita_selecionados if ids_receita_selecionados else (None if aplicar_todos_sem_selecao else [])
                linhas_receita = montar_prev_aplicacao_receita_rolo_manual(produtos_base_receita, ids_para_previa)

                # =========================================================
                # BOTÃO VISÍVEL - APLICAÇÃO RÁPIDA DA RECEITA BASE ROLÔ
                # Correção v29: o botão principal ficava depois da prévia,
                # fora da área visível. Agora aparece logo abaixo da seleção.
                # =========================================================
                st.markdown("---")
                col_aplicar_receita_visivel, col_fechar_receita_visivel = st.columns([2, 1])

                with col_aplicar_receita_visivel:
                    if st.button(
                        "Aplicar receita base Rolô manual",
                        key="btn_aplicar_receita_base_rolo_manual_visivel",
                        type="primary",
                        use_container_width=True,
                        disabled=not linhas_receita,
                    ):
                        atualizados = 0
                        pulados = 0
                        erros = []

                        for linha in linhas_receita:
                            pid = int(linha.get("id") or 0)
                            carrinho = linha.get("carrinho") or []
                            faltantes = str(linha.get("faltantes") or "").strip()
                            produto_original = next(
                                (p for p in produtos_base_receita if int(p.get("id") or 0) == pid),
                                None,
                            )

                            if not produto_original:
                                pulados += 1
                                continue

                            if faltantes or not carrinho:
                                pulados += 1
                                continue

                            # Segurança: se já tiver receita salva, não sobrescreve por este botão rápido.
                            # Para sobrescrever, use a prévia completa mais abaixo e marque a opção de substituição.
                            if linha.get("ja_tem_receita") == "Sim":
                                pulados += 1
                                continue

                            payload = montar_payload_produto_massa(produto_original)
                            payload["possui_composicao"] = "Sim"
                            payload["observacoes"] = embutir_receita_tecnica_observacoes(
                                produto_original.get("observacoes"),
                                carrinho,
                            )

                            try:
                                resp = atualizar_produto(
                                    pid,
                                    preservar_payload_termos_comerciais(payload),
                                )

                                if resp is not None and resp.status_code in [200, 201, 204]:
                                    atualizados += 1
                                else:
                                    status = getattr(resp, "status_code", "sem resposta")
                                    erros.append(f"Produto {pid}: status {status}")

                            except Exception as e:
                                erros.append(f"Produto {pid}: {e}")

                        if atualizados:
                            st.success(f"✅ Receita base Rolô manual aplicada em {atualizados} produto(s).")

                        if pulados:
                            st.warning(
                                f"⚠️ {pulados} produto(s) foram pulados por falta de componentes, receita já existente ou regra de segurança."
                            )

                        if erros:
                            st.error("Alguns produtos não puderam ser atualizados:")
                            for erro in erros[:20]:
                                st.caption(erro)

                        if atualizados and not erros:
                            st.session_state.mensagem_acao_produtos = f"✅ Receita base Rolô manual aplicada em {atualizados} produto(s)."
                            st.session_state.acao_mais_produtos = ""
                            st.rerun()

                with col_fechar_receita_visivel:
                    if st.button(
                        "Fechar",
                        key="btn_fechar_receita_rolo_manual_visivel",
                        use_container_width=True,
                    ):
                        st.session_state.acao_mais_produtos = ""
                        st.rerun()

                st.markdown("---")

                if ids_receita_selecionados:
                    st.caption(f"Modo selecionados: {len(ids_receita_selecionados)} produto(s) marcado(s). A receita será avaliada somente nesses itens.")
                elif aplicar_todos_sem_selecao:
                    st.caption("Nenhum item marcado. A prévia considera todos os produtos finais PERSIANA_ROLO manuais encontrados.")
                else:
                    st.caption("Marque produtos na lista acima ou habilite a opção de aplicar em todos para gerar a prévia.")

                if not linhas_receita:
                    if ids_receita_selecionados:
                        st.warning("Nenhum dos produtos selecionados é PERSIANA_ROLO manual válido para aplicar a receita base. Confira se não são motorizados ou componentes.")
                    elif not aplicar_todos_sem_selecao:
                        st.warning("Nenhum produto marcado para gerar prévia.")
                    else:
                        st.warning("Nenhum produto final PERSIANA_ROLO manual encontrado para aplicar a receita base.")
                    if st.button("Fechar", key="fechar_aplicar_receita_rolo_manual_sem_itens", use_container_width=True):
                        st.session_state.acao_mais_produtos = ""
                        st.rerun()
                else:
                    df_prev_receita = pd.DataFrame([
                        {k: v for k, v in linha.items() if k != "carrinho"}
                        for linha in linhas_receita
                    ])
                    st.success(f"{len(linhas_receita)} produto(s) PERSIANA_ROLO manual encontrado(s).")
                    st.dataframe(df_prev_receita, use_container_width=True, hide_index=True)

                    com_faltantes = [l for l in linhas_receita if str(l.get("faltantes") or "").strip()]
                    ja_tem = [l for l in linhas_receita if l.get("ja_tem_receita") == "Sim"]

                    if com_faltantes:
                        st.warning(
                            f"{len(com_faltantes)} produto(s) ainda têm item faltante. "
                            "Eles não serão atualizados nesta rodada para não salvar receita incompleta."
                        )
                    if ja_tem:
                        st.warning(
                            f"{len(ja_tem)} produto(s) já possuem receita salva. "
                            "Por segurança, eles só serão sobrescritos se você marcar a opção abaixo."
                        )

                    substituir_receitas = st.checkbox(
                        "Substituir receitas já existentes nos produtos PERSIANA_ROLO manuais.",
                        key="substituir_receita_rolo_manual_existente",
                        value=False,
                    )
                    confirmar_receita = st.checkbox(
                        "Conferi a prévia e quero aplicar a receita base Rolô manual.",
                        key="confirmar_aplicar_receita_rolo_manual",
                    )

                    c_apply, c_close, _ = st.columns([1.4, 1.0, 3.6])
                    with c_apply:
                        if st.button(
                            "Aplicar receita base",
                            key="btn_aplicar_receita_base_rolo_manual",
                            type="primary",
                            disabled=not confirmar_receita,
                            use_container_width=True,
                        ):
                            atualizados = 0
                            pulados = 0
                            erros = []

                            for linha in linhas_receita:
                                pid = int(linha.get("id") or 0)
                                carrinho = linha.get("carrinho") or []
                                faltantes = str(linha.get("faltantes") or "").strip()
                                produto_original = next((p for p in produtos_base_receita if int(p.get("id") or 0) == pid), None)
                                if not produto_original:
                                    pulados += 1
                                    continue
                                if faltantes or not carrinho:
                                    pulados += 1
                                    continue
                                if linha.get("ja_tem_receita") == "Sim" and not substituir_receitas:
                                    pulados += 1
                                    continue

                                payload = montar_payload_produto_massa(produto_original)
                                payload["possui_composicao"] = "Sim"
                                payload["observacoes"] = embutir_receita_tecnica_observacoes(
                                    produto_original.get("observacoes"),
                                    carrinho,
                                )

                                try:
                                    resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                    if resp is not None and resp.status_code in [200, 201, 204]:
                                        atualizados += 1
                                    else:
                                        status = getattr(resp, "status_code", "sem resposta")
                                        erros.append(f"Produto {pid}: status {status}")
                                except Exception as e:
                                    erros.append(f"Produto {pid}: {e}")

                            st.session_state.mensagem_acao_produtos = (
                                f"✅ Receita base Rolô manual aplicada. Atualizados: {atualizados}. Pulados: {pulados}. Erros: {len(erros)}."
                            )
                            if erros:
                                st.error("Alguns produtos não puderam ser atualizados:")
                                for erro in erros[:20]:
                                    st.caption(erro)
                            else:
                                st.rerun()

                    with c_close:
                        if st.button("Fechar", key="fechar_aplicar_receita_rolo_manual", use_container_width=True):
                            st.session_state.acao_mais_produtos = ""
                            st.rerun()

            elif acao == "ajustar_valores":
                st.subheader("Ajustar valores em massa")
                st.info("Filtre os produtos. Depois escolha se deseja aumentar ou diminuir os valores encontrados.")

                produtos_base_ajuste = buscar_produtos_api()

                grupos_disponiveis = ["Todos"]
                try:
                    grupos_disponiveis += sorted({
                        str(p.get("grupo_produto") or "").strip()
                        for p in produtos_base_ajuste
                        if str(p.get("grupo_produto") or "").strip()
                    })
                except Exception:
                    pass

                if "ajuste_valores_busca_executada" not in st.session_state:
                    st.session_state.ajuste_valores_busca_executada = False

                if "ajuste_valores_popup_operacao" not in st.session_state:
                    st.session_state.ajuste_valores_popup_operacao = ""

                st.markdown("### 1. Filtrar produtos")

                f1, f2, f3 = st.columns(3)
                with f1:
                    filtro_grupo = st.selectbox("Grupo", grupos_disponiveis, key="filtro_grupo_ajuste_valores_massa")
                with f2:
                    filtro_nome = st.text_input("Nome", key="filtro_nome_ajuste_valores_massa")
                with f3:
                    filtro_codigo = st.text_input("Código", key="filtro_codigo_ajuste_valores_massa")

                f4, f5, f6 = st.columns(3)
                with f4:
                    st.selectbox("Ativo", ["Todos", "Sim", "Não"], key="filtro_ativo_ajuste_valores_massa")
                with f5:
                    filtro_situacao = st.selectbox("Situação", ["Todos", "Ativo", "Inativo"], key="filtro_situacao_ajuste_valores_massa")
                with f6:
                    st.text_input("Nº da compra", key="filtro_compra_ajuste_valores_massa", placeholder="Em breve", disabled=True)

                config_filtro = {
                    "grupo": filtro_grupo,
                    "nome": filtro_nome,
                    "codigo": filtro_codigo,
                    "situacao": filtro_situacao,
                    "modelo": "",
                    "largura": "",
                    "motor": "",
                }

                b1, b2, _ = st.columns([0.8, 0.8, 4])
                with b1:
                    if st.button("Buscar", key="buscar_ajuste_valores_massa"):
                        st.session_state.ajuste_valores_busca_executada = True
                        st.session_state.ajuste_valores_popup_operacao = ""
                        st.rerun()

                with b2:
                    if st.button("Limpar", key="limpar_ajuste_valores_massa"):
                        for chave in [
                            "filtro_nome_ajuste_valores_massa",
                            "filtro_codigo_ajuste_valores_massa",
                        ]:
                            st.session_state[chave] = ""
                        st.session_state.ajuste_valores_busca_executada = False
                        st.session_state.ajuste_valores_popup_operacao = ""
                        st.rerun()

                produtos_preview = []

                if st.session_state.ajuste_valores_busca_executada:
                    produtos_preview = filtrar_produtos_ajuste_massa(produtos_base_ajuste, config_filtro)

                    if produtos_preview:
                        st.success(f"{len(produtos_preview)} produto(s) encontrado(s) para o ajuste.")
                        st.markdown("### 2. Produtos encontrados")

                        df_prev = pd.DataFrame(produtos_preview).fillna("")
                        colunas_prev = [
                            c for c in [
                                "id",
                                "codigo_interno",
                                "nome",
                                "grupo_produto",
                                "valor_custo",
                                "custo_final",
                                "margem_lucro",
                                "valor_venda",
                                "situacao",
                            ]
                            if c in df_prev.columns
                        ]
                        st.dataframe(df_prev[colunas_prev].head(100), use_container_width=True, hide_index=True)

                        st.markdown("### 3. Aplicar reajuste")
                        ac1, ac2, ac3 = st.columns([0.55, 0.55, 3.0])

                        with ac1:
                            if st.button("Aumentar", key="abrir_popup_aumentar_valores_massa", type="primary", use_container_width=True):
                                st.session_state.ajuste_valores_popup_operacao = "Aumentar"
                                st.rerun()

                        with ac2:
                            if st.button("Diminuir", key="abrir_popup_diminuir_valores_massa", use_container_width=True):
                                st.session_state.ajuste_valores_popup_operacao = "Reduzir"
                                st.rerun()

                    else:
                        st.warning("Nenhum produto encontrado com os filtros informados.")

                operacao_popup = st.session_state.get("ajuste_valores_popup_operacao", "")

                def renderizar_formulario_ajuste_valores():
                    tabelas_venda = carregar_tabelas_valores_venda()

                    tipo_valor_ajuste = st.selectbox(
                        "Tipo",
                        ["Lucro utilizado", "Valor de venda"],
                        key="tipo_valor_ajuste_massa_produtos_popup",
                    )

                    st.markdown("##### Tabelas de venda")
                    col_tabelas = st.columns(3)
                    tabelas_selecionadas = []

                    for i, tabela in enumerate(tabelas_venda):
                        nome_tabela = tabela.get("nome", f"Tabela {i+1}")
                        with col_tabelas[i % 3]:
                            marcado = st.checkbox(
                                nome_tabela,
                                value=True,
                                key=f"ajuste_valores_tabela_{i}_{nome_tabela}",
                            )
                            if marcado:
                                tabelas_selecionadas.append(nome_tabela)

                    p1, p2 = st.columns([1, 2])
                    with p1:
                        tipo_ajuste = st.selectbox(
                            "Formato",
                            ["Percentual", "Valor fixo"],
                            key="tipo_ajuste_massa_produtos_popup",
                        )

                    with p2:
                        if tipo_ajuste == "Percentual":
                            label_valor = "Porcentagem a aumentar" if operacao_popup == "Aumentar" else "Porcentagem a diminuir"
                        else:
                            label_valor = "Valor a aumentar" if operacao_popup == "Aumentar" else "Valor a diminuir"

                        valor_ajuste = st.number_input(
                            label_valor,
                            value=0.0,
                            step=1.0,
                            format="%.2f",
                            key="valor_ajuste_massa_produtos_popup",
                        )

                    _, c_cancelar, c_aplicar = st.columns([4, 0.8, 0.8])
                    with c_cancelar:
                        if st.button("Cancelar", key="cancelar_popup_ajuste_valores_massa"):
                            st.session_state.ajuste_valores_popup_operacao = ""
                            st.rerun()

                    with c_aplicar:
                        if st.button("Aplicar", key="aplicar_popup_ajuste_valores_massa", type="primary"):
                            if float(valor_ajuste or 0) <= 0:
                                st.warning("Informe um valor maior que zero.")
                            elif not produtos_preview:
                                st.warning("Nenhum produto encontrado para aplicar o ajuste.")
                            elif not tabelas_selecionadas:
                                st.warning("Selecione pelo menos uma tabela de venda.")
                            else:
                                config_aplicar = dict(config_filtro)
                                config_aplicar.update({
                                    "tipo_valor": tipo_valor_ajuste,
                                    "tipo": tipo_ajuste,
                                    "operacao": operacao_popup,
                                    "valor": valor_ajuste,
                                    "tabelas_venda": tabelas_selecionadas,
                                })

                                st.session_state.config_ajuste_valores_massa = config_aplicar
                                st.session_state.ajuste_valores_popup_operacao = ""
                                executar_ajuste_valores_massa(mudar_tela)

                if operacao_popup:
                    titulo_popup = f"{operacao_popup} valor de venda"

                    dialog_decorator = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)

                    if dialog_decorator:

                        @dialog_decorator(titulo_popup)
                        def dialog_ajuste_valores():
                            renderizar_formulario_ajuste_valores()

                        dialog_ajuste_valores()
                    else:
                        st.markdown("---")
                        st.warning("Sua versão do Streamlit não tem popup nativo. O formulário será exibido abaixo sem travar o sistema.")
                        st.markdown(f"### {'➕' if operacao_popup == 'Aumentar' else '➖'} {titulo_popup}")
                        renderizar_formulario_ajuste_valores()

            elif acao == "ajustar_produtos":
                st.subheader("Edição em massa")
                st.info("Escolha o campo para alteração e edite somente os produtos marcados. O sistema salva apenas os selecionados. Grupo = comercial/estoque. Grupo técnico = motor/cálculo.")

                if st.session_state.get("resetar_campo_edicao_massa_produtos"):
                    if "campo_edicao_massa_produtos" in st.session_state:
                        del st.session_state["campo_edicao_massa_produtos"]
                    st.session_state.resetar_campo_edicao_massa_produtos = False

                if st.session_state.get("mensagem_edicao_massa_produtos"):
                    mensagem_temp_edicao = st.session_state.get("mensagem_edicao_massa_produtos")
                    st.success(mensagem_temp_edicao)
                    st.session_state.mensagem_edicao_massa_produtos = ""

                produtos_base_edicao = buscar_produtos_api()

                if not produtos_base_edicao:
                    st.info("Nenhum produto encontrado para edição em massa.")
                else:
                    df_edicao = pd.DataFrame(produtos_base_edicao).fillna("")

                    try:
                        termo_busca_massa = str(busca_texto or "").strip()
                    except Exception:
                        termo_busca_massa = ""

                    # SmartTec v24: busca flexível na edição em massa.
                    # Agora pesquisar "persiana rolo" encontra PERSIANA_ROLO,
                    # mesmo que o texto esteja salvo com underline ou acento.
                    # Também inclui o grupo técnico efetivo/inferido na busca.
                    if not df_edicao.empty:
                        df_edicao["_grupo_tecnico_filtro_edicao"] = df_edicao.apply(
                            lambda linha: grupo_tecnico_filtro_produto(linha.to_dict()),
                            axis=1,
                        )

                    if termo_busca_massa:
                        mask_busca = pd.Series([False] * len(df_edicao), index=df_edicao.index)
                        for campo in [
                            "nome",
                            "codigo_interno",
                            "codigo_barras",
                            "grupo_produto",
                            "modelo_tecnico",
                            "grupo_tecnico",
                            "_grupo_tecnico_filtro_edicao",
                            "linha",
                            "modelo",
                            "tipo_cortina_persiana",
                            "material_tecido",
                            "cor",
                        ]:
                            if campo in df_edicao.columns:
                                mask_busca = mask_busca | serie_contem_busca_flexivel(df_edicao[campo], termo_busca_massa)
                        df_edicao = df_edicao[mask_busca].copy()

                    # SmartTec v19: filtro dedicado na Edição em Massa por Grupo Técnico.
                    # Agora é possível ir direto para SEM_GRUPO_TECNICO ou qualquer outro grupo
                    # e ajustar manualmente somente aquele bloco, sem navegar por todas as páginas.
                    try:
                        opcoes_grupo_edicao = montar_opcoes_grupo_tecnico_filtro(produtos_base_edicao)
                    except Exception:
                        opcoes_grupo_edicao = ["Todos", "SEM_GRUPO_TECNICO"]

                    if "grupo_tecnico_edicao_massa_produtos" not in st.session_state:
                        st.session_state.grupo_tecnico_edicao_massa_produtos = "Todos"

                    if st.session_state.grupo_tecnico_edicao_massa_produtos not in opcoes_grupo_edicao:
                        st.session_state.grupo_tecnico_edicao_massa_produtos = "Todos"

                    filtro_col1, filtro_col2, filtro_col3 = st.columns([1.8, 2.0, 2.2])
                    with filtro_col1:
                        grupo_tecnico_edicao = st.selectbox(
                            "Filtrar edição por Grupo Técnico",
                            opcoes_grupo_edicao,
                            index=opcoes_grupo_edicao.index(st.session_state.grupo_tecnico_edicao_massa_produtos),
                            key="grupo_tecnico_edicao_massa_produtos",
                        )

                    # Calcula o grupo técnico efetivo de cada produto, incluindo inferência e SEM_GRUPO_TECNICO.
                    if not df_edicao.empty:
                        if "_grupo_tecnico_filtro_edicao" not in df_edicao.columns:
                            df_edicao["_grupo_tecnico_filtro_edicao"] = df_edicao.apply(
                                lambda linha: grupo_tecnico_filtro_produto(linha.to_dict()),
                                axis=1,
                            )

                        if grupo_tecnico_edicao != "Todos":
                            df_edicao = df_edicao[
                                df_edicao["_grupo_tecnico_filtro_edicao"].astype(str) == str(grupo_tecnico_edicao)
                            ].copy()

                    with filtro_col2:
                        st.caption(f"Grupo técnico selecionado: {grupo_tecnico_edicao}")
                    with filtro_col3:
                        st.caption(f"Produtos encontrados nesse filtro: {len(df_edicao)}")

                    if df_edicao.empty:
                        st.warning("Nenhum produto encontrado com os filtros atuais.")
                    else:
                        topo1, topo2, topo3 = st.columns([1.1, 2.8, 2.3])

                        with topo1:
                            if st.button("Gerenciar produtos", key="btn_voltar_ajuste_produtos_massa"):
                                st.session_state.acao_mais_produtos = ""
                                st.rerun()

                        with topo3:
                            campo_escolhido = st.selectbox(
                                "Campo para alteração",
                                list(CAMPOS_EDICAO_MASSA_PRODUTOS.keys()),
                                key="campo_edicao_massa_produtos",
                                label_visibility="collapsed",
                            )

                        cfg_campo = CAMPOS_EDICAO_MASSA_PRODUTOS[campo_escolhido]

                        if cfg_campo.get("tipo") == "indisponivel":
                            st.warning(cfg_campo.get("mensagem", "Campo ainda não disponível no backend."))

                        st.markdown("""
                        <style>
                            div[data-testid="stHorizontalBlock"]:has(.cab-edicao-massa-produtos) {
                                border-top: 1px solid #d9dee3;
                                border-left: 1px solid #d9dee3;
                                border-right: 1px solid #d9dee3;
                                background: #ffffff;
                                padding: 10px 8px;
                                margin-top: 8px;
                            }
                            .cab-edicao-massa-produtos {
                                font-weight: 700;
                                color: #111827;
                                font-size: 14px;
                            }
                            .linha-edicao-massa-produtos {
                                border-left: 1px solid #d9dee3;
                                border-right: 1px solid #d9dee3;
                                border-bottom: 1px solid #d9dee3;
                                padding: 8px 8px 2px 8px;
                            }
                            .linha-edicao-massa-produtos:nth-child(even) {
                                background: #f7f7f7;
                            }
                            .texto-linha-edicao-produto {
                                padding-top: 9px;
                                font-size: 14px;
                            }
                        </style>
                        """, unsafe_allow_html=True)

                        # Paginação da edição em massa.
                        # Antes a tela carregava somente os primeiros 100 produtos e não havia como avançar.
                        # Agora mantém 100 por página para não pesar o Streamlit, mas permite navegar pela lista toda.
                        produtos_por_pagina = 100
                        total_registros_edicao = len(df_edicao)
                        total_paginas_edicao = max(1, math.ceil(total_registros_edicao / produtos_por_pagina))

                        if "pagina_edicao_massa_produtos" not in st.session_state:
                            st.session_state.pagina_edicao_massa_produtos = 1

                        try:
                            pagina_atual_edicao = int(st.session_state.pagina_edicao_massa_produtos)
                        except Exception:
                            pagina_atual_edicao = 1

                        pagina_atual_edicao = max(1, min(pagina_atual_edicao, total_paginas_edicao))
                        st.session_state.pagina_edicao_massa_produtos = pagina_atual_edicao

                        inicio_edicao = (pagina_atual_edicao - 1) * produtos_por_pagina
                        fim_edicao = inicio_edicao + produtos_por_pagina
                        produtos_visiveis = df_edicao.iloc[inicio_edicao:fim_edicao].to_dict(orient="records")

                        pag1, pag2, pag3, pag4 = st.columns([1.0, 1.0, 2.5, 1.2])
                        with pag1:
                            if st.button("Anterior", key="edicao_massa_produtos_pagina_anterior", disabled=pagina_atual_edicao <= 1, use_container_width=True):
                                st.session_state.pagina_edicao_massa_produtos = max(1, pagina_atual_edicao - 1)
                                st.rerun()
                        with pag2:
                            if st.button("Próxima", key="edicao_massa_produtos_pagina_proxima", disabled=pagina_atual_edicao >= total_paginas_edicao, use_container_width=True):
                                st.session_state.pagina_edicao_massa_produtos = min(total_paginas_edicao, pagina_atual_edicao + 1)
                                st.rerun()
                        with pag3:
                            st.caption(f"Página {pagina_atual_edicao} de {total_paginas_edicao} • exibindo {inicio_edicao + 1}-{min(fim_edicao, total_registros_edicao)} de {total_registros_edicao} produto(s)")
                        with pag4:
                            pagina_digitada = st.number_input(
                                "Ir para página",
                                min_value=1,
                                max_value=total_paginas_edicao,
                                value=pagina_atual_edicao,
                                step=1,
                                key="edicao_massa_produtos_ir_pagina",
                            )
                            if int(pagina_digitada) != pagina_atual_edicao:
                                st.session_state.pagina_edicao_massa_produtos = int(pagina_digitada)
                                st.rerun()

                        if "ajuste_prod_marcar_todos" not in st.session_state:
                            st.session_state.ajuste_prod_marcar_todos = True

                        cab1, cab2, cab3, cab4, cab5 = st.columns([0.45, 1.15, 3.15, 1.15, 2.75])
                        with cab1:
                            marcar_todos = st.checkbox(
                                "",
                                value=st.session_state.ajuste_prod_marcar_todos,
                                key="ajuste_prod_checkbox_cabecalho",
                                label_visibility="collapsed",
                            )

                            if marcar_todos != st.session_state.ajuste_prod_marcar_todos:
                                st.session_state.ajuste_prod_marcar_todos = marcar_todos
                                for produto_sel in produtos_visiveis:
                                    try:
                                        pid_sel = int(produto_sel.get("id"))
                                        st.session_state[f"ajuste_prod_sel_{pid_sel}"] = marcar_todos
                                    except Exception:
                                        pass
                                st.rerun()

                        with cab2:
                            st.markdown('<div class="cab-edicao-massa-produtos">Código</div>', unsafe_allow_html=True)
                        with cab3:
                            st.markdown('<div class="cab-edicao-massa-produtos">Nome</div>', unsafe_allow_html=True)
                        with cab4:
                            st.markdown('<div class="cab-edicao-massa-produtos">Cor</div>', unsafe_allow_html=True)
                        with cab5:
                            st.markdown(f'<div class="cab-edicao-massa-produtos">{html.escape(campo_escolhido)}</div>', unsafe_allow_html=True)

                        for produto in produtos_visiveis:
                            pid = int(produto.get("id"))

                            chave_sel = f"ajuste_prod_sel_{pid}"
                            if chave_sel not in st.session_state:
                                st.session_state[chave_sel] = st.session_state.get("ajuste_prod_marcar_todos", True)

                            chave_valor = f"ajuste_prod_val_{pid}_{campo_escolhido}"
                            if cfg_campo.get("tipo") not in ["placeholder", "indisponivel"]:
                                if chave_valor not in st.session_state:
                                    st.session_state[chave_valor] = valor_inicial_campo_edicao_massa_produtos(produto, cfg_campo)

                            with st.container():
                                st.markdown('<div class="linha-edicao-massa-produtos">', unsafe_allow_html=True)
                                c1, c2, c3, c4, c5 = st.columns([0.45, 1.15, 3.15, 1.15, 2.75])

                                with c1:
                                    st.checkbox("", key=chave_sel, label_visibility="collapsed")

                                with c2:
                                    codigo_mostrar = str(produto.get("codigo_interno") or produto.get("codigo_barras") or produto.get("id") or "")
                                    st.markdown(f'<div class="texto-linha-edicao-produto">{html.escape(codigo_mostrar)}</div>', unsafe_allow_html=True)

                                with c3:
                                    nome_mostrar = str(produto.get("nome") or "")
                                    st.markdown(f'<div class="texto-linha-edicao-produto">{html.escape(nome_mostrar)}</div>', unsafe_allow_html=True)

                                with c4:
                                    cor_mostrar = str(
                                        produto.get("cor")
                                        or produto.get("cor_componente")
                                        or produto.get("material_tecido")
                                        or produto.get("linha")
                                        or ""
                                    )
                                    st.markdown(f'<div class="texto-linha-edicao-produto">{html.escape(cor_mostrar)}</div>', unsafe_allow_html=True)

                                with c5:
                                    tipo = cfg_campo.get("tipo")

                                    if tipo == "placeholder":
                                        st.caption("Selecione um campo")

                                    elif tipo == "indisponivel":
                                        st.caption("Em breve")

                                    elif tipo == "texto":
                                        st.text_input("", key=chave_valor, label_visibility="collapsed")

                                    elif tipo == "numero":
                                        st.number_input(
                                            "",
                                            key=chave_valor,
                                            step=cfg_campo.get("step", 1.0),
                                            format=cfg_campo.get("format", "%.2f"),
                                            label_visibility="collapsed",
                                        )

                                    elif tipo == "select":
                                        opcoes = opcoes_campo_edicao_massa_produtos(cfg_campo)
                                        valor_atual = st.session_state.get(chave_valor, opcoes[0] if opcoes else "")
                                        if valor_atual and valor_atual not in opcoes:
                                            opcoes.append(valor_atual)
                                        idx_opcao = opcoes.index(valor_atual) if valor_atual in opcoes else 0
                                        novo_valor = st.selectbox(
                                            "",
                                            opcoes,
                                            index=idx_opcao,
                                            key=f"{chave_valor}_select",
                                            label_visibility="collapsed",
                                        )
                                        st.session_state[chave_valor] = novo_valor

                                    elif tipo == "opcao_categoria":
                                        opcoes = opcoes_campo_edicao_massa_produtos(cfg_campo)
                                        valor_atual = st.session_state.get(chave_valor, opcoes[0] if opcoes else "")
                                        if valor_atual and valor_atual not in opcoes:
                                            opcoes.append(valor_atual)
                                        idx_opcao = opcoes.index(valor_atual) if valor_atual in opcoes else 0
                                        novo_valor = st.selectbox(
                                            "",
                                            opcoes,
                                            index=idx_opcao,
                                            key=f"{chave_valor}_select",
                                            label_visibility="collapsed",
                                        )
                                        st.session_state[chave_valor] = novo_valor

                                st.markdown('</div>', unsafe_allow_html=True)

                        selecionados = []
                        for produto in produtos_visiveis:
                            pid = int(produto.get("id"))
                            if st.session_state.get(f"ajuste_prod_sel_{pid}", False):
                                selecionados.append(produto)

                        st.caption(f"{len(selecionados)} produto(s) selecionado(s) nesta página.")

                        def limpar_estado_edicao_massa_produtos():
                            chaves_para_apagar = [
                                chave for chave in list(st.session_state.keys())
                                if str(chave).startswith("ajuste_prod_sel_")
                                or str(chave).startswith("ajuste_prod_val_")
                            ]
                            for chave in chaves_para_apagar:
                                del st.session_state[chave]

                            st.session_state.ajuste_prod_marcar_todos = True
                            st.session_state.pagina_edicao_massa_produtos = 1
                            st.session_state.resetar_campo_edicao_massa_produtos = True

                        btn_cancelar, btn_aplicar, espaco = st.columns([0.8, 1.05, 4])
                        with btn_cancelar:
                            if st.button("Cancelar", key="cancelar_edicao_massa_produtos"):
                                limpar_estado_edicao_massa_produtos()
                                st.session_state.acao_mais_produtos = ""
                                st.rerun()

                        with btn_aplicar:
                            if st.button("Aplicar alterações", key="aplicar_edicao_massa_produtos", type="primary"):
                                if campo_escolhido == "Selecione o campo para alteração":
                                    st.warning("Selecione o campo que deseja alterar.")
                                elif cfg_campo.get("tipo") == "indisponivel":
                                    st.warning(cfg_campo.get("mensagem", "Campo ainda não disponível."))
                                elif not selecionados:
                                    st.warning("Selecione pelo menos um produto.")
                                else:
                                    atualizados = 0
                                    erros = []

                                    for produto in selecionados:
                                        pid = int(produto.get("id"))
                                        chave_valor = f"ajuste_prod_val_{pid}_{campo_escolhido}"
                                        valor_ui = st.session_state.get(chave_valor)
                                        novo_valor_api = converter_valor_edicao_massa_produtos_para_api(valor_ui, cfg_campo)

                                        payload = montar_payload_produto_massa(produto)
                                        payload[cfg_campo["api"]] = novo_valor_api

                                        try:
                                            resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                            if resp is not None and resp.status_code in [200, 201, 204]:
                                                atualizados += 1
                                            else:
                                                status = resp.status_code if resp is not None else "sem resposta"
                                                detalhe = ""
                                                try:
                                                    detalhe = resp.text
                                                except Exception:
                                                    pass
                                                erros.append(f"Produto {pid}: status {status} {detalhe}")
                                        except Exception as e:
                                            erros.append(f"Produto {pid}: {e}")

                                    if atualizados:
                                        mensagem_ok = f"✅ {atualizados} produto(s) atualizado(s) com sucesso no campo '{campo_escolhido}'."
                                        st.session_state.mensagem_acao_produtos = mensagem_ok
                                        st.session_state.mensagem_edicao_massa_produtos = mensagem_ok

                                    if erros:
                                        st.error("Alguns itens não puderam ser atualizados:")
                                        for erro in erros[:10]:
                                            st.write(f"- {erro}")

                                    if atualizados and not erros:
                                        limpar_estado_edicao_massa_produtos()
                                        st.rerun()
                                    elif atualizados:
                                        st.success(st.session_state.mensagem_acao_produtos)

            elif acao == "ferramentas_massa":
                st.subheader("Ferramentas em massa")
                st.info("Selecione os produtos na listagem, escolha o destino técnico e aplique. Esta ferramenta altera em massa sem criar vários botões no menu.")

                produtos_base_ferramenta = buscar_produtos_api(todos=True, limit=500, max_paginas=20)
                total_produtos_ferramenta = len(produtos_base_ferramenta)
                sem_grupo_ferramenta = len([
                    p for p in produtos_base_ferramenta
                    if not str(p.get("grupo_tecnico") or "").strip()
                ])
                classificados_ferramenta = max(total_produtos_ferramenta - sem_grupo_ferramenta, 0)
                perc_classificado = 0
                if total_produtos_ferramenta > 0:
                    perc_classificado = int((classificados_ferramenta / total_produtos_ferramenta) * 100)

                st.markdown(
                    f"""
                    <div style="border:1px solid #d1d5db;background:#ffffff;border-radius:8px;padding:14px 16px;margin:8px 0 14px 0;">
                        <div style="font-size:15px;font-weight:800;color:#111827;margin-bottom:6px;">Organização técnica da base</div>
                        <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:#374151;">
                            <div><b>Total:</b> {total_produtos_ferramenta}</div>
                            <div><b>Sem grupo técnico:</b> {sem_grupo_ferramenta}</div>
                            <div><b>Classificados:</b> {classificados_ferramenta}</div>
                            <div><b>Progresso:</b> {perc_classificado}%</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if sem_grupo_ferramenta == 0 and total_produtos_ferramenta > 0:
                    st.success("🎉 Banco de produtos totalmente organizado. Nenhum item sem grupo técnico.")

                ids = normalizar_ids_selecionados_produtos()
                selecionados_ferramenta = [
                    p for p in produtos_base_ferramenta
                    if int(p.get("id") or 0) in ids
                ]

                st.caption(f"{len(selecionados_ferramenta)} produto(s) selecionado(s).")

                opcoes_destino_grupo = {
                    "Manter atual": None,
                    "Tecidos Rolô / Romana / Painel": "TECIDOS_ROLO_ROMANA_PAINEL",
                    "Tecidos Double Vision": "TECIDOS_DOUBLE_VISION",
                    "Tecidos Toldo": "TECIDOS_TOLDO",
                    "Componentes Persianas": "COMPONENTES_PERSIANAS",
                    "Componentes Double Vision": "COMPONENTES_DOUBLE_VISION",
                    "Componentes Cortinas": "COMPONENTES_CORTINAS",
                    "Componentes Toldo": "COMPONENTES_TOLDO",
                    "Componentes Externa": "COMPONENTES_EXTERNA",
                    "Motores": "MOTORES",
                    "Acessórios Motor": "ACESSORIOS_MOTOR",
                    "Baú Persianas": "BAU_PERSIANAS",
                    "Baú Cortinas": "BAU_CORTINAS",
                    "Baú Externa": "BAU_EXTERNA",
                    "Baú Motores": "BAU_MOTORES",
                }

                acao_ferramenta = st.selectbox(
                    "O que deseja fazer?",
                    [
                        "Alterar destino técnico / tipo do produto",
                        "Inativar selecionados",
                        "Reativar selecionados",
                    ],
                    key="ferramenta_massa_acao_produtos",
                )

                novo_grupo_ferramenta = None
                novo_tipo_ferramenta = None

                if acao_ferramenta == "Alterar destino técnico / tipo do produto":
                    c_fg1, c_fg2 = st.columns([1.4, 1.0])
                    with c_fg1:
                        destino_label = st.selectbox(
                            "Destino do Grupo Técnico",
                            list(opcoes_destino_grupo.keys()),
                            key="ferramenta_massa_destino_grupo_tecnico",
                        )
                        novo_grupo_ferramenta = opcoes_destino_grupo.get(destino_label)
                    with c_fg2:
                        novo_tipo_ferramenta = st.selectbox(
                            "Tipo do Produto",
                            ["Manter atual", "Componente", "Produto fabricado", "Produto acabado", "Serviço"],
                            key="ferramenta_massa_novo_tipo_produto",
                        )
                    st.caption("Componentes compartilhados devem ir para Componentes Persianas. Wave, Americana, Franzida, Macho e Fêmea não são componentes; são modelos de confecção da cortina.")

                if selecionados_ferramenta:
                    df_prev_ferr = pd.DataFrame(selecionados_ferramenta).fillna("")
                    colunas_prev_ferr = [
                        c for c in ["id", "codigo_interno", "nome", "grupo_produto", "grupo_tecnico", "modelo_tecnico", "tipo_produto", "situacao"]
                        if c in df_prev_ferr.columns
                    ]
                    st.dataframe(df_prev_ferr[colunas_prev_ferr].head(150), use_container_width=True, hide_index=True)
                else:
                    st.warning("Nenhum produto selecionado. Marque os itens na lista abaixo usando a coluna ☑.")

                confirmar_ferramenta = st.checkbox(
                    "Conferi os produtos selecionados e quero aplicar esta ação.",
                    key="ferramenta_massa_confirmar_produtos",
                    value=False,
                )

                cf1, cf2, cf3 = st.columns([1, 1, 4])
                with cf1:
                    if st.button("Limpar seleção", key="ferramenta_massa_limpar_selecao", use_container_width=True):
                        limpar_selecao_produtos_lote()
                        st.rerun()
                with cf2:
                    if st.button(
                        "Aplicar",
                        key="ferramenta_massa_aplicar",
                        type="primary",
                        use_container_width=True,
                        disabled=(not selecionados_ferramenta or not confirmar_ferramenta),
                    ):
                        atualizados = 0
                        erros = []

                        for produto in selecionados_ferramenta:
                            pid = int(produto.get("id") or 0)
                            payload = montar_payload_produto_massa(produto)

                            if acao_ferramenta == "Inativar selecionados":
                                payload["situacao"] = "Inativo"
                            elif acao_ferramenta == "Reativar selecionados":
                                payload["situacao"] = "Ativo"
                            else:
                                if novo_grupo_ferramenta:
                                    payload["grupo_tecnico"] = normalizar_grupo_tecnico(novo_grupo_ferramenta) or novo_grupo_ferramenta
                                if novo_tipo_ferramenta and novo_tipo_ferramenta != "Manter atual":
                                    payload["tipo_produto"] = novo_tipo_ferramenta

                            try:
                                resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                if resp is not None and resp.status_code in [200, 201, 204]:
                                    atualizados += 1
                                else:
                                    detalhe = ""
                                    try:
                                        detalhe = resp.text
                                    except Exception:
                                        pass
                                    erros.append(f"Produto {pid}: status {getattr(resp, 'status_code', 'sem resposta')} {detalhe}")
                            except Exception as e:
                                erros.append(f"Produto {pid}: {e}")

                        if erros:
                            st.error("Alguns produtos não puderam ser atualizados:")
                            for erro in erros[:15]:
                                st.caption(erro)
                        if atualizados:
                            limpar_selecao_produtos_lote()
                            st.session_state.mensagem_acao_produtos = f"✅ {atualizados} produto(s) atualizado(s) pela Ferramenta em massa."
                            st.rerun()

            elif acao == "copiar_para_bau_componentes":
                st.subheader("Copiar selecionados para o Baú de Componentes")
                st.info("Essa ação NÃO altera o Grupo Técnico original. Ela apenas marca o componente para também aparecer no Baú de Componentes Compartilhados das receitas.")

                ids = normalizar_ids_selecionados_produtos()
                if not ids:
                    st.info("Marque os componentes na coluna ☑ da lista abaixo e depois volte aqui para copiar para o baú.")
                    st.warning("Nenhum produto selecionado ainda.")
                else:
                    produtos_base = buscar_produtos_api()
                    selecionados_bau = [p for p in produtos_base if int(p.get("id") or 0) in ids]
                    bloqueados = [p for p in selecionados_bau if not produto_pode_ir_para_bau_componentes(p)]
                    liberados = [p for p in selecionados_bau if produto_pode_ir_para_bau_componentes(p)]

                    st.success(f"{len(liberados)} componente(s) liberado(s) para copiar ao baú.")
                    if bloqueados:
                        st.warning(f"{len(bloqueados)} item(ns) foram bloqueados por segurança porque parecem produto final, tecido, lâmina ou motor puro.")
                        for item in bloqueados[:8]:
                            st.caption(f"Bloqueado: {item.get('nome')} | Grupo técnico: {grupo_tecnico_filtro_produto(item)}")

                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button("Limpar seleção", key="limpar_selecao_copiar_bau", use_container_width=True):
                            limpar_selecao_produtos_lote()
                            st.rerun()
                    with c2:
                        if st.button("Copiar para o Baú", key="confirmar_copiar_para_bau", type="primary", use_container_width=True, disabled=not liberados):
                            atualizados = 0
                            erros = []
                            for produto in liberados:
                                pid = int(produto.get("id") or 0)
                                payload = montar_payload_produto_massa(produto)
                                payload = aplicar_marcador_bau_componentes_no_payload(payload, ativo=True)
                                try:
                                    resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                    if resp is not None and resp.status_code in [200, 201, 204]:
                                        atualizados += 1
                                    else:
                                        erros.append(f"Produto {pid}: status {getattr(resp, 'status_code', 'sem resposta')}")
                                except Exception as e:
                                    erros.append(f"Produto {pid}: {e}")

                            if erros:
                                st.error("Alguns produtos não puderam ser copiados para o baú.")
                                for erro in erros[:10]:
                                    st.caption(erro)
                            if atualizados:
                                limpar_selecao_produtos_lote()
                                st.session_state.mensagem_acao_produtos = f"✅ {atualizados} componente(s) copiado(s) para o Baú sem alterar o grupo técnico original."
                                st.rerun()

            elif acao == "remover_do_bau_componentes":
                st.subheader("Remover selecionados do Baú de Componentes")
                st.info("Essa ação remove apenas a marcação do baú. O Grupo Técnico original permanece intacto.")

                ids = normalizar_ids_selecionados_produtos()
                if not ids:
                    st.info("Marque os produtos na coluna ☑ da lista abaixo e depois volte aqui para remover do baú.")
                    st.warning("Nenhum produto selecionado ainda.")
                else:
                    produtos_base = buscar_produtos_api()
                    selecionados_bau = [p for p in produtos_base if int(p.get("id") or 0) in ids]
                    no_bau = [p for p in selecionados_bau if produto_disponivel_no_bau_componentes(p)]

                    st.success(f"{len(no_bau)} item(ns) selecionado(s) estão marcados no baú.")
                    if len(no_bau) < len(selecionados_bau):
                        st.warning(f"{len(selecionados_bau) - len(no_bau)} item(ns) selecionado(s) não estavam no baú.")

                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button("Limpar seleção", key="limpar_selecao_remover_bau", use_container_width=True):
                            limpar_selecao_produtos_lote()
                            st.rerun()
                    with c2:
                        if st.button("Remover do Baú", key="confirmar_remover_do_bau", type="primary", use_container_width=True, disabled=not no_bau):
                            atualizados = 0
                            erros = []
                            for produto in no_bau:
                                pid = int(produto.get("id") or 0)
                                payload = montar_payload_produto_massa(produto)
                                payload = aplicar_marcador_bau_componentes_no_payload(payload, ativo=False)
                                try:
                                    resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                    if resp is not None and resp.status_code in [200, 201, 204]:
                                        atualizados += 1
                                    else:
                                        erros.append(f"Produto {pid}: status {getattr(resp, 'status_code', 'sem resposta')}")
                                except Exception as e:
                                    erros.append(f"Produto {pid}: {e}")

                            if erros:
                                st.error("Alguns produtos não puderam ser removidos do baú.")
                                for erro in erros[:10]:
                                    st.caption(erro)
                            if atualizados:
                                limpar_selecao_produtos_lote()
                                st.session_state.mensagem_acao_produtos = f"✅ {atualizados} item(ns) removido(s) do Baú."
                                st.rerun()

            elif acao == "inativar_selecionados":
                st.subheader("Inativar produtos selecionados")
                ids = normalizar_ids_selecionados_produtos()
                if not ids:
                    st.info("Marque os produtos na coluna ☑ da lista abaixo e depois volte aqui para inativar.")
                    st.warning("Nenhum produto selecionado ainda.")
                else:
                    st.success(f"{len(ids)} produto(s) selecionado(s) para inativar.")
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button("Limpar seleção", key="limpar_selecao_inativar_lote_produtos", use_container_width=True):
                            limpar_selecao_produtos_lote()
                            st.rerun()
                    with c2:
                        if st.button("Inativar selecionados", key="confirmar_inativar_lote_produtos", type="primary", use_container_width=True):
                            atualizados = 0
                            erros = []
                            produtos_base = buscar_produtos_api()
                            for produto in produtos_base:
                                pid = int(produto.get("id") or 0)
                                if pid in ids:
                                    payload = montar_payload_produto_massa(produto)
                                    payload["situacao"] = "Inativo"
                                    try:
                                        resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                        if resp is not None and resp.status_code in [200, 201, 204]:
                                            atualizados += 1
                                        else:
                                            erros.append(f"Produto {pid}: status {getattr(resp, 'status_code', 'sem resposta')}")
                                    except Exception as e:
                                        erros.append(f"Produto {pid}: {e}")
                            if erros:
                                st.error("Alguns produtos não puderam ser inativados.")
                                for erro in erros[:10]:
                                    st.caption(erro)
                            if atualizados:
                                limpar_selecao_produtos_lote()
                                st.session_state.mensagem_acao_produtos = f"✅ {atualizados} produto(s) inativado(s) com sucesso."
                                st.rerun()

            elif acao == "reativar_selecionados":
                st.subheader("Reativar produtos selecionados")
                ids = normalizar_ids_selecionados_produtos()
                if not ids:
                    st.info("Marque os produtos na coluna ☑ da lista abaixo e depois volte aqui para reativar.")
                    st.warning("Nenhum produto selecionado ainda.")
                else:
                    st.success(f"{len(ids)} produto(s) selecionado(s) para reativar.")
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button("Limpar seleção", key="limpar_selecao_reativar_lote_produtos", use_container_width=True):
                            limpar_selecao_produtos_lote()
                            st.rerun()
                    with c2:
                        if st.button("Reativar selecionados", key="confirmar_reativar_lote_produtos", type="primary", use_container_width=True):
                            atualizados = 0
                            erros = []
                            produtos_base = buscar_produtos_api()
                            for produto in produtos_base:
                                pid = int(produto.get("id") or 0)
                                if pid in ids:
                                    payload = montar_payload_produto_massa(produto)
                                    payload["situacao"] = "Ativo"
                                    try:
                                        resp = atualizar_produto(pid, preservar_payload_termos_comerciais(payload))
                                        if resp is not None and resp.status_code in [200, 201, 204]:
                                            atualizados += 1
                                        else:
                                            erros.append(f"Produto {pid}: status {getattr(resp, 'status_code', 'sem resposta')}")
                                    except Exception as e:
                                        erros.append(f"Produto {pid}: {e}")
                            if erros:
                                st.error("Alguns produtos não puderam ser reativados.")
                                for erro in erros[:10]:
                                    st.caption(erro)
                            if atualizados:
                                limpar_selecao_produtos_lote()
                                st.session_state.mensagem_acao_produtos = f"✅ {atualizados} produto(s) reativado(s) com sucesso."
                                st.rerun()

            elif acao == "excluir_selecionados":
                st.subheader("Excluir produtos selecionados")

                ids = normalizar_ids_selecionados_produtos()
                total = len(ids)

                if total == 0:
                    st.info("Marque os produtos na coluna ☑ da lista abaixo e depois volte aqui para confirmar a exclusão.")
                    st.warning("Nenhum produto selecionado ainda.")
                else:
                    st.success(f"{total} produto(s) selecionado(s) para exclusão.")
                    c1, c2 = st.columns([1, 1])

                    with c1:
                        if st.button("Limpar seleção", key="limpar_selecao_lote_produtos", use_container_width=True):
                            limpar_selecao_produtos_lote()
                            st.session_state.confirmar_exclusao_produtos_lote = False
                            st.rerun()

                    with c2:
                        if st.button("Excluir selecionados", key="abrir_confirmacao_exclusao_lote_produtos", type="primary", use_container_width=True):
                            st.session_state.confirmar_exclusao_produtos_lote = True
                            st.rerun()

            if acao not in ["ajustar_valores", "ajustar_produtos"]:
                c_fechar, _ = st.columns([1, 5])
                with c_fechar:
                    if st.button("Fechar painel", key="fechar_painel_mais_acoes_produtos", use_container_width=True):
                        st.session_state.acao_mais_produtos = ""
                        st.session_state.confirmar_exclusao_produtos_lote = False
                        st.session_state.confirmar_ajuste_valores_massa = False
                        st.session_state.config_ajuste_valores_massa = {}
                        if acao in ["ferramentas_massa", "excluir_selecionados", "inativar_selecionados", "reativar_selecionados", "copiar_para_bau_componentes", "remover_do_bau_componentes", "aplicar_receita_rolo_manual"]:
                            limpar_selecao_produtos_lote()
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

            if acao == "ajustar_produtos":
                return

        if st.session_state.mostrar_busca_avancada_produtos:
            renderizar_busca_avancada_produtos()

        produtos = buscar_produtos_api()

        if not produtos:
            st.info("Nenhum produto cadastrado no banco de dados ainda. Clique em 'Adicionar +' para cadastrar o primeiro!")
            return

        df = pd.DataFrame(produtos).fillna("")

        # Garante Modelo Técnico e Grupo Técnico mesmo para produtos antigos ainda sem os campos no backend.
        if "modelo_tecnico" not in df.columns:
            df["modelo_tecnico"] = ""
        if "grupo_tecnico" not in df.columns:
            df["grupo_tecnico"] = ""

        if "grupo_tecnico_filtro" not in df.columns:
            df["grupo_tecnico_filtro"] = ""

        for idx, row in df.iterrows():
            produto_row = row.to_dict()
            if not str(df.at[idx, "modelo_tecnico"] or "").strip():
                df.at[idx, "modelo_tecnico"] = modelo_tecnico_label(produto_row)

            # Mantém a coluna visual como SEM_GRUPO_TECNICO quando não houver grupo salvo/inferido.
            # Assim a listagem, a busca avançada e o resumo falam a mesma língua.
            grupo_filtro = grupo_tecnico_filtro_produto(produto_row)
            df.at[idx, "grupo_tecnico_filtro"] = grupo_filtro
            if not str(df.at[idx, "grupo_tecnico"] or "").strip():
                df.at[idx, "grupo_tecnico"] = grupo_filtro

        grupos_tecnicos_filtro = montar_opcoes_grupo_tecnico_filtro(produtos)

        grupo_tecnico_filtro = st.selectbox(
            "Grupo técnico",
            grupos_tecnicos_filtro,
            key="produtos_filtro_grupo_tecnico",
            help="Filtra o cadastro por setor técnico. Ideal para inativar/excluir itens fora de linha sem mexer no sistema todo.",
        )

        if grupo_tecnico_filtro != "Todos":
            df = df[df["grupo_tecnico_filtro"].astype(str).str.strip() == grupo_tecnico_filtro]

        if busca_texto:
            termo = str(busca_texto or "").strip()
            mask_busca = pd.Series([False] * len(df), index=df.index)

            for campo in ["nome", "codigo_interno", "codigo_barras", "grupo_produto", "modelo_tecnico", "grupo_tecnico", "grupo_tecnico_filtro", "linha", "modelo", "tipo_cortina_persiana", "material_tecido", "cor"]:
                if campo in df.columns:
                    mask_busca = mask_busca | serie_contem_busca_flexivel(df[campo], termo)

            df = df[mask_busca]

        df = aplicar_filtros_produtos(df)

        if df.empty:
            st.warning("Nenhum produto encontrado.")
            return

        # Paginação: evita renderizar 1000+ produtos a cada interação do Streamlit.
        total_produtos_filtrados = len(df)
        col_pag_a, col_pag_b, col_pag_c, col_pag_d = st.columns([1.1, 1.1, 1.4, 4])

        with col_pag_a:
            produtos_por_pagina = st.selectbox(
                "Itens por página",
                [25, 50, 100, 200],
                index=1,
                key="produtos_itens_por_pagina",
            )

        total_paginas = max(1, int(math.ceil(total_produtos_filtrados / int(produtos_por_pagina))))

        pagina_atual = int(st.session_state.get("produtos_pagina_atual", 1) or 1)
        pagina_atual = max(1, min(pagina_atual, total_paginas))
        st.session_state.produtos_pagina_atual = pagina_atual

        with col_pag_b:
            pagina_escolhida = st.number_input(
                "Página",
                min_value=1,
                max_value=total_paginas,
                value=pagina_atual,
                step=1,
                key="produtos_pagina_input",
            )

        st.session_state.produtos_pagina_atual = int(pagina_escolhida)

        inicio_pagina = (int(pagina_escolhida) - 1) * int(produtos_por_pagina)
        fim_pagina = inicio_pagina + int(produtos_por_pagina)
        df_pagina = df.iloc[inicio_pagina:fim_pagina].copy()

        with col_pag_c:
            st.markdown(
                f"""
                <div style="padding-top:26px;color:#6b7280;font-size:0.92rem;">
                    Mostrando {inicio_pagina + 1}-{min(fim_pagina, total_produtos_filtrados)} de {total_produtos_filtrados}
                </div>
                """,
                unsafe_allow_html=True,
            )

        produtos_por_id = {}
        try:
            produtos_por_id = {
                int(item.get("id", 0)): item
                for item in produtos
                if item.get("id") is not None
            }
        except Exception:
            produtos_por_id = {}

        renderizar_confirmacao_exclusao_produto(mudar_tela)
        renderizar_confirmacao_exclusao_lote_produtos(produtos_por_id, mudar_tela)
        renderizar_confirmacao_ajuste_valores_massa(mudar_tela)
        renderizar_tabela_produtos(df_pagina, mudar_tela)

    elif tela_atual in ["adicionar", "editar", "visualizar", "clonar"]:
        modo = tela_atual
        is_visualizar = modo == "visualizar"
        produto_atual = {}

        if modo in ["editar", "visualizar", "clonar"]:
            produto_atual = buscar_produto_por_id(st.session_state.id_produto_editar)

            if not produto_atual:
                st.error("Produto não encontrado.")
                if st.button("Voltar"):
                    mudar_tela("listar")
                    st.rerun()
                return

            if modo == "clonar":
                produto_atual = dict(produto_atual)
                produto_atual.pop("id", None)
                produto_atual["nome"] = f'{valor_str(produto_atual, "nome")} - CÓPIA'.strip()
                produto_atual["codigo_interno"] = ""
                produto_atual["codigo_barras"] = ""

        produto_atual = preparar_codigos_automaticos_produto(produto_atual, modo)

        titulo_tela = {
            "adicionar": "Adicionar produto",
            "editar": "Editar produto",
            "visualizar": "Visualizar produto",
            "clonar": "Clonar produto",
        }.get(modo, "Produto")

        st.markdown(f'<div class="erp-form-page-title">{titulo_tela}</div>', unsafe_allow_html=True)

        # IMPORTANTE:
        # Não usamos st.form aqui porque, dentro de form, o Streamlit só recalcula ao clicar em submit.
        # Com container, os valores recalculam ao clicar fora do campo, igual ao comportamento do modelo.
        with st.container():
            # Abas do cadastro: organizam visualmente o formulario sem alterar regras ou payload.
            (
                aba_geral,
                aba_tecnico,
                aba_composicao,
                aba_valores,
                aba_estoque,
                aba_fiscal,
                aba_descricao,
            ) = st.tabs([
                "Geral",
                "Técnico",
                "Composição / Receita",
                "Valores",
                "Estoque",
                "Fiscal",
                "Descrição",
            ])

            with aba_geral:
                (
                    nome,
                    codigo_interno,
                    codigo_barras,
                    grupo_produto,
                    tipo_produto,
                    unidade_venda,
                    movimenta_estoque,
                    possui_composicao,
                    habilitar_nota_fiscal,
                    possui_variacoes,
                    situacao,
                ) = renderizar_aba_geral(
                    produto_atual,
                    is_visualizar,
                    modo,
                    st.session_state.id_produto_editar,
                )

            with aba_tecnico:
                (
                    modelo_tecnico,
                    grupo_tecnico,
                    familia_tecnica,
                    varia_cor,
                    cor_componente,
                    usar_conversao_custo,
                    custo_unitario_saida,
                    unidade_venda,
                    linha,
                    modelo,
                    tipo_cortina_persiana,
                    material_tecido,
                    cor,
                    largura,
                    altura,
                    comprimento,
                    peso,
                ) = renderizar_aba_tecnico(
                    produto_atual,
                    is_visualizar,
                    modo,
                    st.session_state.id_produto_editar,
                    unidade_venda,
                )

            with aba_composicao:
                custo_composicao_final, usar_custo_composicao = renderizar_aba_composicao(
                    produto_atual,
                    is_visualizar,
                    modo,
                    st.session_state.id_produto_editar,
                    possui_composicao,
                    nome,
                    linha,
                    modelo,
                    tipo_cortina_persiana,
                    material_tecido,
                    cor,
                    largura,
                    altura,
                    comprimento,
                    tipo_produto,
                    grupo_produto,
                )

            with aba_valores:
                (
                    valor_custo,
                    despesas_acessorias,
                    outras_despesas,
                    margem_lucro,
                    valor_venda,
                ) = renderizar_aba_valores(
                    produto_atual,
                    is_visualizar,
                    modo,
                    st.session_state.id_produto_editar,
                    possui_composicao,
                    usar_custo_composicao,
                    custo_composicao_final,
                    usar_conversao_custo,
                    custo_unitario_saida,
                )

            with aba_estoque:
                estoque_minimo, estoque_maximo, estoque_atual = renderizar_aba_estoque(
                    produto_atual,
                    is_visualizar,
                )

            with aba_fiscal:
                ncm, cest, origem = renderizar_aba_fiscal(
                    produto_atual,
                    is_visualizar,
                )

            with aba_descricao:
                descricao, observacoes = renderizar_aba_descricao(
                    produto_atual,
                    is_visualizar,
                )

            st.markdown('<div class="erp-form-actions-spacer"></div>', unsafe_allow_html=True)

            _, col_salvar, col_cancelar = st.columns([7.0, 1.4, 1.4])

            with col_salvar:
                texto_botao = "Cadastrar" if modo in ["adicionar", "clonar"] else "Salvar" if modo == "editar" else "Visualizar"
                salvar = st.button(texto_botao, type="primary", disabled=is_visualizar, use_container_width=True, key=f"btn_salvar_produto_{modo}_{st.session_state.id_produto_editar}")

            with col_cancelar:
                cancelar = st.button("Voltar" if is_visualizar else "Cancelar", type="secondary", use_container_width=True, key=f"btn_cancelar_produto_{modo}_{st.session_state.id_produto_editar}")

            if salvar and not is_visualizar:
                if not str(nome).strip():
                    st.error("⚠️ O campo Nome é obrigatório.")
                    return

                payload_produto = montar_payload_produto(
                    nome=nome,
                    codigo_interno=codigo_interno,
                    codigo_barras=codigo_barras,
                    grupo_produto=grupo_produto,
                    tipo_produto=tipo_produto,
                    modelo_tecnico=modelo_tecnico,
                    grupo_tecnico=grupo_tecnico,
                    familia_tecnica=familia_tecnica,
                    varia_cor=varia_cor,
                    cor_componente=cor_componente,
                    unidade_venda=unidade_venda,
                    movimenta_estoque=movimenta_estoque,
                    habilitar_nota_fiscal=habilitar_nota_fiscal,
                    possui_variacoes=possui_variacoes,
                    possui_composicao=possui_composicao,
                    situacao=situacao,
                    linha=linha,
                    modelo=modelo,
                    tipo_cortina_persiana=tipo_cortina_persiana,
                    material_tecido=material_tecido,
                    cor=cor,
                    largura=largura,
                    altura=altura,
                    comprimento=comprimento,
                    peso=peso,
                    descricao=descricao,
                    observacoes=observacoes,
                    valor_custo=valor_custo,
                    despesas_acessorias=despesas_acessorias,
                    outras_despesas=outras_despesas,
                    margem_lucro=margem_lucro,
                    valor_venda=valor_venda,
                    estoque_minimo=estoque_minimo,
                    estoque_maximo=estoque_maximo,
                    estoque_atual=estoque_atual,
                    ncm=ncm,
                    cest=cest,
                    origem=origem,
                )

                carrinho_receita_para_salvar = obter_carrinho_receita_session(modo, st.session_state.id_produto_editar)
                if carrinho_receita_para_salvar:
                    payload_produto["observacoes"] = embutir_receita_tecnica_observacoes(
                        observacoes,
                        carrinho_receita_para_salvar,
                    )
                else:
                    # Se o usuário não carregou/montou carrinho nesta tela, preserva receita já existente do produto original.
                    receita_existente = extrair_receita_tecnica_observacoes(produto_atual.get("observacoes"))
                    if receita_existente:
                        payload_produto["observacoes"] = embutir_receita_tecnica_observacoes(observacoes, receita_existente)

                payload_produto = preservar_payload_termos_comerciais(payload_produto)

                id_produto_atual = st.session_state.id_produto_editar

                with st.spinner("Enviando dados para o servidor..."):
                    if modo in ["adicionar", "clonar"]:
                        resposta = criar_produto(preservar_payload_termos_comerciais(payload_produto))
                    else:
                        resposta = atualizar_produto(id_produto_atual, preservar_payload_termos_comerciais(payload_produto))

                if resposta is not None and resposta.status_code in [200, 201, 204]:
                    st.session_state.mensagem_acao_produtos = "✅ Produto salvo com sucesso."
                    st.success(st.session_state.mensagem_acao_produtos)
                    time.sleep(0.4)
                    mudar_tela("listar")
                    st.rerun()

                else:
                    status = resposta.status_code if resposta is not None else "sem resposta"
                    st.error(f"🔴 Erro ao salvar produto. Status: {status}")

                    try:
                        st.code(resposta.text)
                    except Exception:
                        pass

            if cancelar:
                mudar_tela("listar")
                st.rerun()
