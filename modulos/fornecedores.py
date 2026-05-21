import streamlit as st
import pandas as pd


def telaFornecedores():
    # ==========================================
    # CONTROLE DE ESTADO (NAVEGAÇÃO)
    # ==========================================
    if 'tela_atual_fornecedores' not in st.session_state:
        st.session_state.tela_atual_fornecedores = 'listar'

    def mudar_tela(nova_tela):
        st.session_state.tela_atual_fornecedores = nova_tela

    # ==========================================
    # TÍTULO + BREADCRUMB
    # ==========================================
    col_titulo, col_caminho = st.columns([1, 1])
    with col_titulo:
        st.title("🏢 Fornecedores")
    with col_caminho:
        tela_fmt = st.session_state.tela_atual_fornecedores.replace('_', ' ').title()
        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: flex-end;
                align-items: center;
                height: 80px;
                gap: 4px;
            ">
                <a href="?nav=dashboard" target="_self" style="
                    color: #888;
                    font-size: 12px;
                    text-decoration: none;
                ">🏠 Início</a>
                <span style="color: #888; font-size: 12px;">›</span>
                <a href="?nav=fornecedores_listar" target="_self" style="
                    color: #888;
                    font-size: 12px;
                    text-decoration: none;
                ">Fornecedores</a>
                <span style="color: #888; font-size: 12px;">›</span>
                <span style="
                    color: #888;
                    font-size: 12px;
                    font-weight: bold;
                ">{tela_fmt}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==========================================
    # TELA 1: LISTAR (Padrão)
    # ==========================================
    if st.session_state.tela_atual_fornecedores == 'listar':
        
                # --- BARRA SUPERIOR ESTILO GESTÃO CLICK ---
        col_add, col_more, col_search, col_adv = st.columns([1.5, 1.5, 3, 1.5])
        
        with col_add:
            st.button("➕ Adicionar", on_click=mudar_tela, args=('adicionar',), use_container_width=True, type="primary")
            
        with col_more:
            # Botão Dropdown apenas com Importar e Exportar
            with st.popover("⚙️ Mais ações", use_container_width=True):
                if st.button("☁️ Importar", use_container_width=True):
                    st.session_state.pagina_atual = 'ImpFornecedores'
                    st.rerun()
                if st.button("📤 Exportar", use_container_width=True):
                    st.info("Em construção")
                    
        with col_search:
            termo_busca = st.text_input("Busca", placeholder="Buscar por nome...", label_visibility="collapsed")
            
        with col_adv:
            st.button("🔍 Busca avançada", on_click=mudar_tela, args=('busca_avancada',), use_container_width=True)

        # Tabela simulada (Até conectarmos no Backend igual fizemos com Clientes)
        st.info("Nenhum fornecedor cadastrado. Clique em 'Adicionar' para começar.")

    # ==========================================
    # TELA 2: ADICIONAR (CADASTRO COMPLETO)
    # ==========================================
    elif st.session_state.tela_atual_fornecedores == 'adicionar':
        st.button("⬅️ Início - Fornecedores", on_click=mudar_tela, args=('listar',))
        
        st.title("Adicionar fornecedor")
        
        with st.form("form_novo_fornecedor", clear_on_submit=True):
            
            # --- DADOS GERAIS ---
            st.markdown("### 📝 Dados gerais")
            col1, col2, col3 = st.columns([1.5, 1.5, 3])
            with col1:
                tipo = st.selectbox("Tipo de fornecedor *", ["Selecione", "Pessoa Física", "Pessoa Jurídica"])
            with col2:
                situacao = st.selectbox("Situação", ["Ativo", "Inativo"])
            with col3:
                nome = st.text_input("Nome *")
                
            col4, col5, col6 = st.columns(3)
            with col4:
                email = st.text_input("Email")
            with col5:
                telefone = st.text_input("Telefone")
            with col6:
                celular = st.text_input("Celular")

            st.markdown("---")
            
            # --- ENDEREÇOS ---
            st.markdown("### 📍 Endereços")
            col_cep, col_log, col_num = st.columns([1, 3, 1])
            with col_cep:
                cep = st.text_input("CEP", placeholder="Digite para buscar")
            with col_log:
                logradouro = st.text_input("Logradouro")
            with col_num:
                numero = st.text_input("Número")
                
            col_comp, col_bairro, col_cid = st.columns([2, 2, 2])
            with col_comp:
                complemento = st.text_input("Complemento")
            with col_bairro:
                bairro = st.text_input("Bairro")
            with col_cid:
                cidade_uf = st.text_input("Cidade/UF", placeholder="Digite para buscar")

            st.markdown("---")

            # --- ANEXOS ---
            st.markdown("### 📎 Anexos")
            st.caption("Utilize este espaço para anexar arquivos e documentos. Tamanho máximo 5MB.")
            anexo = st.file_uploader("Selecionar arquivo", label_visibility="collapsed")

            st.markdown("---")

            # --- OBSERVAÇÕES ---
            st.markdown("### 📝 Observações")
            observacoes = st.text_area("Observações", height=100, label_visibility="collapsed")

            st.markdown("---")
            
            # --- BOTÕES DE AÇÃO ---
            col_btn_salvar, col_btn_cancelar, _ = st.columns([1.5, 1.5, 7])
            with col_btn_salvar:
                salvar = st.form_submit_button("✔️ Cadastrar", type="primary", use_container_width=True)
            with col_btn_cancelar:
                cancelar = st.form_submit_button("✖️ Cancelar", use_container_width=True)
            
            if salvar:
                st.success("Fornecedor cadastrado com sucesso! (Layout pronto, falta ligar no banco)")
            if cancelar:
                mudar_tela('listar')
                st.rerun()

    # ==========================================
    # TELA 3: BUSCA AVANÇADA
    # ==========================================
    elif st.session_state.tela_atual_fornecedores == 'busca_avancada':
        st.button("⬅️ Voltar para Lista", on_click=mudar_tela, args=('listar',))
        
        st.title("🔍 Busca Avançada - Fornecedores")
        st.info("Filtros avançados em construção.")
