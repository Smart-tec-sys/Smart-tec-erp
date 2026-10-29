-- Admin SaaS: vinculo opcional com o cadastro oficial formas_pagamento (empresa da plataforma).
-- Aditivo: forma_pagamento (texto) permanece como snapshot historico/fallback. Sem backfill.
BEGIN;

ALTER TABLE pedidos_modulos_saas
    ADD COLUMN IF NOT EXISTS forma_pagamento_id INTEGER NULL
    REFERENCES formas_pagamento(id) ON DELETE SET NULL;

ALTER TABLE pagamentos_saas
    ADD COLUMN IF NOT EXISTS forma_pagamento_id INTEGER NULL
    REFERENCES formas_pagamento(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_pedidos_modulos_saas_forma_pagamento_id
    ON pedidos_modulos_saas (forma_pagamento_id);
CREATE INDEX IF NOT EXISTS ix_pagamentos_saas_forma_pagamento_id
    ON pagamentos_saas (forma_pagamento_id);

COMMIT;