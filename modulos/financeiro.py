import streamlit as st
import pandas as pd
from utils.ui import toolbar, cabecalho


def telaFinanceiro():

    # ==========================================
    # ESTADO E NAVEGAÇÃO
    # ==========================================
    if "tela_financeiro" not in st.session_state:
        st.session_state.tela_financeiro = "listar"

    def mudar_tela(tela):
        st.session_state.tela_financeiro = tela

    # ==========================================
    # CABEÇALHO PADRONIZADO (Substitui o st.title)
    # ==========================================
    tela_nome = "Listar" if st.session_state.tela_financeiro == "listar" else "Adicionar"
    
    cabecalho(
        titulo="💰 Financeiro",
        modulo="Financeiro",
        tela_atual=tela_nome,
        funcao_mudar_tela=mudar_tela
    )

    # ==========================================
    # TELA: LISTAR
    # ==========================================
    if st.session_state.tela_financeiro == "listar":

        tb = toolbar(placeholder="Buscar lançamento...")

        # Ação do botão Novo
        if tb.get("add"):
            mudar_tela("adicionar")
            st.rerun()

        st.info("Nenhum lançamento financeiro encontrado.")

    # ==========================================
    # TELA: ADICIONAR
    # ==========================================
    elif st.session_state.tela_financeiro == "adicionar":

        if st.button("⬅️ Voltar"):
            mudar_tela("listar")
            st.rerun()

        st.subheader("Novo Lançamento Financeiro")

        with st.form("form_financeiro"):

            col1, col2 = st.columns([3, 1])
            with col1:
                descricao = st.text_input("Descrição")
            with col2:
                tipo = st.selectbox("Tipo", ["Receita 📈", "Despesa 📉"])

            valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")

            salvar = st.form_submit_button("Salvar Lançamento", type="primary")

            if salvar:
                # Aqui você integraria com a API/Backend depois
                st.success("Lançamento salvo com sucesso!")
                mudar_tela("listar")
                st.rerun()
