BEGIN;

CREATE TABLE IF NOT EXISTS agenda_eventos (
    id SERIAL PRIMARY KEY,

    empresa_id INTEGER NOT NULL,
    external_uid VARCHAR(80) NOT NULL,

    titulo VARCHAR(180) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(80) NOT NULL DEFAULT 'GERAL',
    status VARCHAR(40) NOT NULL DEFAULT 'AGENDADO',

    inicio TIMESTAMPTZ NOT NULL,
    fim TIMESTAMPTZ,
    dia_inteiro BOOLEAN NOT NULL DEFAULT FALSE,

    cliente_id INTEGER,
    cliente_nome VARCHAR(180),

    responsavel_ref VARCHAR(120),
    responsavel_nome VARCHAR(180),

    local VARCHAR(220),
    endereco TEXT,
    observacoes TEXT,

    origem VARCHAR(60) NOT NULL DEFAULT 'ERP',
    origem_ref VARCHAR(160),
    origem_updated_at TIMESTAMPTZ,

    sincronizacao_status VARCHAR(30) NOT NULL DEFAULT 'LOCAL',

    metadados JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_agenda_eventos_empresa
        FOREIGN KEY (empresa_id)
        REFERENCES empresas(id),

    CONSTRAINT fk_agenda_eventos_cliente
        FOREIGN KEY (cliente_id)
        REFERENCES clientes(id)
        ON DELETE SET NULL,

    CONSTRAINT uq_agenda_eventos_empresa_external_uid
        UNIQUE (empresa_id, external_uid)
);

CREATE INDEX IF NOT EXISTS ix_agenda_eventos_empresa_id
    ON agenda_eventos (empresa_id);

CREATE INDEX IF NOT EXISTS ix_agenda_eventos_cliente_id
    ON agenda_eventos (cliente_id);

CREATE INDEX IF NOT EXISTS ix_agenda_eventos_inicio
    ON agenda_eventos (inicio);

CREATE INDEX IF NOT EXISTS ix_agenda_eventos_empresa_inicio
    ON agenda_eventos (empresa_id, inicio);

CREATE INDEX IF NOT EXISTS ix_agenda_eventos_empresa_status_inicio
    ON agenda_eventos (empresa_id, status, inicio);

CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_eventos_origem_ref
    ON agenda_eventos (empresa_id, origem, origem_ref)
    WHERE origem_ref IS NOT NULL;

COMMIT;
