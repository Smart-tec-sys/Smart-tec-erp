-- FASE 1 — NÚCLEO COMERCIAL
-- REFERÊNCIA: smarttec_erp_dev
-- DESTINO EXCLUSIVO: smarttec_erp_staging / public / smarttec_staging
-- BASELINE INFORMADO: clientes=1; demais cinco tabelas operacionais=0.
-- Fase 1: 60 colunas novas e 2 existentes preservadas, 62 verificadas ao final.
--
-- PROPOSTA NÃO EXECUTADA.
-- Não contém carga de dados, UPDATE, DELETE, TRUNCATE ou setval.
-- As tabelas novas são montadas dentro da mesma transação.
-- Objetos previstos que já existam devem corresponder à definição esperada.

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '120s';
SET LOCAL search_path = pg_catalog, public;

-- 1. Destino e dependências.
DO $preflight$
DECLARE
    v_tabela text;
    v_oid oid;
BEGIN
    IF current_database() <> 'smarttec_erp_staging' THEN
        RAISE EXCEPTION
            'Destino incorreto: esperado smarttec_erp_staging; atual %',
            current_database();
    END IF;

    IF current_user <> 'smarttec_staging' THEN
        RAISE EXCEPTION
            'Usuário incorreto: esperado smarttec_staging; atual %',
            current_user;
    END IF;

    IF current_setting('server_version_num')::integer < 120000 THEN
        RAISE EXCEPTION 'Esta proposta requer PostgreSQL 12 ou superior.';
    END IF;

    FOREACH v_tabela IN ARRAY ARRAY[
        'clientes', 'orcamentos', 'orcamentos_itens',
        'pedidos', 'pedidos_itens',
        'empresas', 'funcionarios', 'produtos', 'financeiro'
    ]
    LOOP
        v_oid := to_regclass(format('public.%I', v_tabela));

        IF v_oid IS NULL THEN
            RAISE EXCEPTION 'Tabela obrigatória ausente: public.%', v_tabela;
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_class
            WHERE oid = v_oid AND relkind = 'r'
        ) THEN
            RAISE EXCEPTION
                'public.% não é uma tabela comum compatível com a referência',
                v_tabela;
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_attribute a
            JOIN pg_constraint c
              ON c.conrelid = a.attrelid
             AND c.conkey = ARRAY[a.attnum]::smallint[]
             AND c.contype IN ('p', 'u')
             AND c.convalidated
             AND NOT c.condeferrable
            WHERE a.attrelid = v_oid
              AND a.attname = 'id'
              AND NOT a.attisdropped
              AND a.atttypid = 'integer'::regtype
        ) THEN
            RAISE EXCEPTION
                'public.%.id precisa ser integer com PK/UNIQUE compatível',
                v_tabela;
        END IF;
    END LOOP;

    -- perfil_comercial de orçamentos não faz parte das colunas a adicionar.
    IF NOT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'public.orcamentos'::regclass
          AND attname = 'perfil_comercial'
          AND NOT attisdropped
          AND format_type(atttypid, atttypmod) = 'character varying(30)'
    ) THEN
        RAISE EXCEPTION
            'Pré-requisito: orcamentos.perfil_comercial varchar(30) deve existir';
    END IF;

    FOREACH v_tabela IN ARRAY ARRAY[
        'parceiros_comerciais', 'representantes',
        'parceiro_representantes', 'parceiro_clientes', 'representantes_rt'
    ]
    LOOP
        v_oid := to_regclass(format('public.%I', v_tabela));

        IF v_oid IS NOT NULL THEN
            RAISE EXCEPTION
                'Baseline divergente: public.% deveria estar ausente', v_tabela;
        END IF;
    END LOOP;

    -- Estas duas colunas já existem no staging: validar, nunca recriar.
    IF NOT EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = 'public.orcamentos'::regclass
          AND attname = 'observacao_interna'
          AND attnum > 0 AND NOT attisdropped
          AND atttypid = 'text'::regtype
    ) OR NOT EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = 'public.orcamentos_itens'::regclass
          AND attname = 'dados_tecnicos'
          AND attnum > 0 AND NOT attisdropped
          AND atttypid = 'jsonb'::regtype
    ) THEN
        RAISE EXCEPTION
            'Pré-requisito: orcamentos.observacao_interna text e orcamentos_itens.dados_tecnicos jsonb devem existir';
    END IF;
END;
$preflight$;

-- 2. Relações novas.
-- As colunas serão adicionadas pelo catálogo explícito da seção 4.
-- Não recria tabelas existentes.

CREATE TABLE IF NOT EXISTS public.parceiros_comerciais ();
CREATE TABLE IF NOT EXISTS public.representantes ();
CREATE TABLE IF NOT EXISTS public.parceiro_representantes ();
CREATE TABLE IF NOT EXISTS public.parceiro_clientes ();
CREATE TABLE IF NOT EXISTS public.representantes_rt ();

-- Impede escritas concorrentes durante a alteração e a conferência do baseline.
-- lock_timeout interrompe a tentativa caso os locks não sejam obtidos.
LOCK TABLE
    public.clientes,
    public.orcamentos,
    public.orcamentos_itens,
    public.pedidos,
    public.pedidos_itens,
    public.financeiro,
    public.parceiros_comerciais,
    public.representantes,
    public.parceiro_representantes,
    public.parceiro_clientes,
    public.representantes_rt
IN SHARE ROW EXCLUSIVE MODE;

DO $baseline$
BEGIN
    IF (SELECT count(*) FROM public.clientes) <> 1
       OR (SELECT count(*) FROM public.orcamentos) <> 0
       OR (SELECT count(*) FROM public.orcamentos_itens) <> 0
       OR (SELECT count(*) FROM public.pedidos) <> 0
       OR (SELECT count(*) FROM public.pedidos_itens) <> 0
       OR (SELECT count(*) FROM public.financeiro) <> 0
    THEN
        RAISE EXCEPTION
            'Contagens divergentes do baseline informado; revisar antes de executar';
    END IF;
END;
$baseline$;

DO $integridade_baseline$
BEGIN
    IF EXISTS (
        SELECT numero FROM public.orcamentos
        GROUP BY numero HAVING count(*) > 1
    ) OR EXISTS (
        SELECT numero FROM public.pedidos
        GROUP BY numero HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Baseline divergente: números duplicados em orcamentos ou pedidos';
    END IF;

    IF EXISTS (
        SELECT 1 FROM public.orcamentos o
        WHERE o.cliente_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM public.clientes c WHERE c.id = o.cliente_id)
    ) OR EXISTS (
        SELECT 1 FROM public.orcamentos_itens i
        WHERE i.orcamento_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM public.orcamentos o WHERE o.id = i.orcamento_id)
    ) OR EXISTS (
        SELECT 1 FROM public.pedidos_itens i
        WHERE i.pedido_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM public.pedidos p WHERE p.id = i.pedido_id)
    ) OR EXISTS (
        SELECT 1 FROM public.financeiro f
        WHERE f.pedido_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM public.pedidos p WHERE p.id = f.pedido_id)
    ) THEN
        RAISE EXCEPTION 'Baseline divergente: vínculos órfãos nas tabelas operacionais';
    END IF;
END;
$integridade_baseline$;

