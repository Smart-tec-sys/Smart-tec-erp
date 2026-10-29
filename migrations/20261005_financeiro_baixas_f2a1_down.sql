-- Reverte a F2A.1. Nao toca em colunas/linhas de financeiro alem da constraint unica adicionada.
BEGIN;

DROP TABLE IF EXISTS financeiro_baixas;
ALTER TABLE financeiro DROP CONSTRAINT IF EXISTS uq_financeiro_id_empresa;

COMMIT;