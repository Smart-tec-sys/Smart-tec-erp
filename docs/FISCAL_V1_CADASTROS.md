# Fiscal V1 — Cadastros em revisão

Configuração fiscal por empresa em `empresas.configuracoes.fiscal_nfe` e tabela separada `fiscal_produtos` por empresa/produto (FK composta). O cadastro de preços, custos, SKU e orçamentos não é alterado.

**Rotas previstas após migração e deploy de homologação**:
- GET/PATCH `/fiscal/cadastros/empresa`
- GET/PATCH `/fiscal/cadastros/produtos/{produto_id}`
- GET `/pedidos/{pedido_id}/fiscal/preparacao-nfe`

Leituras requerem tenant autenticado. Gravações exigem vínculo ativo OWNER/ADMIN. Não há transmissão nem certificado; os códigos informados são apenas campos declaratórios (validam formato, não conformidade legal), sem cálculo de impostos. Os códigos devem ser conferidos pelo contador e com tabelas vigentes. A pré-validação da nota ainda retorna `NAO_APTO_EMISSAO`.

**Migração:** `migrations/20261114_fiscal_v1_cadastros_up.sql` é opt-in, depende de `uq_produtos_id_empresa`. O SQL não foi aplicado em nenhum Render. Testar em uma instância isolada antes da ativação; rollback do DOWN remove cadastros fiscais da versão 1 e só pode ser executado com backup/autorização.

**Limitações conhecidas:** Sem captura de IE do destinatário, sem cadastro completo de impostos por item, sem cálculos de ICMS/PIS/COFINS/IPI/IBS/CBS, sem regras por UF/CFOP, sem assinatura, XML ou SEFAZ. Série de homologação cadastrada aqui não reserva número de nota. Nenhum vínculo com a NFS-e da plataforma Smart-tec.

## Staging Render: execução protegida (ainda não realizada)

O staging smarttec_erp_staging foi consultado em modo leitura: 1 empresa, 0 produtos, 0 pedidos, sem fiscal_produtos e sem a chave única composta em produtos. O serviço de staging utiliza a branch staging, compartilhada por outros módulos; não trocar indiscriminadamente para a branch Fiscal, que contém alterações acumuladas de outros módulos.

O runner scripts/fiscal/staging_migrate.py executa pré-verificação somente leitura por padrão. A aplicação é separada, exige confirmação, nome exato do banco, contagens verificadas, lock de transação e pre/postchecks. Todos os arquivos SQL são aplicados em uma única transação; ausência de pré-requisitos causa rollback.

Executar somente por sessão administrativa autenticada do backend staging, em checkout da branch fiscal aprovada, com DATABASE_URL já apontando ao banco correto e nunca compartilhado no chat:

```bash
python scripts/fiscal/staging_migrate.py
# Somente depois do preflight e autorização:
python scripts/fiscal/staging_migrate.py --apply --confirm STAGING_FISCAL_V1
```

O conector Render usado nesta revisão permite apenas consultas SQL read-only, não pode efetuar a migração. Não executar em produção, assinantes, banco da Smart-tec Persianas ou na prévia visual pública. Após aplicação no staging, verificar tabela e constraints sem inserir dados comerciais, e só então implantar uma API isolada com autenticação/testes de sessão. A prévia visual QA não usa API nem banco.
