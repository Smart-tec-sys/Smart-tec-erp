import base64
import io
import json
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from utils.ui import cabecalho
from utils.api_client import get_opcoes_auxiliares_por_categoria, criar_opcao_auxiliar

CATEGORIA_MODELOS_ETIQUETA = "modelo_etiqueta_produto"

CAMPOS_ETIQUETA = [
    ("representante", "Representante", "REP"),
    ("data", "Data", "DATA"),
    ("pedido", "Pedido", "PEDIDO"),
    ("cliente", "Cliente", "CLIENTE"),
    ("codigo", "Código / SKU", "CÓD"),
    ("largura", "Largura", "LARG"),
    ("altura", "Altura", "ALT"),
    ("item", "Item", "ITEM"),
    ("tc", "TC", "TC"),
    ("acionamento", "Acionamento", "AC"),
    ("tecido", "Tecido", "TECIDO"),
    ("motor", "Motor", "MOTOR"),
    ("modelo", "Modelo", "MODELO"),
    ("ambiente", "Ambiente", "AMBIENTE"),
    ("cor", "Cor", "COR"),
    ("redutor_peso", "Redutor", "REDUTOR"),
    ("invertida", "Invertida", "INV"),
]

CAMPOS_COMPACTO = ["codigo", "pedido", "representante", "data", "item", "cliente", "largura", "altura", "tc", "tecido", "ambiente", "cor"]
CAMPOS_COMPLETO = [campo[0] for campo in CAMPOS_ETIQUETA]