-- 3. Sequências integer, sem copiar ou redefinir valores correntes.
DO $sequencias$
DECLARE
    v_tabela text;
    v_nome text;
    v_seq oid;
BEGIN
    FOREACH v_tabela IN ARRAY ARRAY[
        'parceiros_comerciais', 'representantes',
        'parceiro_representantes', 'parceiro_clientes', 'representantes_rt'
    ]
    LOOP
        v_nome := v_tabela || '_id_seq';
        v_seq := to_regclass(format('public.%I', v_nome));

        IF v_seq IS NULL THEN
            EXECUTE format(
                'CREATE SEQUENCE public.%I AS integer
                 INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647
                 START WITH 1 CACHE 1 NO CYCLE',
                v_nome
            );
        ELSE
            IF NOT EXISTS (
                SELECT 1
                FROM pg_class c
                JOIN pg_sequence s ON s.seqrelid = c.oid
                WHERE c.oid = v_seq
                  AND c.relkind = 'S'
                  AND s.seqtypid = 'integer'::regtype
                  AND s.seqstart = 1
                  AND s.seqincrement = 1
                  AND s.seqmin = 1
                  AND s.seqmax = 2147483647
                  AND s.seqcache = 1
                  AND NOT s.seqcycle
            ) THEN
                RAISE EXCEPTION 'Sequência incompatível: public.%', v_nome;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_depend d
                JOIN pg_attribute a
                  ON a.attrelid = d.refobjid
                 AND a.attnum = d.refobjsubid
                WHERE d.classid = 'pg_class'::regclass
                  AND d.refclassid = 'pg_class'::regclass
                  AND d.objid = v_seq
                  AND d.deptype = 'a'
                  AND d.refobjid = to_regclass(format('public.%I', v_tabela))
                  AND a.attname = 'id'
                  AND NOT a.attisdropped
            ) THEN
                RAISE EXCEPTION
                    'Sequência public.% já existe sem o vínculo esperado com %.id',
                    v_nome, v_tabela;
            END IF;
        END IF;
    END LOOP;
END;
$sequencias$;

-- 4. Colunas físicas reais.
-- obrigatoria=true significa NOT NULL apenas na criação da coluna.
-- Uma coluna existente divergente provoca erro; não é alterada.
-- NULL em padrao significa ausência de default no PostgreSQL.

DO $colunas$
DECLARE
    r record;
    v_tipo text;
    v_obrigatoria boolean;
    v_padrao text;
    v_identity text;
    v_generated text;
