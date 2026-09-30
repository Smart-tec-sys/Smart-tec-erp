# Fase 7D — validação piloto de equivalências comerciais

Data da validação: 31/08/2026. Banco autorizado: `smarttec_erp_dev`.
Empresa: `1 — Smart-tec Persianas`.

## Backup anterior à escrita

- Arquivo: `C:\Users\valmi\Smart-tec-backups\smarttec_erp_dev_pre_fase7d_20260830_145518.backup`
- Tamanho: 759.596 bytes
- SHA-256: `17B6BB0F953BD2B871F3DE6CBAD445D3BA827C408F649B2910443DE854CB5FDF`
- Arquivo custom do PostgreSQL validado por `pg_restore -l`.

## Equivalências mantidas

| Função técnica | Produto comercial | Fornecedor | Prioridade | Preferencial | Ativo |
|---|---|---|---:|---|---|
| `ESPAGUETE_ROMANA_2_5MM` | 660 — Espaguete flexível transparente — 2,5 mm | Não especificado | 10 | Sim | Sim |
| `ESPAGUETE_BASE_ROMANA_3MM` | 661 — Espaguete flexível transparente — 3,0 mm | Não especificado | 10 | Sim | Sim |

As associações têm alta confiança porque nome, material, transparência, bitola,
unidade por metro e status comercial correspondem ao contrato técnico. Os dois
produtos pertencem à empresa 1. Nenhum fornecedor foi inferido porque o cadastro
dos produtos não contém vínculo comprovável.

Custos, estoque, produtos e fornecedores não foram alterados. Tabelas externas
de fornecedores são apenas referências para comparação de nomenclaturas e não
foram importadas nem usadas como prova automática de equivalência.

## Validação operacional

O ciclo controlado da equivalência 1 validou alteração e restauração de
preferencial, prioridade e status. Quando inativa, ela deixou de integrar o
resultado ativo do resolvedor. O estado final foi restaurado para prioridade 10,
preferencial e ativo.

Consultas com o tenant fictício `999999` não listaram nem acessaram os registros
da empresa 1. Testes isolados cobrem produto e fornecedor de outro tenant e a
rejeição de `LEGACY_UNSCOPED`.

Na interface autenticada, acesse **Produtos → Equivalências técnicas**. A tabela
deve mostrar somente as duas linhas acima, com “Sem fornecedor específico”,
prioridade 10, preferencial e ativo. A seleção de função técnica permite conferir
cada código individualmente.

## Reversão

Caso a reversão seja autorizada, remover exclusivamente as duas associações da
empresa 1, identificadas pelas combinações função/produto acima. Não remover nem
alterar os produtos 660 e 661. Para restauração integral do DEV, utilizar o backup
registrado neste documento.

## Limites preservados

O resolvedor não foi conectado aos motores. `app/technical`, receitas, regras de
Romana/Rolô, Supabase remoto e banco original não foram alterados. Nenhuma empresa,
usuário, produto ou fornecedor foi criado.