def carregar_css_etiquetas():
    st.markdown("""
    <style>
    .block-container {
        padding-top: 4.6rem !important;
        padding-left: .8rem !important;
        padding-right: .8rem !important;
        max-width:100% !important;
        width:100% !important;
    }

    div[data-testid="stButton"] button {
        min-height:40px !important;
        height:40px !important;
        border-radius:4px !important;
        font-size:14px !important;
        font-weight:600 !important;
        box-shadow:none !important;
        white-space:nowrap !important;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    textarea {
        background:#fff !important;
        border:1.5px solid #9ca3af !important;
        color:#111827 !important;
        border-radius:4px !important;
    }

    div[data-testid="stNumberInput"] button {
        display:none !important;
    }

    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus,
    textarea:focus {
        border:2px solid #2563eb !important;
        box-shadow:0 0 0 1px #2563eb33 !important;
        outline:none !important;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        background:#fff !important;
        border:1.5px solid #9ca3af !important;
        color:#111827 !important;
        border-radius:4px !important;
    }

    .erp-info-etiqueta {
        background:#d9edf7;
        border:1px solid #bce8f1;
        color:#286090;
        padding:12px 14px;
        border-radius:4px;
        font-size:13px;
        margin:8px 0 14px 0;
    }

    .erp-section-card {
        border:1px solid #d1d5db;
        border-radius:4px;
        background:#fff;
        margin-bottom:12px;
    }

    .erp-section-card-title {
        padding:12px 14px;
        border-bottom:1px solid #e5e7eb;
        font-size:18px;
        font-weight:700;
        color:#111827;
    }

    .erp-section-card-body {
        padding:14px;
    }

    .etiqueta-preview-wrap {
        background:#f3f4f6;
        border:1px solid #d1d5db;
        padding:16px;
        border-radius:4px;
        overflow-x:auto;
    }

    .etiqueta-folha-preview {
        background:#fff;
        border:1px solid #cfcfcf;
        padding:12px;
        display:grid;
        gap:8px;
        width:fit-content;
        min-width:520px;
    }

    .etiqueta-box {
        border:1px dashed #9ca3af;
        background:#fff;
        color:#111827;
        padding:7px 8px;
        box-sizing:border-box;
        font-size:10.5px;
        line-height:1.16;
        overflow:hidden;
        position:relative;
        min-height: 168px;
    }

    .etiqueta-title {
        font-weight:900;
        text-align:center;
        font-size:12px;
        margin-bottom:4px;
        border-bottom:1px solid #e5e7eb;
        padding-bottom:3px;
        letter-spacing:.2px;
    }

    .etiqueta-grid-2 {
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:1px 7px;
    }

    .etiqueta-grid-3 {
        display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:1px 6px;
    }

    .etiqueta-line {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .etiqueta-line strong {
        font-weight:900;
    }

    .etiqueta-footer {
        margin-top:4px;
        display:grid;
        grid-template-columns: 1fr 54px;
        gap:6px;
        align-items:end;
    }

    .etiqueta-qr-img {
        width:52px;
        height:52px;
        object-fit:contain;
        justify-self:end;
    }

    .etiqueta-barcode {
        font-family:monospace;
        font-size:9.5px;
        letter-spacing:1px;
        border-top:1px solid #111827;
        border-bottom:1px solid #111827;
        padding:2px 3px;
        text-align:center;
        min-width:110px;
        max-width: 155px;
        align-self:end;
    }

    .etiqueta-small-muted {
        color:#6b7280;
        font-size:10px;
        text-align:center;
    }


    .etiqueta-compact-main {
        display: grid;
        grid-template-columns: 1fr 34px;
        gap: 4px;
        align-items: start;
    }

    .etiqueta-compact-dados {
        min-width: 0;
    }

    .etiqueta-compact-codigos {
        display: flex;
        align-items: flex-start;
        justify-content: flex-end;
        min-height: 32px;
    }


    .etiqueta-compact-documento {
        border-top: 1px solid #e5e7eb;
        margin-top: 1px;
        padding-top: 1px;
        gap: 0 6px;
    }

    .etiqueta-compact-topo,
    .etiqueta-compact-meio,
    .etiqueta-compact-extra {
        gap: 0 6px;
    }

    .etiqueta-footer-compacta {
        grid-template-columns: 1fr !important;
        margin-top: 1px !important;
    }

    .etiqueta-actions-row {
        display:flex;
        gap:10px;
        align-items:center;
        flex-wrap:wrap;
        margin-top: 12px;
    }

    .etiqueta-box-compacta { font-size:9.8px; line-height:1.06; min-height:118px; padding:6px 7px; }
    .etiqueta-title-compacta { font-size:11px; margin-bottom:3px; padding-bottom:2px; }
    .etiqueta-footer-compacta { margin-top:3px; grid-template-columns:1fr 42px; gap:4px; }
    .etiqueta-qr-img-compacta { width:40px; height:40px; }
    .etiqueta-barcode-compacta { font-size:8px; letter-spacing:.7px; min-width:82px; max-width:130px; padding:1px 2px; }
    .erp-warning-etiqueta { background:#fff3cd; border:1px solid #ffe69c; color:#856404; padding:10px 12px; border-radius:4px; font-size:13px; margin:8px 0 14px 0; }
    </style>
    """, unsafe_allow_html=True)


def gerar_qrcode_base64(conteudo):
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1,
        )
        qr.add_data(conteudo)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return ""


def montar_qr(dados):
    return json.dumps({
        "empresa": dados.get("empresa", ""),
        "tipo": dados.get("tipo_etiqueta", ""),
        "pedido": dados.get("pedido", ""),
        "item": dados.get("item", ""),
        "cliente": dados.get("cliente", ""),
        "representante": dados.get("representante", ""),
        "modelo": dados.get("modelo", ""),
        "ambiente": dados.get("ambiente", ""),
        "largura": dados.get("largura", ""),
        "altura": dados.get("altura", ""),
        "tecido": dados.get("tecido", ""),
        "cor": dados.get("cor", ""),
        "motor": dados.get("motor", ""),
        "acionamento": dados.get("acionamento", ""),
        "codigo": dados.get("codigo", ""),
    }, ensure_ascii=False)


def barcode_visual(codigo):
    codigo = str(codigo or "SEM-CODIGO").strip()
    return f"||| | ||| || | | |||<br><span>{codigo}</span>"


def get_label(campo_id):
    for cid, nome, label in CAMPOS_ETIQUETA:
        if cid == campo_id:
            return label
    return str(campo_id).upper()


