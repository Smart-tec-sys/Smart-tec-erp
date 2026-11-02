-- Revendas V1: campos aditivos de cadastro completo para parceiros_comerciais.
-- Requer a tabela base da fase comercial e funcionarios no schema public.
BEGIN;

DO $preflight$
BEGIN
    IF to_regclass('public.parceiros_comerciais') IS NULL THEN
        RAISE EXCEPTION
            'Pré-requisito: public.parceiros_comerciais deve existir antes da migration Revendas V1';
    END IF;
    IF to_regclass('public.funcionarios') IS NULL THEN
        RAISE EXCEPTION
            'Pré-requisito: public.funcionarios deve existir antes da migration Revendas V1';
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'public.parceiros_comerciais'::regclass
          AND attname = 'empresa_id'
          AND attnum > 0
          AND NOT attisdropped
    ) OR NOT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'public.funcionarios'::regclass
          AND attname = 'id'
          AND attnum > 0
          AND NOT attisdropped
    ) OR NOT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'public.funcionarios'::regclass
          AND attname = 'empresa_id'
          AND attnum > 0
          AND NOT attisdropped
    ) THEN
        RAISE EXCEPTION
            'Pré-requisito: parceiros_comerciais.empresa_id e funcionarios.empresa_id devem existir';
    END IF;
END;
$preflight$;

ALTER TABLE public.parceiros_comerciais
    ADD COLUMN IF NOT EXISTS tipo_pessoa VARCHAR(8),
    ADD COLUMN IF NOT EXISTS nome_fantasia VARCHAR(255),
    ADD COLUMN IF NOT EXISTS razao_social VARCHAR(255),
    ADD COLUMN IF NOT EXISTS situacao_cadastral VARCHAR(100),
    ADD COLUMN IF NOT EXISTS inscricao_estadual VARCHAR(80),
    ADD COLUMN IF NOT EXISTS inscricao_municipal VARCHAR(80),
    ADD COLUMN IF NOT EXISTS tipo_contribuinte VARCHAR(30),
    ADD COLUMN IF NOT EXISTS isento_ie BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS telefone_celular VARCHAR(50),
    ADD COLUMN IF NOT EXISTS responsavel VARCHAR(120),
    ADD COLUMN IF NOT EXISTS site VARCHAR(500),
    ADD COLUMN IF NOT EXISTS cep VARCHAR(8),
    ADD COLUMN IF NOT EXISTS logradouro VARCHAR(255),
    ADD COLUMN IF NOT EXISTS numero VARCHAR(30),
    ADD COLUMN IF NOT EXISTS complemento VARCHAR(255),
    ADD COLUMN IF NOT EXISTS bairro VARCHAR(100),
    ADD COLUMN IF NOT EXISTS cidade VARCHAR(150),
    ADD COLUMN IF NOT EXISTS estado VARCHAR(2),
    ADD COLUMN IF NOT EXISTS vendedor_responsavel_id INTEGER,
    ADD COLUMN IF NOT EXISTS limite_credito NUMERIC(14, 2),
    ADD COLUMN IF NOT EXISTS permitir_exceder_limite BOOLEAN NOT NULL DEFAULT FALSE;

DO $columns$
DECLARE
    r RECORD;
    v_type TEXT;
    v_not_null BOOLEAN;
    v_default TEXT;
