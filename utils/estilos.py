# utils/estilos.py


def css_botoes_barra():
    return """
    <style>
    /* Botão Adicionar (Verde) */
    button[kind="primary"] {
        background-color: #00a65a !important;
        border-color: #008d4c !important;
        color: white !important;
    }
    button[kind="primary"]:hover {
        background-color: #008d4c !important;
    }
    /* Botões Escuros */
    button[kind="secondary"] {
        background-color: #222d32 !important;
        border-color: #222d32 !important;
        color: white !important;
    }
    button[kind="secondary"]:hover {
        background-color: #1a2226 !important;
        color: white !important;
    }
    /* Popover Mais Ações */
    div[data-testid="stPopover"] > button {
        background-color: #222d32 !important;
        border-color: #222d32 !important;
        color: white !important;
    }
    </style>
    """