def linha_campo(dados, campo_id):
    valor = str(dados.get(campo_id, "") or "").strip()
    if not valor:
        return ""
    return f'<div class="etiqueta-line"><strong>{get_label(campo_id)}:</strong> {valor}</div>'


def escolher_modelo_por_tamanho(largura_mm, altura_mm, modelo_layout):
    if modelo_layout != "Automático":
        return modelo_layout

    try:
        largura = float(largura_mm or 0)
        altura = float(altura_mm or 0)
    except Exception:
        return "Compacto"

    if altura <= 40:
        return "Compacto"

    if largura <= 80 and altura <= 55:
        return "Compacto"

    return "Completo"


def campos_do_modelo(modelo_layout, campos_personalizados=None):
    if modelo_layout == "Compacto":
        return CAMPOS_COMPACTO
    if modelo_layout == "Personalizado":
        return campos_personalizados or CAMPOS_COMPACTO
    return CAMPOS_COMPLETO


def otimizar_compacto_por_tamanho(largura_mm, altura_mm, mostrar_qr, mostrar_barcode, campos_personalizados=None):
    """
    Regras para etiqueta baixa:
    - mantém campos essenciais primeiro
    - reduz a quantidade de campos quando a altura é pequena
    - preserva espaço para QR Code e/ou código de barras
    """
    try:
        altura = float(altura_mm or 0)
    except Exception:
        altura = 0

    campos_base = campos_personalizados or CAMPOS_COMPACTO

    prioridade = [
        "codigo",
        "pedido",
        "representante",
        "data",
        "item",
        "cliente",
        "largura",
        "altura",
        "tc",
        "tecido",
        "ambiente",
        "cor",
        "modelo",
        "motor",
        "acionamento",
    ]

    campos_ordenados = [campo for campo in prioridade if campo in campos_base]

    if altura <= 30:
        limite = 6 if (mostrar_qr or mostrar_barcode) else 8
        return campos_ordenados[:limite]

    if altura <= 40:
        limite = 8 if (mostrar_qr and mostrar_barcode) else 10
        return campos_ordenados[:limite]

    return campos_ordenados[:12]


