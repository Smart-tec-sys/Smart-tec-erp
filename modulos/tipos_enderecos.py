import streamlit as st


def telaTiposEnderecos():
    # ==========================================
    # CONTROLE DE ESTADO E DADOS (MEMÓRIA)
    # ==========================================
    if 'tela_atual_tipos_enderecos' not in st.session_state:
        st.session_state.tela_atual_tipos_enderecos = 'listar'
        
    if 'endereco_em_edicao' not in st.session_state:
        st.session_state.endereco_em_edicao = None

    if 'dados_enderecos' not in st.session_state:
        st.session_state.dados_enderecos = [
            {"id": 1, "nome": "Comercial", "cadastrado_por": "Valmir Barbosa", "cadastrado_em": "23/10/2026 08:22:51", "modificado_em": "23/10/2026 08:22:51"},
            {"id": 2, "nome": "Residencial", "cadastrado_por": "Valmir Barbosa", "cadastrado_em": "23/10/2026 08:22:51", "modificado_em": "23/10/2026 08:22:51"},
            {"id": 3, "nome": "Entrega", "cadastrado_por": "Valmir Barbosa", "cadastrado_em": "23/10/2026 08:22:51", "modificado_em": "23/10/2026 08:22:51"}
        ]

    def mudar_tela(nova_tela, id_endereco=None):
        st.session_state.tela_atual_tipos_enderecos = nova_tela
        st.session_state.endereco_em_edicao = id_endereco

    def excluir_endereco(id_endereco):
        st.session_state.dados_enderecos = [e for e in st.session_state.dados_enderecos if e["id"] != id_endereco]

    # ==========================================
    # TELA 1: LISTAR
    # ==========================================
    if st.session_state.tela_atual_tipos_enderecos == 'listar':
        st.title("📍 Tipos de endereços")
        
        col_add, col_search = st.columns([1.5, 5.5])
        with col_add:
            st.button("➕ Adicionar", on_click=mudar_tela, args=('adicionar',), use_container_width=True, type="primary")
        with col_search:
            termo_busca = st.text_input("Busca", placeholder="Buscar por nome...", label_visibility="collapsed")
            
        st.divider()
        st.info("Durante o cadastro de clientes, fornecedores e transportadoras é possível informar o tipo de endereço ao qual eles pertencem.")
        
        dados_filtrados = st.session_state.dados_enderecos
        if termo_busca:
            dados_filtrados = [e for e in dados_filtrados if termo_busca.lower() in e["nome"].lower()]

        if dados_filtrados:
            col_nome, c_v, c_e, c_d = st.columns([6, 0.5, 0.5, 0.5])
            col_nome.markdown("**↓ Nome**")
            c_v.markdown("**Ações**")
            st.markdown("---")
            
            for endereco in dados_filtrados:
                col_nome, c_v, c_e, c_d = st.columns([6, 0.5, 0.5, 0.5])
                
                col_nome.write(endereco["nome"])
                
                with c_v:
                    if st.button("🔍", key=f"view_{endereco['id']}", help="Visualizar"):
                        mudar_tela('visualizar', endereco['id'])
                        st.rerun()
                with c_e:
                    if st.button("✏️", key=f"edit_{endereco['id']}", help="Editar"):
                        mudar_tela('editar', endereco['id'])
                        st.rerun()
                with c_d:
                    if st.button("✖️", key=f"del_{endereco['id']}", help="Excluir"):
                        excluir_endereco(endereco['id'])
                        st.rerun()
                
                st.markdown("---")
        else:
            st.warning("Nenhum tipo de endereço encontrado.")

    # ==========================================
    # TELA 2: VISUALIZAR
    # ==========================================
    elif st.session_state.tela_atual_tipos_enderecos == 'visualizar':
        st.button("⬅️ Início - Tipos de endereços", on_click=mudar_tela, args=('listar',))
        st.title("Visualizar tipo de endereço")
        
        id_view = st.session_state.endereco_em_edicao
        endereco_atual = next((e for e in st.session_state.dados_enderecos if e["id"] == id_view), None)
        
        if endereco_atual:
            st.markdown(f"""
            | | |
            |---|---|
            | **Nome** | {endereco_atual['nome']} |
            | **Cadastrado por** | {endereco_atual.get('cadastrado_por', 'Sistema')} |
            | **Cadastrado em** | {endereco_atual.get('cadastrado_em', '-')} |
            | **Modificado em** | {endereco_atual.get('modificado_em', '-')} |
            """)

    # ==========================================
    # TELA 3: ADICIONAR
    # ==========================================
    elif st.session_state.tela_atual_tipos_enderecos == 'adicionar':
        st.button("⬅️ Início - Tipos de endereços", on_click=mudar_tela, args=('listar',))
        st.title("Adicionar tipo de endereço")
        
        with st.form("form_novo_tipo_endereco", clear_on_submit=True):
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
                    lista_ids = [e["id"] for e in st.session_state.dados_enderecos]
                    novo_id = max(lista_ids) + 1 if len(lista_ids) > 0 else 1
                        
                    st.session_state.dados_enderecos.append({
                        "id": novo_id, "nome": nome,
                        "cadastrado_por": "Usuário Atual",
                        "cadastrado_em": "Agora", "modificado_em": "Agora"
                    })
                    st.success(f"Tipo de endereço '{nome}' cadastrado com sucesso!")
                    mudar_tela('listar')
                    st.rerun()
            
            if cancelar:
                mudar_tela('listar')
                st.rerun()

    # ==========================================
    # TELA 4: EDITAR
    # ==========================================
    elif st.session_state.tela_atual_tipos_enderecos == 'editar':
        st.button("⬅️ Início - Tipos de endereços", on_click=mudar_tela, args=('listar',))
        st.title("Editar tipo de endereço")
        
        id_edit = st.session_state.endereco_em_edicao
        endereco_atual = next((e for e in st.session_state.dados_enderecos if e["id"] == id_edit), None)
        
        if endereco_atual:
            with st.form("form_editar_tipo_endereco"):
                novo_nome = st.text_input("Nome *", value=endereco_atual["nome"])
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
                        for e in st.session_state.dados_enderecos:
                            if e["id"] == id_edit:
                                e["nome"] = novo_nome
                                e["modificado_em"] = "Agora"
                        st.success("Endereço atualizado com sucesso!")
                        mudar_tela('listar')
                        st.rerun()
                
                if cancelar:
                    mudar_tela('listar')
                    st.rerun()
