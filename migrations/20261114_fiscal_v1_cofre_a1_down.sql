-- ROLLBACK DESTRUTIVO: apaga ciphertext e pode inutilizar certificados.
-- Somente CI descartável ou aprovação formal com backup. NÃO usar em produção.
BEGIN;
DROP TABLE IF EXISTS fiscal_certificados_cofre;
COMMIT;
