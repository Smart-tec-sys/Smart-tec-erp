# Fase 5 — expansão tenant-aware

Os módulos persistidos restantes foram bloqueados porque suas tabelas ainda não
possuem `empresa_id`. Nenhum CRUD inseguro foi apresentado como tenant-aware.

A fase criou namespace central para sessão e cache comerciais, contratos não
persistidos de autenticação, preview de onboarding zerado, portfólio em memória
isolado por empresa e contrato futuro de equivalência comercial. Esses
componentes não alteram o núcleo técnico nem dados do DEV.

Módulos sem persistência real continuam legados até receberem domínio e schema
claros. `LEGACY_UNSCOPED` permanece bloqueado em qualquer helper novo que
prometa isolamento.

Próxima etapa técnica: migration controlada dos módulos listados no relatório,
autenticação real e onboarding persistente, cada um com backup, preview e testes
de acesso cruzado.
