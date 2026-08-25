# Smart-tec ERP - Changelog

Todas as mudancas relevantes do projeto devem ser registradas neste arquivo.

## 2026-06-30

### Concluido

#### Repaginacao do modulo Produtos

- Formulario reorganizado em abas:
  - Geral
  - Tecnico
  - Composicao / Receita
  - Valores
  - Estoque
  - Fiscal
  - Descricao

#### Correcao de compatibilidade do campo `varia_cor`

- Alinhamento entre todas as camadas:
  - Frontend envia boolean.
  - Schema Pydantic aceita boolean.
  - Model SQLAlchemy utiliza Boolean.
  - PostgreSQL possui coluna BOOLEAN.
- Resultado:
  - Eliminado erro 422 de validacao.
  - Eliminado erro 500 na atualizacao do produto.
  - Fluxo de edicao voltou a funcionar normalmente.

#### Modularizacao interna do formulario de Produtos

- Criadas as funcoes:
  - `renderizar_aba_geral`;
  - `renderizar_aba_tecnico`;
  - `renderizar_aba_composicao`;
  - `renderizar_aba_valores`;
  - `renderizar_aba_estoque`;
  - `renderizar_aba_fiscal`;
  - `renderizar_aba_descricao`.
- Consolidacao das funcoes com docstrings curtas.
- Padronizacao visual do botao `Calcular valor de venda` para o azul principal.

### Adicionado

- Criado `AGENTS.md` com memoria permanente do projeto.
- Criado `SMARTTEC_RULES.md` com regras tecnicas e de negocio identificadas.
- Criado `UI_GUIDE.md` com guia de interface Streamlit.
- Criado `ROADMAP.md` com prioridades tecnicas conhecidas.
- Criado `CHANGELOG.md` para registrar evolucoes futuras.

### Observacoes

- Nenhum arquivo Python deve ser alterado na criacao destes documentos.
- Estes documentos foram criados a partir das informacoes ja registradas sobre
  arquitetura, convencoes, problemas conhecidos, regras de negocio e
  prioridades tecnicas do Smart-tec ERP.
