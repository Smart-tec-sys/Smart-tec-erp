-- Fase 2: base estrutural multiempresa. PREPARADA, NÃO EXECUTADA.
-- Não atribui registros legados a nenhuma empresa.

BEGIN;

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),
    documento VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVA',
    slug VARCHAR(100) NOT NULL,
    configuracoes JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_empresas_status CHECK (status IN ('ATIVA', 'INATIVA')),
    CONSTRAINT uq_empresas_slug UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS empresa_portfolio (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    modelo_tecnico VARCHAR(100) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    configuracoes_locais JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_empresa_portfolio_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    CONSTRAINT uq_empresa_portfolio_empresa_modelo
        UNIQUE (empresa_id, modelo_tecnico)
);

ALTER TABLE produtos ADD COLUMN IF NOT EXISTS empresa_id INTEGER NULL;
ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS empresa_id INTEGER NULL;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS empresa_id INTEGER NULL;
ALTER TABLE orcamentos ADD COLUMN IF NOT EXISTS empresa_id INTEGER NULL;

CREATE INDEX IF NOT EXISTS ix_produtos_empresa_id ON produtos (empresa_id);
CREATE INDEX IF NOT EXISTS ix_fornecedores_empresa_id ON fornecedores (empresa_id);
CREATE INDEX IF NOT EXISTS ix_clientes_empresa_id ON clientes (empresa_id);
CREATE INDEX IF NOT EXISTS ix_orcamentos_empresa_id ON orcamentos (empresa_id);
CREATE INDEX IF NOT EXISTS ix_empresa_portfolio_empresa_id
    ON empresa_portfolio (empresa_id);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_produtos_empresa_id') THEN
        ALTER TABLE produtos ADD CONSTRAINT fk_produtos_empresa_id
            FOREIGN KEY (empresa_id) REFERENCES empresas(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_fornecedores_empresa_id') THEN
        ALTER TABLE fornecedores ADD CONSTRAINT fk_fornecedores_empresa_id
            FOREIGN KEY (empresa_id) REFERENCES empresas(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_clientes_empresa_id') THEN
        ALTER TABLE clientes ADD CONSTRAINT fk_clientes_empresa_id
            FOREIGN KEY (empresa_id) REFERENCES empresas(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_orcamentos_empresa_id') THEN
        ALTER TABLE orcamentos ADD CONSTRAINT fk_orcamentos_empresa_id
            FOREIGN KEY (empresa_id) REFERENCES empresas(id);
    END IF;
END $$;

COMMIT;
