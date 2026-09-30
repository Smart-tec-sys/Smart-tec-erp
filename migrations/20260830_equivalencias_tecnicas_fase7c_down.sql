BEGIN;

DROP TRIGGER IF EXISTS trg_validar_tenant_equivalencia_tecnica
    ON empresa_equivalencias_tecnicas;
DROP TABLE IF EXISTS empresa_equivalencias_tecnicas;
DROP FUNCTION IF EXISTS validar_tenant_equivalencia_tecnica();

COMMIT;
