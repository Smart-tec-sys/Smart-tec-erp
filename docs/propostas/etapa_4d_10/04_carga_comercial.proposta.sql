-- ETAPA 4D.10 | PROPOSTA DE CARGA COMERCIAL | NAO EXECUTAR
-- Marcadores sao decisoes em aberto, nunca valores comerciais substitutos.
-- valor=NULL e ativo=false APROVADOS para NOVOS planos; nao ativa clientes.
-- Nao carrega modulos, empresas, assinaturas ou pagamentos.
-- Cinco impedimentos de CADASTRO sao conferidos no checklist abaixo.
-- Vinculo empresa-assinatura, prova financeira e convencao temporal historica
-- sao condicoes separadas de ATIVACAO; esta carga nao as satisfaz nem libera acesso.
-- 4D.13: produto por categoria, PERSONALIZADO, dias_trial=0, valor=NULL e ativo=false aprovados.
-- A protecao 4D.11 recusa trial de plano com zero explicito; nao e bloqueio global de trial.
-- Essencial: CLIENTES/PRODUTOS/ORCAMENTOS/VENDAS; Profissional acrescenta FINANCEIRO.
-- Visita/Prime e integracao comercial dos modulos proprios continuam em homologacao.
-- Nenhum vinculo em plano_modulos_saas e criado por esta carga.
-- Nao assumir 7 dias: dias_trial sera sempre fornecido explicitamente.
-- Sem IDs numericos fixos: id usa o gerador existente, validado no esquema real.
DO $carga$
DECLARE
    planos CONSTANT jsonb := $planos$
[
  {
    "codigo": "SMARTTEC_VISITA_CONNECT",
    "nome": "Visita Connect",
    "limite_usuarios": 2,
    "produto": "VISITA_CONNECT",
    "dias_trial": 0,
    "periodicidade": "PERSONALIZADO",
    "valor": null,
    "ativo": false
  },
  {
    "codigo": "SMARTTEC_ERP_ESSENCIAL",
    "nome": "ERP Essencial",
    "limite_usuarios": 2,
    "produto": "ERP_ESSENCIAL",
    "dias_trial": 0,
    "periodicidade": "PERSONALIZADO",
    "valor": null,
    "ativo": false
  },
  {
    "codigo": "SMARTTEC_ERP_PROFISSIONAL",
    "nome": "ERP Profissional",
    "limite_usuarios": 3,
    "produto": "ERP_PROFISSIONAL",
    "dias_trial": 0,
    "periodicidade": "PERSONALIZADO",
    "valor": null,
    "ativo": false
  },
  {
    "codigo": "SMARTTEC_PRIME_CONNECT",
    "nome": "Prime Connect",
    "limite_usuarios": 4,
    "produto": "PRIME_CONNECT",
    "dias_trial": 0,
    "periodicidade": "PERSONALIZADO",
    "valor": null,
    "ativo": false
  }
]
$planos$::jsonb;
    mapas CONSTANT jsonb := $mapas$