def etiqueta_html(dados, mostrar_qr=True, mostrar_barcode=True, modelo_layout="Completo", campos_personalizados=None):
    campos = campos_do_modelo(modelo_layout, campos_personalizados)
    compacto = modelo_layout == "Compacto"

    qr_html = ""
    qr_class = "etiqueta-qr-img-compacta" if compacto else ""
    if mostrar_qr:
        qr_b64 = gerar_qrcode_base64(montar_qr(dados))
        qr_html = (
            f'<img class="etiqueta-qr-img {qr_class}" src="data:image/png;base64,{qr_b64}" />'
            if qr_b64
            else '<div class="etiqueta-small-muted">QR Code<br>instale qrcode</div>'
        )

    codigo = dados.get("codigo") or f'PED{dados.get("pedido","")}-IT{dados.get("item","")}'
    barcode_class = "etiqueta-barcode-compacta" if compacto else ""
    barcode_html = f'<div class="etiqueta-barcode {barcode_class}">{barcode_visual(codigo)}</div>' if mostrar_barcode else ""

    if compacto:
        # Compacto inteligente: aproveita a área ao lado do QR Code e
        # mantém representante, data e TC quando houver espaço.
        topo = []
        # Ordem compacta mais natural:
        # CÓD / PEDIDO
        # REP / DATA
        # ITEM / CLIENTE
        # LARG / ALT
        # TC / TECIDO
        for campo in ["codigo", "pedido", "representante", "data", "item", "cliente", "largura", "altura", "tc", "tecido"]:
            if campo in campos:
                linha = linha_campo(dados, campo)
                if linha:
                    topo.append(linha)

        documento = []

        meio = []
        for campo in ["representante", "data", "tecido", "ambiente", "cor", "modelo", "motor", "acionamento"]:
            if campo in campos:
                linha = linha_campo(dados, campo)
                if linha:
                    meio.append(linha)

        extras = []
        for campo in ["redutor_peso", "invertida"]:
            if campo in campos:
                linha = linha_campo(dados, campo)
                if linha:
                    extras.append(linha)

        topo_html = "".join(topo)
        documento_html = ""
        meio_html = "".join(meio)
        extras_html = "".join(extras)

        return f"""
        <div class="etiqueta-box etiqueta-box-compacta">
          <div class="etiqueta-title etiqueta-title-compacta">{dados.get("empresa", "SMART-TEC PERSIANAS")}</div>

          <div class="etiqueta-compact-main">
              <div class="etiqueta-compact-dados">
                  <div class="etiqueta-grid-2 etiqueta-compact-topo">{topo_html}</div>
                  <div class="etiqueta-grid-2 etiqueta-compact-meio">{meio_html}</div>
                  <div class="etiqueta-grid-2 etiqueta-compact-extra">{extras_html}</div>
              </div>
              <div class="etiqueta-compact-codigos">{qr_html}</div>
          </div>

          <div class="etiqueta-footer etiqueta-footer-compacta">{barcode_html}</div>
        </div>
        """

    def renderiza(campo):
        return linha_campo(dados, campo) if campo in campos else ""

    return f"""
    <div class="etiqueta-box">
      <div class="etiqueta-title">{dados.get("empresa", "SMART-TEC PERSIANAS")}</div>
      <div class="etiqueta-grid-2">{renderiza("representante")}{renderiza("data")}</div>
      <div class="etiqueta-grid-3">{renderiza("largura")}{renderiza("altura")}{renderiza("tc")}</div>
      <div class="etiqueta-grid-2">{renderiza("item")}{renderiza("motor")}</div>
      {renderiza("acionamento")}
      {renderiza("tecido")}
      {renderiza("modelo")}
      {renderiza("ambiente")}
      {renderiza("cor")}
      <div class="etiqueta-grid-2">{renderiza("redutor_peso")}{renderiza("invertida")}</div>
      <div class="etiqueta-grid-2">{renderiza("cliente")}{renderiza("pedido")}</div>
      {renderiza("codigo")}
      <div class="etiqueta-footer">{barcode_html}{qr_html}</div>
    </div>
    """


def gerar_html_impressao(dados, quantidade, colunas, largura_mm, altura_mm, mostrar_qr, mostrar_barcode, abrir_impressao=True, modelo_layout="Completo", campos_personalizados=None):
    etiquetas = "\n".join(
        etiqueta_html(dados, mostrar_qr, mostrar_barcode, modelo_layout=modelo_layout, campos_personalizados=campos_personalizados)
        for _ in range(int(quantidade or 1))
    )

    compacto = modelo_layout == "Compacto"
    fonte = "6.5pt" if compacto else "7.9pt"
    linha = "0.98" if compacto else "1.08"
    titulo = "7.2pt" if compacto else "8.5pt"
    qr_tamanho = "10mm" if compacto else "15mm"
    gap_y = "1.8mm" if compacto else "2.5mm"
    padding = "1.1mm" if compacto else "2mm"
    barcode_font = "5.8pt" if compacto else "7pt"

    script_print = """
<script>
window.onload = function() {
    setTimeout(function() { window.print(); }, 500);
}
</script>
""" if abrir_impressao else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Etiquetas SmartTec</title>
<style>
@page {{ size:A4; margin:8mm; }}

body {{
    margin:0;
    font-family:Arial, sans-serif;
    color:#111827;
}}

.folha {{
    display:grid;
    grid-template-columns:repeat({int(colunas)}, {float(largura_mm)}mm);
    grid-auto-rows:{float(altura_mm)}mm;
    gap:{gap_y} 3mm;
    align-content:start;
}}

.etiqueta-box {{
    border:1px dashed #777;
    padding:{padding};
    box-sizing:border-box;
    font-size:{fonte};
    line-height:{linha};
    overflow:hidden;
    page-break-inside:avoid;
}}

