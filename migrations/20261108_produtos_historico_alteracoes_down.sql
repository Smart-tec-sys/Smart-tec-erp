-- Rollback proposto; nao descarta historico ja registrado.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM produtos_historico_alteracoes) THEN
        RAISE EXCEPTION
            'Rollback recusado: o historico de alteracoes de produtos deve ser preservado';
    END IF;
END;
$$;

DROP TABLE produtos_historico_alteracoes;

ALTER TABLE produtos
    DROP CONSTRAINT uq_produtos_id_empresa;

COMMIT;
