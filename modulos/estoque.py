import streamlit as st
import pandas as pd
from utils.ui import toolbar, cabecalho


def telaEstoque():

    # ==========================================
    # ESTADO E NAVEGAÇÃO
    # ==========================================
    if "tela_estoque" not in st.session_state:
        st.session_state.tela_estoque = "listar"

    def mudar_tela(tela):
        st.session_state.tela_estoque = tela

    # ==========================================
    # CABEÇALHO PADRONIZADO (Substitui o st.title)
    # ==========================================
    tela_nome = "Listar" if st.session_state.tela_estoque == "listar" else "Adicionar"
    
    cabecalho(
        titulo="📦 Estoque",
        modulo="Estoque",
        tela_atual=tela_nome,
        funcao_mudar_tela=mudar_tela
    )

    # ==========================================
    # TELA: LISTAR
    # ==========================================
    if st.session_state.tela_estoque == "listar":

        tb = toolbar(placeholder="Buscar produto no estoque...")

        # Usando .get("add") para evitar erros
        if tb.get("add"):
            mudar_tela("adicionar")
            st.rerun()

        st.info("Nenhum item no estoque cadastrado.")

    # ==========================================
    # TELA: ADICIONAR
    # ==========================================
    elif st.session_state.tela_estoque == "adicionar":

        if st.button("⬅️ Voltar"):
            mudar_tela("listar")
            st.rerun()

        st.subheader("Adicionar item ao estoque")

        with st.form("form_estoque"):

            nome_campo = st.text_input("Nome do Produto")
            
            # Adicionei um campo de quantidade só para dar cara de estoque
            quantidade = st.number_input("Quantidade", min_value=0, step=1) 

            salvar = st.form_submit_button("Salvar", type="primary")

            if salvar:
                # Aqui você integraria com a API/Backend depois
                st.success("Estoque salvo com sucesso!")
                mudar_tela("listar")
                st.rerun()
