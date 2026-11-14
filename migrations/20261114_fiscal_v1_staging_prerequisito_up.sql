-- Ajuste de dependência para homologação do Fiscal V1.
-- REVISAR COM A EQUIPE; não executar automaticamente em banco Render.
-- O staging consultado em 14/11/2026 tem zero produtos e não possui uq_produtos_id_empresa.
-- O banco operacional já possui essa constraint e NÃO precisa desta migration.
BEGIN;

DO $preflight$
BEGIN
  IF to_regclass('public.produtos') IS NULL THEN
    RAISE EXCEPTION 'Tabela produtos ausente.';
  END IF;
  IF EXISTS (SELECT 1 FROM produtos WHERE empresa_id IS NULL) THEN
    RAISE EXCEPTION 'Produtos legados sem empresa_id. Corrigir tenant antes da constraint fiscal.';
  END IF;
  IF EXISTS (
    SELECT 1 FROM produtos GROUP BY id, empresa_id HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'Duplicidade de id + empresa_id em produtos.';
  END IF;
END
$preflight$;

DO $constraint$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid='public.produtos'::regclass
      AND conname='uq_produtos_id_empresa'
      AND contype='u'
  ) THEN
    ALTER TABLE produtos ADD CONSTRAINT uq_produtos_id_empresa UNIQUE (id, empresa_id);
  END IF;
END
$constraint$;

COMMIT;
