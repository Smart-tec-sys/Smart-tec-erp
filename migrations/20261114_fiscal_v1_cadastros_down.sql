-- Rollback DESTRUTIVO: remove apenas classificações fiscais da tabela V1.
-- Execute somente com aprovação explícita e backup.
BEGIN;
DROP TABLE IF EXISTS fiscal_produtos;
COMMIT;
