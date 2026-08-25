# Smart-tec ERP - Guia de Interface

Este guia registra os padroes de interface ja observados no frontend Streamlit
do projeto.

## Entrada Principal

O frontend Streamlit comeca em `app.py`.

O arquivo configura:

- titulo da pagina;
- icone;
- layout wide;
- sidebar expandida;
- logo em `assets/logo.png`;
- menu lateral com `st.selectbox`;
- rotas para funcoes da pasta `modulos`.

## Navegacao

Telas conectadas no menu principal:

- Dashboard;
- Clientes;
- Produtos;
- Pedidos;
- Orcamentos;
- Financeiro;
- Compras;
- Vendas;
- Estoque;
- Notas Fiscais;
- Relatorios;
- Simulador.

## Componentes Observados

A interface usa Streamlit nativo:

- sidebar;
- forms;
- expanders;
- columns;
- containers;
- metrics;
- mensagens com `st.error`, `st.success`, `st.warning`, `st.info` e
  `st.caption`.

## Padrao de Telas

- Modulos Streamlit expoem uma funcao principal de tela.
- Exemplos identificados: `telaDashboard`, `telaClientes`, `telaProdutos`.
- Funcoes auxiliares usam nomes em portugues.
- O frontend acessa diretamente o banco em modulos como clientes, produtos e
  dashboard.
- Nesses pontos, o frontend nao consome a API FastAPI.

## Orientacoes Visuais

- Preservar o uso de Streamlit nativo.
- Manter consistencia com sidebar, forms, expanders, columns e containers ja
  existentes.
- Usar mensagens claras de erro, sucesso, alerta e informacao.
- Evitar inserir novos frameworks visuais sem decisao explicita.
- Evitar reestruturacoes grandes de layout sem necessidade.

## Modulos em Construcao

Telas Streamlit marcadas como "Em construcao":

- Financeiro;
- Orcamentos;
- Pedidos;
- Estoque;
- Vendas;
- Compras;
- Notas Fiscais;
- Relatorios;
- Simulador.
