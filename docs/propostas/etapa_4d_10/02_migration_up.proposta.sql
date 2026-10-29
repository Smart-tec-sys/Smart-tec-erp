-- ETAPA 4D.10 | PROPOSTA ESTRUTURAL UP | NAO EXECUTAR
-- 4D.13: quatro planos PERSONALIZADO, dias_trial=0, valor=NULL, ativo=false, limites 2/2/3/4.
-- Parametros da carga; nenhum default historico ou vinculo de modulo e alterado aqui.
-- Bloqueio incondicional e definicoes estruturais mantidos integralmente.
-- Validar esquema real e obter autorizacao especifica antes de revisar o bloqueio.
-- Uma unica instrucao DO: a excecao impede todo o DDL, inclusive em autocommit.
DO $up$
DECLARE
    plano_oid oid;
    id_att smallint;
    esperado record;
    coluna_real record;
    gerador_oid oid;
    estrutura_atual jsonb;
    revisao_esquema_real CONSTANT text := '__PENDENTE_EVIDENCIA_ESQUEMA_REAL__';
BEGIN
    RAISE EXCEPTION '4D.10 BLOQUEADA: proposta UP sem autorizacao de execucao.';

    -- Evidencia humana do destino continua obrigatoria: snapshot local nao prova banco real.
    IF revisao_esquema_real LIKE '__PENDENTE_%' OR btrim(revisao_esquema_real) = '' THEN
        RAISE EXCEPTION 'UP exige referencia da revisao aprovada do esquema real.';
    END IF;
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);
    PERFORM set_config('lock_timeout', '5s', true);
    FOR esperado IN SELECT unnest(ARRAY[
        'public.planos_saas','public.assinaturas_saas',
        'public.plano_modulos_saas','public.modulos_saas'
    ]) AS tabela LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid = to_regclass(esperado.tabela)
            AND relkind = 'r' AND relpersistence = 'p' AND NOT relispartition
            AND NOT relrowsecurity AND NOT relforcerowsecurity)
           OR EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid = to_regclass(esperado.tabela)
               OR inhparent = to_regclass(esperado.tabela)) THEN
            RAISE EXCEPTION 'Tabela ausente ou forma/RLS divergente: %.', esperado.tabela;
        END IF;
    END LOOP;
    LOCK TABLE public.planos_saas IN ACCESS EXCLUSIVE MODE;
    LOCK TABLE public.assinaturas_saas, public.plano_modulos_saas, public.modulos_saas
      IN ACCESS SHARE MODE;
    IF EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtenabled <> 'D')
       OR EXISTS (SELECT 1 FROM pg_trigger
                  WHERE tgrelid = 'public.planos_saas'::regclass AND NOT tgisinternal)
       OR EXISTS (SELECT 1 FROM pg_rewrite WHERE ev_class = 'public.planos_saas'::regclass)
       OR EXISTS (SELECT 1 FROM pg_policy WHERE polrelid = ANY (ARRAY[
            'public.planos_saas'::regclass,'public.assinaturas_saas'::regclass,
            'public.plano_modulos_saas'::regclass,'public.modulos_saas'::regclass])) THEN
        RAISE EXCEPTION 'Triggers, regras ou politicas exigem revisao especifica; nao presumir efeitos.';
    END IF;
    -- Manifesto de tipos/nulidade derivado do snapshot local; gerador do id tratado abaixo.
    FOR esperado IN SELECT * FROM (VALUES
        ('public.planos_saas','id','integer',true,'GERADOR_SEPARADO'),
        ('public.planos_saas','codigo','character varying(50)',true,NULL),
        ('public.planos_saas','nome','character varying(120)',true,NULL),
        ('public.planos_saas','produto','character varying(50)',true,NULL),
        ('public.planos_saas','periodicidade','character varying(20)',true,NULL),
        ('public.planos_saas','valor','numeric(12,2)',false,NULL),
        ('public.planos_saas','dias_trial','integer',true,'7'),
        ('public.planos_saas','ativo','boolean',true,'true'),
        ('public.planos_saas','descricao','text',false,NULL),
        ('public.planos_saas','criado_em','timestamp without time zone',true,'now()'),
        ('public.planos_saas','atualizado_em','timestamp without time zone',true,'now()'),
        ('public.assinaturas_saas','plano_id','integer',false,NULL),
        ('public.assinaturas_saas','periodicidade','character varying(20)',false,NULL),
        ('public.plano_modulos_saas','plano_id','integer',true,NULL),
        ('public.plano_modulos_saas','modulo_id','integer',true,NULL),
        ('public.plano_modulos_saas','incluido','boolean',true,'true'),
        ('public.modulos_saas','id','integer',true,'GERADOR_SEPARADO'),
        ('public.modulos_saas','codigo','character varying(80)',true,NULL)
    ) AS e(tabela,coluna,tipo,obrigatoria,padrao) LOOP
        SELECT a.*, pg_get_expr(ad.adbin, ad.adrelid, false) AS expressao_padrao
          INTO coluna_real
        FROM pg_attribute a LEFT JOIN pg_attrdef ad
          ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
        WHERE a.attrelid = to_regclass(esperado.tabela) AND a.attname = esperado.coluna
          AND a.attnum > 0 AND NOT a.attisdropped;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Coluna ausente: %.%.', esperado.tabela, esperado.coluna;
        END IF;
        IF format_type(coluna_real.atttypid,coluna_real.atttypmod) IS DISTINCT FROM esperado.tipo
           OR coluna_real.attnotnull IS DISTINCT FROM esperado.obrigatoria
           OR coluna_real.attidentity <> '' OR coluna_real.attgenerated <> ''
           OR (esperado.padrao IS DISTINCT FROM 'GERADOR_SEPARADO'
               AND coluna_real.expressao_padrao IS DISTINCT FROM esperado.padrao) THEN
            RAISE EXCEPTION 'Tipo, nulidade ou default divergente: %.%.', esperado.tabela, esperado.coluna;
        END IF;
    END LOOP;
    IF (SELECT count(*) FROM pg_attribute WHERE attrelid = 'public.planos_saas'::regclass
        AND attnum > 0 AND NOT attisdropped) <> 11 THEN
        RAISE EXCEPTION 'planos_saas possui colunas adicionais ou ausentes; revisar.';
    END IF;
    -- PKs e unicidade simples de codigo: conferir colunas e indice efetivo.
    FOR esperado IN SELECT unnest(ARRAY['public.planos_saas','public.modulos_saas']) AS tabela LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c JOIN pg_index i ON i.indexrelid = c.conindid
            WHERE c.conrelid = to_regclass(esperado.tabela) AND c.contype = 'p'
              AND c.conkey = ARRAY[(SELECT attnum FROM pg_attribute
                  WHERE attrelid = c.conrelid AND attname = 'id' AND NOT attisdropped)]::smallint[]
              AND c.convalidated AND NOT c.condeferrable AND i.indisvalid AND i.indisready
              AND i.indisunique AND i.indexprs IS NULL AND i.indpred IS NULL
        ) OR NOT EXISTS (
            SELECT 1 FROM pg_constraint c JOIN pg_index i ON i.indexrelid = c.conindid
            WHERE c.conrelid = to_regclass(esperado.tabela) AND c.contype = 'u'
              AND c.conkey = ARRAY[(SELECT attnum FROM pg_attribute
                  WHERE attrelid = c.conrelid AND attname = 'codigo' AND NOT attisdropped)]::smallint[]
              AND c.convalidated AND NOT c.condeferrable AND i.indisvalid AND i.indisready
              AND i.indisunique AND i.indexprs IS NULL AND i.indpred IS NULL
        ) THEN
            RAISE EXCEPTION 'PK ou UNIQUE(codigo) efetiva divergente: %.', esperado.tabela;
        END IF;
    END LOOP;
    -- FKs historicas: chaves, destino, tipo de correspondencia, acoes e validacao.
    FOR esperado IN SELECT * FROM (VALUES
        ('public.assinaturas_saas','plano_id','public.planos_saas','r'),
        ('public.plano_modulos_saas','plano_id','public.planos_saas','c'),
        ('public.plano_modulos_saas','modulo_id','public.modulos_saas','c')
    ) AS e(origem,coluna,destino,exclusao) LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            WHERE c.conrelid = to_regclass(esperado.origem) AND c.contype = 'f'
              AND c.confrelid = to_regclass(esperado.destino)
              AND c.conkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = c.conrelid
                  AND attname = esperado.coluna AND NOT attisdropped)]::smallint[]
              AND c.confkey = ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid = c.confrelid
                  AND attname = 'id' AND NOT attisdropped)]::smallint[]
              AND c.confdeltype::text = esperado.exclusao AND c.confupdtype = 'a'
              AND c.confmatchtype = 's' AND c.convalidated AND NOT c.condeferrable
              AND COALESCE((to_jsonb(c)->>'conenforced')::boolean,true)
        ) THEN
            RAISE EXCEPTION 'FK divergente: %.% -> %.', esperado.origem, esperado.coluna, esperado.destino;
        END IF;
    END LOOP;
    IF (SELECT count(*) FROM pg_constraint WHERE contype = 'f'
        AND confrelid = 'public.planos_saas'::regclass) <> 2 THEN
        RAISE EXCEPTION 'Dependencias adicionais de planos_saas exigem revisao.';
    END IF;
    -- Definicoes de CHECK copiadas do snapshot: comparar expressao efetiva.
    -- Diferencas de versao/formatacao tambem bloqueiam: revisar evidencia, nunca ignorar.
    FOR esperado IN SELECT * FROM (VALUES
        ('public.planos_saas','ck_planos_periodicidade',
         $def$CHECK (((periodicidade)::text = ANY ((ARRAY['MENSAL'::character varying, 'ANUAL'::character varying, 'PERSONALIZADO'::character varying])::text[])))$def$),
        ('public.planos_saas','ck_planos_trial',$def$CHECK ((dias_trial >= 0))$def$),
        ('public.planos_saas','ck_planos_valor',$def$CHECK (((valor IS NULL) OR (valor >= (0)::numeric)))$def$),
        ('public.assinaturas_saas','ck_assinatura_periodicidade',
         $def$CHECK (((periodicidade IS NULL) OR ((periodicidade)::text = ANY ((ARRAY['MENSAL'::character varying, 'ANUAL'::character varying, 'PERSONALIZADO'::character varying])::text[]))))$def$)
    ) AS e(tabela,nome,definicao) LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c WHERE c.conrelid = to_regclass(esperado.tabela)
              AND c.conname = esperado.nome AND c.contype = 'c' AND c.convalidated
              AND COALESCE((to_jsonb(c)->>'conenforced')::boolean,true)
              AND regexp_replace(pg_get_constraintdef(c.oid,false),'\s+',' ','g')
                  = regexp_replace(esperado.definicao,'\s+',' ','g')
        ) THEN
            RAISE EXCEPTION 'CHECK efetivo divergente: %.%.', esperado.tabela, esperado.nome;
        END IF;
    END LOOP;
    IF (SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'public.planos_saas'::regclass AND contype = 'c') <> 3 THEN
        RAISE EXCEPTION 'CHECK adicional ou ausente em planos_saas; revisar.';
    END IF;
    gerador_oid := to_regclass('public.planos_saas_id_seq');
    IF gerador_oid IS NULL OR pg_get_serial_sequence('public.planos_saas','id')::regclass
        IS DISTINCT FROM gerador_oid::regclass THEN
        RAISE EXCEPTION 'Gerador de planos_saas.id diferente da sequencia historica.';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_attrdef ad JOIN pg_attribute a
          ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
        WHERE a.attrelid = 'public.planos_saas'::regclass AND a.attname = 'id'
          AND pg_get_expr(ad.adbin,ad.adrelid,false)
              = format('nextval(%L::regclass)',gerador_oid::regclass::text)
    ) OR NOT EXISTS (
        SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
          AND d.objid = gerador_oid AND d.refclassid = 'pg_class'::regclass
          AND d.refobjid = 'public.planos_saas'::regclass
          AND d.refobjsubid = (SELECT attnum FROM pg_attribute
              WHERE attrelid = d.refobjid AND attname = 'id' AND NOT attisdropped)
          AND d.deptype = 'a'
    ) OR NOT EXISTS (
        SELECT 1 FROM pg_sequence WHERE seqrelid = gerador_oid
          AND seqtypid = 'integer'::regtype AND seqstart = 1 AND seqincrement = 1
          AND seqmin = 1 AND seqmax = 2147483647 AND seqcache = 1 AND NOT seqcycle
    ) THEN
        RAISE EXCEPTION 'Default, propriedade ou configuracao do gerador de IDs divergente.';
    END IF;

    plano_oid := to_regclass('public.planos_saas');
    IF plano_oid IS NULL OR NOT EXISTS (
        SELECT 1 FROM pg_class WHERE oid = plano_oid AND relkind = 'r'
    ) THEN
        RAISE EXCEPTION 'Esperada tabela comum public.planos_saas; revisar esquema real.';
    END IF;
    LOCK TABLE public.planos_saas IN ACCESS EXCLUSIVE MODE;
    SELECT attnum INTO id_att FROM pg_attribute
    WHERE attrelid = plano_oid AND attname = 'id' AND NOT attisdropped
      AND atttypid = 'integer'::regtype AND attnotnull;
    IF id_att IS NULL OR NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = plano_oid
          AND contype = 'p' AND conkey = ARRAY[id_att]::smallint[]
    ) THEN
        RAISE EXCEPTION 'planos_saas.id deve ser INTEGER com PK individual.';
    END IF;
    -- Recusar estruturas anteriores, inclusive aplicacao parcial. Nao adotar objetos.
    IF EXISTS (
        SELECT 1 FROM pg_attribute WHERE attrelid = plano_oid
          AND attname = 'limite_usuarios' AND NOT attisdropped
    ) OR EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = plano_oid
          AND conname = 'ck_planos_saas_limite_usuarios_4d10'
    ) OR to_regclass('public.planos_saas_wix') IS NOT NULL THEN
        RAISE EXCEPTION 'Estrutura 4D.10 ja existe total ou parcialmente; revisar sem sobrescrever.';
    END IF;

    ALTER TABLE public.planos_saas ADD COLUMN limite_usuarios INTEGER NULL;
    ALTER TABLE public.planos_saas
      ADD CONSTRAINT ck_planos_saas_limite_usuarios_4d10
      CHECK (limite_usuarios IS NULL OR limite_usuarios >= 0);
    COMMENT ON COLUMN public.planos_saas.limite_usuarios
      IS 'SMARTTEC_ETAPA_4D_10_V1';
    COMMENT ON CONSTRAINT ck_planos_saas_limite_usuarios_4d10 ON public.planos_saas
      IS 'SMARTTEC_ETAPA_4D_10_V1';

    CREATE TABLE public.planos_saas_wix (
        wix_plan_id UUID NOT NULL,
        plano_id INTEGER NOT NULL,
        periodicidade VARCHAR(20) NOT NULL,
        CONSTRAINT pk_planos_saas_wix_4d10 PRIMARY KEY (wix_plan_id),
        CONSTRAINT fk_planos_saas_wix_plano_4d10 FOREIGN KEY (plano_id)
          REFERENCES public.planos_saas(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
        CONSTRAINT ck_planos_saas_wix_periodicidade_4d10
          CHECK (periodicidade IN ('MENSAL', 'ANUAL')),
        CONSTRAINT uq_planos_saas_wix_plano_periodo_4d10 UNIQUE (plano_id, periodicidade)
    );
    -- MESMA CONSULTA ESTRUTURAL nos tres SQLs; sem ler linhas comerciais.
    -- Compara definicoes efetivas e dependencias, nao apenas nomes/quantidades.
    SELECT jsonb_build_object(
        'banco', current_database(), 'versao', current_setting('server_version_num'),
        'tabelas', (
            SELECT jsonb_agg(jsonb_build_object(
                'nome', n.nspname || '.' || t.relname,
                'tipo', t.relkind, 'persistencia', t.relpersistence,
                'particao', t.relispartition, 'dono', t.relowner,
                'rls', t.relrowsecurity, 'forcar_rls', t.relforcerowsecurity,
                'acl', to_jsonb(t.relacl), 'opcoes', to_jsonb(t.reloptions),
                'heranca', (SELECT jsonb_agg(to_jsonb(h) ORDER BY h.inhrelid,h.inhseqno)
                    FROM pg_inherits h WHERE h.inhrelid = t.oid OR h.inhparent = t.oid),
                'colunas', (
                    SELECT jsonb_agg(jsonb_build_object(
                        'posicao', a.attnum, 'nome', a.attname,
                        'tipo', format_type(a.atttypid, a.atttypmod),
                        'obrigatoria', a.attnotnull, 'identidade', a.attidentity,
                        'gerada', a.attgenerated, 'colacao', a.attcollation,
                        'acl', to_jsonb(a.attacl),
                        'padrao', pg_get_expr(ad.adbin, ad.adrelid, false),
                        'comentario', col_description(t.oid, a.attnum)
                    ) ORDER BY a.attnum)
                    FROM pg_attribute a LEFT JOIN pg_attrdef ad
                      ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
                    WHERE a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped
                ),
                'restricoes', (
                    SELECT jsonb_agg(jsonb_build_object(
                        'nome', c.conname, 'tipo', c.contype,
                        'definicao', pg_get_constraintdef(c.oid, false),
                        'validada', c.convalidated,
                        'enforced', to_jsonb(c)->'conenforced',
                        'comentario', obj_description(c.oid, 'pg_constraint')
                    ) ORDER BY c.conname)
                    FROM pg_constraint c WHERE c.conrelid = t.oid
                ),
                'indices', (
                    SELECT jsonb_agg(jsonb_build_object(
                        'definicao', pg_get_indexdef(i.indexrelid, 0, false),
                        'valido', i.indisvalid, 'pronto', i.indisready,
                        'vivo', i.indislive, 'replica', i.indisreplident
                    ) ORDER BY i.indexrelid)
                    FROM pg_index i WHERE i.indrelid = t.oid
                ),
                'triggers', (
                    SELECT jsonb_agg(jsonb_build_object(
                        'definicao', pg_get_triggerdef(tr.oid, false),
                        'habilitado', tr.tgenabled, 'interno', tr.tgisinternal
                    ) ORDER BY tr.tgname)
                    FROM pg_trigger tr WHERE tr.tgrelid = t.oid
                ),
                'regras', (
                    SELECT jsonb_agg(pg_get_ruledef(r.oid, false) ORDER BY r.rulename)
                    FROM pg_rewrite r WHERE r.ev_class = t.oid
                ),
                'politicas', (
                    SELECT jsonb_agg(to_jsonb(pol) ORDER BY pol.polname)
                    FROM pg_policy pol WHERE pol.polrelid = t.oid
                ),
                'dependencias', (
                    SELECT jsonb_agg(to_jsonb(d) ORDER BY
                        d.classid,d.objid,d.objsubid,d.refclassid,d.refobjid,d.refobjsubid,d.deptype)
                    FROM pg_depend d
                    WHERE (d.refclassid = 'pg_class'::regclass AND d.refobjid = t.oid)
                       OR (d.classid = 'pg_class'::regclass AND d.objid = t.oid)
                )
            ) ORDER BY n.nspname,t.relname)
            FROM pg_class t JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE t.oid = ANY (ARRAY[
                to_regclass('public.planos_saas'), to_regclass('public.planos_saas_wix'),
                to_regclass('public.assinaturas_saas'), to_regclass('public.plano_modulos_saas'),
                to_regclass('public.modulos_saas')
            ])
        ),
        'gerador_id', (
            SELECT jsonb_build_object(
                'configuracao', to_jsonb(s), 'nome', c.oid::regclass::text,
                'dono', c.relowner, 'acl', to_jsonb(c.relacl),
                'dependencias', (SELECT jsonb_agg(to_jsonb(d) ORDER BY
                    d.classid,d.objid,d.objsubid,d.refclassid,d.refobjid,d.refobjsubid,d.deptype)
                    FROM pg_depend d WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid)
            )
            FROM pg_sequence s JOIN pg_class c ON c.oid = s.seqrelid
            WHERE s.seqrelid = to_regclass('public.planos_saas_id_seq')
        )
    ) INTO estrutura_atual;
    -- Registro estrutural da criacao para conferir carga/DOWN no mesmo destino.
    -- Nao e historico de migrations nem autorizacao para executar ou reverter.
    EXECUTE format('COMMENT ON TABLE public.planos_saas_wix IS %L',
        jsonb_build_object('origem','SMARTTEC_ETAPA_4D_10B_V2',
                           'estrutura',estrutura_atual)::text);
    -- Sem DML, backfill, alteracao de assinatura, modulo, webhook ou modo comercial.
END;
$up$;
