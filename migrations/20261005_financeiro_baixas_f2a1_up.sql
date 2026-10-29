-- F2A.1: estrutura de baixas (pagamento/recebimento parcial). Complementa a F2A.
-- Requer a migration 20261005_financeiro_titulos_f2a_up.sql aplicada antes.
-- Apenas estrutura: sem endpoints de baixa/estorno e sem alterar dados existentes.
-- financeiro.valor_pago/data_baixa sao resumos; a fonte detalhada e esta tabela.
BEGIN;

-- Permite FK composta (financeiro_id, empresa_id): uma baixa nunca aponta para
-- titulo de outra empresa. Aditivo; id ja e unico, entao nao pode falhar por dados.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'financeiro'::regclass AND conname = 'uq_financeiro_id_empresa'
    ) THEN
        ALTER TABLE financeiro ADD CONSTRAINT uq_financeiro_id_empresa UNIQUE (id, empresa_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS financeiro_baixas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL
        CONSTRAINT fk_financeiro_baixas_empresa REFERENCES empresas(id),
    financeiro_id INTEGER NOT NULL,
    data_baixa DATE NOT NULL,
    valor NUMERIC(14,2) NOT NULL,
    juros NUMERIC(14,2) NOT NULL DEFAULT 0,
    desconto NUMERIC(14,2) NOT NULL DEFAULT 0,
    conta_financeira_id INTEGER
        CONSTRAINT fk_financeiro_baixas_conta REFERENCES contas_financeiras(id) ON DELETE SET NULL,
    forma_pagamento_id INTEGER
        CONSTRAINT fk_financeiro_baixas_forma REFERENCES formas_pagamento(id) ON DELETE SET NULL,
    observacao TEXT,
    estornada_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    -- Sem CASCADE: titulo com baixa nao pode ser excluido (NO ACTION).
    CONSTRAINT fk_financeiro_baixas_titulo
        FOREIGN KEY (financeiro_id, empresa_id)
        REFERENCES financeiro (id, empresa_id),
    CONSTRAINT ck_financeiro_baixas_valor CHECK (valor > 0),
    CONSTRAINT ck_financeiro_baixas_juros CHECK (juros >= 0),
    CONSTRAINT ck_financeiro_baixas_desconto CHECK (desconto >= 0)
);

CREATE INDEX IF NOT EXISTS ix_financeiro_baixas_empresa_id ON financeiro_baixas (empresa_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_baixas_financeiro_id ON financeiro_baixas (financeiro_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_baixas_data_baixa ON financeiro_baixas (data_baixa);
CREATE INDEX IF NOT EXISTS ix_financeiro_baixas_conta_financeira_id ON financeiro_baixas (conta_financeira_id);

COMMIT;