# Plano de autenticação multiempresa

Não existe autenticação implementada hoje. A Fase 5 adiciona somente contratos
de domínio, sem usuário, senha, tabela ou provedor externo.

Fluxo futuro: login validado → `UserContext` ativo → vínculo autorizado com uma
empresa ativa → `AuthenticatedTenantContext` → `TenantContext` usado pelos
serviços. Logout elimina a sessão; sessão expirada, usuário inativo ou empresa
inativa não produz contexto autenticado.

Proposta futura de persistência, sujeita a revisão: `usuarios`,
`empresa_usuarios` e papéis/perfis. Um administrador Smart-tec Sistemas pode
existir, mas acesso multiempresa deve ser explícito e auditado; nunca um bypass
silencioso de filtro. Senhas e provedor de identidade só serão definidos com a
arquitetura de autenticação real.