[
  {
    "wix_plan_id": "1c973b08-47e1-4dcd-ab73-8cc4a8831fea",
    "codigo": "SMARTTEC_VISITA_CONNECT",
    "periodicidade": "MENSAL"
  },
  {
    "wix_plan_id": "57fe070c-5e20-41a6-b118-6b32773fecf9",
    "codigo": "SMARTTEC_ERP_ESSENCIAL",
    "periodicidade": "MENSAL"
  },
  {
    "wix_plan_id": "6fec4ea9-a428-4507-be8c-516b3cbda075",
    "codigo": "SMARTTEC_ERP_PROFISSIONAL",
    "periodicidade": "MENSAL"
  },
  {
    "wix_plan_id": "6522d0b2-63bd-43f9-bb40-cb95154cc2f2",
    "codigo": "SMARTTEC_PRIME_CONNECT",
    "periodicidade": "MENSAL"
  },
  {
    "wix_plan_id": "ca5c9f3b-cd24-45be-866e-7703fa62ab53",
    "codigo": "SMARTTEC_VISITA_CONNECT",
    "periodicidade": "ANUAL"
  },
  {
    "wix_plan_id": "435f12fb-dcee-4f75-a5eb-af67de7c1720",
    "codigo": "SMARTTEC_ERP_ESSENCIAL",
    "periodicidade": "ANUAL"
  },
  {
    "wix_plan_id": "73f654cf-9c5b-4b71-8881-4a7cd20fe024",
    "codigo": "SMARTTEC_ERP_PROFISSIONAL",
    "periodicidade": "ANUAL"
  },
  {
    "wix_plan_id": "76ecce76-0c79-48d0-bb81-a5e22c9f5e8a",
    "codigo": "SMARTTEC_PRIME_CONNECT",
    "periodicidade": "ANUAL"
  }
]
$mapas$::jsonb;
    -- Tres decisoes de preparacao aprovadas na 4D.13, restritas aos quatro planos.
    -- Composicao integrada e esquema real permanecem NAO COMPROVADOS.
    cadastro CONSTANT jsonb := '{
        "produto_aprovado": true,
        "periodicidade_catalogo_compativel": true,
        "politica_dias_trial_efetiva": true,
        "composicao_modulos_comprovada": false,
        "esquema_destino_validado": false
    }'::jsonb;
    revisao_cadastro CONSTANT text := '__PENDENTE_REFERENCIA_REVISAO_CADASTRO__';
    requisito text;
    marca jsonb;
    estrutura_atual jsonb;
    p record;
    m record;
    existente record;
    vinculo record;
    plano_destino integer;
