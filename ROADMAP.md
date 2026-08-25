# Smart-tec ERP - Roadmap Tecnico

Este roadmap organiza as prioridades tecnicas conhecidas do projeto.

## Prioridade 1 - Estabilizar Execucao

- Corrigir erros que impedem importacao ou execucao.
- Corrigir trechos HTML acidentais dentro de arquivos Python.
- Corrigir imports quebrados.
- Corrigir `modulos/producao.py` ou criar `formatar_moeda`.
- Implementar `get_cursor` ou adaptar scripts de importacao.

## Prioridade 2 - Alinhar Backend

- Corrigir `main.py` ou estruturar `routes` corretamente.
- Decidir estrutura oficial dos routers: `routes` ou `models`.
- Corrigir imports `from database import conectar`.
- Eliminar duplicacao entre `models` e `frontend/pages`.

## Prioridade 3 - Alinhar Dados

- Resolver divergencia de schemas entre API e Streamlit.
- Alinhar campos de clientes entre API, Streamlit e banco.
- Alinhar campos de produtos entre API, Streamlit e banco.
- Definir papel do arquivo `banco.db`.
- Criar ou preencher schema SQL oficial.

## Prioridade 4 - Revisar Importadores

- Revisar scripts de importacao Excel.
- Corrigir uso de `psycopg` quando o padrao principal usa `psycopg2`, se essa
  decisao for confirmada.
- Remover credenciais hardcoded.
- Validar dados Excel e decidir onde devem ficar.

## Prioridade 5 - Evoluir Frontend

- [Concluido] Repaginacao do modulo Produtos com formulario reorganizado em abas:
  Geral, Tecnico, Composicao / Receita, Valores, Estoque, Fiscal e Descricao.
- Definir se Streamlit acessa o banco diretamente ou consome a API FastAPI.
- Implementar gradualmente telas marcadas como "Em construcao".
- Preservar padroes atuais de interface durante a evolucao.

## Concluido - Compatibilidade Produtos

- [Concluido] Correcao de compatibilidade do campo `varia_cor`:
  frontend envia boolean, schema Pydantic aceita boolean, model SQLAlchemy usa
  Boolean e PostgreSQL possui coluna BOOLEAN.
- [Concluido] Eliminados os erros 422 de validacao e 500 na atualizacao do
  produto.
- [Concluido] Fluxo de edicao de produto voltou a funcionar normalmente.
- [Concluido] Modularizacao interna do formulario de Produtos com as funcoes
  `renderizar_aba_geral`, `renderizar_aba_tecnico`,
  `renderizar_aba_composicao`, `renderizar_aba_valores`,
  `renderizar_aba_estoque`, `renderizar_aba_fiscal` e
  `renderizar_aba_descricao`.
- [Concluido] Consolidacao das funcoes de abas com docstrings curtas.
- [Concluido] Padronizacao visual do botao `Calcular valor de venda` para o
  azul principal.

## Prioridade 6 - Documentacao e Qualidade

- Atualizar `README.md`.
- Preencher arquivos SQL.
- Corrigir problemas de encoding/mojibake em textos com acentos e emojis.
- Documentar decisoes tecnicas confirmadas pelo usuario.
