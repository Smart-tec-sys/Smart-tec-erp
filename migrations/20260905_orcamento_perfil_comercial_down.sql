BEGIN;

ALTER TABLE orcamentos DROP CONSTRAINT IF EXISTS ck_orcamentos_perfil_comercial;
ALTER TABLE orcamentos DROP COLUMN IF EXISTS perfil_comercial;

COMMIT;
