-- F2A do Financeiro: evolucao ADITIVA da tabela financeiro (titulos).
-- Nao remove nem altera colunas existentes; nao toca em linhas historicas.
-- Writers atuais (Venda/Contabilidade/RT) continuam inserindo sem os novos campos.
-- Observacao: valor_original NULL => tratar "valor" como valor original.
BEGIN;

ALTER TABLE financeiro
    ADD COLUMN IF NOT EXISTS competencia DATE,
    ADD COLUMN IF NOT EXISTS conta_financeira_id INTEGER
        CONSTRAINT fk_financeiro_conta_financeira
        REFERENCES contas_financeiras(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS forma_pagamento_id INTEGER
        CONSTRAINT fk_financeiro_forma_pagamento
        REFERENCES formas_pagamento(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS plano_conta_id INTEGER
        CONSTRAINT fk_financeiro_plano_conta
        REFERENCES plano_contas(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS centro_custo_id INTEGER
        CONSTRAINT fk_financeiro_centro_custo
        REFERENCES centros_custo(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS situacao_financeira_id INTEGER
        CONSTRAINT fk_financeiro_situacao_financeira
        REFERENCES situacoes_financeiras(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS valor_original NUMERIC(14,2)
        CONSTRAINT ck_financeiro_valor_original CHECK (valor_original IS NULL OR valor_original >= 0),
    ADD COLUMN IF NOT EXISTS desconto NUMERIC(14,2) NOT NULL DEFAULT 0
        CONSTRAINT ck_financeiro_desconto CHECK (desconto >= 0),
    ADD COLUMN IF NOT EXISTS juros NUMERIC(14,2) NOT NULL DEFAULT 0
        CONSTRAINT ck_financeiro_juros CHECK (juros >= 0),
    ADD COLUMN IF NOT EXISTS valor_pago NUMERIC(14,2) NOT NULL DEFAULT 0
        CONSTRAINT ck_financeiro_valor_pago CHECK (valor_pago >= 0),
    ADD COLUMN IF NOT EXISTS data_baixa DATE,
    ADD COLUMN IF NOT EXISTS numero_parcela INTEGER,
    ADD COLUMN IF NOT EXISTS total_parcelas INTEGER,
    ADD COLUMN IF NOT EXISTS parcelamento_grupo VARCHAR(40),
    ADD COLUMN IF NOT EXISTS recorrente BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS recorrencia_grupo VARCHAR(40);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'financeiro'::regclass AND conname = 'ck_financeiro_parcelas'
    ) THEN
        ALTER TABLE financeiro ADD CONSTRAINT ck_financeiro_parcelas CHECK (
            (numero_parcela IS NULL AND total_parcelas IS NULL)
            OR (numero_parcela IS NOT NULL AND total_parcelas IS NOT NULL
                AND numero_parcela >= 1 AND total_parcelas >= numero_parcela)
        );
    END IF;
END $$;

-- Ja existentes (nao duplicar): idx_financeiro_tipo, idx_financeiro_venc, ix_financeiro_empresa_id.
CREATE INDEX IF NOT EXISTS ix_financeiro_empresa_tipo_status_venc
    ON financeiro (empresa_id, tipo, status, vencimento);
CREATE INDEX IF NOT EXISTS ix_financeiro_pedido_id ON financeiro (pedido_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_cliente_id ON financeiro (cliente_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_fornecedor_id ON financeiro (fornecedor_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_conta_financeira_id ON financeiro (conta_financeira_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_forma_pagamento_id ON financeiro (forma_pagamento_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_plano_conta_id ON financeiro (plano_conta_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_centro_custo_id ON financeiro (centro_custo_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_situacao_financeira_id ON financeiro (situacao_financeira_id);
CREATE INDEX IF NOT EXISTS ix_financeiro_parcelamento_grupo
    ON financeiro (empresa_id, parcelamento_grupo) WHERE parcelamento_grupo IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_financeiro_recorrencia_grupo
    ON financeiro (empresa_id, recorrencia_grupo) WHERE recorrencia_grupo IS NOT NULL;

COMMIT;