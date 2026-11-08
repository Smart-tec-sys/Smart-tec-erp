# Fase 7B — Login Streamlit e tenant autenticado

## Fluxos

Em `SMARTTEC_AUTH_MODE=dev`, o ERP continua sem exigir login e usa o resolvedor
DEV explícito da Empresa 1 somente quando `SMARTTEC_ENV` é `dev`,
`development` ou `local`. Sem esse marcador local, o backend falha fechado.
Para testar operações auditadas, `SMARTTEC_DEV_USER_ID` pode identificar no
servidor um usuário ativo que tenha vínculo ativo com a Empresa 1. O cliente
nunca escolhe o usuário; `X-User-ID` é ignorado.

Em `SMARTTEC_AUTH_MODE=authenticated`:

1. o Streamlit autentica e-mail e senha diretamente no Supabase Auth usando
   `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY`;
2. somente tokens retornados ficam em `st.session_state`; a senha não é retida;
3. `GET /auth/me` valida o Bearer por JWKS e retorna apenas vínculos ativos;
4. uma empresa é escolhida automaticamente ou pelo seletor entre vínculos reais;
5. chamadas comerciais enviam Bearer e a empresa solicitada;
6. o backend cruza JWT, usuário, vínculo e empresa ativa antes de criar o
   `TenantContext`.

`X-Empresa-ID` é somente uma solicitação de contexto no modo autenticado. Sem
Bearer válido e vínculo persistido, o backend responde 401/403. O header de
teste não contorna o modo authenticated.

## Ativação futura

Configurar no ambiente, sem gravar segredos no repositório:

- `SMARTTEC_AUTH_MODE=authenticated`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_AUTH_ISSUER`
- `SUPABASE_JWKS_URL`

`SMARTTEC_AUTH_MODE=authenticated` deve ser configurado explicitamente fora do
desenvolvimento local. O padrão de modo continua `dev`, mas o resolvedor DEV é
recusado sem `SMARTTEC_ENV` local; esta fase não altera `.env` nem ativa login
global.

## Sessão, logout e troca de empresa

Tokens, usuário, validade, empresas autorizadas e empresa ativa usam chaves
centralizadas. Logout remove tokens, tenant e caches comerciais. Trocar de
empresa limpa os namespaces comerciais anteriores, preservando o núcleo
técnico global.

## Correção de navegação autenticada

Links HTML com `href="?go_to=..."` no menu principal recarregavam o documento
e criavam um novo WebSocket Streamlit, descartando o `session_state` anterior.
O menu passou a usar callbacks Streamlit que alteram `st.query_params` dentro
da sessão corrente. Painel, Produtos, Clientes, Fornecedores, Orçamentos e os
demais destinos do menu preservam tokens e empresa ativa durante reruns.

## Redirect de confirmação

O redirect atual do Supabase para `localhost:3000` pertence à configuração
remota do projeto. Como cadastro aberto não faz parte desta fase, ele não foi
alterado. Em uma implantação futura, a URL deve apontar para a origem pública
do frontend autorizada no Supabase.

## Limites

Não há endpoint de login com e-mail livre no backend, senha local, uso de
`service_role`, `JWT_SECRET`, token fixo, migration ou escrita no banco.
