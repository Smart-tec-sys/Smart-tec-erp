-- Rollback local. Recusa apagar autorizacoes ou ambientes ja registrados.
BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pedidos
        WHERE producao_aprovado_em IS NOT NULL
           OR producao_liberado_em IS NOT NULL
           OR producao_historico <> '[]'::jsonb
    ) THEN
        RAISE EXCEPTION 'Rollback recusado: preserve historico de autorizacao de fabricacao';
    END IF;
    IF EXISTS (SELECT 1 FROM orcamentos_itens WHERE ambiente IS NOT NULL)
       OR EXISTS (SELECT 1 FROM pedidos_itens WHERE ambiente IS NOT NULL) THEN
        RAISE EXCEPTION 'Rollback recusado: preserve ambientes informados nos itens';
    END IF;
END;
$$;

ALTER TABLE pedidos
    DROP COLUMN producao_historico,
    DROP COLUMN producao_liberado_em,
    DROP COLUMN producao_liberado_por,
    DROP COLUMN producao_aprovado_em,
    DROP COLUMN producao_aprovado_por;
ALTER TABLE pedidos_itens DROP COLUMN ambiente;
ALTER TABLE orcamentos_itens DROP COLUMN ambiente;

COMMIT;
