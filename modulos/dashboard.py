import streamlit as st


def telaDashboard():
    st.title("🏠 Dashboard")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Clientes", 128)

    with col2:
        st.metric("Pedidos", 42)

    with col3:
        st.metric("Faturamento", "R$ 58.320")
