# Multiempresa — Fase 6A

## Estado do banco recebido

A estrutura foi migrada e validada manualmente antes desta fase no banco
`smarttec_erp_dev`. Nenhuma migration ou escrita de dados é executada pela
Fase 6A.

Backup pré-Fase 6:
`C:\Users\valmi\Smart-tec-backups\smarttec_erp_dev_pre_fase6_20260830_101406.backup`

- tamanho: 738896 bytes
- SHA-256: `68983D716BE82B5186F35DECA8B9DA71D1FC3C8D092AB7F190E7B6F52B75E740`

## Tabelas e contagens confirmadas

| Tabela | Total | empresa_id = 1 | empresa_id NULL |
|---|---:|---:|---:|
| funcionarios | 4 | 4 | 0 |
| transportadoras | 3 | 3 | 0 |
| opcoes_auxiliares | 84 | 84 | 0 |
| compras | 0 | 0 | 0 |
| pedidos | 0 | 0 | 0 |
| financeiro | 0 | 0 | 0 |

Todas essas tabelas já possuem `empresa_id`, FK para `empresas.id` e índice,
conforme validação manual informada pelo usuário.

## Código ativado

Os ORM ativos `FuncionarioDB`, `TransportadoraDB` e `OpcaoAuxiliarDB` foram
alinhados com a coluna nullable existente. Seus serviços agora exigem
`TenantContext`, filtram listas e buscas por empresa, derivam `empresa_id` no
create e validam ownership em update/delete. As rotas usam exclusivamente
`get_current_tenant`, o mesmo resolvedor central da Fase 4.

Os schemas públicos de criação/edição não expõem `empresa_id`. O cliente HTTP
do Streamlit envia o header tenant já centralizado para os três módulos.
Chaves futuras de cache e sessão desses namespaces devem usar
`tenant_cache_key()` e `tenant_session_key()`; os testes comprovam que empresas
distintas não compartilham chaves. Nenhum cache técnico global foi alterado.

## Módulos sem CRUD real

`compras`, `pedidos` e `financeiro` existem no schema, mas não possuem, nesta
árvore, ORM + serviço + rota persistidos ativos equivalentes. A Fase 6A não
inventa CRUD nem relacionamentos. As proteções para pedido/cliente/produto,
compra/fornecedor e financeiro permanecem pendentes para quando houver fluxo
persistido real.

## Isolamento

- Empresa 1 acessa os registros comerciais já vinculados a ela.
- Empresa 999999 recebe listas vazias e não acessa IDs da Empresa 1.
- `LEGACY_UNSCOPED` é recusado pelos serviços ativados.
- `app/technical`, motores produtivos e regras de fabricação permanecem globais
  e inalterados.
