-- Reverte o vinculo forma_pagamento_id. O texto forma_pagamento nao e tocado.
BEGIN;

DROP INDEX IF EXISTS ix_pagamentos_saas_forma_pagamento_id;
DROP INDEX IF EXISTS ix_pedidos_modulos_saas_forma_pagamento_id;
ALTER TABLE pagamentos_saas DROP COLUMN IF EXISTS forma_pagamento_id;
ALTER TABLE pedidos_modulos_saas DROP COLUMN IF EXISTS forma_pagamento_id;

COMMIT;