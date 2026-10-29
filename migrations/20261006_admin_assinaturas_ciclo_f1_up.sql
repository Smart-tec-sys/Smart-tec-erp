-- Assinaturas F1: cobrança antecipada. Sem backfill.
BEGIN;
ALTER TABLE public.assinaturas_saas DROP CONSTRAINT ck_assinatura_status;
ALTER TABLE public.assinaturas_saas ADD CONSTRAINT ck_assinatura_status CHECK (status IN ('TRIAL','TRIAL_EXPIRADO','PENDENTE','ATIVA','PROXIMA_VENCIMENTO','VENCIDA','SUSPENSA','CANCELADA'));
ALTER TABLE public.assinaturas_saas ADD COLUMN forma_pagamento_id INTEGER NULL;
ALTER TABLE public.assinaturas_saas ADD CONSTRAINT fk_assinaturas_saas_forma_pagamento FOREIGN KEY (forma_pagamento_id) REFERENCES public.formas_pagamento(id) ON DELETE SET NULL;
CREATE INDEX ix_assinaturas_saas_forma_pagamento_id ON public.assinaturas_saas(forma_pagamento_id);
ALTER TABLE public.pagamentos_saas ADD COLUMN ciclo_inicio DATE NULL, ADD COLUMN ciclo_fim DATE NULL;
ALTER TABLE public.pagamentos_saas ADD CONSTRAINT ck_pagamentos_saas_ciclo_datas CHECK ((ciclo_inicio IS NULL AND ciclo_fim IS NULL) OR (ciclo_inicio IS NOT NULL AND ciclo_fim IS NOT NULL AND ciclo_fim>ciclo_inicio));
CREATE UNIQUE INDEX uq_pagamentos_saas_assinatura_ciclo ON public.pagamentos_saas(assinatura_id,ciclo_inicio,ciclo_fim) WHERE tipo='ASSINATURA' AND status IN ('PENDENTE','PROCESSANDO','PAGO','ATRASADO','ESTORNADO');
COMMIT;
