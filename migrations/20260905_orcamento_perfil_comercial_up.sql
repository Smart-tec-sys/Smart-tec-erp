BEGIN;

ALTER TABLE orcamentos
    ADD COLUMN perfil_comercial VARCHAR(30) NOT NULL DEFAULT 'VAREJO';

ALTER TABLE orcamentos
    ADD CONSTRAINT ck_orcamentos_perfil_comercial
    CHECK (perfil_comercial IN ('DECORADOR', 'VAREJO', 'CONSUMIDOR_FINAL'));

COMMIT;