BEGIN
    RAISE EXCEPTION '4D.10 BLOQUEADA: carga pendente de decisoes, esquema real e autorizacao.';

    FOREACH requisito IN ARRAY ARRAY[
        'produto_aprovado','periodicidade_catalogo_compativel',
        'politica_dias_trial_efetiva','composicao_modulos_comprovada','esquema_destino_validado'
    ] LOOP
        IF cadastro->requisito IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'Cadastro bloqueado: falta aprovacao/evidencia de %.', requisito;
        END IF;
    END LOOP;
    IF revisao_cadastro LIKE '__PENDENTE_%' OR btrim(revisao_cadastro) = '' THEN
        RAISE EXCEPTION 'Registrar referencia verificavel das cinco decisoes de cadastro.';
    END IF;
    IF planos::text LIKE '%__PENDENTE_%' THEN
        RAISE EXCEPTION 'Preencher e revisar todos os marcadores antes de preparar carga executavel.';
    END IF;
    PERFORM set_config('search_path', 'pg_catalog, pg_temp', true);
    PERFORM set_config('lock_timeout', '5s', true);
    IF EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtenabled <> 'D') THEN
        RAISE EXCEPTION 'Carga recusa event triggers habilitados sem revisao especifica.';
    END IF;
    -- Serializa tambem escritores comuns; uma falha desfaz todo este DO.
    LOCK TABLE public.planos_saas, public.planos_saas_wix IN SHARE ROW EXCLUSIVE MODE;
    LOCK TABLE public.assinaturas_saas, public.plano_modulos_saas, public.modulos_saas
      IN ACCESS SHARE MODE;
    marca := obj_description('public.planos_saas_wix'::regclass, 'pg_class')::jsonb;
    IF marca->>'origem' IS DISTINCT FROM 'SMARTTEC_ETAPA_4D_10B_V2'
       OR jsonb_typeof(marca->'estrutura') IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'Carga exige registro estrutural valido produzido pelo UP revisado.';
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
        RAISE EXCEPTION 'Carga bloqueada: esquema, gerador ou dependencias divergentes do UP.';
    END IF;
    IF jsonb_array_length(planos) <> 4 OR jsonb_array_length(mapas) <> 8
       OR (SELECT count(DISTINCT x->>'codigo') FROM jsonb_array_elements(planos) x) <> 4
       OR (SELECT count(DISTINCT x->>'wix_plan_id') FROM jsonb_array_elements(mapas) x) <> 8
       OR (SELECT count(DISTINCT (x->>'codigo',x->>'periodicidade'))
           FROM jsonb_array_elements(mapas) x) <> 8 THEN
        RAISE EXCEPTION 'Cardinalidade ou unicidade da proposta de quatro planos/oito ofertas alterada.';
    END IF;
    FOR p IN SELECT * FROM jsonb_to_recordset(planos) AS x(
        codigo text, nome text, limite_usuarios integer, produto text,
        dias_trial integer, periodicidade text, valor numeric, ativo boolean
    ) LOOP
        IF p.produto IS NULL OR btrim(p.produto) = '' OR char_length(p.produto) > 50
           OR p.dias_trial IS DISTINCT FROM 0
           OR p.periodicidade IS DISTINCT FROM 'PERSONALIZADO'
           OR p.limite_usuarios IS NULL OR p.limite_usuarios < 0
           OR p.valor IS NOT NULL OR p.ativo IS DISTINCT FROM false THEN
            RAISE EXCEPTION 'Valores comerciais invalidos ou incompletos para %.', p.codigo;
        END IF;
        SELECT * INTO existente FROM public.planos_saas WHERE codigo = p.codigo;
        IF FOUND THEN
            IF existente.nome IS DISTINCT FROM p.nome
               OR existente.produto IS DISTINCT FROM p.produto
               OR existente.periodicidade IS DISTINCT FROM p.periodicidade
               OR existente.valor IS DISTINCT FROM p.valor
               OR existente.dias_trial IS DISTINCT FROM p.dias_trial
               OR existente.ativo IS DISTINCT FROM p.ativo
               OR existente.limite_usuarios IS DISTINCT FROM p.limite_usuarios THEN
                RAISE EXCEPTION 'Conflito no plano %: preservar registro e decidir manualmente.', p.codigo;
            END IF;
        ELSE
            INSERT INTO public.planos_saas
                (codigo,nome,produto,periodicidade,valor,dias_trial,ativo,limite_usuarios)
            VALUES
                (p.codigo,p.nome,p.produto,p.periodicidade,p.valor,p.dias_trial,p.ativo,p.limite_usuarios);
        END IF;
    END LOOP;

    FOR m IN SELECT * FROM jsonb_to_recordset(mapas) AS x(
        wix_plan_id uuid, codigo text, periodicidade text
    ) LOOP
        SELECT id INTO STRICT plano_destino FROM public.planos_saas WHERE codigo = m.codigo;
        SELECT * INTO vinculo FROM public.planos_saas_wix WHERE wix_plan_id = m.wix_plan_id;
        IF FOUND THEN
            IF vinculo.plano_id IS DISTINCT FROM plano_destino
               OR vinculo.periodicidade IS DISTINCT FROM m.periodicidade THEN
                RAISE EXCEPTION 'Conflito no UUID Wix %; nenhuma substituicao permitida.', m.wix_plan_id;
            END IF;
        ELSE
            IF EXISTS (
                SELECT 1 FROM public.planos_saas_wix
                WHERE plano_id = plano_destino AND periodicidade = m.periodicidade
            ) THEN
                RAISE EXCEPTION 'Plano/ciclo %/% associado a outro UUID Wix.', m.codigo, m.periodicidade;
            END IF;
            INSERT INTO public.planos_saas_wix (wix_plan_id,plano_id,periodicidade)
            VALUES (m.wix_plan_id,plano_destino,m.periodicidade);
        END IF;
    END LOOP;
    -- Repeticao de conteudo identico nao escreve; divergencia aborta tudo.
    -- Nao usar UPDATE, ON CONFLICT DO UPDATE, DELETE ou ajustes de sequencia.
END;
$carga$;
