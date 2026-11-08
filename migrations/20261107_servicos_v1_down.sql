-- Rollback proposto; nao executar sem revisar os dados persistidos.
BEGIN;

DROP TRIGGER IF EXISTS definir_empresa_pedido_item_servico ON pedidos_itens;
DROP TRIGGER IF EXISTS definir_empresa_orcamento_item_servico ON orcamentos_itens;
DROP FUNCTION IF EXISTS definir_empresa_pedido_item_servico_v1();
DROP FUNCTION IF EXISTS definir_empresa_orcamento_item_servico_v1();

ALTER TABLE pedidos_itens
    DROP CONSTRAINT IF EXISTS fk_pedidos_itens_servico_empresa_v1,
    DROP CONSTRAINT IF EXISTS fk_pedidos_itens_documento_empresa_servicos_v1;
ALTER TABLE orcamentos_itens
    DROP CONSTRAINT IF EXISTS fk_orcamentos_itens_servico_empresa_v1,
    DROP CONSTRAINT IF EXISTS fk_orcamentos_itens_documento_empresa_servicos_v1;

DROP INDEX IF EXISTS ix_pedidos_itens_servico;
DROP INDEX IF EXISTS ix_orcamentos_itens_servico;
ALTER TABLE pedidos_itens
    DROP COLUMN IF EXISTS servico_id,
    DROP COLUMN IF EXISTS empresa_id;
ALTER TABLE orcamentos_itens
    DROP COLUMN IF EXISTS servico_id,
    DROP COLUMN IF EXISTS empresa_id;
DROP INDEX IF EXISTS ix_servicos_empresa_situacao_descricao;
DROP TABLE IF EXISTS servicos;

ALTER TABLE pedidos
    DROP CONSTRAINT IF EXISTS uq_pedidos_id_empresa;
ALTER TABLE orcamentos
    DROP CONSTRAINT IF EXISTS uq_orcamentos_id_empresa;

COMMIT;