BEGIN
    FOR r IN
        SELECT *
        FROM (VALUES
            ('tipo_pessoa', 'character varying(8)', FALSE, NULL::TEXT),
            ('nome_fantasia', 'character varying(255)', FALSE, NULL::TEXT),
            ('razao_social', 'character varying(255)', FALSE, NULL::TEXT),
            ('situacao_cadastral', 'character varying(100)', FALSE, NULL::TEXT),
            ('inscricao_estadual', 'character varying(80)', FALSE, NULL::TEXT),
            ('inscricao_municipal', 'character varying(80)', FALSE, NULL::TEXT),
            ('tipo_contribuinte', 'character varying(30)', FALSE, NULL::TEXT),
            ('isento_ie', 'boolean', TRUE, 'false'),
            ('telefone_celular', 'character varying(50)', FALSE, NULL::TEXT),
            ('responsavel', 'character varying(120)', FALSE, NULL::TEXT),
            ('site', 'character varying(500)', FALSE, NULL::TEXT),
            ('cep', 'character varying(8)', FALSE, NULL::TEXT),
            ('logradouro', 'character varying(255)', FALSE, NULL::TEXT),
            ('numero', 'character varying(30)', FALSE, NULL::TEXT),
            ('complemento', 'character varying(255)', FALSE, NULL::TEXT),
            ('bairro', 'character varying(100)', FALSE, NULL::TEXT),
            ('cidade', 'character varying(150)', FALSE, NULL::TEXT),
            ('estado', 'character varying(2)', FALSE, NULL::TEXT),
            ('vendedor_responsavel_id', 'integer', FALSE, NULL::TEXT),
            ('limite_credito', 'numeric(14,2)', FALSE, NULL::TEXT),
            ('permitir_exceder_limite', 'boolean', TRUE, 'false')
        ) AS expected(column_name, expected_type, expected_not_null, expected_default)
    LOOP
        SELECT
            format_type(a.atttypid, a.atttypmod),
            a.attnotnull,
            regexp_replace(
                lower(coalesce(pg_get_expr(d.adbin, d.adrelid), '')),
                '::[a-z ]+',
                '',
                'g'
            )
        INTO v_type, v_not_null, v_default
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d
          ON d.adrelid = a.attrelid
         AND d.adnum = a.attnum
        WHERE a.attrelid = 'public.parceiros_comerciais'::regclass
          AND a.attname = r.column_name
          AND a.attnum > 0
          AND NOT a.attisdropped;

        IF v_type IS DISTINCT FROM r.expected_type
           OR v_not_null IS DISTINCT FROM r.expected_not_null
           OR (r.expected_default IS NULL AND v_default <> '')
           OR (
               r.expected_default IS NOT NULL
               AND regexp_replace(v_default, '[()[:space:]]', '', 'g')
                   <> r.expected_default
           ) THEN
            RAISE EXCEPTION
                'Coluna public.parceiros_comerciais.% incompatível: tipo/null/default divergente',
                r.column_name;
        END IF;
    END LOOP;
END;
$columns$;

