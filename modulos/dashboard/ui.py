import streamlit as st
import plotly.express as px
from datetime import date
import pandas as pd
from core.kpi import KPI


# ───────────────────────────────────────────────
# 1. FUNÇÕES QUE BUSCAM DADOS (mock por enquanto)
#    Troque depois por consultas ao banco / API.
# ───────────────────────────────────────────────
def get_total_clientes() -> int:
    return 128


def get_total_pedidos() -> int:
    return 42


def get_faturamento() -> float:
    return 58320.32


def get_fluxo_caixa_dataframe() -> pd.DataFrame:
    dias = pd.date_range(date.today().replace(day=1), periods=10)
    entradas = [10000, 8000, 6000, 12000, 9000, 11000, 7000, 9500, 10500, 9800]
    saidas = [5000, 3000, 4000, 4500, 3500, 6000, 4000, 4600, 5200, 5100]
    return pd.DataFrame({"Dia": dias, "Entradas": entradas, "Saídas": saidas})


def get_vendas_dataframe() -> pd.DataFrame:
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
    valores = [12000, 15000, 14000, 18000, 21000, 23000]
    return pd.DataFrame({"Mês": meses, "Vendas": valores})


# ───────────────────────────────────────────────
# 2. LISTA DE KPIs A EXIBIR NO TOPO
# ───────────────────────────────────────────────
KPIS: list[KPI] = [
    KPI("Clientes", get_total_clientes, icon="👥"),
    KPI("Pedidos", get_total_pedidos, icon="🛒"),
    KPI("Faturamento", get_faturamento, icon="💰", format="R$ {:,.2f}"),
]


# ───────────────────────────────────────────────
# 3. FUNÇÃO CHAMADA PELO ROTEADOR PRINCIPAL
# ───────────────────────────────────────────────
def telaDashboard() -> None:
    # ─ Barra superior (nome do usuário fictício e switch de tema)
    col_user, col_space, col_theme = st.columns([1, 6, 1])
    with col_user:
        st.markdown("#### 👤 Yalmir")
    with col_theme:
        if st.toggle("Dark"):
            st.write("")  # usar tema escuro do navegador

    st.markdown("## 🏠 Dashboard")

    # ─ KPIs em linha
    cols = st.columns(len(KPIS))
    for col, kpi in zip(cols, KPIS):
        with col:
            st.metric(label=f"{kpi.icon or ''} {kpi.label}",
                    value=kpi.format.format(kpi.value_fn()))

    st.divider()

    # ─ Gráfico de Fluxo de Caixa
    fluxo_df = get_fluxo_caixa_dataframe()
    fig_fluxo = px.bar(
        fluxo_df.melt(id_vars="Dia", var_name="Tipo", value_name="Valor"),
        x="Dia", y="Valor", color="Tipo", barmode="group",
        title="Fluxo de Caixa"
    )
    st.plotly_chart(fig_fluxo, use_container_width=True)

    # ─ Gráfico de Vendas
    vendas_df = get_vendas_dataframe()
    fig_vendas = px.line(
        vendas_df, x="Mês", y="Vendas", markers=True, title="Gráfico de Vendas"
    )
    st.plotly_chart(fig_vendas, use_container_width=True)