BEGIN
    FOR r IN
        SELECT *
        FROM (
            VALUES
            -- parceiros_comerciais
            (1, 'parceiros_comerciais', 'id', 'integer', true, $d$nextval('parceiros_comerciais_id_seq'::regclass)$d$),
            (2, 'parceiros_comerciais', 'empresa_id', 'integer', true, NULL),
            (3, 'parceiros_comerciais', 'nome', 'character varying(255)', true, NULL),
            (4, 'parceiros_comerciais', 'documento', 'character varying(30)', false, NULL),
            (5, 'parceiros_comerciais', 'email', 'character varying(255)', false, NULL),
            (6, 'parceiros_comerciais', 'telefone', 'character varying(50)', false, NULL),
            (7, 'parceiros_comerciais', 'percentual_padrao', 'numeric(8,4)', true, '0'),
            (8, 'parceiros_comerciais', 'ativo', 'boolean', true, 'true'),
            (9, 'parceiros_comerciais', 'observacao', 'text', false, NULL),
            (10, 'parceiros_comerciais', 'criado_em', 'timestamp without time zone', true, 'now()'),
            (11, 'parceiros_comerciais', 'atualizado_em', 'timestamp without time zone', false, NULL),

            -- representantes
            (1, 'representantes', 'id', 'integer', true, $d$nextval('representantes_id_seq'::regclass)$d$),
            (2, 'representantes', 'empresa_id', 'integer', true, NULL),
            (3, 'representantes', 'parceiro_id', 'integer', false, NULL),
            (4, 'representantes', 'nome', 'character varying(255)', true, NULL),
            (5, 'representantes', 'documento', 'character varying(30)', false, NULL),
            (6, 'representantes', 'email', 'character varying(255)', false, NULL),
            (7, 'representantes', 'telefone', 'character varying(50)', false, NULL),
            (8, 'representantes', 'tipo_rt_padrao', 'character varying(20)', true, $d$'PERCENTUAL'::character varying$d$),
            (9, 'representantes', 'percentual_rt_padrao', 'numeric(8,4)', true, '0'),
            (10, 'representantes', 'valor_rt_padrao', 'numeric(14,2)', true, '0'),
            (11, 'representantes', 'ativo', 'boolean', true, 'true'),
            (12, 'representantes', 'observacao', 'text', false, NULL),
            (13, 'representantes', 'criado_em', 'timestamp without time zone', true, 'now()'),
            (14, 'representantes', 'atualizado_em', 'timestamp without time zone', false, NULL),

            -- parceiro_representantes
            (1, 'parceiro_representantes', 'id', 'integer', true, $d$nextval('parceiro_representantes_id_seq'::regclass)$d$),
            (2, 'parceiro_representantes', 'empresa_id', 'integer', true, NULL),
            (3, 'parceiro_representantes', 'parceiro_id', 'integer', true, NULL),
            (4, 'parceiro_representantes', 'nome', 'character varying(255)', true, NULL),
            (5, 'parceiro_representantes', 'documento', 'character varying(50)', false, NULL),
            (6, 'parceiro_representantes', 'email', 'character varying(255)', false, NULL),
            (7, 'parceiro_representantes', 'telefone', 'character varying(100)', false, NULL),
            (8, 'parceiro_representantes', 'endereco', 'text', false, NULL),
            (9, 'parceiro_representantes', 'ativo', 'boolean', true, 'true'),
            (10, 'parceiro_representantes', 'criado_em', 'timestamp without time zone', true, 'now()'),
            (11, 'parceiro_representantes', 'atualizado_em', 'timestamp without time zone', false, NULL),

            -- parceiro_clientes
            (1, 'parceiro_clientes', 'id', 'integer', true, $d$nextval('parceiro_clientes_id_seq'::regclass)$d$),
            (2, 'parceiro_clientes', 'empresa_id', 'integer', true, NULL),
            (3, 'parceiro_clientes', 'parceiro_id', 'integer', true, NULL),
            (4, 'parceiro_clientes', 'representante_parceiro_id', 'integer', false, NULL),
            (5, 'parceiro_clientes', 'nome', 'character varying(255)', true, NULL),
            (6, 'parceiro_clientes', 'documento', 'character varying(50)', false, NULL),
            (7, 'parceiro_clientes', 'email', 'character varying(255)', false, NULL),
            (8, 'parceiro_clientes', 'telefone', 'character varying(100)', false, NULL),
            (9, 'parceiro_clientes', 'endereco', 'text', false, NULL),
            (10, 'parceiro_clientes', 'cadastro_completo', 'boolean', true, 'false'),
            (11, 'parceiro_clientes', 'ativo', 'boolean', true, 'true'),
            (12, 'parceiro_clientes', 'criado_em', 'timestamp without time zone', true, 'now()'),
            (13, 'parceiro_clientes', 'atualizado_em', 'timestamp without time zone', false, NULL),

            -- representantes_rt
            (1, 'representantes_rt', 'id', 'integer', true, $d$nextval('representantes_rt_id_seq'::regclass)$d$),
            (2, 'representantes_rt', 'empresa_id', 'integer', true, NULL),
            (3, 'representantes_rt', 'pedido_id', 'integer', true, NULL),
            (4, 'representantes_rt', 'representante_id', 'integer', true, NULL),
            (5, 'representantes_rt', 'parceiro_id', 'integer', false, NULL),
            (6, 'representantes_rt', 'competencia', 'date', true, NULL),
            (7, 'representantes_rt', 'vencimento', 'date', false, NULL),
            (8, 'representantes_rt', 'base_calculo', 'numeric(14,2)', true, '0'),
            (9, 'representantes_rt', 'tipo_calculo', 'character varying(20)', true, NULL),
            (10, 'representantes_rt', 'percentual', 'numeric(8,4)', true, '0'),
            (11, 'representantes_rt', 'valor_fixo', 'numeric(14,2)', true, '0'),
            (12, 'representantes_rt', 'valor_rt', 'numeric(14,2)', true, '0'),
            (13, 'representantes_rt', 'status', 'character varying(20)', true, $d$'PENDENTE'::character varying$d$),
            (14, 'representantes_rt', 'financeiro_id', 'integer', false, NULL),
            (15, 'representantes_rt', 'pago_em', 'date', false, NULL),
            (16, 'representantes_rt', 'observacao', 'text', false, NULL),
            (17, 'representantes_rt', 'criado_em', 'timestamp without time zone', true, 'now()'),
            (18, 'representantes_rt', 'atualizado_em', 'timestamp without time zone', false, NULL),

            -- clientes: somente os dois vínculos
            (1, 'clientes', 'parceiro_id', 'integer', false, NULL),
            (2, 'clientes', 'representante_id', 'integer', false, NULL),

            -- orcamentos: somente as evoluções desta fase
            (2, 'orcamentos', 'parceiro_id', 'integer', false, NULL),
            (3, 'orcamentos', 'representante_id', 'integer', false, NULL),
            (4, 'orcamentos', 'percentual_parceiro', 'numeric(8,4)', true, '0'),
            (5, 'orcamentos', 'incluir_rt', 'boolean', true, 'false'),
            (6, 'orcamentos', 'tipo_rt', 'character varying(20)', false, NULL),
            (7, 'orcamentos', 'percentual_rt', 'numeric(8,4)', true, '0'),
            (8, 'orcamentos', 'valor_rt', 'numeric(14,2)', true, '0'),
            (9, 'orcamentos', 'incluir_taxa_bancaria', 'boolean', true, 'false'),
            (10, 'orcamentos', 'taxa_bancaria_percentual', 'numeric(8,4)', true, '0'),
            (11, 'orcamentos', 'valor_parceiro', 'numeric(14,2)', true, '0'),
            (12, 'orcamentos', 'base_protegida', 'numeric(14,2)', true, '0'),
            (13, 'orcamentos', 'valor_taxa_bancaria', 'numeric(14,2)', true, '0'),
            (14, 'orcamentos', 'total_cliente_final', 'numeric(14,2)', true, '0'),
            (15, 'orcamentos', 'vendedor_id', 'integer', false, NULL),
            (16, 'orcamentos', 'cliente_final_nome', 'text', false, NULL),
            (17, 'orcamentos', 'cliente_final_documento', 'text', false, NULL),
            (18, 'orcamentos', 'cliente_final_telefone', 'text', false, NULL),
            (19, 'orcamentos', 'cliente_final_email', 'text', false, NULL),
            (20, 'orcamentos', 'cliente_final_endereco', 'text', false, NULL),

            -- observacao_interna em orcamentos e dados_tecnicos em
            -- orcamentos_itens já existem: não entram no catálogo de adição.

            -- pedidos: composição permanece nullable e sem defaults
            (1, 'pedidos', 'orcamento_id', 'integer', false, NULL),
            (2, 'pedidos', 'perfil_comercial', 'character varying(30)', true, $d$'VAREJO'::character varying$d$),
            (3, 'pedidos', 'data_venda', 'date', false, NULL),
            (4, 'pedidos', 'canal_venda', 'character varying(100)', false, NULL),
            (5, 'pedidos', 'observacao_interna', 'text', false, NULL),
            (6, 'pedidos', 'vendedor_id', 'integer', false, NULL),
            (7, 'pedidos', 'parceiro_id', 'integer', false, NULL),
            (8, 'pedidos', 'representante_id', 'integer', false, NULL),
            (9, 'pedidos', 'cliente_final_nome', 'text', false, NULL),
            (10, 'pedidos', 'cliente_final_documento', 'text', false, NULL),
            (11, 'pedidos', 'cliente_final_telefone', 'text', false, NULL),
            (12, 'pedidos', 'cliente_final_email', 'text', false, NULL),
            (13, 'pedidos', 'cliente_final_endereco', 'text', false, NULL),
            (14, 'pedidos', 'percentual_parceiro', 'numeric(8,4)', false, NULL),
            (15, 'pedidos', 'incluir_rt', 'boolean', false, NULL),
            (16, 'pedidos', 'tipo_rt', 'character varying(20)', false, NULL),
            (17, 'pedidos', 'percentual_rt', 'numeric(8,4)', false, NULL),
            (18, 'pedidos', 'valor_rt', 'numeric(14,2)', false, NULL),
            (19, 'pedidos', 'incluir_taxa_bancaria', 'boolean', false, NULL),
            (20, 'pedidos', 'taxa_bancaria_percentual', 'numeric(8,4)', false, NULL),
            (21, 'pedidos', 'valor_parceiro', 'numeric(14,2)', false, NULL),
            (22, 'pedidos', 'valor_taxa_bancaria', 'numeric(14,2)', false, NULL),
            (23, 'pedidos', 'total_cliente_final', 'numeric(14,2)', false, NULL),

            -- pedidos_itens: tipos físicos locais
            (1, 'pedidos_itens', 'tipo_item', 'character varying(30)', true, $d$'PRODUTO'::character varying$d$),
            (2, 'pedidos_itens', 'descricao', 'text', false, NULL),
            (3, 'pedidos_itens', 'codigo_interno', 'character varying', false, NULL),
            (4, 'pedidos_itens', 'grupo_tecnico', 'character varying', false, NULL),
            (5, 'pedidos_itens', 'modelo_tecnico', 'character varying', false, NULL),
            (6, 'pedidos_itens', 'unidade', 'character varying', false, NULL),
            (7, 'pedidos_itens', 'largura', 'numeric(12,3)', true, '0'),
            (8, 'pedidos_itens', 'altura', 'numeric(12,3)', true, '0'),
            (9, 'pedidos_itens', 'area', 'numeric(14,4)', true, '0'),
            (10, 'pedidos_itens', 'observacao_item', 'text', false, NULL),
            (11, 'pedidos_itens', 'material', 'character varying', false, NULL),
            (12, 'pedidos_itens', 'cor', 'character varying', false, NULL),
            (13, 'pedidos_itens', 'acionamento', 'character varying', false, NULL),
            (14, 'pedidos_itens', 'lado_comando', 'character varying', false, NULL),
            (15, 'pedidos_itens', 'calculo_producao_status', 'character varying', false, NULL),
            (16, 'pedidos_itens', 'dados_tecnicos', 'jsonb', false, NULL)
        ) AS especificacao(ordem, tabela, coluna, tipo, obrigatoria, padrao)
        ORDER BY tabela, ordem
    LOOP
        SELECT
            format_type(a.atttypid, a.atttypmod),
            a.attnotnull,
            pg_get_expr(d.adbin, d.adrelid),
            a.attidentity::text,
            a.attgenerated::text
        INTO
            v_tipo, v_obrigatoria, v_padrao, v_identity, v_generated
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d
          ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = to_regclass(format('public.%I', r.tabela))
          AND a.attname = r.coluna
          AND a.attnum > 0
          AND NOT a.attisdropped;

        IF FOUND THEN
            IF v_tipo IS DISTINCT FROM r.tipo
               OR v_obrigatoria IS DISTINCT FROM r.obrigatoria
               OR v_padrao IS DISTINCT FROM r.padrao
               OR v_identity IS DISTINCT FROM ''
               OR v_generated IS DISTINCT FROM ''
            THEN
                RAISE EXCEPTION
                    'Coluna incompatível: %.%. Esperado tipo=%, NOT NULL=%, default=%. Atual tipo=%, NOT NULL=%, default=%, identity=%, generated=%',
                    r.tabela, r.coluna,
                    r.tipo, r.obrigatoria, r.padrao,
                    v_tipo, v_obrigatoria, v_padrao, v_identity, v_generated;
            END IF;
        ELSE
            EXECUTE format(
                'ALTER TABLE public.%I ADD COLUMN IF NOT EXISTS %I %s%s%s',
                r.tabela,
                r.coluna,
                r.tipo,
                CASE WHEN r.obrigatoria THEN ' NOT NULL' ELSE '' END,
                CASE
                    WHEN r.padrao IS NULL THEN ''
                    ELSE ' DEFAULT ' || r.padrao
                END
            );
        END IF;
    END LOOP;
