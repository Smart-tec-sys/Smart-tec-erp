# Base multiempresa — Fase 2

## Resultado arquitetural

A Fase 2 prepara uma fronteira de tenant sem ativá-la no ERP legado:

- global: `app/technical/`, motores e regras universais;
- por empresa: catálogo, fornecedores, clientes, orçamentos, custos, preços,
  estoque, importações, equivalências, configurações e portfólio.

Nenhum dado foi migrado e nenhuma empresa real foi criada.

## Ativação em duas etapas

### Etapa preparada nesta fase

1. Modelos novos `EmpresaDB` e `EmpresaPortfolioDB`.
2. Schemas de entrada e saída.
3. `TenantContext` puro e helpers de isolamento.
4. Dependência FastAPI e adaptador de sessão ainda desconectados.
5. Migration SQL de subida e reversão, apenas em arquivo.
6. Plano de colunas nullable para os modelos legados.

### Etapa futura, não executada

1. Revisar backup, schema e preview no DEV.
2. Executar a migration no DEV.
3. Confirmar tabelas, colunas, índices e FKs.
4. Somente então adicionar `empresa_id` aos modelos ORM ativos.
5. Criar a primeira empresa e associar dados com preview e auditoria próprios.

Adicionar as colunas aos modelos ativos antes da migration faria o SQLAlchemy
consultar campos inexistentes. Por isso `produto.py`, `fornecedor.py`,
`cliente.py` e `orcamento.py` permanecem intactos nesta fase.

## Empresa

`EmpresaDB` contém id, nome, nome fantasia, documento, status, slug,
configurações e timestamps. O status aceita `ATIVA` e `INATIVA`; o slug é único.
Não foram adicionadas regras fiscais além desses campos básicos.

## Portfólio

`EmpresaPortfolioDB` contém empresa, modelo técnico, estado, configurações locais
e timestamps. A combinação empresa/modelo é única. A tabela nasce vazia e não
ativa família automaticamente.

## Migration preparada

O arquivo de subida faria, nesta ordem:

1. criar `empresas`;
2. criar `empresa_portfolio`;
3. adicionar `empresa_id INTEGER NULL` em produtos, fornecedores, clientes e
   orçamentos;
4. criar índices simples de empresa;
5. criar FKs nullable para `empresas`.

O arquivo de reversão remove FKs, índices, colunas e tabelas em ordem segura.
Não há carga, alteração ou remoção de registros de negócio. A migration não foi
executada.

`orcamentos_itens` não recebe `empresa_id`: o escopo é herdado do orçamento,
evitando duplicação e divergência. Consultas diretas precisarão juntar o
cabeçalho. O snapshot comercial atual do item foi preservado.

## Auth e FastAPI

Não foi encontrado sistema de autenticação/usuários implementado. O contrato
futuro é usuário autenticado → empresa autorizada → `TenantContext`. A
dependência preparada aceita header apenas para desenvolvimento e testes; ela
não foi ligada às rotas e não representa autenticação definitiva. Não foi
inventado RBAC.

## Streamlit e estado

`get_tenant_from_session` recebe um objeto de mapeamento e não importa Streamlit.
Isso evita acoplar o núcleo do tenant ao frontend. A empresa não é armazenada em
variável global de módulo.

Estados comerciais que precisarão de chave por empresa incluem:

- listas, seleção e filtros de produtos, fornecedores e clientes;
- carrinhos de receita técnica;
- `smarttec_ultima_receita_tecnica`;
- caches de componentes montados em `modulos/produtos.py`;
- IDs selecionados para editar ou excluir;
- filtros, resultados e seleção de orçamentos;
- preços, valores de venda e estados de estoque;
- dados temporários de importação e classificação.

Não foram encontrados decoradores de cache nos trechos auditados; o risco atual
está principalmente em `st.session_state`. A refatoração ampla foi adiada.
Caches novos devem usar `tenant_cache_key`, que inclui empresa e rejeita o modo
sem escopo.

## Novo tenant zerado

O contrato `new_tenant_empty_snapshot` garante zero produtos, fornecedores,
clientes, custos, estoque e portfólio. Ele expõe somente os códigos do catálogo
técnico global. Assim, nenhuma empresa herda itens comerciais da Smart-tec ou de
qualquer outra empresa.

## Restrições adiadas

Unicidades de produto, fornecedor e número de orçamento por empresa dependem da
auditoria dos registros atuais. A FK entre produto e fornecedor padrão também
depende de saneamento: o modelo e o banco atual não estão alinhados e os vínculos
existentes precisam ser validados antes de criar constraint.

## Compatibilidade

Nenhuma rota ou serviço atual exige tenant. `LEGACY_UNSCOPED` existe apenas para
expressar esse período transitório e está bloqueado nos helpers que prometem
isolamento. Motores de Romana, Romana de teto, Rolô e Double Vision não foram
alterados.
