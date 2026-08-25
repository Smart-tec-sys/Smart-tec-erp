# Smart-tec ERP - Memoria Permanente

Este arquivo registra a arquitetura atual, convencoes, regras de desenvolvimento,
problemas conhecidos e prioridades tecnicas do projeto Smart-tec ERP.

Use este documento como referencia antes de qualquer alteracao futura no projeto.
Nao invente informacoes: atualize este arquivo apenas com base em codigo existente,
decisoes confirmadas pelo usuario ou alteracoes realmente implementadas.

## Arquitetura Atual do Projeto

O Smart-tec ERP e um projeto Python com duas entradas principais:

- Backend FastAPI em `main.py`.
- Frontend Streamlit em `app.py`.

O backend foi planejado para usar FastAPI, Uvicorn e PostgreSQL.
O frontend usa Streamlit e importa telas da pasta `modulos`.

O banco configurado no codigo principal e PostgreSQL, acessado por `psycopg2`
em `backend/database.py`.

Existe tambem um arquivo `banco.db` SQLite na raiz, mas o codigo principal
identificado usa PostgreSQL.

## Convencoes de Desenvolvimento

O projeto usa Python procedural com funcoes por modulo.

Padroes observados:

- Modulos Streamlit expoem uma funcao principal de tela.
- Exemplos: `telaDashboard`, `telaClientes`, `telaProdutos`.
- Funcoes auxiliares usam nomes em portugues.
- O codigo usa SQL direto com cursores PostgreSQL.
- Nao ha ORM identificado.
- O backend FastAPI usa `pydantic.BaseModel` para schemas de entrada.
- Mensagens de interface usam `st.error`, `st.success`, `st.warning`,
  `st.info` e `st.caption`.
- A interface usa Streamlit nativo, sidebar, forms, expanders, columns,
  containers e metrics.

Ao desenvolver, preserve o estilo atual do projeto:

- manter nomes em portugues quando estiver alterando codigo existente;
- evitar reestruturacoes amplas sem necessidade;
- evitar misturar padroes novos sem decisao explicita;
- respeitar os fluxos ja existentes de conexao com banco;
- alterar somente os arquivos necessarios para a tarefa.

## Regras Obrigatorias Antes de Alterar Arquivos

Antes de qualquer alteracao:

1. Ler os arquivos relacionados a tarefa.
2. Verificar impactos em FastAPI, Streamlit, banco, importadores e dados.
3. Explicar claramente o plano de alteracao ao usuario.
4. Aguardar confirmacao explicita antes de editar qualquer arquivo.
5. Evitar alteracoes parciais que deixem uma funcionalidade quebrada.
6. Preservar compatibilidade com o restante do projeto.
7. Sempre que possivel, testar a alteracao antes de finalizar.

Ao concluir qualquer tarefa, informar:

- arquivos alterados;
- motivo de cada alteracao;
- possiveis impactos;
- como validar.

## Principais Problemas Conhecidos

- `main.py` importa routers de `routes`, mas `routes` esta vazio.
- Routers implementados foram identificados em `models`.
- Ha duplicacao de routers em `frontend/pages`.
- Alguns imports usam `from database import conectar`, mas o modulo real
  identificado e `backend.database`.
- Alguns arquivos possuem trechos HTML literais inseridos no meio do Python.
- `modulos/producao.py` importa `formatar_moeda` de `modulos.produtos`, mas
  essa funcao nao foi identificada em `modulos/produtos.py`.
- Scripts de importacao usam `get_cursor`, mas `backend/database.py` nao define
  essa funcao.
- Existem divergencias de campos entre API, Streamlit e banco.
- Ha arquivos vazios ou incompletos.
- Ha textos com possiveis problemas de encoding/mojibake.

## Prioridades Tecnicas

1. Corrigir erros que impedem importacao ou execucao.
2. Corrigir imports quebrados.
3. Decidir estrutura oficial dos routers: `routes` ou `models`.
4. Eliminar duplicacao entre `models` e `frontend/pages`.
5. Definir se Streamlit acessa o banco diretamente ou consome a API FastAPI.
6. Alinhar campos de clientes e produtos entre API, Streamlit e banco.
7. Implementar ou remover `get_cursor`.
8. Revisar scripts de importacao Excel.
9. Criar ou preencher schema SQL oficial.
10. Implementar gradualmente telas marcadas como "Em construcao".

## Orientacao Para Preservar Compatibilidade

Qualquer alteracao deve ser feita com cuidado para nao quebrar o fluxo atual.

Antes de alterar uma funcionalidade:

- identificar todos os arquivos que participam dela;
- verificar se ha copia duplicada da mesma logica;
- verificar se a alteracao afeta banco, frontend, backend ou importadores;
- preferir mudancas pequenas e completas;
- nao corrigir apenas uma parte se outra copia continuar inconsistente;
- validar imports e execucao quando houver Python disponivel;
- documentar impactos conhecidos ao finalizar.

Se houver conflito entre corrigir rapido e preservar compatibilidade, priorizar
preservar compatibilidade e pedir confirmacao do usuario.
