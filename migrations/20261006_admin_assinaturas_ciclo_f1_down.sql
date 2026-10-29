-- Reversão bloqueada se o estado PENDENTE ainda estiver em uso.
BEGIN;
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM public.assinaturas_saas WHERE status='PENDENTE') THEN
  RAISE EXCEPTION 'DOWN bloqueado: existem assinaturas PENDENTE.';
 END IF;
END $$;
DROP INDEX public.uq_pagamentos_saas_assinatura_ciclo;
ALTER TABLE public.pagamentos_saas DROP CONSTRAINT ck_pagamentos_saas_ciclo_datas, DROP COLUMN ciclo_inicio, DROP COLUMN ciclo_fim;
DROP INDEX public.ix_assinaturas_saas_forma_pagamento_id;
ALTER TABLE public.assinaturas_saas DROP CONSTRAINT fk_assinaturas_saas_forma_pagamento, DROP COLUMN forma_pagamento_id;
ALTER TABLE public.assinaturas_saas DROP CONSTRAINT ck_assinatura_status;
ALTER TABLE public.assinaturas_saas ADD CONSTRAINT ck_assinatura_status CHECK (status IN ('TRIAL','TRIAL_EXPIRADO','ATIVA','PROXIMA_VENCIMENTO','VENCIDA','SUSPENSA','CANCELADA'));
COMMIT;