END;
$colunas$;

-- 5. Ownership das sequências, após a criação das colunas id.
DO $ownership$
DECLARE
    v_tabela text;
BEGIN
    FOREACH v_tabela IN ARRAY ARRAY[
        'parceiros_comerciais', 'representantes',
        'parceiro_representantes', 'parceiro_clientes', 'representantes_rt'
    ]
    LOOP
        EXECUTE format(
            'ALTER SEQUENCE public.%I OWNED BY public.%I.id',
            v_tabela || '_id_seq', v_tabela
        );
    END LOOP;
END;
$ownership$;

-- 6. Constraints.
-- As definições esperadas são as extraídas do catálogo local.
-- A ordem garante PKs/UNIQUEs antes das FKs dependentes.

DO $constraints$
DECLARE
    r record;
    v_definicao text;
    v_validada boolean;
    v_deferrable boolean;
    v_deferred boolean;
    v_contype text;
    v_contype_esperado text;
    v_no_inherit boolean;
    v_expressao_check text;
    v_colunas_textuais text[];
    v_coluna_textual text;
    v_expr text;
    v_antes text;
    v_assinaturas text[];
    v_literais text[];
    v_literais_esperados text[];
    v_regex_literal text := $rx$'[A-Z_]+'$rx$;
    v_regex_array text;
    v_regex_atomo text;
    v_nivel integer;
    v_pos integer;
    v_envolve boolean;