.etiqueta-title {{
    font-weight:900;
    text-align:center;
    font-size:{titulo};
    margin-bottom:1.2mm;
    border-bottom:1px solid #ddd;
    padding-bottom:.8mm;
    letter-spacing:.15mm;
}}

.etiqueta-grid-2 {{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:.2mm 2.5mm;
}}

.etiqueta-grid-3 {{
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:.2mm 2.5mm;
}}

.etiqueta-line {{
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}}

.etiqueta-line strong {{
    font-weight:900;
}}

.etiqueta-footer {{
    margin-top:1.5mm;
    display:grid;
    grid-template-columns:1fr {qr_tamanho};
    gap:2mm;
    align-items:end;
}}

.etiqueta-qr-img {{
    width:{qr_tamanho};
    height:{qr_tamanho};
    object-fit:contain;
    justify-self:end;
}}

.etiqueta-barcode {{
    font-family:monospace;
    font-size:{barcode_font};
    letter-spacing:.7mm;
    border-top:1px solid #111827;
    border-bottom:1px solid #111827;
    padding:.7mm;
    text-align:center;
    min-width:32mm;
}}

.etiqueta-barcode span {{
    letter-spacing:0;
    font-size:6.8pt;
}}

.etiqueta-small-muted {{
    color:#666;
    font-size:6.5pt;
    text-align:center;
}}


.etiqueta-compact-main {{
    display:grid;
    grid-template-columns:1fr 10mm;
    gap:1mm;
    align-items:start;
}}

.etiqueta-compact-dados {{
    min-width:0;
}}

.etiqueta-compact-codigos {{
    display:flex;
    align-items:flex-start;
    justify-content:flex-end;
    min-height:10mm;
}}

.etiqueta-footer-compacta {{
    grid-template-columns:1fr !important;
    margin-top:.5mm !important;
}}

.etiqueta-footer-compacta .etiqueta-barcode {{
    width:100%;
    max-width:none;
}}

