BEGIN;

ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS pagamento_modalidade VARCHAR(20),
    ADD COLUMN IF NOT EXISTS pagamento_numero_parcelas INTEGER,
    ADD COLUMN IF NOT EXISTS pagamento_intervalo_dias INTEGER,
    ADD COLUMN IF NOT EXISTS pagamento_primeiro_vencimento DATE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pedidos_id_empresa
    ON pedidos (id, empresa_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_formas_pagamento_id_empresa
    ON formas_pagamento (id, empresa_id);

CREATE TABLE IF NOT EXISTS pedido_parcelas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    pedido_id INTEGER NOT NULL,
    numero INTEGER NOT NULL CHECK (numero BETWEEN 1 AND 24),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('PARCELA', 'ENTRADA', 'SALDO')),
    valor NUMERIC(14, 2) NOT NULL CHECK (valor > 0),
    vencimento DATE NOT NULL,
    forma_pagamento_id INTEGER NOT NULL,
    forma_pagamento_nome VARCHAR(80) NOT NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_pedido_parcelas_pedido_empresa
        FOREIGN KEY (pedido_id, empresa_id)
        REFERENCES pedidos(id, empresa_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pedido_parcelas_forma_empresa
        FOREIGN KEY (forma_pagamento_id, empresa_id)
        REFERENCES formas_pagamento(id, empresa_id)
        ON DELETE RESTRICT,
    CONSTRAINT uq_pedido_parcelas_numero UNIQUE (pedido_id, numero)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'pedido_parcelas'::regclass
          AND conname = 'fk_pedido_parcelas_forma_empresa'
    ) THEN
        ALTER TABLE pedido_parcelas
            ADD CONSTRAINT fk_pedido_parcelas_forma_empresa
            FOREIGN KEY (forma_pagamento_id, empresa_id)
            REFERENCES formas_pagamento(id, empresa_id)
            ON DELETE RESTRICT;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS ix_pedido_parcelas_empresa
    ON pedido_parcelas (empresa_id);
CREATE INDEX IF NOT EXISTS ix_pedido_parcelas_pedido
    ON pedido_parcelas (pedido_id);

COMMIT;