BEGIN
    FOR r IN
        SELECT *
        FROM (
            VALUES
            (10, 'parceiros_comerciais', 'parceiros_comerciais_pkey',
                $d$PRIMARY KEY (id)$d$),
            (11, 'parceiros_comerciais', 'parceiros_comerciais_empresa_id_fkey',
                $d$FOREIGN KEY (empresa_id) REFERENCES empresas(id)$d$),
            (12, 'parceiros_comerciais', 'ck_parceiros_percentual_padrao',
                $d$CHECK (percentual_padrao >= 0::numeric AND percentual_padrao <= 100::numeric)$d$),

            (20, 'representantes', 'representantes_pkey',
                $d$PRIMARY KEY (id)$d$),
            (21, 'representantes', 'representantes_empresa_id_fkey',
                $d$FOREIGN KEY (empresa_id) REFERENCES empresas(id)$d$),
            (22, 'representantes', 'representantes_parceiro_id_fkey',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE SET NULL$d$),
            (23, 'representantes', 'ck_representantes_percentual_rt',
                $d$CHECK (percentual_rt_padrao >= 0::numeric AND percentual_rt_padrao <= 100::numeric)$d$),
            (24, 'representantes', 'ck_representantes_tipo_rt',
                $d$CHECK (tipo_rt_padrao::text = ANY (ARRAY['PERCENTUAL'::character varying, 'VALOR_FIXO'::character varying]::text[]))$d$),
            (25, 'representantes', 'ck_representantes_valor_rt',
                $d$CHECK (valor_rt_padrao >= 0::numeric)$d$),

            (30, 'parceiro_representantes', 'parceiro_representantes_pkey',
                $d$PRIMARY KEY (id)$d$),
            (31, 'parceiro_representantes', 'parceiro_representantes_empresa_id_fkey',
                $d$FOREIGN KEY (empresa_id) REFERENCES empresas(id)$d$),
            (32, 'parceiro_representantes', 'parceiro_representantes_parceiro_id_fkey',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE CASCADE$d$),
            (33, 'parceiro_representantes', 'uq_parceiro_representante_contexto',
                $d$UNIQUE (id, empresa_id, parceiro_id)$d$),

            (40, 'parceiro_clientes', 'parceiro_clientes_pkey',
                $d$PRIMARY KEY (id)$d$),
            (41, 'parceiro_clientes', 'parceiro_clientes_empresa_id_fkey',
                $d$FOREIGN KEY (empresa_id) REFERENCES empresas(id)$d$),
            (42, 'parceiro_clientes', 'parceiro_clientes_parceiro_id_fkey',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE CASCADE$d$),
            (43, 'parceiro_clientes', 'fk_parceiro_cliente_representante_contexto',
                $d$FOREIGN KEY (representante_parceiro_id, empresa_id, parceiro_id) REFERENCES parceiro_representantes(id, empresa_id, parceiro_id) ON DELETE SET NULL$d$),

            (50, 'representantes_rt', 'representantes_rt_pkey',
                $d$PRIMARY KEY (id)$d$),
            (51, 'representantes_rt', 'representantes_rt_empresa_id_fkey',
                $d$FOREIGN KEY (empresa_id) REFERENCES empresas(id)$d$),
            (52, 'representantes_rt', 'representantes_rt_pedido_id_fkey',
                $d$FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE RESTRICT$d$),
            (53, 'representantes_rt', 'representantes_rt_representante_id_fkey',
                $d$FOREIGN KEY (representante_id) REFERENCES representantes(id) ON DELETE RESTRICT$d$),
            (54, 'representantes_rt', 'representantes_rt_parceiro_id_fkey',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE SET NULL$d$),
            (55, 'representantes_rt', 'representantes_rt_financeiro_id_fkey',
                $d$FOREIGN KEY (financeiro_id) REFERENCES financeiro(id) ON DELETE SET NULL$d$),
            (56, 'representantes_rt', 'ck_representantes_rt_percentual',
                $d$CHECK (percentual >= 0::numeric AND percentual <= 100::numeric)$d$),
            (57, 'representantes_rt', 'ck_representantes_rt_tipo',
                $d$CHECK (tipo_calculo::text = ANY (ARRAY['PERCENTUAL'::character varying, 'VALOR_FIXO'::character varying]::text[]))$d$),
            (58, 'representantes_rt', 'ck_representantes_rt_status',
                $d$CHECK (status::text = ANY (ARRAY['PENDENTE'::character varying, 'AGUARDANDO_PAGAMENTO'::character varying, 'PAGO'::character varying, 'CANCELADO'::character varying]::text[]))$d$),
            (59, 'representantes_rt', 'ck_representantes_rt_valores',
                $d$CHECK (base_calculo >= 0::numeric AND valor_fixo >= 0::numeric AND valor_rt >= 0::numeric)$d$),

            (60, 'clientes', 'fk_clientes_parceiro',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE SET NULL$d$),
            (61, 'clientes', 'fk_clientes_representante',
                $d$FOREIGN KEY (representante_id) REFERENCES representantes(id) ON DELETE SET NULL$d$),
            (62, 'clientes', 'ck_clientes_vinculo_comercial_unico',
                $d$CHECK (parceiro_id IS NULL OR representante_id IS NULL)$d$),

            (70, 'orcamentos', 'fk_orcamentos_parceiro',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE SET NULL$d$),
            (71, 'orcamentos', 'fk_orcamentos_representante',
                $d$FOREIGN KEY (representante_id) REFERENCES representantes(id) ON DELETE SET NULL$d$),
            (72, 'orcamentos', 'fk_orcamentos_vendedor',
                $d$FOREIGN KEY (vendedor_id) REFERENCES funcionarios(id) ON DELETE SET NULL$d$),
            (73, 'orcamentos', 'ck_orcamentos_percentual_parceiro',
                $d$CHECK (percentual_parceiro >= 0::numeric AND percentual_parceiro <= 1000::numeric)$d$),
            (74, 'orcamentos', 'ck_orcamentos_perfil_comercial',
                $d$CHECK (perfil_comercial::text = ANY (ARRAY['DECORADOR'::character varying, 'VAREJO'::character varying, 'CONSUMIDOR_FINAL'::character varying]::text[]))$d$),
            (75, 'orcamentos', 'ck_orcamentos_taxa_bancaria',
                $d$CHECK (taxa_bancaria_percentual >= 0::numeric AND taxa_bancaria_percentual < 100::numeric)$d$),
            (76, 'orcamentos', 'ck_orcamentos_tipo_rt',
                $d$CHECK (tipo_rt IS NULL OR (tipo_rt::text = ANY (ARRAY['VALOR_FIXO'::character varying, 'PERCENTUAL'::character varying]::text[])))$d$),

            (80, 'pedidos', 'fk_pedidos_orcamento',
                $d$FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE SET NULL$d$),
            (81, 'pedidos', 'pedidos_vendedor_id_fkey',
                $d$FOREIGN KEY (vendedor_id) REFERENCES funcionarios(id) ON DELETE SET NULL$d$),
            (82, 'pedidos', 'pedidos_parceiro_id_fkey',
                $d$FOREIGN KEY (parceiro_id) REFERENCES parceiros_comerciais(id) ON DELETE SET NULL$d$),
            (83, 'pedidos', 'pedidos_representante_id_fkey',
                $d$FOREIGN KEY (representante_id) REFERENCES representantes(id) ON DELETE SET NULL$d$)
        ) AS especificacao(ordem, tabela, nome, definicao)
        ORDER BY ordem
    LOOP
        v_contype_esperado := CASE
            WHEN r.definicao LIKE 'CHECK %' THEN 'c'
            WHEN r.definicao LIKE 'FOREIGN KEY %' THEN 'f'
            WHEN r.definicao LIKE 'PRIMARY KEY %' THEN 'p'
            WHEN r.definicao LIKE 'UNIQUE %' THEN 'u'
        END;

        SELECT
            pg_get_constraintdef(c.oid, true),
            c.convalidated,
            c.condeferrable,
            c.condeferred,
            c.contype::text,
            c.connoinherit,
            pg_get_expr(c.conbin, c.conrelid, true),
            ARRAY(
                SELECT a.attname::text
                FROM pg_attribute a
                WHERE a.attrelid = c.conrelid
                  AND a.attnum = ANY(c.conkey)
                  AND NOT a.attisdropped
                  AND a.atttypid IN ('text'::regtype, 'character varying'::regtype)
                  AND a.attname ~ '^[a-z_][a-z_0-9]*$'
                ORDER BY a.attnum
            )
        INTO
            v_definicao, v_validada, v_deferrable, v_deferred,
            v_contype, v_no_inherit, v_expressao_check, v_colunas_textuais
        FROM pg_constraint c
        WHERE c.conrelid = to_regclass(format('public.%I', r.tabela))
          AND c.conname = r.nome;

        IF FOUND THEN
            IF v_contype_esperado IS NULL
               OR v_contype IS DISTINCT FROM v_contype_esperado
               OR NOT v_validada
               OR v_deferrable
               OR v_deferred
               OR (v_contype = 'c' AND v_no_inherit)
            THEN
                RAISE EXCEPTION
                    'Metadados de constraint incompatíveis: %.%. Tipo esperado=%, atual=%, validada=%, deferrable=%, deferred=%, NO INHERIT=%',
                    r.tabela, r.nome, v_contype_esperado, v_contype,
                    v_validada, v_deferrable, v_deferred, v_no_inherit;
            END IF;

            IF v_contype = 'c' THEN
                -- Assinatura restrita aos CHECKs desta migration, sem avaliar dados.
                -- Literais, operadores, limites e agrupamentos lógicos são preservados.
                -- Só casts sem typmod, em átomos compatíveis, podem ser removidos.
                SELECT coalesce(array_agg(m[1] ORDER BY ordem), ARRAY[]::text[])
                INTO v_literais_esperados
                FROM regexp_matches(
                    r.definicao, $rx$'(?:[^']|'')*'$rx$, 'g'
                ) WITH ORDINALITY AS literais(m, ordem);

                v_regex_array := $rx$ARRAY \[ $rx$ || v_regex_literal
                    || '(?: , ' || v_regex_literal || $rx$)* \]$rx$;
                v_regex_atomo := '(?:[a-z_][a-z_0-9]*|' || v_regex_literal
                    || '|[0-9]+)(?: :: (?:text|character varying|numeric))*';
                v_assinaturas := ARRAY[]::text[];

                FOREACH v_expr IN ARRAY ARRAY[
                    regexp_replace(r.definicao, '^CHECK[[:space:]]*', ''),
                    v_expressao_check
                ]
                LOOP
                    SELECT coalesce(array_agg(m[1] ORDER BY ordem), ARRAY[]::text[])
                    INTO v_literais
                    FROM regexp_matches(
                        v_expr, $rx$'(?:[^']|'')*'$rx$, 'g'
                    ) WITH ORDINALITY AS literais(m, ordem);

                    IF v_literais IS DISTINCT FROM v_literais_esperados
                       OR EXISTS (
                           SELECT 1 FROM unnest(v_literais) AS l(valor)
                           WHERE valor !~ ('^' || v_regex_literal || '$')
                       )
                       OR position('"' IN v_expr) > 0
                       OR EXISTS (
                           SELECT 1
                           FROM regexp_matches(
                               v_expr,
                               $rx$([a-zA-Z_][a-zA-Z_0-9]*)[[:space:]]*\($rx$,
                               'g'
                           ) AS chamadas(m)
                           WHERE m[1] NOT IN ('ANY', 'AND', 'OR')
                       )
                    THEN
                        RAISE EXCEPTION
                            'CHECK incompatível ou fora das formas suportadas: %.%. Atual: %',
                            r.tabela, r.nome, v_definicao;
                    END IF;

                    -- Tokenizar mantém "character varying" distinto de um tipo
                    -- chamado charactervarying; não concatena identificadores.
                    SELECT string_agg(m[1], ' ' ORDER BY ordem)
                    INTO v_expr
                    FROM regexp_matches(
                        v_expr,
                        $rx$'(?:[^']|'')*'|[a-zA-Z_][a-zA-Z_0-9]*|::|>=|<=|<>|!=|[0-9]+|[^[:space:]]$rx$,
                        'g'
                    ) WITH ORDINALITY AS tokens(m, ordem);

                    LOOP
                        v_antes := v_expr;

                        -- Não remover os parênteses obrigatórios de ANY(...).
                        v_expr := regexp_replace(
                            v_expr, $rx$(?<!ANY )\( ($rx$ || v_regex_atomo || $rx$) \)$rx$,
                            $rx$\1$rx$, 'g'
                        );
                        v_expr := regexp_replace(
                            v_expr, $rx$(?<!ANY )\( ($rx$ || v_regex_array || $rx$) \)$rx$,
                            $rx$\1$rx$, 'g'
                        );

                        FOREACH v_coluna_textual IN ARRAY v_colunas_textuais
                        LOOP
                            v_expr := regexp_replace(
                                v_expr,
                                '(^| )(' || v_coluna_textual
                                    || $rx$) :: (?:text|character varying)(?= |$)(?! [\[(])$rx$,
                                $rx$\1\2$rx$, 'g'
                            );
                        END LOOP;

                        v_expr := regexp_replace(
                            v_expr,
                            '(' || v_regex_literal
                                || $rx$) :: (?:text|character varying)(?= |$)(?! [\[(])$rx$,
                            $rx$\1$rx$, 'g'
                        );
                        v_expr := regexp_replace(
                            v_expr,
                            $rx$(^| )([0-9]+) :: numeric(?= |$)(?! [\[(])$rx$,
                            $rx$\1\2$rx$, 'g'
                        );
                        v_expr := regexp_replace(
                            v_expr,
                            '(' || v_regex_array
                                || $rx$) :: (?:text|character varying) \[ \](?! \[)$rx$,
                            $rx$\1$rx$, 'g'
                        );

                        -- Retirar wrappers apenas de predicados atômicos.
                        v_expr := regexp_replace(
                            v_expr,
                            $rx$\( ([a-z_][a-z_0-9]* (?:>=|<=|<|=) [0-9]+) \)$rx$,
                            $rx$\1$rx$, 'g'
                        );
                        v_expr := regexp_replace(
                            v_expr, $rx$\( ([a-z_][a-z_0-9]* IS NULL) \)$rx$,
                            $rx$\1$rx$, 'g'
                        );
                        v_expr := regexp_replace(
                            v_expr,
                            $rx$\( ([a-z_][a-z_0-9]* = ANY \( $rx$
                                || v_regex_array || $rx$ \)) \)$rx$,
                            $rx$\1$rx$, 'g'
                        );

                        -- Um wrapper externo só sai se envolver a expressão inteira.
                        WHILE left(v_expr, 1) = '(' AND right(v_expr, 1) = ')'
                        LOOP
                            v_nivel := 0;
                            v_envolve := true;
                            FOR v_pos IN 1..length(v_expr)
                            LOOP
                                IF substr(v_expr, v_pos, 1) = '(' THEN
                                    v_nivel := v_nivel + 1;
                                ELSIF substr(v_expr, v_pos, 1) = ')' THEN
                                    v_nivel := v_nivel - 1;
                                END IF;
                                IF v_nivel = 0 AND v_pos < length(v_expr) THEN
                                    v_envolve := false;
                                    EXIT;
                                END IF;
                            END LOOP;
                            EXIT WHEN NOT v_envolve OR v_nivel <> 0;
                            v_expr := btrim(substr(v_expr, 2, length(v_expr) - 2));
                        END LOOP;

                        EXIT WHEN v_expr IS NOT DISTINCT FROM v_antes;
                    END LOOP;
                    v_assinaturas := array_append(v_assinaturas, v_expr);
                END LOOP;

                IF v_assinaturas[1] IS DISTINCT FROM v_assinaturas[2] THEN
                    RAISE EXCEPTION
                        'CHECK incompatível: %.%. Esperada: %. Atual: %',
                        r.tabela, r.nome, r.definicao, v_definicao;
                END IF;
            ELSIF v_definicao IS DISTINCT FROM r.definicao THEN
                -- FKs/PK/UNIQUE mantêm a conferência integral da definição.
                RAISE EXCEPTION
                    'Constraint incompatível: %.%. Esperada: %. Atual: %',
                    r.tabela, r.nome, r.definicao, v_definicao;
            END IF;
        ELSE
            EXECUTE format(
                'ALTER TABLE public.%I ADD CONSTRAINT %I %s',
                r.tabela, r.nome, r.definicao
            );
        END IF;
    END LOOP;
END;
$constraints$;

-- 7. Índices.
-- Índices de PK/UNIQUE das tabelas novas já foram criados pelas constraints.
-- Os nomes e definições abaixo são os do catálogo local.

DO $indices$
DECLARE
    r record;
    v_tabela text;
    v_definicao text;
    v_valido boolean;
    v_pronto boolean;
BEGIN
    FOR r IN
        SELECT *
        FROM (
            VALUES
            ('parceiros_comerciais', 'idx_parceiros_empresa',
             'CREATE INDEX idx_parceiros_empresa ON public.parceiros_comerciais USING btree (empresa_id)'),
            ('parceiros_comerciais', 'idx_parceiros_ativo',
             'CREATE INDEX idx_parceiros_ativo ON public.parceiros_comerciais USING btree (empresa_id, ativo)'),

            ('representantes', 'idx_representantes_empresa',
             'CREATE INDEX idx_representantes_empresa ON public.representantes USING btree (empresa_id)'),
            ('representantes', 'idx_representantes_ativo',
             'CREATE INDEX idx_representantes_ativo ON public.representantes USING btree (empresa_id, ativo)'),
            ('representantes', 'idx_representantes_parceiro',
             'CREATE INDEX idx_representantes_parceiro ON public.representantes USING btree (parceiro_id)'),

            ('parceiro_representantes', 'idx_parceiro_representantes_empresa_parceiro',
             'CREATE INDEX idx_parceiro_representantes_empresa_parceiro ON public.parceiro_representantes USING btree (empresa_id, parceiro_id)'),
            ('parceiro_representantes', 'idx_parceiro_representantes_nome',
             'CREATE INDEX idx_parceiro_representantes_nome ON public.parceiro_representantes USING btree (empresa_id, parceiro_id, nome)'),

            ('parceiro_clientes', 'idx_parceiro_clientes_empresa_parceiro',
             'CREATE INDEX idx_parceiro_clientes_empresa_parceiro ON public.parceiro_clientes USING btree (empresa_id, parceiro_id)'),
            ('parceiro_clientes', 'idx_parceiro_clientes_nome',
             'CREATE INDEX idx_parceiro_clientes_nome ON public.parceiro_clientes USING btree (empresa_id, parceiro_id, nome)'),
            ('parceiro_clientes', 'idx_parceiro_clientes_representante',
             'CREATE INDEX idx_parceiro_clientes_representante ON public.parceiro_clientes USING btree (empresa_id, parceiro_id, representante_parceiro_id)'),

            ('representantes_rt', 'idx_representantes_rt_empresa',
             'CREATE INDEX idx_representantes_rt_empresa ON public.representantes_rt USING btree (empresa_id)'),
            ('representantes_rt', 'idx_representantes_rt_competencia',
             'CREATE INDEX idx_representantes_rt_competencia ON public.representantes_rt USING btree (empresa_id, competencia)'),
            ('representantes_rt', 'idx_representantes_rt_status',
             'CREATE INDEX idx_representantes_rt_status ON public.representantes_rt USING btree (empresa_id, status)'),
            ('representantes_rt', 'idx_representantes_rt_pedido',
             'CREATE INDEX idx_representantes_rt_pedido ON public.representantes_rt USING btree (pedido_id)'),
            ('representantes_rt', 'idx_representantes_rt_representante',
             'CREATE INDEX idx_representantes_rt_representante ON public.representantes_rt USING btree (representante_id)'),
            ('representantes_rt', 'idx_representantes_rt_financeiro',
             'CREATE INDEX idx_representantes_rt_financeiro ON public.representantes_rt USING btree (financeiro_id)'),
            ('representantes_rt', 'uq_representante_rt_venda_ativa',
             $d$CREATE UNIQUE INDEX uq_representante_rt_venda_ativa ON public.representantes_rt USING btree (empresa_id, pedido_id, representante_id) WHERE ((status)::text <> 'CANCELADO'::text)$d$),

            ('clientes', 'ix_clientes_parceiro_id',
             'CREATE INDEX ix_clientes_parceiro_id ON public.clientes USING btree (parceiro_id)'),
            ('clientes', 'ix_clientes_representante_id',
             'CREATE INDEX ix_clientes_representante_id ON public.clientes USING btree (representante_id)'),

            ('orcamentos', 'idx_orcamentos_parceiro',
             'CREATE INDEX idx_orcamentos_parceiro ON public.orcamentos USING btree (empresa_id, parceiro_id)'),
            ('orcamentos', 'idx_orcamentos_representante',
             'CREATE INDEX idx_orcamentos_representante ON public.orcamentos USING btree (empresa_id, representante_id)'),
            ('orcamentos', 'ix_orcamentos_cliente_id',
             'CREATE INDEX ix_orcamentos_cliente_id ON public.orcamentos USING btree (cliente_id)'),
            ('orcamentos', 'ix_orcamentos_empresa_id',
             'CREATE INDEX ix_orcamentos_empresa_id ON public.orcamentos USING btree (empresa_id)'),

            ('pedidos', 'idx_pedidos_cliente',
             'CREATE INDEX idx_pedidos_cliente ON public.pedidos USING btree (cliente_id)'),
            ('pedidos', 'idx_pedidos_data_venda',
             'CREATE INDEX idx_pedidos_data_venda ON public.pedidos USING btree (data_venda)'),
            ('pedidos', 'idx_pedidos_empresa',
             'CREATE INDEX idx_pedidos_empresa ON public.pedidos USING btree (empresa_id)'),
            ('pedidos', 'idx_pedidos_orcamento',
             'CREATE INDEX idx_pedidos_orcamento ON public.pedidos USING btree (orcamento_id)'),
            ('pedidos', 'idx_pedidos_status',
             'CREATE INDEX idx_pedidos_status ON public.pedidos USING btree (status)'),
            ('pedidos', 'ix_pedidos_empresa_id',
             'CREATE INDEX ix_pedidos_empresa_id ON public.pedidos USING btree (empresa_id)'),
            ('pedidos', 'uq_pedidos_orcamento',
             'CREATE UNIQUE INDEX uq_pedidos_orcamento ON public.pedidos USING btree (orcamento_id) WHERE (orcamento_id IS NOT NULL)'),

            ('pedidos_itens', 'idx_pedidos_itens_pedido',
             'CREATE INDEX idx_pedidos_itens_pedido ON public.pedidos_itens USING btree (pedido_id)'),
            ('pedidos_itens', 'idx_pedidos_itens_produto',
             'CREATE INDEX idx_pedidos_itens_produto ON public.pedidos_itens USING btree (produto_id)')
        ) AS especificacao(tabela, nome, definicao)
        ORDER BY tabela, nome
    LOOP
        SELECT
            p.tablename,
            p.indexdef,
            i.indisvalid,
            i.indisready
        INTO
            v_tabela, v_definicao, v_valido, v_pronto
        FROM pg_indexes p
        JOIN pg_namespace n ON n.nspname = p.schemaname
        JOIN pg_class c
          ON c.relnamespace = n.oid AND c.relname = p.indexname
        JOIN pg_index i ON i.indexrelid = c.oid
        WHERE p.schemaname = 'public'
          AND p.indexname = r.nome;

        IF FOUND THEN
            IF v_tabela IS DISTINCT FROM r.tabela
               OR v_definicao IS DISTINCT FROM r.definicao
               OR NOT v_valido
               OR NOT v_pronto
            THEN
                RAISE EXCEPTION
                    'Índice incompatível: %. Esperado: %. Atual: %',
                    r.nome, r.definicao, v_definicao;
            END IF;
        ELSE
            EXECUTE r.definicao;
        END IF;
    END LOOP;
END;
$indices$;

-- 8. Estrutura final das cinco tabelas novas.
-- Detecta também objetos adicionais incompatíveis com a reprodução prevista.
-- NOT NULL interno do PostgreSQL 18 não entra na contagem de constraints.

DO $estrutura_final$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT *
        FROM (
            VALUES
            ('parceiros_comerciais', 11, 3, 3),
            ('representantes', 14, 6, 4),
            ('parceiro_representantes', 11, 4, 4),
            ('parceiro_clientes', 13, 4, 4),
            ('representantes_rt', 18, 10, 8)
        ) AS esperado(tabela, colunas, constraints, indices)
    LOOP
        IF (
            SELECT count(*)
            FROM pg_attribute
            WHERE attrelid = to_regclass(format('public.%I', r.tabela))
              AND attnum > 0 AND NOT attisdropped
        ) <> r.colunas THEN
            RAISE EXCEPTION 'Quantidade inesperada de colunas em %', r.tabela;
        END IF;

        IF (
            SELECT count(*)
            FROM pg_constraint
            WHERE conrelid = to_regclass(format('public.%I', r.tabela))
              AND contype IN ('p', 'f', 'u', 'c', 'x')
        ) <> r.constraints THEN
            RAISE EXCEPTION 'Quantidade inesperada de constraints em %', r.tabela;
        END IF;

        IF (
            SELECT count(*)
            FROM pg_index
            WHERE indrelid = to_regclass(format('public.%I', r.tabela))
        ) <> r.indices THEN
            RAISE EXCEPTION 'Quantidade inesperada de índices em %', r.tabela;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgrelid = to_regclass(format('public.%I', r.tabela))
              AND NOT tgisinternal
        ) THEN
            RAISE EXCEPTION 'Trigger de usuário inesperado em %', r.tabela;
        END IF;
    END LOOP;
END;
$estrutura_final$;

-- 9. Conferência explícita das 62 colunas da Fase 1, inclusive as duas existentes.
-- Tipos/precisões esperados são os da referência; nenhuma precisão é alterada.
-- NOT NULL/default das 60 adições são conferidos pelo catálogo da seção 4.
-- NOT NULL/default das duas pré-existentes permanecem como estão no destino.
DO $fase1_final$
DECLARE
    r record;
    v_tipo text;
    v_total integer := 0;
BEGIN
    FOR r IN
        SELECT *
        FROM (
            VALUES
            ('clientes', 'parceiro_id', 'integer'),
            ('clientes', 'representante_id', 'integer'),
            ('orcamentos', 'observacao_interna', 'text'),
            ('orcamentos', 'parceiro_id', 'integer'),
            ('orcamentos', 'representante_id', 'integer'),
            ('orcamentos', 'percentual_parceiro', 'numeric(8,4)'),
            ('orcamentos', 'incluir_rt', 'boolean'),
            ('orcamentos', 'tipo_rt', 'character varying(20)'),
            ('orcamentos', 'percentual_rt', 'numeric(8,4)'),
            ('orcamentos', 'valor_rt', 'numeric(14,2)'),
            ('orcamentos', 'incluir_taxa_bancaria', 'boolean'),
            ('orcamentos', 'taxa_bancaria_percentual', 'numeric(8,4)'),
            ('orcamentos', 'valor_parceiro', 'numeric(14,2)'),
            ('orcamentos', 'base_protegida', 'numeric(14,2)'),
            ('orcamentos', 'valor_taxa_bancaria', 'numeric(14,2)'),
            ('orcamentos', 'total_cliente_final', 'numeric(14,2)'),
            ('orcamentos', 'vendedor_id', 'integer'),
            ('orcamentos', 'cliente_final_nome', 'text'),
            ('orcamentos', 'cliente_final_documento', 'text'),
            ('orcamentos', 'cliente_final_telefone', 'text'),
            ('orcamentos', 'cliente_final_email', 'text'),
            ('orcamentos', 'cliente_final_endereco', 'text'),
            ('orcamentos_itens', 'dados_tecnicos', 'jsonb'),
            ('pedidos', 'orcamento_id', 'integer'),
            ('pedidos', 'perfil_comercial', 'character varying(30)'),
            ('pedidos', 'data_venda', 'date'),
            ('pedidos', 'canal_venda', 'character varying(100)'),
            ('pedidos', 'observacao_interna', 'text'),
            ('pedidos', 'vendedor_id', 'integer'),
            ('pedidos', 'parceiro_id', 'integer'),
            ('pedidos', 'representante_id', 'integer'),
            ('pedidos', 'cliente_final_nome', 'text'),
            ('pedidos', 'cliente_final_documento', 'text'),
            ('pedidos', 'cliente_final_telefone', 'text'),
            ('pedidos', 'cliente_final_email', 'text'),
            ('pedidos', 'cliente_final_endereco', 'text'),
            ('pedidos', 'percentual_parceiro', 'numeric(8,4)'),
            ('pedidos', 'incluir_rt', 'boolean'),
            ('pedidos', 'tipo_rt', 'character varying(20)'),
            ('pedidos', 'percentual_rt', 'numeric(8,4)'),
            ('pedidos', 'valor_rt', 'numeric(14,2)'),
            ('pedidos', 'incluir_taxa_bancaria', 'boolean'),
            ('pedidos', 'taxa_bancaria_percentual', 'numeric(8,4)'),
            ('pedidos', 'valor_parceiro', 'numeric(14,2)'),
            ('pedidos', 'valor_taxa_bancaria', 'numeric(14,2)'),
            ('pedidos', 'total_cliente_final', 'numeric(14,2)'),
            ('pedidos_itens', 'tipo_item', 'character varying(30)'),
            ('pedidos_itens', 'descricao', 'text'),
            ('pedidos_itens', 'codigo_interno', 'character varying'),
            ('pedidos_itens', 'grupo_tecnico', 'character varying'),
            ('pedidos_itens', 'modelo_tecnico', 'character varying'),
            ('pedidos_itens', 'unidade', 'character varying'),
            ('pedidos_itens', 'largura', 'numeric(12,3)'),
            ('pedidos_itens', 'altura', 'numeric(12,3)'),
            ('pedidos_itens', 'area', 'numeric(14,4)'),
            ('pedidos_itens', 'observacao_item', 'text'),
            ('pedidos_itens', 'material', 'character varying'),
            ('pedidos_itens', 'cor', 'character varying'),
            ('pedidos_itens', 'acionamento', 'character varying'),
            ('pedidos_itens', 'lado_comando', 'character varying'),
            ('pedidos_itens', 'calculo_producao_status', 'character varying'),
            ('pedidos_itens', 'dados_tecnicos', 'jsonb')
        ) AS esperado(tabela, coluna, tipo)
    LOOP
        SELECT format_type(a.atttypid, a.atttypmod)
        INTO v_tipo
        FROM pg_attribute a
        WHERE a.attrelid = to_regclass(format('public.%I', r.tabela))
          AND a.attname = r.coluna
          AND a.attnum > 0 AND NOT a.attisdropped;

        IF NOT FOUND OR v_tipo IS DISTINCT FROM r.tipo THEN
            RAISE EXCEPTION
                'Validação final: %.% ausente ou incompatível; esperado %, atual %',
                r.tabela, r.coluna, r.tipo, v_tipo;
        END IF;
        v_total := v_total + 1;
    END LOOP;

    IF v_total <> 62 THEN
        RAISE EXCEPTION 'Catálogo final incompleto: esperadas 62 colunas, verificadas %', v_total;
    END IF;

    IF (SELECT count(*) FROM public.clientes) <> 1
       OR (SELECT count(*) FROM public.orcamentos) <> 0
       OR (SELECT count(*) FROM public.orcamentos_itens) <> 0
       OR (SELECT count(*) FROM public.pedidos) <> 0
       OR (SELECT count(*) FROM public.pedidos_itens) <> 0
       OR (SELECT count(*) FROM public.financeiro) <> 0
       OR EXISTS (SELECT 1 FROM public.parceiros_comerciais)
       OR EXISTS (SELECT 1 FROM public.representantes)
       OR EXISTS (SELECT 1 FROM public.representantes_rt)
       OR EXISTS (SELECT 1 FROM public.parceiro_representantes)
       OR EXISTS (SELECT 1 FROM public.parceiro_clientes)
    THEN
        RAISE EXCEPTION 'Validação final: baseline de dados não preservado';
    END IF;
END;
$fase1_final$;

COMMIT;
