-- Financeiro F1: cadastros base multiempresa.
-- Aditiva: NAO altera a tabela financeiro nem nenhuma tabela existente.
BEGIN;

CREATE TABLE IF NOT EXISTS contas_financeiras (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(120) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'BANCO',
    banco VARCHAR(120),
    agencia VARCHAR(30),
    numero_conta VARCHAR(40),
    saldo_inicial NUMERIC(14, 2) NOT NULL DEFAULT 0,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    observacao TEXT,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_contas_financeiras_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT ck_contas_financeiras_tipo
        CHECK (tipo IN ('BANCO', 'CAIXA'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_contas_financeiras_empresa_nome
    ON contas_financeiras (empresa_id, LOWER(nome));
CREATE INDEX IF NOT EXISTS ix_contas_financeiras_empresa_id
    ON contas_financeiras (empresa_id);

CREATE TABLE IF NOT EXISTS formas_pagamento (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(80) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'OUTRO',
    conta_financeira_id INTEGER,
    disponivel_para VARCHAR(10) NOT NULL DEFAULT 'AMBOS',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_formas_pagamento_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_formas_pagamento_conta_financeira
        FOREIGN KEY (conta_financeira_id) REFERENCES contas_financeiras(id)
        ON DELETE SET NULL,
    CONSTRAINT ck_formas_pagamento_disponivel_para
        CHECK (disponivel_para IN ('PAGAR', 'RECEBER', 'AMBOS')),
    CONSTRAINT ck_formas_pagamento_tipo
        CHECK (tipo IN ('DINHEIRO', 'PIX', 'BOLETO', 'CARTAO', 'TRANSFERENCIA', 'OUTRO'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_formas_pagamento_empresa_nome
    ON formas_pagamento (empresa_id, LOWER(nome));
CREATE INDEX IF NOT EXISTS ix_formas_pagamento_empresa_id
    ON formas_pagamento (empresa_id);
CREATE INDEX IF NOT EXISTS ix_formas_pagamento_conta_financeira_id
    ON formas_pagamento (conta_financeira_id);

CREATE TABLE IF NOT EXISTS plano_contas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    codigo VARCHAR(30) NOT NULL,
    nome VARCHAR(120) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    pai_id INTEGER,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_plano_contas_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_plano_contas_pai
        FOREIGN KEY (pai_id) REFERENCES plano_contas(id),
    CONSTRAINT ck_plano_contas_tipo
        CHECK (tipo IN ('RECEITA', 'DESPESA')),
    CONSTRAINT uq_plano_contas_empresa_codigo
        UNIQUE (empresa_id, codigo)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_plano_contas_empresa_nome
    ON plano_contas (empresa_id, LOWER(nome));
CREATE INDEX IF NOT EXISTS ix_plano_contas_empresa_id
    ON plano_contas (empresa_id);

CREATE TABLE IF NOT EXISTS situacoes_financeiras (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(80) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'AMBOS',
    quitado BOOLEAN NOT NULL DEFAULT FALSE,
    padrao BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_situacoes_financeiras_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT ck_situacoes_financeiras_tipo
        CHECK (tipo IN ('RECEBER', 'PAGAR', 'AMBOS'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_situacoes_financeiras_empresa_nome
    ON situacoes_financeiras (empresa_id, LOWER(nome));
CREATE UNIQUE INDEX IF NOT EXISTS uq_situacoes_financeiras_empresa_tipo_padrao
    ON situacoes_financeiras (empresa_id, tipo)
    WHERE padrao;
CREATE INDEX IF NOT EXISTS ix_situacoes_financeiras_empresa_id
    ON situacoes_financeiras (empresa_id);

CREATE TABLE IF NOT EXISTS centros_custo (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nome VARCHAR(120) NOT NULL,
    observacao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_centros_custo_empresa
        FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_centros_custo_empresa_nome
    ON centros_custo (empresa_id, LOWER(nome));
CREATE INDEX IF NOT EXISTS ix_centros_custo_empresa_id
    ON centros_custo (empresa_id);

-- Seed minimo para as empresas existentes (idempotente). Centros de custo: sem seed.
INSERT INTO contas_financeiras (empresa_id, nome, tipo)
SELECT e.id, 'Caixa', 'CAIXA' FROM empresas e
ON CONFLICT DO NOTHING;

INSERT INTO formas_pagamento (empresa_id, nome, tipo, conta_financeira_id, disponivel_para)
SELECT e.id, v.nome, v.tipo, NULL, 'AMBOS'
FROM empresas e
CROSS JOIN (VALUES
    ('Dinheiro', 'DINHEIRO'),
    ('PIX', 'PIX'),
    ('Boleto', 'BOLETO'),
    ('Cartão', 'CARTAO')
) AS v(nome, tipo)
ON CONFLICT DO NOTHING;

INSERT INTO situacoes_financeiras (empresa_id, nome, tipo, quitado, padrao)
SELECT e.id, v.nome, 'AMBOS', v.quitado, v.padrao
FROM empresas e
CROSS JOIN (VALUES
    ('Aberto', FALSE, TRUE),
    ('Pago', TRUE, FALSE),
    ('Cancelado', FALSE, FALSE)
) AS v(nome, quitado, padrao)
ON CONFLICT DO NOTHING;

INSERT INTO plano_contas (empresa_id, codigo, nome, tipo)
SELECT e.id, v.codigo, v.nome, v.tipo
FROM empresas e
CROSS JOIN (VALUES
    ('1.01', 'Receitas de vendas', 'RECEITA'),
    ('2.01', 'Contabilidade', 'DESPESA'),
    ('2.02', 'RT', 'DESPESA')
) AS v(codigo, nome, tipo)
ON CONFLICT DO NOTHING;

COMMIT;
