-- Reverte a F2A: remove somente o que ela adicionou em financeiro.
-- Colunas originais e linhas existentes permanecem intactas.
BEGIN;

DROP INDEX IF EXISTS ix_financeiro_empresa_tipo_status_venc;
DROP INDEX IF EXISTS ix_financeiro_pedido_id;
DROP INDEX IF EXISTS ix_financeiro_cliente_id;
DROP INDEX IF EXISTS ix_financeiro_fornecedor_id;
DROP INDEX IF EXISTS ix_financeiro_conta_financeira_id;
DROP INDEX IF EXISTS ix_financeiro_forma_pagamento_id;
DROP INDEX IF EXISTS ix_financeiro_plano_conta_id;
DROP INDEX IF EXISTS ix_financeiro_centro_custo_id;
DROP INDEX IF EXISTS ix_financeiro_situacao_financeira_id;
DROP INDEX IF EXISTS ix_financeiro_parcelamento_grupo;
DROP INDEX IF EXISTS ix_financeiro_recorrencia_grupo;

ALTER TABLE financeiro DROP CONSTRAINT IF EXISTS ck_financeiro_parcelas;

ALTER TABLE financeiro
    DROP COLUMN IF EXISTS competencia,
    DROP COLUMN IF EXISTS conta_financeira_id,
    DROP COLUMN IF EXISTS forma_pagamento_id,
    DROP COLUMN IF EXISTS plano_conta_id,
    DROP COLUMN IF EXISTS centro_custo_id,
    DROP COLUMN IF EXISTS situacao_financeira_id,
    DROP COLUMN IF EXISTS valor_original,
    DROP COLUMN IF EXISTS desconto,
    DROP COLUMN IF EXISTS juros,
    DROP COLUMN IF EXISTS valor_pago,
    DROP COLUMN IF EXISTS data_baixa,
    DROP COLUMN IF EXISTS numero_parcela,
    DROP COLUMN IF EXISTS total_parcelas,
    DROP COLUMN IF EXISTS parcelamento_grupo,
    DROP COLUMN IF EXISTS recorrente,
    DROP COLUMN IF EXISTS recorrencia_grupo;

COMMIT;