@media print {{
    body {{
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}
}}
</style>
</head>
<body>
<div class="folha">{etiquetas}</div>
{script_print}
</body>
</html>"""


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


def buscar_modelos_etiqueta_salvos():
    try:
        dados = get_opcoes_auxiliares_por_categoria(CATEGORIA_MODELOS_ETIQUETA)
        return normalizar_lista_api(dados)
    except Exception:
        return []


def parse_config_modelo(item):
    try:
        return json.loads(item.get("descricao") or "{}")
    except Exception:
        return {}


def salvar_modelo_etiqueta(nome, config):
    payload = {
        "categoria": CATEGORIA_MODELOS_ETIQUETA,
        "nome": nome.strip(),
        "descricao": json.dumps(config, ensure_ascii=False),
        "tipo_campo": "Texto",
        "obrigatorio": "Não",
        "situacao": "Ativo",
        "ordem": 0,
    }
    return criar_opcao_auxiliar(payload)


def indice_opcao(lista, valor, padrao=0):
    try:
        return lista.index(valor)
    except Exception:
        return padrao


def telaProdutosEtiquetas():
    carregar_css_etiquetas()
    cabecalho(titulo="🏷️ Etiquetas", modulo="Produtos", tela_atual="Gerar etiquetas")

    st.markdown("""
    <div class="erp-info-etiqueta">
      Módulo preparado para personalização por segmento. Na SmartTec, começa como etiqueta de produção/pedido; em outros negócios pode virar etiqueta de SKU, lote, validade, localização, assistência técnica etc.
    </div>
    """, unsafe_allow_html=True)

    config_carregada = st.session_state.get("modelo_etiqueta_config_carregada", {}) or {}

    col_config, col_dados = st.columns([1.05, 2.0])

    with col_config:
        st.markdown('<div class="erp-section-card"><div class="erp-section-card-title">⚙️ Configuração</div><div class="erp-section-card-body">', unsafe_allow_html=True)

        modelos_salvos = buscar_modelos_etiqueta_salvos()
        nomes_modelos_salvos = [m.get("nome", "") for m in modelos_salvos if m.get("nome")]

        if nomes_modelos_salvos:
            with st.expander("💾 Usar modelo salvo", expanded=False):
                modelo_salvo_nome = st.selectbox("Modelo salvo", nomes_modelos_salvos, key="modelo_etiqueta_salvo_selecionado")
                if st.button("Aplicar modelo salvo", use_container_width=True):
                    item = next((m for m in modelos_salvos if m.get("nome") == modelo_salvo_nome), None)
                    if item:
                        st.session_state.modelo_etiqueta_config_carregada = parse_config_modelo(item)
                        st.success("Modelo aplicado com sucesso!")
                        st.rerun()

        opcoes_tipo_etiqueta = ["Produção / Pedido", "Produto / Estoque", "Personalizada"]
        tipo_etiqueta = st.selectbox(
            "Tipo de etiqueta",
            opcoes_tipo_etiqueta,
            index=indice_opcao(opcoes_tipo_etiqueta, config_carregada.get("tipo_etiqueta", "Produção / Pedido")),
        )
        opcoes_layout = ["Automático", "Compacto", "Completo", "Personalizado"]
        modelo_layout_opcao = st.selectbox(
            "Modelo de layout",
            opcoes_layout,
            index=indice_opcao(opcoes_layout, config_carregada.get("modelo_layout_opcao", "Automático")),
            help="Automático escolhe Compacto para etiquetas pequenas e Completo para etiquetas maiores.",
        )
        opcoes_modelo_visual = ["SmartTec Produção", "Produto com QR Code", "Produto com Código de Barras", "Personalizado"]
        modelo = st.selectbox(
            "Modelo visual",
            opcoes_modelo_visual,
            index=indice_opcao(opcoes_modelo_visual, config_carregada.get("modelo_visual", "SmartTec Produção")),
        )

        c1, c2 = st.columns(2)
        with c1:
            largura_mm = st.number_input("Largura etiqueta (mm)", min_value=20.0, value=float(config_carregada.get("largura_mm", 70.0)), step=1.0, format="%.1f")
        with c2:
            altura_mm = st.number_input("Altura etiqueta (mm)", min_value=15.0, value=float(config_carregada.get("altura_mm", 50.0)), step=1.0, format="%.1f")

        c3, c4 = st.columns(2)
        with c3:
            colunas = st.number_input("Colunas por folha", min_value=1, max_value=5, value=int(config_carregada.get("colunas", 2)), step=1)
        with c4:
            quantidade = st.number_input("Quantidade", min_value=1, max_value=100, value=int(config_carregada.get("quantidade", 6)), step=1)

        mostrar_qr = st.checkbox("Mostrar QR Code", value=bool(config_carregada.get("mostrar_qr", True)))
        mostrar_barcode = st.checkbox("Mostrar código de barras", value=bool(config_carregada.get("mostrar_barcode", True)))
        abrir_impressao = st.checkbox("Abrir janela de impressão automaticamente", value=bool(config_carregada.get("abrir_impressao", True)))

        modelo_layout = escolher_modelo_por_tamanho(largura_mm, altura_mm, modelo_layout_opcao)

        if modelo_layout_opcao == "Automático":
            st.markdown(
                f'<div class="erp-info-etiqueta">Modelo escolhido automaticamente: <strong>{modelo_layout}</strong>. No compacto, o sistema prioriza Código, Pedido, Item, Cliente, Medidas e principais dados de produção.</div>',
                unsafe_allow_html=True,
            )

        if float(altura_mm or 0) <= 40 and mostrar_qr and mostrar_barcode:
            st.markdown(
                '<div class="erp-warning-etiqueta">Etiqueta baixa: QR Code e código de barras juntos podem cortar informação. O modelo compacto ajuda, mas se necessário use apenas um dos dois.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)

    with col_dados:
        st.markdown('<div class="erp-section-card"><div class="erp-section-card-title">🧾 Dados da etiqueta</div><div class="erp-section-card-body">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            representante = st.text_input("Representante", value="LIDIA MACHADO")
        with c2:
            data_etiqueta = st.text_input("Data", value=date.today().strftime("%d/%m/%Y"))
        with c3:
            pedido = st.text_input("Pedido", value="630")

        c4, c5, c6, c7 = st.columns(4)
        with c4:
            largura = st.text_input("Largura", value="1,90")
        with c5:
            altura = st.text_input("Altura", value="2,55")
        with c6:
            item = st.text_input("Item", value="1")
        with c7:
            tc = st.text_input("TC", value="1,50")

        c8, c9, c10, c11 = st.columns(4)
        with c8:
            acionamento = st.text_input("Acionamento", value="ESQUERDO")
        with c9:
            tecido = st.text_input("Tecido", value="GASE DE LINHO")
        with c10:
            motor = st.selectbox("Motor", ["NÃO", "SIM"])
        with c11:
            modelo_produto = st.text_input("Modelo", value="CORTINA")

        c12, c13, c14, c15 = st.columns(4)
        with c12:
            ambiente = st.text_input("Ambiente", value="SUITE")
        with c13:
            redutor_peso = st.text_input("Redutor de peso", value="")
        with c14:
            cor = st.text_input("Cor", value="OFF WHITE")
        with c15:
            invertida = st.text_input("Invertida", value="")

        c16, c17, c18 = st.columns(3)
        with c16:
            cliente = st.text_input("Cliente", value="GUSTAVO")
        with c17:
            codigo = st.text_input("Código / SKU", value="PED630-IT1")
        with c18:
            empresa = st.text_input("Empresa", value="SMART-TEC PERSIANAS")

        st.markdown("</div></div>", unsafe_allow_html=True)

    campos_personalizados = None
    if modelo_layout == "Personalizado":
        st.markdown("### Campos do modelo personalizado")
        st.caption("Marque os campos que devem aparecer. Isso deixa a etiqueta adaptável para qualquer segmento.")
        campos_personalizados = []
        campos_default = config_carregada.get("campos_personalizados") or CAMPOS_COMPLETO
        cols_campos = st.columns(4)
        for idx, (campo_id, nome, label) in enumerate(CAMPOS_ETIQUETA):
            with cols_campos[idx % 4]:
                if st.checkbox(nome, value=(campo_id in campos_default), key=f"etiqueta_campo_{campo_id}"):
                    campos_personalizados.append(campo_id)

    if modelo_layout == "Compacto":
        campos_personalizados = otimizar_compacto_por_tamanho(
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            mostrar_qr=mostrar_qr,
            mostrar_barcode=mostrar_barcode,
            campos_personalizados=campos_personalizados or CAMPOS_COMPACTO,
        )

    dados = {
        "tipo_etiqueta": tipo_etiqueta,
        "modelo_etiqueta": modelo,
        "empresa": empresa,
        "representante": representante,
        "data": data_etiqueta,
        "pedido": pedido,
        "largura": largura,
        "altura": altura,
        "item": item,
        "tc": tc,
        "acionamento": acionamento,
        "tecido": tecido,
        "motor": motor,
        "modelo": modelo_produto,
        "ambiente": ambiente,
        "redutor_peso": redutor_peso,
        "cor": cor,
        "invertida": invertida,
        "cliente": cliente,
        "codigo": codigo,
    }

    st.markdown("### 💾 Salvar modelo atual")
    st.caption("Salve tamanho, layout, campos, QR Code, código de barras e campos escolhidos para reutilizar depois.")

    col_nome_modelo, col_botao_modelo = st.columns([3.5, 1.2])

    with col_nome_modelo:
        nome_modelo_salvar = st.text_input(
            "Nome do modelo",
            placeholder="Ex.: Pimaco produção 150x35",
            key="nome_modelo_etiqueta_salvar",
        )

    config_para_salvar = {
        "tipo_etiqueta": tipo_etiqueta,
        "modelo_layout_opcao": modelo_layout_opcao,
        "modelo_visual": modelo,
        "largura_mm": float(largura_mm or 0),
        "altura_mm": float(altura_mm or 0),
        "colunas": int(colunas or 1),
        "quantidade": int(quantidade or 1),
        "mostrar_qr": bool(mostrar_qr),
        "mostrar_barcode": bool(mostrar_barcode),
        "abrir_impressao": bool(abrir_impressao),
        "modelo_layout_resolvido": modelo_layout,
        "campos_personalizados": campos_personalizados if campos_personalizados is not None else campos_do_modelo(modelo_layout),
    }

    with col_botao_modelo:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        salvar_modelo_btn = st.button("💾 Salvar modelo", type="primary", use_container_width=True)

    if salvar_modelo_btn:
        if not nome_modelo_salvar.strip():
            st.error("Informe um nome para o modelo.")
        else:
            resp = salvar_modelo_etiqueta(nome_modelo_salvar, config_para_salvar)
            if resp is not None and getattr(resp, "status_code", 200) in [200, 201]:
                st.success("Modelo de etiqueta salvo com sucesso!")
                st.rerun()
            else:
                status = getattr(resp, "status_code", "sem resposta")
                st.error(f"Não foi possível salvar o modelo. Status: {status}")

    html_visualizar = gerar_html_impressao(
        dados=dados,
        quantidade=quantidade,
        colunas=colunas,
        largura_mm=largura_mm,
        altura_mm=altura_mm,
        mostrar_qr=mostrar_qr,
        mostrar_barcode=mostrar_barcode,
        abrir_impressao=False,
        modelo_layout=modelo_layout,
        campos_personalizados=campos_personalizados,
    )

    html_gerado = gerar_html_impressao(
        dados=dados,
        quantidade=quantidade,
        colunas=colunas,
        largura_mm=largura_mm,
        altura_mm=altura_mm,
        mostrar_qr=mostrar_qr,
        mostrar_barcode=mostrar_barcode,
        abrir_impressao=abrir_impressao,
        modelo_layout=modelo_layout,
        campos_personalizados=campos_personalizados,
    )

    st.markdown("### Pré-visualização")

    modo_previa = st.selectbox(
        "Modo de pré-visualização",
        ["🖨️ Prévia de impressão", "👀 Prévia rápida"],
        index=0,
        key="modo_previa_etiquetas",
    )

    if modo_previa == "👀 Prévia rápida":
        preview_html = "".join(
            etiqueta_html(dados, mostrar_qr, mostrar_barcode, modelo_layout=modelo_layout, campos_personalizados=campos_personalizados)
            for _ in range(min(int(quantidade), 6))
        )
        html_previa_rapida = f"""
        <div style="background:#f3f4f6;border:1px solid #d1d5db;padding:16px;border-radius:4px;overflow:auto;">
          <div style="background:#fff;border:1px solid #cfcfcf;padding:12px;display:grid;gap:8px;grid-template-columns:repeat({int(colunas)},260px);width:max-content;min-width:520px;">
            {preview_html}
          </div>
        </div>
        """
        components.html(html_previa_rapida, height=520, scrolling=True)
        st.caption(f"Prévia rápida usando o modelo: {modelo_layout}.")

    else:
        st.markdown(
            f"""
            <div class="erp-info-etiqueta">
                Esta prévia usa o mesmo HTML da impressão. Modelo em uso: <strong>{modelo_layout}</strong>.
            </div>
            """,
            unsafe_allow_html=True,
        )
        components.html(
            html_visualizar,
            height=720,
            scrolling=True,
        )

    st.markdown('<div class="etiqueta-actions-row">', unsafe_allow_html=True)
    st.download_button(
        "🖨️ Baixar e imprimir",
        data=html_gerado.encode("utf-8"),
        file_name=f"etiquetas_smarttec_pedido_{pedido or 'sem_pedido'}.html",
        mime="text/html",
        type="primary",
    )
    st.download_button(
        "📄 Baixar HTML sem auto-impressão",
        data=html_visualizar.encode("utf-8"),
        file_name=f"etiquetas_smarttec_pedido_{pedido or 'sem_pedido'}_visualizar.html",
        mime="text/html",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.caption("Agora você consegue visualizar a folha de impressão dentro do sistema antes de baixar.")
