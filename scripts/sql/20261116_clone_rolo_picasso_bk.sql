-- Smart-tec Persianas: clonagem idempotente da Rolô Picasso Translúcida (4109).
-- EXECUÇÃO MANUAL CONTROLADA no banco smarttec_persianas_prod; não executar em staging/assinantes.
-- Os cinco tecidos BK já existem: 1367..1371; custo BK 33.824/m²; TR 19.72/m².
-- Custo acabado estimado pelo diferencial do tecido: 89.90 + (33.824 - 19.72) = 104.004/m².
-- Validar custo e preço na simulação antes de usar comercialmente.
BEGIN;
DO $$
DECLARE
  columns_sql text;
  values_sql text;
  col record;
  expression text;
  inserted integer;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM produtos WHERE id=4109 AND empresa_id=1 AND grupo_tecnico='PERSIANA_ROLO') THEN
    RAISE EXCEPTION 'Produto base 4109 não corresponde à Rolô Picasso operacional';
  END IF;
  IF (SELECT count(*) FROM produtos WHERE id BETWEEN 1367 AND 1371 AND empresa_id=1 AND nome ILIKE '%PICASSO BK%') <> 5 THEN
    RAISE EXCEPTION 'Não foram encontrados os cinco tecidos Picasso BK esperados';
  END IF;
  FOR col IN
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='produtos'
      AND column_name NOT IN ('id','criado_em','atualizado_em')
      AND is_generated='NEVER' AND is_identity='NO'
    ORDER BY ordinal_position
  LOOP
    expression := CASE col.column_name
      WHEN 'nome' THEN '''ROLÔ PICASSO BK 2,50 (' || ''' || v.cor || '')''' 
      WHEN 'cor' THEN 'v.cor'
      WHEN 'variacao_cor' THEN 'v.cor'
      WHEN 'tipo_produto' THEN '''Produto fabricado'''
      WHEN 'material_tecido' THEN '''BLACKOUT'''
      WHEN 'codigo_interno' THEN '''ST-ROLO-PICASSO-BK-'' || v.slug'
      WHEN 'codigo' THEN '''ST-ROLO-PICASSO-BK-'' || v.slug'
      WHEN 'valor_custo' THEN '(COALESCE(p.valor_custo,89.90) + 33.824 - 19.72)'
      WHEN 'custo_final' THEN '(COALESCE(p.custo_final,89.90) + 33.824 - 19.72)'
      WHEN 'valor_venda' THEN 'ROUND(((COALESCE(p.custo_final,89.90) + 33.824 - 19.72) * 2.5)::numeric,2)'
      WHEN 'observacoes' THEN '''Tecido Picasso BK: produto ID '' || v.tecido_id || ''; validar composição e cálculo técnico.'''
      ELSE 'p.' || quote_ident(col.column_name)
    END;
    columns_sql := concat_ws(', ',columns_sql,quote_ident(col.column_name));
    values_sql := concat_ws(', ',values_sql,expression);
  END LOOP;
  EXECUTE format(
    'INSERT INTO produtos (%s) SELECT %s FROM produtos p CROSS JOIN (VALUES
       (''AMÊNDOA'',''AMENDOA'',1367),(''BEGE'',''BEGE'',1368),(''CINZA'',''CINZA'',1369),
       (''FENDI'',''FENDI'',1370),(''GELO'',''GELO'',1371)
     ) AS v(cor,slug,tecido_id)
     WHERE p.id=4109 AND NOT EXISTS (
       SELECT 1 FROM produtos existing
       WHERE existing.empresa_id=1 AND existing.nome= ''ROLÔ PICASSO BK 2,50 ('' || v.cor || '')''
     )', columns_sql, values_sql);
  GET DIAGNOSTICS inserted = ROW_COUNT;
  RAISE NOTICE 'Rolô Picasso BK: % novos registros', inserted;
END $$;
-- Conferir os cinco registros antes de COMMIT:
SELECT id,nome,cor,valor_custo,custo_final,valor_venda,grupo_tecnico,modelo_tecnico
FROM produtos WHERE empresa_id=1 AND nome LIKE 'ROLÔ PICASSO BK 2,50 (%' ORDER BY nome;
COMMIT;
