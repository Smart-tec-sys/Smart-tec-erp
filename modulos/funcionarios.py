import streamlit as st
import pandas as pd
from utils.api_client import get_funcionarios, criar_funcionario, atualizar_funcionario, deletar_funcionario


def telaFuncionarios():
    # ==========================================
    # CONTROLE DE ESTADO (NAVEGAÇÃO)
    # ==========================================
    if 'tela_atual_funcionarios' not in st.session_state:
        st.session_state.tela_atual_funcionarios = 'listar'

    def mudar_tela(nova_tela):
        st.session_state.tela_atual_funcionarios = nova_tela

    # ==========================================
    # TÍTULO + BREADCRUMB
    # ==========================================
    col_titulo, col_caminho = st.columns([1, 1])
    with col_titulo:
        st.title("👔 Funcionários")
    with col_caminho:
        tela_fmt = st.session_state.tela_atual_funcionarios.replace('_', ' ').title()
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
                <a href="?nav=funcionarios_listar" target="_self" style="
                    color: #888;
                    font-size: 12px;
                    text-decoration: none;
                ">Funcionários</a>
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
    if st.session_state.tela_atual_funcionarios == 'listar':
        
        # --- BARRA SUPERIOR ESTILO GESTÃO CLICK ---
        col_add, col_search, col_adv = st.columns([1.5, 4, 1.5])
        
        with col_add:
            st.button("➕ Adicionar", on_click=mudar_tela, args=('adicionar',), use_container_width=True, type="primary")
            
        with col_search:
            termo_busca = st.text_input("Busca", placeholder="Buscar por nome...", label_visibility="collapsed")
            
        with col_adv:
            st.button("🔍 Busca avançada", on_click=mudar_tela, args=('busca_avancada',), use_container_width=True)
            
        st.divider()

        # --- BUSCAR DADOS DO BACKEND ---
        funcionarios_cadastrados = []
        try:
            resp = get_funcionarios()
            if resp.status_code == 200:
                funcionarios_cadastrados = resp.json()
        except:
            st.error("🚨 Erro de conexão com o servidor Backend.")

        # --- TABELA ---
        if funcionarios_cadastrados:
            df = pd.DataFrame(funcionarios_cadastrados)
            df_safe = df.fillna("")
            
            if termo_busca:
                df_view = df_safe[df_safe['nome'].str.lower().str.contains(termo_busca.lower())]
            else:
                df_view = df_safe
                
            # Exibe as colunas que existirem no backend
            colunas_exibicao = ["id", "nome", "cpf", "email", "situacao"]
            colunas_presentes = [col for col in colunas_exibicao if col in df_view.columns]
            
            st.dataframe(df_view[colunas_presentes], use_container_width=True, hide_index=True)
            
            # --- EDITAR / EXCLUIR ---
            with st.expander("✏️ Editar ou Excluir um Funcionário"):
                opcoes = {f"{f['id']} - {f['nome']}": f for f in funcionarios_cadastrados}
                selecionado = st.selectbox("Selecione o Funcionário para edição rápida:", [""] + list(opcoes.keys()), key="sel_edit_func")
                
                if selecionado != "":
                    dados_atuais = opcoes[selecionado]
                    with st.form("form_editar_func"):
                        col1, col2 = st.columns(2)
                        with col1:
                            novo_nome = st.text_input("Nome", value=dados_atuais.get("nome", ""))
                            nova_sit = st.selectbox("Situação", ["Ativo", "Inativo"], index=0 if dados_atuais.get("situacao") == "Ativo" else 1)
                        with col2:
                            novo_cpf = st.text_input("CPF", value=dados_atuais.get("cpf", ""))
                            novo_email = st.text_input("E-mail", value=dados_atuais.get("email", ""))
                        
                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            salvar_edicao = st.form_submit_button("🔄 Atualizar", type="primary", use_container_width=True)
                        with c_btn2:
                            excluir_func = st.form_submit_button("🗑️ Excluir", use_container_width=True)
                            
                        if salvar_edicao:
                            dados_atualizados = dados_atuais.copy()
                            dados_atualizados.update({"nome": novo_nome, "cpf": novo_cpf, "situacao": nova_sit, "email": novo_email})
                            atualizar_funcionario(dados_atuais["id"], dados_atualizados)
                            st.rerun()
                        if excluir_func:
                            deletar_funcionario(dados_atuais["id"])
                            st.rerun()
        else:
            st.info("Nenhum funcionário cadastrado. Clique em 'Adicionar' para começar.")

    # ==========================================
    # TELA 2: ADICIONAR (CADASTRO COMPLETO)
    # ==========================================
    elif st.session_state.tela_atual_funcionarios == 'adicionar':
        
        with st.form("form_novo_funcionario", clear_on_submit=True):
            
            # --- DADOS GERAIS ---
            st.markdown("### 📝 Dados gerais")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                nome = st.text_input("Nome *")
            with col2:
                cpf = st.text_input("CPF")
            with col3:
                rg = st.text_input("RG")
            with col4:
                data_nasc = st.date_input("Data de nascimento", format="DD/MM/YYYY")
                
            col5, col6, col7, col8 = st.columns(4)
            with col5:
                sexo = st.selectbox("Sexo", ["Selecione", "Masculino", "Feminino", "Outro"])
            with col6:
                email = st.text_input("E-mail")
            with col7:
                comissao = st.number_input("Comissão (%)", min_value=0.0, step=0.5)
            with col8:
                situacao = st.selectbox("Situação", ["Ativo", "Inativo"])
                
            acesso_sistema = st.checkbox("Permitir acesso ao sistema")
            observacoes = st.text_area("Observações", height=100)

            st.markdown("---")
            
            # --- FOTO ---
            st.markdown("### 📷 Foto")
            st.caption("Insira uma imagem JPG ou GIF de até 1MB.")
            foto = st.file_uploader("Selecione uma foto", type=["jpg", "jpeg", "png", "gif"], label_visibility="collapsed")

            st.markdown("---")

            # --- CONTATOS ---
            st.markdown("### 📞 Contatos")
            col_fixo, col_cel1, col_cel2 = st.columns(3)
            with col_fixo:
                tel_fixo = st.text_input("Telefone fixo")
            with col_cel1:
                celular1 = st.text_input("Celular 1")
            with col_cel2:
                celular2 = st.text_input("Celular 2")

            st.markdown("---")

            # --- ENDEREÇO ---
            st.markdown("### 📍 Endereço")
            col_cep, col_log = st.columns([1, 3])
            with col_cep:
                cep = st.text_input("CEP", placeholder="Digite para buscar")
            with col_log:
                logradouro = st.text_input("Logradouro")
                
            col_num, col_comp = st.columns([1, 3])
            with col_num:
                numero = st.text_input("Número")
            with col_comp:
                complemento = st.text_input("Complemento")
                
            col_bairro, col_cid = st.columns(2)
            with col_bairro:
                bairro = st.text_input("Bairro")
            with col_cid:
                cidade_uf = st.text_input("Cidade/UF", placeholder="Digite para buscar")

            st.markdown("---")

            # --- ANEXOS ---
            st.markdown("### 📎 Anexos")
            st.caption("Utilize este espaço para anexar arquivos e documentos. Tamanho máximo 5MB.")
            anexo = st.file_uploader("Selecionar arquivo", label_visibility="collapsed", key="file_anexo")

            st.markdown("---")
            
            # --- BOTÕES DE AÇÃO ---
            col_btn_salvar, col_btn_cancelar, _ = st.columns([1.5, 1.5, 7])
            with col_btn_salvar:
                salvar = st.form_submit_button("✔️ Cadastrar", type="primary", use_container_width=True)
            with col_btn_cancelar:
                cancelar = st.form_submit_button("✖️ Cancelar", use_container_width=True)
            
            if salvar:
                if not nome:
                    st.error("⚠️ O campo Nome é obrigatório!")
                else:
                    dados = {
                        "nome": nome, "cpf": cpf, "rg": rg, "email": email,
                        "situacao": situacao, "sexo": sexo, "comissao": float(comissao),
                        "tel_fixo": tel_fixo, "celular1": celular1, "celular2": celular2,
                        "cep": cep, "logradouro": logradouro, "numero": numero,
                        "complemento": complemento, "bairro": bairro, "cidade_uf": cidade_uf,
                        "observacoes": observacoes, "acesso_sistema": acesso_sistema
                    }
                    resp = criar_funcionario(dados)
                    if resp.status_code == 200:
                        st.success("✅ Funcionário cadastrado com sucesso!")
                        mudar_tela('listar')
                        st.rerun()
            
            if cancelar:
                mudar_tela('listar')
                st.rerun()

    # ==========================================
    # TELA 3: BUSCA AVANÇADA
    # ==========================================
    elif st.session_state.tela_atual_funcionarios == 'busca_avancada':
        
        st.title("🔍 Busca Avançada - Funcionários")
        st.info("Filtros avançados em construção.")
        
        if st.button("⬅️ Voltar para Lista"):
            mudar_tela('listar')
            st.rerun()
