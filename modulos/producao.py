import time
import html
import json
import pandas as pd
import streamlit as st

from utils.ui import cabecalho
from utils.api_client import (
    get_produtos,
    criar_produto,
    atualizar_produto,
    deletar_produto,
    get_opcoes_auxiliares_por_categoria,
)

CATEGORIA_VALORES_VENDA = "valor_venda_produto"


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
        {"nome": "Varejo", "lucro": 150.0, "ordem": 1},
        {"nome": "Consumidor final", "lucro": 200.0, "ordem": 2},
        {"nome": "Decorador", "lucro": 100.0, "ordem": 3},
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

        div[data-testid="stButton"] button[kind="secondary"] {
            background-color: #161616 !important;
            border-color: #161616 !important;
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

        .erp-busca-avancada-box {
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: #ffffff;
            padding: 16px 20px;
            margin: 8px 0 10px 0;
        }


        /* Limpa os campos numéricos: remove botões - e + para ficar menos poluído */
        div[data-testid="stNumberInput"] button {
            display: none !important;
        }

        div[data-testid="stNumberInput"] > div {
            width: 100% !important;
        }

        div[data-testid="stNumberInput"] input {
            border-radius: 4px !important;
            padding-right: 10px !important;
        }

        .erp-btn-calcular-valores {
            display: inline-block;
            background: #198754;
            color: #ffffff;
            padding: 10px 16px;
            border-radius: 4px;
            font-weight: 700;
            margin: 0 0 12px 0;
            border: 1px solid #198754;
        }


        /* Botão calcular dentro do formulário de produto */
        div[data-testid="stForm"] div[data-testid="stButton"] button:has(p) {
            white-space: nowrap !important;
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
    return html.escape(str(valor))


def valor_str(produto, campo):
    valor = produto.get(campo, "")
    if valor is None:
        return ""
    return str(valor)


def produto_ativo(valor):
    valor = str(valor).strip().lower()
    return valor in ["ativo", "true", "1", "sim", "active"]


def buscar_produtos_api():
    try:
        resp = get_produtos()

        if resp is not None and resp.status_code == 200:
            return resp.json()

        status = resp.status_code if resp is not None else "sem resposta"
        st.error(f"Erro ao buscar produtos. Status: {status}")
        return []

    except Exception as erro:
        st.error(f"🚨 Erro ao conectar com o backend: {erro}")
        return []


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


def moeda_br(valor):
    """
    Formata número no padrão brasileiro.
    """
    try:
        valor = float(valor or 0)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def montar_payload_produto(
    nome,
    codigo_interno,
    codigo_barras,
    grupo_produto,
    tipo_produto,
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


def renderizar_tabela_produtos(df, mudar_tela):
    h0, h1, h2, h3, h4, h5 = st.columns([1.1, 4.0, 1.35, 1.25, 1.0, 1.75])

    with h0:
        st.markdown('<div class="erp-list-header">Código</div>', unsafe_allow_html=True)
    with h1:
        st.markdown('<div class="erp-list-header">Nome</div>', unsafe_allow_html=True)
    with h2:
        st.markdown('<div class="erp-list-header">Vr. venda</div>', unsafe_allow_html=True)
    with h3:
        st.markdown('<div class="erp-list-header">Estoque</div>', unsafe_allow_html=True)
    with h4:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Situação</div>', unsafe_allow_html=True)
    with h5:
        st.markdown('<div class="erp-list-header" style="text-align:center;">Ações</div>', unsafe_allow_html=True)

    for index, row in df.reset_index(drop=True).iterrows():
        produto_id = int(row.get("id", 0))

        codigo = texto_seguro(row.get("codigo_interno", "") or row.get("id", ""))
        nome = texto_seguro(row.get("nome", ""))
        valor_venda = float(row.get("valor_venda", 0) or 0)
        estoque_atual = float(row.get("estoque_atual", 0) or 0)

        ativo = produto_ativo(row.get("situacao", "Ativo"))
        status = "✓" if ativo else "×"
        status_cor = "#00a65a" if ativo else "#ff0019"

        cell_class = "erp-list-cell erp-list-cell-alt" if index % 2 == 0 else "erp-list-cell"

        c0, c1, c2, c3, c4, c5 = st.columns([1.1, 4.0, 1.35, 1.25, 1.0, 1.75])

        with c0:
            st.markdown(f'<div class="{cell_class}">{codigo}</div>', unsafe_allow_html=True)
        with c1:
            st.markdown(f'<div class="{cell_class}">{nome}</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="{cell_class}">{valor_venda:,.2f}</div>'.replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="{cell_class}">{estoque_atual:,.2f}</div>'.replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
        with c4:
            st.markdown(
                f'<div class="{cell_class}" style="justify-content:center;color:{status_cor};font-size:22px;font-weight:800;">{status}</div>',
                unsafe_allow_html=True,
            )
        with c5:
            nome_url = texto_seguro(row.get("nome", ""))
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
        return df[campo].astype(str).str.lower().str.contains(texto, na=False)

    grupo = valor_filtro_produto(filtros.get("grupo_produto"))
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

    if nome:
        df = df[contem("nome", nome)]

    if codigo:
        mask_codigo = pd.Series([False] * len(df), index=df.index)
        if "codigo_interno" in df.columns:
            mask_codigo = mask_codigo | df["codigo_interno"].astype(str).str.lower().str.contains(codigo.lower(), na=False)
        if "codigo_barras" in df.columns:
            mask_codigo = mask_codigo | df["codigo_barras"].astype(str).str.lower().str.contains(codigo.lower(), na=False)
        if "id" in df.columns:
            mask_codigo = mask_codigo | df["id"].astype(str).str.lower().str.contains(codigo.lower(), na=False)
        df = df[mask_codigo]

    if situacao and "situacao" in df.columns:
        df = df[df["situacao"].astype(str).str.lower() == situacao.lower()]

    if linha and "linha" in df.columns:
        df = df[df["linha"].astype(str).str.lower() == linha.lower()]

    if modelo and "modelo" in df.columns:
        df = df[df["modelo"].astype(str).str.lower().str.contains(modelo.lower(), na=False)]

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
            st.text_input("Fornecedor", value="", placeholder="Digite para buscar", disabled=True)

        with c11:
            st.text_input("Marca", value="", disabled=True)

        with c12:
            st.text_input("Largura", value="", disabled=True)

        b1, b2, _ = st.columns([1, 1, 6])

        with b1:
            buscar = st.form_submit_button("✅ Buscar", type="primary", use_container_width=True)

        with b2:
            limpar = st.form_submit_button("✖ Limpar", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if buscar:
            st.session_state.filtros_busca_avancada_produtos = {
                "grupo_produto": grupo_produto,
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

    def mudar_tela(tela, id_produto=None):
        st.session_state.tela_produtos = tela
        st.session_state.id_produto_editar = id_produto

    params = st.query_params

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

    cabecalho(titulo="📦 Produtos", modulo="Produtos", tela_atual=tela_nome)

    if tela_atual == "listar":
        col_add, col_more, col_space, col_search, col_btn, col_advanced = st.columns(
            [1.25, 1.45, 1.75, 2.6, 0.35, 1.55]
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
                    st.button("📥 Importar de uma planilha", use_container_width=True, disabled=True)
                    st.button("🧾 Importar notas fiscais de vendas", use_container_width=True, disabled=True)
                    st.button("📤 Exportar cadastros", use_container_width=True, disabled=True)
                    st.button("💲 Ajustar valores em massa", use_container_width=True, disabled=True)
                    st.button("✏️ Ajustar produtos em massa", use_container_width=True, disabled=True)
                    st.button("🏷️ Gerar etiquetas", use_container_width=True, disabled=True)
                    st.button("✖ Excluir produtos selecionados", use_container_width=True, disabled=True)
                    st.caption("Essas ações serão ativadas nas próximas etapas.")
            else:
                st.button("⚙️ Mais ações", use_container_width=True)

        with col_space:
            st.markdown('<div class="erp-toolbar-spacer"></div>', unsafe_allow_html=True)

        with col_search:
            busca_texto = st.text_input("Buscar", placeholder="Buscar", label_visibility="collapsed")

        with col_btn:
            st.button("🔍", use_container_width=True)

        with col_advanced:
            texto_busca_avancada = "🔎 Busca avançada" if not st.session_state.mostrar_busca_avancada_produtos else "🔎 Ocultar busca"
            if st.button(texto_busca_avancada, use_container_width=True):
                st.session_state.confirmar_exclusao_produto = None
                st.session_state.confirmar_exclusao_produto_nome = ""
                st.session_state._ultima_confirmacao_exclusao_url_processada = ""
                st.session_state.mostrar_busca_avancada_produtos = not st.session_state.mostrar_busca_avancada_produtos
                st.rerun()

        if st.session_state.mostrar_busca_avancada_produtos:
            renderizar_busca_avancada_produtos()

        produtos = buscar_produtos_api()

        if not produtos:
            st.info("Nenhum produto cadastrado no banco de dados ainda. Clique em 'Adicionar +' para cadastrar o primeiro!")
            return

        df = pd.DataFrame(produtos).fillna("")

        if busca_texto:
            termo = busca_texto.lower()
            mask_busca = pd.Series([False] * len(df), index=df.index)

            for campo in ["nome", "codigo_interno", "codigo_barras", "grupo_produto", "linha", "modelo", "tipo_cortina_persiana", "material_tecido", "cor"]:
                if campo in df.columns:
                    mask_busca = mask_busca | df[campo].astype(str).str.lower().str.contains(termo, na=False)

            df = df[mask_busca]

        df = aplicar_filtros_produtos(df)

        if df.empty:
            st.warning("Nenhum produto encontrado.")
            return

        renderizar_confirmacao_exclusao_produto(mudar_tela)
        renderizar_tabela_produtos(df, mudar_tela)

    elif tela_atual in ["adicionar", "editar", "visualizar", "clonar"]:
        modo = tela_atual
        is_visualizar = modo == "visualizar"
        produto_atual = {}

        if modo in ["editar", "visualizar", "clonar"]:
            produto_atual = buscar_produto_por_id(st.session_state.id_produto_editar)

            if not produto_atual:
                st.error("Produto não encontrado.")
                if st.button("⬅️ Voltar"):
                    mudar_tela("listar")
                    st.rerun()
                return

            if modo == "clonar":
                produto_atual = dict(produto_atual)
                produto_atual.pop("id", None)
                produto_atual["nome"] = f'{valor_str(produto_atual, "nome")} - CÓPIA'.strip()
                produto_atual["codigo_interno"] = ""
                produto_atual["codigo_barras"] = ""

        titulo_tela = {
            "adicionar": "Adicionar produto",
            "editar": "Editar produto",
            "visualizar": "Visualizar produto",
            "clonar": "Clonar produto",
        }.get(modo, "Produto")

        st.markdown(f'<div class="erp-form-page-title">{titulo_tela}</div>', unsafe_allow_html=True)

        with st.form("form_produto"):
            st.markdown('<div class="erp-section-title-clean">✍️ Dados</div>', unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                nome = st.text_input("Nome*", value=valor_str(produto_atual, "nome"), disabled=is_visualizar)
            with col2:
                codigo_interno = st.text_input("Código interno", value=valor_str(produto_atual, "codigo_interno"), disabled=is_visualizar)
            with col3:
                codigo_barras = st.text_input("Código de barra", value=valor_str(produto_atual, "codigo_barras"), disabled=is_visualizar)
            with col4:
                opcoes_grupo_produto = carregar_opcoes_categoria("grupo_produto", incluir_vazio=True)
                grupo_produto = st.selectbox(
                    "Grupo do produto",
                    opcoes_grupo_produto,
                    index=indice_select(opcoes_grupo_produto, valor_str(produto_atual, "grupo_produto")),
                    disabled=is_visualizar,
                )

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                opcoes_tipo = carregar_opcoes_categoria("tipo_produto", incluir_vazio=True, padrao="Produto simples")
                tipo_produto = st.selectbox(
                    "Tipo do produto",
                    opcoes_tipo,
                    index=indice_select(opcoes_tipo, valor_str(produto_atual, "tipo_produto"), padrao="Produto simples"),
                    disabled=is_visualizar,
                )
            with col6:
                opcoes_unidade = carregar_opcoes_categoria("unidade_medida", incluir_vazio=True, padrao="Unidade")
                unidade_venda = st.selectbox(
                    "Unidade de venda",
                    opcoes_unidade,
                    index=indice_select(opcoes_unidade, valor_str(produto_atual, "unidade_venda"), padrao="Unidade"),
                    disabled=is_visualizar,
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

            st.markdown('<div class="erp-section-title-clean">📐 Detalhes técnicos</div>', unsafe_allow_html=True)

            col12, col13, col14, col15 = st.columns(4)
            with col12:
                opcoes_linha = carregar_opcoes_categoria("linha_produto", incluir_vazio=True)
                linha = st.selectbox(
                    "Linha",
                    opcoes_linha,
                    index=indice_select(opcoes_linha, valor_str(produto_atual, "linha")),
                    disabled=is_visualizar,
                )
            with col13:
                opcoes_modelo = carregar_opcoes_categoria("modelo_produto", incluir_vazio=True)
                modelo = st.selectbox(
                    "Modelo / variação",
                    opcoes_modelo,
                    index=indice_select(opcoes_modelo, valor_str(produto_atual, "modelo")),
                    disabled=is_visualizar,
                )
            with col14:
                opcoes_tipo_cortina = carregar_opcoes_categoria("tipo_cortina_persiana", incluir_vazio=True)
                tipo_cortina_persiana = st.selectbox(
                    "Tipo cortina/persiana",
                    opcoes_tipo_cortina,
                    index=indice_select(opcoes_tipo_cortina, valor_str(produto_atual, "tipo_cortina_persiana")),
                    disabled=is_visualizar,
                )
            with col15:
                opcoes_material = carregar_opcoes_categoria("material_tecido", incluir_vazio=True)
                material_tecido = st.selectbox(
                    "Material / tecido",
                    opcoes_material,
                    index=indice_select(opcoes_material, valor_str(produto_atual, "material_tecido")),
                    disabled=is_visualizar,
                )

            col16, col17, col18, col19 = st.columns(4)
            with col16:
                opcoes_cor = carregar_opcoes_categoria("cor_produto", incluir_vazio=True)
                cor = st.selectbox(
                    "Cor",
                    opcoes_cor,
                    index=indice_select(opcoes_cor, valor_str(produto_atual, "cor")),
                    disabled=is_visualizar,
                )
            with col17:
                largura = st.number_input("Largura", min_value=0.0, value=float(produto_atual.get("largura") or 0), step=0.01, disabled=is_visualizar)
            with col18:
                altura = st.number_input("Altura", min_value=0.0, value=float(produto_atual.get("altura") or 0), step=0.01, disabled=is_visualizar)
            with col19:
                comprimento = st.number_input("Comprimento", min_value=0.0, value=float(produto_atual.get("comprimento") or 0), step=0.01, disabled=is_visualizar)

            peso = st.number_input("Peso", min_value=0.0, value=float(produto_atual.get("peso") or 0), step=0.01, disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">💰 Valores</div>', unsafe_allow_html=True)

            col_custo_box, col_venda_box = st.columns([1.15, 3.0])

            with col_custo_box:
                st.markdown(
                    """
                    <div style="border:1px solid #d1d5db;border-radius:4px;background:#fff;margin-bottom:10px;">
                        <div style="padding:12px 14px;border-bottom:1px solid #e5e7eb;font-size:18px;font-weight:600;color:#111827;">
                            💵 Valores de custo
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                valor_custo = st.number_input(
                    "Valor de custo *",
                    min_value=0.0,
                    value=float(produto_atual.get("valor_custo") or 0),
                    step=1.0,
                    format="%.2f",
                    disabled=is_visualizar,
                    key=f"produto_valor_custo_{modo}_{st.session_state.id_produto_editar}",
                )

                despesas_acessorias = st.number_input(
                    "Despesas acessórias",
                    min_value=0.0,
                    value=float(produto_atual.get("despesas_acessorias") or 0),
                    step=1.0,
                    format="%.2f",
                    disabled=is_visualizar,
                    key=f"produto_despesas_acessorias_{modo}_{st.session_state.id_produto_editar}",
                )

                outras_despesas = st.number_input(
                    "Outras despesas",
                    min_value=0.0,
                    value=float(produto_atual.get("outras_despesas") or 0),
                    step=1.0,
                    format="%.2f",
                    disabled=is_visualizar,
                    key=f"produto_outras_despesas_{modo}_{st.session_state.id_produto_editar}",
                )

                custo_final_calculado = float(valor_custo or 0) + float(despesas_acessorias or 0) + float(outras_despesas or 0)

                st.number_input(
                    "Custo final *",
                    min_value=0.0,
                    value=float(custo_final_calculado or 0),
                    step=1.0,
                    format="%.2f",
                    disabled=True,
                    key=f"produto_custo_final_calculado_{modo}_{st.session_state.id_produto_editar}",
                )

            with col_venda_box:
                st.markdown(
                    """
                    <div style="border:1px solid #d1d5db;border-radius:4px;background:#fff;margin-bottom:10px;">
                        <div style="padding:12px 14px;border-bottom:1px solid #e5e7eb;font-size:18px;font-weight:600;color:#111827;">
                            💵 Valores de venda
                        </div>
                        <div style="margin:14px;background:#d9edf7;border:1px solid #bce8f1;color:#286090;border-radius:4px;padding:12px 14px;font-size:14px;">
                            O valor de venda é a valoração monetária dos produtos comercializados pelo estabelecimento.
                            Ele pode ser calculado ou indicado livremente.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                calcular_valores = st.form_submit_button(
                    "🧮 Calcular valor de venda",
                    use_container_width=False,
                    disabled=is_visualizar,
                )

                if calcular_valores:
                    st.session_state._versao_calculo_valores_produto += 1

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
                        lucro_utilizado = st.number_input(
                            f"Lucro utilizado {nome_tipo}",
                            min_value=0.0,
                            value=float(margem_default or 0),
                            step=1.0,
                            format="%.2f",
                            label_visibility="collapsed",
                            disabled=is_visualizar,
                            key=f"produto_lucro_{chave}_{modo}_{st.session_state.id_produto_editar}",
                        )

                    valor_sugerido_por_lucro = custo_final_calculado + (custo_final_calculado * (float(lucro_utilizado or 0) / 100))

                    with c_v_sug:
                        st.write(moeda_br(valor_sugerido_por_lucro))

                    valor_padrao_utilizado = valor_sugerido_por_lucro if calcular_valores else (valor_default or valor_sugerido_por_lucro or 0)

                    with c_v_util:
                        valor_utilizado = st.number_input(
                            f"Valor utilizado {nome_tipo}",
                            min_value=0.0,
                            value=float(valor_padrao_utilizado or 0),
                            step=1.0,
                            format="%.2f",
                            label_visibility="collapsed",
                            disabled=is_visualizar,
                            key=f"produto_valor_{chave}_{modo}_{st.session_state.id_produto_editar}_{versao_calculo_valores}",
                        )

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
                            ➕ Cadastrar novo valor de venda
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption("O valor principal salvo no produto é a primeira tabela ativa em Produtos > Valores de venda.")
            st.markdown('<div class="erp-section-title-clean">📦 Estoque</div>', unsafe_allow_html=True)

            col25, col26, col27 = st.columns(3)
            with col25:
                estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, value=float(produto_atual.get("estoque_minimo") or 0), step=1.0, disabled=is_visualizar)
            with col26:
                estoque_maximo = st.number_input("Estoque máximo", min_value=0.0, value=float(produto_atual.get("estoque_maximo") or 0), step=1.0, disabled=is_visualizar)
            with col27:
                estoque_atual = st.number_input("Quantidade atual", min_value=0.0, value=float(produto_atual.get("estoque_atual") or 0), step=1.0, disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">🧾 Fiscal</div>', unsafe_allow_html=True)

            col28, col29, col30 = st.columns(3)
            with col28:
                ncm = st.text_input("NCM", value=valor_str(produto_atual, "ncm"), disabled=is_visualizar)
            with col29:
                cest = st.text_input("CEST", value=valor_str(produto_atual, "cest"), disabled=is_visualizar)
            with col30:
                origem = st.text_input("Origem", value=valor_str(produto_atual, "origem"), disabled=is_visualizar)

            st.markdown('<div class="erp-section-title-clean">🧩 Composição / Produção</div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="erp-blue-info">
                    Esta etapa ficará preparada para a Fase 2: cálculo inteligente para rolo m²,
                    cortina de tecido, persiana externa e toldos.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<div class="erp-section-title-clean">📝 Descrição / Observações</div>', unsafe_allow_html=True)

            descricao = st.text_area(
                "Descrição do produto",
                value=valor_str(produto_atual, "descricao"),
                height=90,
                disabled=is_visualizar,
            )

            observacoes = st.text_area(
                "Observações",
                value=valor_str(produto_atual, "observacoes"),
                height=90,
                disabled=is_visualizar,
            )

            _, col_salvar, col_cancelar = st.columns([7.0, 1.4, 1.4])

            with col_salvar:
                texto_botao = "Cadastrar" if modo in ["adicionar", "clonar"] else "Salvar" if modo == "editar" else "Visualizar"
                salvar = st.form_submit_button(texto_botao, type="primary", disabled=is_visualizar, use_container_width=True)

            with col_cancelar:
                cancelar = st.form_submit_button("Voltar" if is_visualizar else "Cancelar", type="secondary", use_container_width=True)

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

                id_produto_atual = st.session_state.id_produto_editar

                with st.spinner("Enviando dados para o servidor..."):
                    if modo in ["adicionar", "clonar"]:
                        resposta = criar_produto(payload_produto)
                    else:
                        resposta = atualizar_produto(id_produto_atual, payload_produto)

                if resposta is not None and resposta.status_code in [200, 201, 204]:
                    st.success("✅ Produto salvo com sucesso!")
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
