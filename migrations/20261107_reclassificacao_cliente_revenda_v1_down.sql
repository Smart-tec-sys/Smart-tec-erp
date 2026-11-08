BEGIN;

DO $rollback_guard$
BEGIN
    IF EXISTS (SELECT 1 FROM public.cliente_reclassificacoes)
       OR EXISTS (
           SELECT 1
           FROM public.parceiros_comerciais
           WHERE cliente_origem_id IS NOT NULL
       )
    THEN
        RAISE EXCEPTION
            'Rollback bloqueado: há reclassificações persistidas; preserve os vínculos e a auditoria';
    END IF;
END;
$rollback_guard$;

DROP TABLE public.cliente_reclassificacoes;

ALTER TABLE public.parceiros_comerciais
    DROP CONSTRAINT fk_parceiros_cliente_origem_empresa,
    DROP CONSTRAINT uq_parceiros_empresa_cliente_origem,
    DROP CONSTRAINT uq_parceiros_id_empresa_reclassificacao,
    DROP COLUMN cliente_origem_id;

ALTER TABLE public.clientes
    DROP CONSTRAINT uq_clientes_id_empresa_reclassificacao;

COMMIT;
