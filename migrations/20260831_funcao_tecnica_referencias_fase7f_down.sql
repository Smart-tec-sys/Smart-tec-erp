BEGIN;

DROP TRIGGER IF EXISTS trg_validar_tenant_funcao_tecnica_referencia
    ON funcao_tecnica_referencias;
DROP FUNCTION IF EXISTS validar_tenant_funcao_tecnica_referencia();
DROP TABLE IF EXISTS funcao_tecnica_referencias;

COMMIT;
