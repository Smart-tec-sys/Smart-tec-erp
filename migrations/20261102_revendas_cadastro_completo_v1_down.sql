-- Reverte somente os objetos adicionados pela Revendas V1.
-- ATENÇÃO: os valores gravados nas 21 colunas abaixo serão perdidos.
BEGIN;

ALTER TABLE IF EXISTS public.parceiros_comerciais
    DROP CONSTRAINT IF EXISTS fk_parceiros_comerciais_vendedor_responsavel_v1,
    DROP CONSTRAINT IF EXISTS ck_parceiros_comerciais_cep_v1,
    DROP CONSTRAINT IF EXISTS ck_parceiros_comerciais_limite_credito_v1,
    DROP CONSTRAINT IF EXISTS ck_parceiros_comerciais_tipo_contribuinte_v1,
    DROP CONSTRAINT IF EXISTS ck_parceiros_comerciais_tipo_pessoa_v1;

DROP INDEX IF EXISTS public.ix_parceiros_comerciais_empresa_vendedor_v1;

ALTER TABLE IF EXISTS public.parceiros_comerciais
    DROP COLUMN IF EXISTS permitir_exceder_limite,
    DROP COLUMN IF EXISTS limite_credito,
    DROP COLUMN IF EXISTS vendedor_responsavel_id,
    DROP COLUMN IF EXISTS estado,
    DROP COLUMN IF EXISTS cidade,
    DROP COLUMN IF EXISTS bairro,
    DROP COLUMN IF EXISTS complemento,
    DROP COLUMN IF EXISTS numero,
    DROP COLUMN IF EXISTS logradouro,
    DROP COLUMN IF EXISTS cep,
    DROP COLUMN IF EXISTS site,
    DROP COLUMN IF EXISTS responsavel,
    DROP COLUMN IF EXISTS telefone_celular,
    DROP COLUMN IF EXISTS isento_ie,
    DROP COLUMN IF EXISTS tipo_contribuinte,
    DROP COLUMN IF EXISTS inscricao_municipal,
    DROP COLUMN IF EXISTS inscricao_estadual,
    DROP COLUMN IF EXISTS situacao_cadastral,
    DROP COLUMN IF EXISTS razao_social,
    DROP COLUMN IF EXISTS nome_fantasia,
    DROP COLUMN IF EXISTS tipo_pessoa;

COMMIT;
