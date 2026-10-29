-- Reverte a F1 do Financeiro. Nao toca na tabela financeiro.
BEGIN;

DROP TABLE IF EXISTS centros_custo;
DROP TABLE IF EXISTS situacoes_financeiras;
DROP TABLE IF EXISTS plano_contas;
DROP TABLE IF EXISTS formas_pagamento;
DROP TABLE IF EXISTS contas_financeiras;

COMMIT;
