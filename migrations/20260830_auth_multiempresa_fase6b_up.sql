BEGIN;

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    provedor VARCHAR(50),
    provedor_subject VARCHAR(255),
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_usuarios_status
        CHECK (status IN ('ATIVO', 'INATIVO'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_email_normalizado
    ON usuarios (LOWER(email));

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_provedor_subject
    ON usuarios (provedor, provedor_subject)
    WHERE provedor IS NOT NULL
      AND provedor_subject IS NOT NULL;

CREATE TABLE IF NOT EXISTS empresa_usuarios (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    papel VARCHAR(20) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_empresa_usuarios_empresa
        FOREIGN KEY (empresa_id)
        REFERENCES empresas(id),

    CONSTRAINT fk_empresa_usuarios_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id),

    CONSTRAINT uq_empresa_usuarios_empresa_usuario
        UNIQUE (empresa_id, usuario_id),

    CONSTRAINT ck_empresa_usuarios_papel
        CHECK (papel IN ('OWNER','ADMIN','USUARIO'))
);

CREATE INDEX IF NOT EXISTS ix_empresa_usuarios_empresa_id
    ON empresa_usuarios(empresa_id);

CREATE INDEX IF NOT EXISTS ix_empresa_usuarios_usuario_id
    ON empresa_usuarios(usuario_id);

CREATE INDEX IF NOT EXISTS ix_empresa_usuarios_usuario_ativo
    ON empresa_usuarios(usuario_id, ativo);

COMMIT;