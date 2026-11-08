-- Rollback proposto; preserva fichas, componentes, revisoes e conferencias em uso.
BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM producao_componentes)
       OR EXISTS (SELECT 1 FROM producao_revisoes_ficha)
       OR EXISTS (
           SELECT 1 FROM producao_pecas
           WHERE quantidade <> 1
              OR modo_fabricacao <> 'AUTOMATICA'
              OR especificacoes_fabricacao <> '{}'::jsonb
              OR versao_ficha <> 1
              OR conferido_por IS NOT NULL
              OR conferido_em IS NOT NULL
       ) THEN
        RAISE EXCEPTION 'Rollback recusado: existem fichas editadas, componentes ou conferencias que devem ser preservadas';
    END IF;
END;
$$;

DROP TRIGGER validar_revisao_producao_empresa ON producao_revisoes_ficha;
DROP FUNCTION validar_vinculo_revisao_producao_v1();
DROP TRIGGER validar_componente_producao_empresa ON producao_componentes;
DROP FUNCTION validar_vinculo_componente_producao_v1();
DROP TABLE producao_revisoes_ficha;
DROP TABLE producao_componentes;

ALTER TABLE producao_pecas
    DROP CONSTRAINT ck_producao_quantidade,
    DROP CONSTRAINT ck_producao_modo_fabricacao,
    DROP CONSTRAINT ck_producao_versao_ficha,
    DROP COLUMN conferido_em,
    DROP COLUMN conferido_por,
    DROP COLUMN versao_ficha,
    DROP COLUMN especificacoes_fabricacao,
    DROP COLUMN modo_fabricacao,
    DROP COLUMN quantidade;

COMMIT;
