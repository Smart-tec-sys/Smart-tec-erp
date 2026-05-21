import streamlit as st


def telaImportarXML():
    st.title("📄 Importar XML")
    
    col_upload, col_instrucoes = st.columns([1.5, 1])
    
    with col_upload:
        st.subheader("Importar notas fiscais")
        st.write("Importe suas notas fiscais de produtos que foram emitidas em um outro sistema para o nosso e faça o cadastro de produtos, clientes, fornecedores e transportadoras. Faça a importação clicando no botão abaixo.")
        
        st.warning("Atenção: Caso você queira importar XML de uma nota fiscal de compra emitida pelo seu fornecedor, acesse o menu principal Estoque -> Compras e clique em Importar XML.")
        
        st.write("")
        st.markdown("<h4 style='text-align: center;'>Solte os arquivos aqui para fazer upload...</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>ou</p>", unsafe_allow_html=True)
        
        arquivo_xml = st.file_uploader("Selecionar arquivos XML", type=['xml'], accept_multiple_files=True, label_visibility="collapsed")
        st.caption("Envie até 50 arquivos por vez.")
        
        if arquivo_xml:
            st.success(f"{len(arquivo_xml)} arquivo(s) selecionado(s) com sucesso!")
            st.button("✔️ Importar", type="primary")

    with col_instrucoes:
        st.subheader("Importações")
        st.markdown("""
        - ✔️ Notas fiscais não cadastradas
        - ✔️ Clientes não cadastrados
        - ✔️ Produtos não cadastrados
        - ✔️ Fornecedores não cadastrados
        - ✔️ Transportadoras não cadastradas
        """)
