import streamlit as st
from utils.api_client import get_produtos


def telaProdutos():
    st.title("📦 Produtos")

    resposta = get_produtos()

    if resposta.status_code == 200:
        st.dataframe(resposta.json(), use_container_width=True)
    else:
        st.error("Erro ao carregar produtos")
