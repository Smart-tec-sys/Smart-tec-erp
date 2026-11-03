-- PREPARADA SOMENTE. Recusa rollback se houver qualquer OP.
BEGIN;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM ordens_producao) OR EXISTS (SELECT 1 FROM producao_pecas) THEN
        RAISE EXCEPTION 'Rollback recusado: preserve as ordens e pecas existentes';
    END IF;
END;
$$;
DROP TABLE producao_pecas;
DROP TABLE ordens_producao;
DROP FUNCTION validar_vinculo_producao_v1();
COMMIT;
