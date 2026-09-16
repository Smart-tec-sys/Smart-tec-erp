BEGIN;

DROP INDEX IF EXISTS ix_empresa_usuarios_usuario_ativo;
DROP INDEX IF EXISTS ix_empresa_usuarios_usuario_id;
DROP INDEX IF EXISTS ix_empresa_usuarios_empresa_id;

DROP TABLE IF EXISTS empresa_usuarios;

DROP INDEX IF EXISTS ux_usuarios_provedor_subject;
DROP INDEX IF EXISTS ux_usuarios_email_normalizado;

DROP TABLE IF EXISTS usuarios;

COMMIT;