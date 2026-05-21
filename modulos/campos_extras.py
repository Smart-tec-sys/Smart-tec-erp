import streamlit as st


def telaCamposExtras():
    # ==========================================
    # CONTROLE DE ESTADO E DADOS (MEMÓRIA)
    # ==========================================
    if 'tela_atual_campos_extras' not in st.session_state:
        st.session_state.tela_atual_campos_extras = 'listar'
        
    if 'campo_extra_em_edicao' not in st.session_state:
        st.session_state.campo_extra_em_edicao = None

    # Começamos com a lista VAZIA para mostrar a tela de "boas-vindas" da sua imagem 1
    if 'dados_campos_extras' not in st.session_state:
        st.session_state.dados_campos_extras = []

    def mudar_tela(nova_tela, id_campo=None):
        st.session_state.tela_atual_campos_extras = nova_tela
        st.session_state.campo_extra_em_edicao = id_campo

    def excluir_campo(id_campo):
        st.session_state.dados_campos_extras = [c for c in st.session_state.dados_campos_extras if c["id"] != id_campo]

    # ==========================================
    # TELA 1: LISTAR
    # ==========================================
    if st.session_state.tela_atual_campos_extras == 'listar':
        st.title("📄 Campos extras")
        
        col_add, col_search = st.columns([1.5, 5.5])
        with col_add:
            st.button("➕ Adicionar", on_click=mudar_tela, args=('adicionar',), use_container_width=True, type="primary")
        with col_search:
            termo_busca = st.text_input("Busca", placeholder="Buscar por nome...", label_visibility="collapsed")
            
        st.divider()
        st.info("Durante o cadastro de clientes, é possível vincular seus campos extras.")
        
        dados_filtrados = st.session_state.dados_campos_extras
        if termo_busca:
            dados_filtrados = [c for c in dados_filtrados if termo_busca.lower() in c["nome"].lower()]

        # SE TIVER DADOS, MOSTRA A TABELA
        if dados_filtrados:
            col_nome, col_tipo, col_obrig, c_v, c_e, c_d = st.columns([3, 2, 1, 0.5, 0.5, 0.5])
            col_nome.markdown("**↓ Nome**")
            col_tipo.markdown("**Tipo**")
            col_obrig.markdown("**Obrigatório**")
            c_v.markdown("**Ações**")
            st.markdown("---")
            
            for campo in dados_filtrados:
                col_nome, col_tipo, col_obrig, c_v, c_e, c_d = st.columns([3, 2, 1, 0.5, 0.5, 0.5])
                
                col_nome.write(campo["nome"])
                col_tipo.write(campo["tipo"])
                col_obrig.write(campo["obrigatorio"])
                
                with c_v:
                    if st.button("🔍", key=f"view_{campo['id']}", help="Visualizar"):
                        mudar_tela('visualizar', campo['id'])
                        st.rerun()
                with c_e:
                    if st.button("✏️", key=f"edit_{campo['id']}", help="Editar"):
                        mudar_tela('editar', campo['id'])
                        st.rerun()
                with c_d:
                    if st.button("✖️", key=f"del_{campo['id']}", help="Excluir"):
                        excluir_campo(campo['id'])
                        st.rerun()
                
                st.markdown("---")
                
        # SE NÃO TIVER DADOS, MOSTRA A TELA DE BOAS-VINDAS (Igual à imagem 1)
        else:
            col_icone, col_texto = st.columns([1, 4])
            with col_icone:
                st.markdown("<h1 style='text-align: center; font-size: 80px; color: #555;'>📄</h1>", unsafe_allow_html=True)
            with col_texto:
                st.subheader("Campos extras")
                st.write("Campos extras são campos que podem ser criados pelo usuário.")
                st.button("➕ Adicionar meu primeiro campo extra", on_click=mudar_tela, args=('adicionar',), type="primary")
                
                st.markdown("""
                **Adicionando campos extras você vai conseguir:**
                - ✅ Criar campos para atribuir dados que não possuem um campo no formulário padrão
                - ✅ Filtrar registros através da informação atribuída no campo na busca avançada
                - ✅ Gerar relatórios com filtros de campos extras
                - ✅ E muito mais...
                """)

    # ==========================================
    # TELA 2: VISUALIZAR
    # ==========================================
    elif st.session_state.tela_atual_campos_extras == 'visualizar':
        st.button("⬅️ Início - Campos extras", on_click=mudar_tela, args=('listar',))
        st.title("Visualizar campo extra")
        
        id_view = st.session_state.campo_extra_em_edicao
        campo_atual = next((c for c in st.session_state.dados_campos_extras if c["id"] == id_view), None)
        
        if campo_atual:
            st.markdown(f"""
            | | |
            |---|---|
            | **Nome** | {campo_atual['nome']} |
            | **Tipo** | {campo_atual['tipo']} |
            | **Obrigatório** | {campo_atual['obrigatorio']} |
            """)

    # ==========================================
    # TELA 3: ADICIONAR
    # ==========================================
    elif st.session_state.tela_atual_campos_extras == 'adicionar':
        st.button("⬅️ Início - Campos extras", on_click=mudar_tela, args=('listar',))
        st.title("Adicionar campo extra")
        
        with st.form("form_novo_campo_extra", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1.5, 1.5])
            with col1:
                nome = st.text_input("Nome *")
            with col2:
                tipo = st.selectbox("Tipo", ["Texto", "Data", "Número", "Seleção Múltipla", "Caixa de Seleção"])
            with col3:
                obrigatorio = st.selectbox("Obrigatório", ["Não", "Sim"])
                
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
                    lista_ids = [c["id"] for c in st.session_state.dados_campos_extras]
                    novo_id = max(lista_ids) + 1 if len(lista_ids) > 0 else 1
                        
                    st.session_state.dados_campos_extras.append({
                        "id": novo_id, "nome": nome, "tipo": tipo, "obrigatorio": obrigatorio
                    })
                    st.success(f"Campo extra '{nome}' cadastrado com sucesso!")
                    mudar_tela('listar')
                    st.rerun()
            
            if cancelar:
                mudar_tela('listar')
                st.rerun()

    # ==========================================
    # TELA 4: EDITAR
    # ==========================================
    elif st.session_state.tela_atual_campos_extras == 'editar':
        st.button("⬅️ Início - Campos extras", on_click=mudar_tela, args=('listar',))
        st.title("Editar campo extra")
        
        id_edit = st.session_state.campo_extra_em_edicao
        campo_atual = next((c for c in st.session_state.dados_campos_extras if c["id"] == id_edit), None)
        
        if campo_atual:
            with st.form("form_editar_campo_extra"):
                col1, col2, col3 = st.columns([2, 1.5, 1.5])
                with col1:
                    novo_nome = st.text_input("Nome *", value=campo_atual["nome"])
                with col2:
                    novo_tipo = st.selectbox("Tipo", ["Texto", "Data", "Número", "Seleção Múltipla", "Caixa de Seleção"], index=["Texto", "Data", "Número", "Seleção Múltipla", "Caixa de Seleção"].index(campo_atual["tipo"]))
                with col3:
                    novo_obrig = st.selectbox("Obrigatório", ["Não", "Sim"], index=["Não", "Sim"].index(campo_atual["obrigatorio"]))
                
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
                        for c in st.session_state.dados_campos_extras:
                            if c["id"] == id_edit:
                                c["nome"] = novo_nome
                                c["tipo"] = novo_tipo
                                c["obrigatorio"] = novo_obrig
                        st.success("Campo atualizado com sucesso!")
                        mudar_tela('listar')
                        st.rerun()
                
                if cancelar:
                    mudar_tela('listar')
                    st.rerun()
