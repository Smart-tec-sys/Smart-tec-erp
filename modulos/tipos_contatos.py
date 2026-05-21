import streamlit as st


def telaTiposContatos():
    # ==========================================
    # CONTROLE DE ESTADO E DADOS (MEMÓRIA)
    # ==========================================
    if 'tela_atual_tipos_contatos' not in st.session_state:
        st.session_state.tela_atual_tipos_contatos = 'listar'
        
    if 'contato_em_edicao' not in st.session_state:
        st.session_state.contato_em_edicao = None

    # Adicionei dados extras para a tela de "Visualizar" ficar igual à sua imagem
    if 'dados_contatos' not in st.session_state:
        st.session_state.dados_contatos = [
            {"id": 1, "nome": "Comercial", "cadastrado_por": "Valmir Barbosa", "cadastrado_em": "23/10/2026 08:22:51", "modificado_em": "23/10/2026 08:22:51"},
            {"id": 2, "nome": "Residencial", "cadastrado_por": "Valmir Barbosa", "cadastrado_em": "23/10/2026 08:22:51", "modificado_em": "23/10/2026 08:22:51"},
            {"id": 3, "nome": "Entrega", "cadastrado_por": "Valmir Barbosa", "cadastrado_em": "23/10/2026 08:22:51", "modificado_em": "23/10/2026 08:22:51"}
        ]

    def mudar_tela(nova_tela, id_contato=None):
        st.session_state.tela_atual_tipos_contatos = nova_tela
        st.session_state.contato_em_edicao = id_contato

    def excluir_contato(id_contato):
        st.session_state.dados_contatos = [c for c in st.session_state.dados_contatos if c["id"] != id_contato]

    # ==========================================
    # TELA 1: LISTAR
    # ==========================================
    if st.session_state.tela_atual_tipos_contatos == 'listar':
        st.title("📞 Tipos de contatos")
        
        col_add, col_search = st.columns([1.5, 5.5])
        with col_add:
            st.button("➕ Adicionar", on_click=mudar_tela, args=('adicionar',), use_container_width=True, type="primary")
        with col_search:
            termo_busca = st.text_input("Busca", placeholder="Buscar por nome...", label_visibility="collapsed")
            
        st.divider()
        st.info("Durante o cadastro de clientes, fornecedores e transportadoras é possível informar o tipo de contato ao qual eles pertencem.")
        
        dados_filtrados = st.session_state.dados_contatos
        if termo_busca:
            dados_filtrados = [c for c in dados_filtrados if termo_busca.lower() in c["nome"].lower()]

        if dados_filtrados:
            # Cabeçalho: Nome ocupa muito espaço (6), botões ocupam pouco (0.5 cada)
            col_nome, c_v, c_e, c_d = st.columns([6, 0.5, 0.5, 0.5])
            col_nome.markdown("**↓ Nome**")
            c_v.markdown("**Ações**")  # Título fica em cima do primeiro botão
            st.markdown("---")
            
            # Linhas da tabela
            for contato in dados_filtrados:
                col_nome, c_v, c_e, c_d = st.columns([6, 0.5, 0.5, 0.5])
                
                col_nome.write(contato["nome"])
                
                with c_v:
                    if st.button("🔍", key=f"view_{contato['id']}", help="Visualizar"):
                        mudar_tela('visualizar', contato['id'])
                        st.rerun()
                with c_e:
                    if st.button("✏️", key=f"edit_{contato['id']}", help="Editar"):
                        mudar_tela('editar', contato['id'])
                        st.rerun()
                with c_d:
                    if st.button("✖️", key=f"del_{contato['id']}", help="Excluir"):
                        excluir_contato(contato['id'])
                        st.rerun()
                
                st.markdown("---")
        else:
            st.warning("Nenhum tipo de contato encontrado.")

    # ==========================================
    # TELA 2: VISUALIZAR
    # ==========================================
    elif st.session_state.tela_atual_tipos_contatos == 'visualizar':
        st.button("⬅️ Início - Tipos de contatos", on_click=mudar_tela, args=('listar',))
        st.title("Visualizar tipo de contato")
        
        id_view = st.session_state.contato_em_edicao
        contato_atual = next((c for c in st.session_state.dados_contatos if c["id"] == id_view), None)
        
        if contato_atual:
            # Desenhando uma tabela de visualização simples com markdown
            st.markdown(f"""
            | | |
            |---|---|
            | **Nome** | {contato_atual['nome']} |
            | **Cadastrado por** | {contato_atual.get('cadastrado_por', 'Sistema')} |
            | **Cadastrado em** | {contato_atual.get('cadastrado_em', '-')} |
            | **Modificado em** | {contato_atual.get('modificado_em', '-')} |
            """)

    # ==========================================
    # TELA 3: ADICIONAR
    # ==========================================
    elif st.session_state.tela_atual_tipos_contatos == 'adicionar':
        st.button("⬅️ Início - Tipos de contatos", on_click=mudar_tela, args=('listar',))
        st.title("Adicionar tipo de contato")
        
        with st.form("form_novo_tipo_contato", clear_on_submit=True):
            nome = st.text_input("Nome *")
            st.markdown("---")
            
            col_btn_salvar, col_btn_cancelar, _ = st.columns([1.5, 1.5, 7])
            with col_btn_salvar:
                salvar = st.form_submit_button("✔️ Cadastrar", type="primary", use_container_width=True)
            with col_btn_cancelar:
                cancelar = st.form_submit_button("✖️ Cancelar", use_container_width=True)
            
            if salvar:
                if not nome:
                    st.error("⚠️ O campo Nome é obrigatório!")
                else:
                    lista_ids = [c["id"] for c in st.session_state.dados_contatos]
                    novo_id = max(lista_ids) + 1 if len(lista_ids) > 0 else 1
                        
                    st.session_state.dados_contatos.append({
                        "id": novo_id, "nome": nome,
                        "cadastrado_por": "Usuário Atual",
                        "cadastrado_em": "Agora", "modificado_em": "Agora"
                    })
                    st.success(f"Tipo de contato '{nome}' cadastrado com sucesso!")
                    mudar_tela('listar')
                    st.rerun()
            
            if cancelar:
                mudar_tela('listar')
                st.rerun()

    # ==========================================
    # TELA 4: EDITAR
    # ==========================================
    elif st.session_state.tela_atual_tipos_contatos == 'editar':
        st.button("⬅️ Início - Tipos de contatos", on_click=mudar_tela, args=('listar',))
        st.title("Editar tipo de contato")
        
        id_edit = st.session_state.contato_em_edicao
        contato_atual = next((c for c in st.session_state.dados_contatos if c["id"] == id_edit), None)
        
        if contato_atual:
            with st.form("form_editar_tipo_contato"):
                novo_nome = st.text_input("Nome *", value=contato_atual["nome"])
                st.markdown("---")
                
                col_btn_salvar, col_btn_cancelar, _ = st.columns([1.5, 1.5, 7])
                with col_btn_salvar:
                    salvar = st.form_submit_button("✔️ Atualizar", type="primary", use_container_width=True)
                with col_btn_cancelar:
                    cancelar = st.form_submit_button("✖️ Cancelar", use_container_width=True)
                
                if salvar:
                    if not novo_nome:
                        st.error("⚠️ O campo Nome é obrigatório!")
                    else:
                        for c in st.session_state.dados_contatos:
                            if c["id"] == id_edit:
                                c["nome"] = novo_nome
                                c["modificado_em"] = "Agora"
                        st.success("Contato atualizado com sucesso!")
                        mudar_tela('listar')
                        st.rerun()
                
                if cancelar:
                    mudar_tela('listar')
                    st.rerun()
