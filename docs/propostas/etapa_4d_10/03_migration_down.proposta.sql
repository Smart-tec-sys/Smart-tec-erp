-- ETAPA 4D.10 | PROPOSTA ESTRUTURAL DOWN | NAO EXECUTAR
-- 4D.13: quatro planos PERSONALIZADO, dias_trial=0, valor=NULL, ativo=false, limites 2/2/3/4.
-- Parametros da carga; nenhum default historico ou vinculo de modulo e alterado aqui.
-- Bloqueio incondicional e definicoes estruturais mantidos integralmente.
-- Nao desfaz carga comercial. Recusa qualquer dado ou indicio de uso.
-- __PENDENTE_COMPROVAR_AUSENCIA_DE_CONSUMIDORES__:
-- banco nao identifica leitores externos, SQL dinamico ou dependencias de deploys.
-- Revisar tambem forma, comentarios e dependencias dos objetos no esquema real.
DO $down$
DECLARE
    plano_oid oid;
    wix_oid oid;
    limite_att smallint;
    check_oid oid;
    marca jsonb;
    estrutura_atual jsonb;
    revisao_esquema_real CONSTANT text := '__PENDENTE_EVIDENCIA_ESQUEMA_REAL__';
    ausencia_consumidores CONSTANT text := '__PENDENTE_COMPROVAR_AUSENCIA_DE_CONSUMIDORES__';
BEGIN
    RAISE EXCEPTION '4D.10 BLOQUEADA: DOWN exige autorizacao e prova de ausencia de uso.';

    IF revisao_esquema_real LIKE '__PENDENTE_%' OR btrim(revisao_esquema_real) = ''
       OR ausencia_consumidores LIKE '__PENDENTE_%' OR btrim(ausencia_consumidores) = '' THEN
        RAISE EXCEPTION 'DOWN exige evidencias aprovadas de esquema e ausencia de consumidores.';
    END IF;
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);
    PERFORM set_config('lock_timeout', '5s', true);
    IF EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtenabled <> 'D') THEN
        RAISE EXCEPTION 'DOWN recusa event triggers habilitados sem revisao especifica.';
    END IF;
    plano_oid := to_regclass('public.planos_saas');
    wix_oid := to_regclass('public.planos_saas_wix');
    IF plano_oid IS NULL OR wix_oid IS NULL THEN
        RAISE EXCEPTION 'DOWN recusa estado ausente ou parcial; nao inferir propriedade.';
    END IF;
    LOCK TABLE public.planos_saas, public.planos_saas_wix IN ACCESS EXCLUSIVE MODE;
    LOCK TABLE public.assinaturas_saas, public.plano_modulos_saas, public.modulos_saas
      IN ACCESS SHARE MODE;
    IF EXISTS (SELECT 1 FROM pg_class WHERE oid IN (plano_oid,wix_oid)
        AND (relkind <> 'r' OR relpersistence <> 'p' OR relispartition
             OR relrowsecurity OR relforcerowsecurity))
       OR EXISTS (SELECT 1 FROM pg_policy WHERE polrelid IN (plano_oid,wix_oid)) THEN
        RAISE EXCEPTION 'DOWN recusa forma/RLS divergente; nao confiar em leitura parcial dos dados.';
    END IF;
    -- Comentario antigo, ausente ou JSON invalido aborta; nunca adotar automaticamente.
    marca := obj_description(wix_oid, 'pg_class')::jsonb;
    SELECT attnum INTO limite_att FROM pg_attribute
    WHERE attrelid = plano_oid AND attname = 'limite_usuarios' AND NOT attisdropped
      AND atttypid = 'integer'::regtype AND NOT attnotnull AND NOT atthasdef;
    SELECT oid INTO check_oid FROM pg_constraint
    WHERE conrelid = plano_oid AND conname = 'ck_planos_saas_limite_usuarios_4d10'
      AND contype = 'c';
    IF limite_att IS NULL OR check_oid IS NULL
       OR col_description(plano_oid, limite_att) IS DISTINCT FROM 'SMARTTEC_ETAPA_4D_10_V1'
       OR obj_description(check_oid, 'pg_constraint') IS DISTINCT FROM 'SMARTTEC_ETAPA_4D_10_V1'
       OR marca->>'origem' IS DISTINCT FROM 'SMARTTEC_ETAPA_4D_10B_V2'
       OR jsonb_typeof(marca->'estrutura') IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'DOWN recusa objetos sem a origem e a forma esperadas.';
    END IF;
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
    IF estrutura_atual IS DISTINCT FROM marca->'estrutura' THEN
        RAISE EXCEPTION 'DOWN bloqueado: definicoes efetivas ou dependencias diferem do UP.';
    END IF;
    IF EXISTS (SELECT 1 FROM public.planos_saas_wix)
       OR EXISTS (SELECT 1 FROM public.planos_saas WHERE limite_usuarios IS NOT NULL) THEN
        RAISE EXCEPTION 'DOWN bloqueado: mapeamentos ou limites preenchidos; preservar dados.';
    END IF;
    -- DROP COLUMN pode remover automaticamente indices/constraints da propria tabela.
    -- Recusar qualquer dependencia da coluna alem do CHECK criado pelo UP.
    IF EXISTS (
        SELECT 1 FROM pg_depend
        WHERE refclassid = 'pg_class'::regclass AND refobjid = plano_oid
          AND refobjsubid = limite_att
          AND NOT (classid = 'pg_constraint'::regclass AND objid = check_oid)
    ) THEN
        RAISE EXCEPTION 'DOWN bloqueado: dependencia adicional de limite_usuarios.';
    END IF;
    -- A comparacao acima inclui definicoes completas de colunas, CHECK/FK/PK/UNIQUE,
    -- indices, defaults, triggers, regras, politicas, ACL e dependencias nas cinco tabelas.

    -- RESTRICT preserva dependencias externas registradas no catalogo PostgreSQL.
    DROP TABLE public.planos_saas_wix RESTRICT;
    ALTER TABLE public.planos_saas
      DROP CONSTRAINT ck_planos_saas_limite_usuarios_4d10 RESTRICT;
    ALTER TABLE public.planos_saas DROP COLUMN limite_usuarios RESTRICT;
    -- Nenhuma linha de planos_saas, assinatura, pagamento ou modulo e removida.
END;
$down$;
