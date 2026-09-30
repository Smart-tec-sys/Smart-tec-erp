# Fase 7C — Equivalência técnica comercial

## Checkpoint e backup

- banco: `smarttec_erp_dev`
- empresa: `1 — Smart-tec Persianas — ATIVA`
- produtos: 3441
- fornecedores: 3
- empresa_portfolio: 3
- usuários: 1
- vínculos usuário-empresa: 1

Backup: `C:\Users\valmi\Smart-tec-backups\smarttec_erp_dev_pre_fase7c_20260830_143636.backup`

- tamanho: 751628 bytes
- SHA-256: `12922956E93E51D4DA9A5051097E56E9B6F85774BD3ECCF8833CD5728B56EC60`
- `pg_restore -l`: 325 entradas, válido

## Persistência

`empresa_equivalencias_tecnicas` liga um código global de função técnica a um
produto comercial do tenant e, opcionalmente, a um fornecedor do mesmo tenant.
Mantém prioridade, preferência, estado e configurações comerciais locais.

A migration cria FKs simples, índices de consulta, combinação única e índice
parcial que permite apenas um preferencial ativo por empresa/função. Um trigger
PostgreSQL sem `SECURITY DEFINER` impede produto ou fornecedor cross-tenant.
A tabela foi criada vazia; nenhum vínculo foi inferido ou inserido.

O acesso ocorre pelo backend tenant-aware. A tabela não foi publicada nem
concedida diretamente ao Supabase Data API; portanto nenhuma política ou grant
remoto foi criado nesta fase.

## Limites

O resolvedor retorna candidatos comerciais ordenados, mas não calcula receita,
quantidade, custo técnico ou estoque. Nenhum motor importa esse serviço.
