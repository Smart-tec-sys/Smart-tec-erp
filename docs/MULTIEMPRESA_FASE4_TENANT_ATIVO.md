# Multiempresa Fase 4 — tenant ativo

Produtos, fornecedores, clientes e orçamentos agora exigem `TenantContext` em
suas rotas e serviços. Listagens e buscas por ID filtram `empresa_id`; criação
deriva a empresa do contexto; alteração e exclusão validam ownership. Itens de
orçamento continuam herdando o escopo do cabeçalho.

No ambiente `development`, `dev` ou `local`, o resolvedor central usa
temporariamente a Smart-tec Persianas (`empresa_id=1`, slug
`smart-tec-persianas`). Fora desses ambientes não existe fallback silencioso.
O header de tenant só é aceito quando `SMARTTEC_ALLOW_TEST_TENANT_HEADER=1`.

O Streamlit inicializa `tenant_empresa_id` e `tenant_slug` uma vez na sessão. O
cliente HTTP usa a mesma identidade DEV fora dos payloads comerciais. Carrinhos
de receita, descoberta de componentes e cadastros usados por Orçamentos incluem
tenant nas chaves de cache alteradas nesta fase.

`LEGACY_UNSCOPED` permanece disponível apenas para módulos ainda não migrados e
é rejeitado pelos quatro serviços tenant-aware. O núcleo `app/technical` e seus
caches técnicos continuam globais.

Riscos pendentes: autenticação real, autorização de usuário por empresa, demais
módulos comerciais, caches legados não alcançados nesta fase, portfólio por
tenant e onboarding zerado.
