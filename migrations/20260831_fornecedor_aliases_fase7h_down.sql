BEGIN;

DROP TRIGGER IF EXISTS trg_validar_tenant_fornecedor_alias ON fornecedor_aliases;
DROP FUNCTION IF EXISTS validar_tenant_fornecedor_alias();
DROP TABLE IF EXISTS fornecedor_aliases;

COMMIT;
