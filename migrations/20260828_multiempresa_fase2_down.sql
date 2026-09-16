-- Reversão da estrutura preparada na Fase 2. PREPARADA, NÃO EXECUTADA.

BEGIN;

ALTER TABLE orcamentos DROP CONSTRAINT IF EXISTS fk_orcamentos_empresa_id;
ALTER TABLE clientes DROP CONSTRAINT IF EXISTS fk_clientes_empresa_id;
ALTER TABLE fornecedores DROP CONSTRAINT IF EXISTS fk_fornecedores_empresa_id;
ALTER TABLE produtos DROP CONSTRAINT IF EXISTS fk_produtos_empresa_id;

DROP INDEX IF EXISTS ix_orcamentos_empresa_id;
DROP INDEX IF EXISTS ix_clientes_empresa_id;
DROP INDEX IF EXISTS ix_fornecedores_empresa_id;
DROP INDEX IF EXISTS ix_produtos_empresa_id;
DROP INDEX IF EXISTS ix_empresa_portfolio_empresa_id;

ALTER TABLE orcamentos DROP COLUMN IF EXISTS empresa_id;
ALTER TABLE clientes DROP COLUMN IF EXISTS empresa_id;
ALTER TABLE fornecedores DROP COLUMN IF EXISTS empresa_id;
ALTER TABLE produtos DROP COLUMN IF EXISTS empresa_id;

DROP TABLE IF EXISTS empresa_portfolio;
DROP TABLE IF EXISTS empresas;

COMMIT;
