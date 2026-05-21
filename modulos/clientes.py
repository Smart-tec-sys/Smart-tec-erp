import streamlit as st
import pandas as pd
from utils.api_client import get_clientes, criar_cliente, atualizar_cliente, deletar_cliente


def telaClientes():
    # ==========================================
    # CONTROLE DE ESTADO (NAVEGAÇÃO)
    # ==========================================
    if 'tela_atual_clientes' not in st.session_state:
        st.session_state.tela_atual_clientes = 'listar'

    def mudar_tela(nova_tela):
        st.session_state.tela_atual_clientes = nova_tela

    def ir_para_inicio():
        st.session_state.pagina_atual = 'Dashboard'
        st.rerun()

    # ==========================================
    # CAPTURA QUERY PARAMS (DEVE VIR ANTES DE TUDO)
    # ==========================================
    params = st.query_params
    if params.get("nav") == "dashboard":
        st.query_params.clear()
        ir_para_inicio()
    elif params.get("nav") == "clientes_listar":
        st.query_params.clear()
        st.session_state.tela_atual_clientes = 'listar'
        st.rerun()

    # ==========================================
    # TÍTULO + BREADCRUMB
    # ==========================================
    col_titulo, col_caminho = st.columns([1, 1])
    with col_titulo:
        st.title("👥 Clientes")
    with col_caminho:
        tela_fmt = st.session_state.tela_atual_clientes.replace('_', ' ').title()
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
                <a href="?nav=clientes_listar" target="_self" style="
                    color: #888;
                    font-size: 12px;
                    text-decoration: none;
                ">Clientes</a>
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

    # --- BUSCAR DADOS DO BACKEND ---
    clientes_cadastrados = []
    try:
        resp = get_clientes()
        if resp.status_code == 200:
            clientes_cadastrados = resp.json()
    except:
        st.error("🚨 Erro de conexão com o servidor Backend.")

    # ==========================================
    # TELA 1: LISTAR (Padrão)
    # ==========================================
    if st.session_state.tela_atual_clientes == 'listar':
        
        col_add, col_more, col_search, col_adv = st.columns([1.5, 1.5, 3, 1.5])
        
        with col_add:
            st.button("➕ Adicionar", on_click=mudar_tela, args=('adicionar',), use_container_width=True, type="primary")
            
        with col_more:
            with st.popover("⚙️ Mais ações", use_container_width=True):
                if st.button("📄 Importar de uma planilha", use_container_width=True):
                    st.session_state.pagina_atual = 'ImpPlanilhaClientes'
                    st.rerun()
                if st.button("🧾 Importar de notas fiscais", use_container_width=True):
                    st.session_state.pagina_atual = 'ImpNFClientes'
                    st.rerun()
                if st.button("📤 Exportar clientes", use_container_width=True):
                    st.success("Clientes exportados com sucesso!")
                if st.button("✖️ Excluir clientes", use_container_width=True):
                    st.error("⚠️ Você realmente deseja excluir os clientes selecionados?")
                    
        with col_search:
            termo_busca = st.text_input("Busca", placeholder="Buscar por nome...", label_visibility="collapsed")
            
        with col_adv:
            st.button("🔍 Busca avançada", on_click=mudar_tela, args=('busca_avancada',), use_container_width=True)

        st.divider()

        if clientes_cadastrados:
            df = pd.DataFrame(clientes_cadastrados)
            df_safe = df.fillna("")
            
            if termo_busca:
                df_view = df_safe[df_safe['nome'].str.lower().str.contains(termo_busca.lower())]
            else:
                df_view = df_safe
                
            colunas_exibicao = ["id", "nome", "documento", "telefone_celular", "situacao"]
            colunas_presentes = [col for col in colunas_exibicao if col in df_view.columns]
            
            st.dataframe(df_view[colunas_presentes], use_container_width=True, hide_index=True)
            
            with st.expander("✏️ Editar ou Excluir um Cliente"):
                opcoes_clientes = {f"{c['id']} - {c['nome']}": c for c in clientes_cadastrados}
                cliente_selecionado = st.selectbox("Selecione o Cliente:", [""] + list(opcoes_clientes.keys()))
                
                if cliente_selecionado != "":
                    dados_atuais = opcoes_clientes[cliente_selecionado]
                    with st.form("form_editar_lista"):
                        col1, col2 = st.columns(2)
                        with col1:
                            novo_nome = st.text_input("Nome", value=dados_atuais.get("nome", ""))
                            nova_sit = st.selectbox("Situação", ["Ativo", "Inativo"], index=0 if dados_atuais.get("situacao") == "Ativo" else 1)
                        with col2:
                            novo_doc = st.text_input("CPF / CNPJ", value=dados_atuais.get("documento", ""))
                            novo_cel = st.text_input("Celular", value=dados_atuais.get("telefone_celular", ""))
                        
                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            salvar_edicao = st.form_submit_button("🔄 Atualizar", type="primary", use_container_width=True)
                        with c_btn2:
                            excluir_cli = st.form_submit_button("🗑️ Excluir", use_container_width=True)
                            
                        if salvar_edicao:
                            dados_atualizados = dados_atuais.copy()
                            dados_atualizados.update({"nome": novo_nome, "documento": novo_doc, "situacao": nova_sit, "telefone_celular": novo_cel})
                            atualizar_cliente(dados_atuais["id"], dados_atualizados)
                            st.rerun()
                        if excluir_cli:
                            deletar_cliente(dados_atuais["id"])
                            st.rerun()
        else:
            st.info("Nenhum cliente cadastrado. Clique em 'Adicionar' para começar.")

    # ==========================================
    # TELA 2: ADICIONAR
    # ==========================================
    elif st.session_state.tela_atual_clientes == 'adicionar':
        st.button("⬅️ Voltar para Lista", on_click=mudar_tela, args=('listar',))
        st.title("➕ Adicionar Cliente")
        with st.form("form_novo_cliente", clear_on_submit=True):
            st.markdown("#### 📝 Dados Gerais")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                tipo = st.selectbox("Tipo *", ["Pessoa Física", "Pessoa Jurídica"])
            with col2:
                situacao = st.selectbox("Situação", ["Ativo", "Inativo"])
            with col3:
                nome = st.text_input("Nome *")
            with col4:
                email = st.text_input("E-mail")
            col5, col6, col7 = st.columns([1, 1, 2])
            with col5:
                tel_celular = st.text_input("Celular")
            with col6:
                documento = st.text_input("CPF/CNPJ")
            with col7:
                site = st.text_input("Site")
            st.markdown("#### 📍 Endereço")
            col_cep, col_log, col_num = st.columns([1, 3, 1])
            with col_cep:
                cep = st.text_input("CEP")
            with col_log:
                logradouro = st.text_input("Logradouro")
            with col_num:
                numero = st.text_input("Número")
            st.markdown("#### 💰 Financeiro")
            limite_credito = st.number_input("Limite de crédito (R$)", min_value=0.0, step=100.0)
            st.markdown("---")
            salvar = st.form_submit_button("💾 Salvar Cliente", type="primary", use_container_width=True)
            if salvar:
                if not nome:
                    st.error("⚠️ O campo Nome é obrigatório!")
                else:
                    dados = {
                        "tipo": tipo, "situacao": situacao, "nome": nome,
                        "documento": documento, "telefone_celular": tel_celular,
                        "email": email, "telefone_comercial": "", "site": site,
                        "cep": cep, "logradouro": logradouro, "numero": numero,
                        "limite_credito": limite_credito, "permitir_exceder": False
                    }
                    resp = criar_cliente(dados)
                    if resp.status_code == 200:
                        st.success("✅ Cliente cadastrado!")
                        mudar_tela('listar')
                        st.rerun()

    # ==========================================
    # TELA 3: BUSCA AVANÇADA
    # ==========================================
    elif st.session_state.tela_atual_clientes == 'busca_avancada':
        st.button("⬅️ Voltar para Lista", on_click=mudar_tela, args=('listar',))
        st.title("🔍 Busca Avançada")
        st.markdown("Preencha os campos abaixo para filtrar detalhadamente (Em construção).")
        with st.form("form_busca_avancada"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.selectbox("Tipo de Cliente", ["Todos", "Pessoa Física", "Pessoa Jurídica"])
                st.text_input("Telefone / Celular")
            with col2:
                st.text_input("Nome")
                st.text_input("E-mail")
            with col3:
                st.text_input("CPF / CNPJ")
                st.selectbox("Situação", ["Todos", "Ativo", "Inativo"])
            col_b1, col_b2 = st.columns([1, 5])
            with col_b1:
                st.form_submit_button("✔️ Buscar", type="primary")
            with col_b2:
                st.form_submit_button("✖️ Limpar")
