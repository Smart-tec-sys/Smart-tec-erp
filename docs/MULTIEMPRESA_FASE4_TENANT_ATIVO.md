# Multiempresa Fase 4 — tenant ativo

Produtos, fornecedores, clientes e orçamentos agora exigem `TenantContext` em
suas rotas e serviços. Listagens e buscas por ID filtram `empresa_id`; criação
deriva a empresa do contexto; alteração e exclusão validam ownership. Itens de
orçamento continuam herdando o escopo do cabeçalho.

No ambiente `development`, `dev` ou `local`, o resolvedor central usa
temporariamente a Smart-tec Persianas (`empresa_id=1`, slug
`smart-tec-persianas`). O modo DEV só funciona quando `SMARTTEC_ENV` declara
explicitamente um desses ambientes locais. Fora deles, o backend falha fechado.
`X-Empresa-ID` e `X-User-ID` não definem identidade no modo DEV; quando
`SMARTTEC_DEV_USER_ID` está configurado no servidor, o usuário e seu vínculo
ativo com a empresa 1 são verificados no banco.

O Streamlit inicializa `tenant_empresa_id` e `tenant_slug` uma vez na sessão. O
cliente HTTP usa a mesma identidade DEV fora dos payloads comerciais. Carrinhos
de receita, descoberta de componentes e cadastros usados por Orçamentos incluem
tenant nas chaves de cache alteradas nesta fase.

`LEGACY_UNSCOPED` permanece disponível apenas para módulos ainda não migrados e
é rejeitado pelos quatro serviços tenant-aware. O núcleo `app/technical` e seus
caches técnicos continuam globais.

O modo autenticado continua obrigatório fora do desenvolvimento local. O
resolvedor DEV sem `SMARTTEC_DEV_USER_ID` não atribui usuário e, portanto, não
permite operações que exigem auditoria de responsável.
