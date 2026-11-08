-- Migration aditiva local para a autorizacao comercial e rastreabilidade da OP.
-- Requer 20261103_producao_v1_up.sql previamente aplicada; nao executar sem autorizacao.
BEGIN;

ALTER TABLE pedidos
    ADD COLUMN producao_aprovado_por VARCHAR(100),
    ADD COLUMN producao_aprovado_em TIMESTAMPTZ,
    ADD COLUMN producao_liberado_por VARCHAR(100),
    ADD COLUMN producao_liberado_em TIMESTAMPTZ,
    ADD COLUMN producao_historico JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE orcamentos_itens
    ADD COLUMN ambiente VARCHAR(200);
ALTER TABLE pedidos_itens
    ADD COLUMN ambiente VARCHAR(200);

-- Mantem autorizacoes explicitas de OPs existentes sem promover OP nao liberada.
UPDATE pedidos AS pedido
SET producao_aprovado_por = op.confirmado_por,
    producao_aprovado_em = op.confirmado_em,
    producao_liberado_por = op.liberado_por,
    producao_liberado_em = op.liberado_em,
    producao_historico = CASE
        WHEN op.liberado_em IS NULL THEN jsonb_build_array(
            jsonb_build_object('acao', 'APROVACAO_LEGADA_OP', 'usuario', op.confirmado_por,
                               'em', op.confirmado_em)
        )
        ELSE jsonb_build_array(
            jsonb_build_object('acao', 'APROVACAO_LEGADA_OP', 'usuario', op.confirmado_por,
                               'em', op.confirmado_em),
            jsonb_build_object('acao', 'LIBERACAO_LEGADA_OP', 'usuario', op.liberado_por,
                               'em', op.liberado_em)
        )
    END
FROM ordens_producao AS op
WHERE op.pedido_id = pedido.id
  AND op.empresa_id = pedido.empresa_id;

UPDATE ordens_producao AS op
SET snapshot = (
    op.snapshot::jsonb || jsonb_build_object(
        'cliente', COALESCE(NULLIF(pedido.cliente_final_nome, ''), cliente.nome, '')
    )
)::json
FROM pedidos AS pedido
LEFT JOIN clientes AS cliente
    ON cliente.id = pedido.cliente_id
   AND cliente.empresa_id = pedido.empresa_id
WHERE op.pedido_id = pedido.id
  AND op.empresa_id = pedido.empresa_id
  AND NULLIF(op.snapshot->>'cliente', '') IS NULL;

COMMIT;