DO $constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.parceiros_comerciais'::regclass
          AND conname = 'ck_parceiros_comerciais_tipo_pessoa_v1'
    ) THEN
        ALTER TABLE public.parceiros_comerciais
            ADD CONSTRAINT ck_parceiros_comerciais_tipo_pessoa_v1
            CHECK (tipo_pessoa IS NULL OR tipo_pessoa IN ('FISICA', 'JURIDICA'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.parceiros_comerciais'::regclass
          AND conname = 'ck_parceiros_comerciais_tipo_contribuinte_v1'
    ) THEN
        ALTER TABLE public.parceiros_comerciais
            ADD CONSTRAINT ck_parceiros_comerciais_tipo_contribuinte_v1
            CHECK (
                tipo_contribuinte IS NULL
                OR tipo_contribuinte IN ('CONTRIBUINTE', 'ISENTO', 'NAO_CONTRIBUINTE')
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.parceiros_comerciais'::regclass
          AND conname = 'ck_parceiros_comerciais_cep_v1'
    ) THEN
        ALTER TABLE public.parceiros_comerciais
            ADD CONSTRAINT ck_parceiros_comerciais_cep_v1
            CHECK (cep IS NULL OR cep ~ '^[0-9]{8}$');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.parceiros_comerciais'::regclass
          AND conname = 'ck_parceiros_comerciais_limite_credito_v1'
    ) THEN
        ALTER TABLE public.parceiros_comerciais
            ADD CONSTRAINT ck_parceiros_comerciais_limite_credito_v1
            CHECK (
                limite_credito IS NULL
                OR (
                    limite_credito >= 0
                    AND limite_credito::text NOT IN ('NaN', 'Infinity', '-Infinity')
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.parceiros_comerciais'::regclass
          AND conname = 'fk_parceiros_comerciais_vendedor_responsavel_v1'
    ) THEN
        ALTER TABLE public.parceiros_comerciais
            ADD CONSTRAINT fk_parceiros_comerciais_vendedor_responsavel_v1
            FOREIGN KEY (vendedor_responsavel_id)
            REFERENCES public.funcionarios(id)
            ON DELETE SET NULL;
    END IF;
END;
$constraints$;

DO $validate_constraints$
DECLARE
    r RECORD;
    v_definition TEXT;
BEGIN
    FOR r IN
        SELECT *
        FROM (VALUES
            ('ck_parceiros_comerciais_tipo_pessoa_v1', 'c', ARRAY['tipo_pessoa', 'fisica', 'juridica']::TEXT[]),
            ('ck_parceiros_comerciais_tipo_contribuinte_v1', 'c', ARRAY['tipo_contribuinte', 'contribuinte', 'isento', 'nao_contribuinte']::TEXT[]),
            ('ck_parceiros_comerciais_cep_v1', 'c', ARRAY['cep', '^[0-9]{8}$']::TEXT[]),
            ('ck_parceiros_comerciais_limite_credito_v1', 'c', ARRAY['limite_credito', 'nan', 'infinity', '>=']::TEXT[]),
            ('fk_parceiros_comerciais_vendedor_responsavel_v1', 'f', ARRAY['vendedor_responsavel_id', 'funcionarios', 'set null']::TEXT[])
        ) AS expected(constraint_name, constraint_type, required_fragments)
    LOOP
        SELECT lower(pg_get_constraintdef(c.oid))
        INTO v_definition
        FROM pg_constraint c
        WHERE c.conrelid = 'public.parceiros_comerciais'::regclass
          AND c.conname = r.constraint_name
          AND c.contype::TEXT = r.constraint_type
          AND c.convalidated
          AND (
              r.constraint_type <> 'f'
              OR (
                  c.confrelid = 'public.funcionarios'::regclass
                  AND c.confdeltype = 'n'
                  AND c.conkey = ARRAY[(
                      SELECT attnum
                      FROM pg_attribute
                      WHERE attrelid = c.conrelid
                        AND attname = 'vendedor_responsavel_id'
                  )]::SMALLINT[]
                  AND c.confkey = ARRAY[(
                      SELECT attnum
                      FROM pg_attribute
                      WHERE attrelid = c.confrelid
                        AND attname = 'id'
                  )]::SMALLINT[]
              )
          );
        IF v_definition IS NULL THEN
            RAISE EXCEPTION
                'Constraint Revendas V1 ausente, não validada ou incompatível: %',
                r.constraint_name;
        END IF;
        IF EXISTS (
            SELECT 1
            FROM unnest(r.required_fragments) AS fragments(fragment)
            WHERE position(fragment IN v_definition) = 0
        ) THEN
            RAISE EXCEPTION
                'Definição inesperada para constraint Revendas V1: %',
                r.constraint_name;
        END IF;
    END LOOP;
END;
$validate_constraints$;

CREATE INDEX IF NOT EXISTS ix_parceiros_comerciais_empresa_vendedor_v1
    ON public.parceiros_comerciais (empresa_id, vendedor_responsavel_id)
    WHERE vendedor_responsavel_id IS NOT NULL;

DO $validate_index$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class idx ON idx.oid = i.indexrelid
        WHERE i.indexrelid = to_regclass(
                  'public.ix_parceiros_comerciais_empresa_vendedor_v1'
              )
          AND i.indrelid = 'public.parceiros_comerciais'::regclass
          AND i.indisvalid
          AND i.indisready
          AND NOT i.indisunique
          AND i.indnkeyatts = 2
          AND i.indnatts = 2
          AND i.indkey[0] = (
              SELECT attnum FROM pg_attribute
              WHERE attrelid = i.indrelid AND attname = 'empresa_id'
          )
          AND i.indkey[1] = (
              SELECT attnum FROM pg_attribute
              WHERE attrelid = i.indrelid AND attname = 'vendedor_responsavel_id'
          )
          AND regexp_replace(
              lower(pg_get_expr(i.indpred, i.indrelid)),
              '[[:space:]()"]',
              '',
              'g'
          ) = 'vendedor_responsavel_idisnotnull'
    ) THEN
        RAISE EXCEPTION
            'Índice ix_parceiros_comerciais_empresa_vendedor_v1 ausente ou incompatível';
    END IF;
END;
$validate_index$;

COMMIT;
