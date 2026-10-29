-- REVISÃO ESTÁTICA; NÃO EXECUTADO. Aplicação exige autorização separada.
-- Banco permitido: smarttec_erp_dev; empresa 1; somente os 48 IDs do plano ALTA.
-- Valores originais capturados por SELECT somente leitura em 2026-10-08.
-- Autossuficiente: nenhum arquivo externo ou estado prévio de psql é necessário.
-- IS NOT DISTINCT FROM compara inclusive NULL sem confundi-lo com string vazia.
-- Qualquer divergência de estado/contagem aborta toda a transação.
-- Tabela TEMP apenas verifica preservação; não há criação de estrutura permanente.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $guard$
BEGIN
 IF current_database() <> 'smarttec_erp_dev' THEN
  RAISE EXCEPTION 'Banco incorreto';
 END IF;
END
$guard$;
SELECT id FROM public.produtos WHERE empresa_id=1 AND id IN (3024, 3025, 3026, 3027, 3028, 3029, 3030, 3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3043, 3044, 3045, 3046, 3047, 3048, 3049, 3050, 3051, 3052, 3053, 3054, 3055, 3056, 3060, 3061, 3062, 3063, 3064, 3065, 3066, 3067, 3068, 3070, 3073, 3541, 3542, 3545, 3546, 3549, 3554, 3555, 3556) ORDER BY id FOR UPDATE;
CREATE TEMP TABLE normalizacao_cortinas_snapshot ON COMMIT DROP AS
SELECT id, to_jsonb(p) AS original FROM public.produtos p WHERE empresa_id=1 AND id IN (3024, 3025, 3026, 3027, 3028, 3029, 3030, 3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3043, 3044, 3045, 3046, 3047, 3048, 3049, 3050, 3051, 3052, 3053, 3054, 3055, 3056, 3060, 3061, 3062, 3063, 3064, 3065, 3066, 3067, 3068, 3070, 3073, 3541, 3542, 3545, 3546, 3549, 3554, 3555, 3556);
DO $apply$
DECLARE affected integer;
BEGIN
 IF (SELECT count(*) FROM pg_temp.normalizacao_cortinas_snapshot) <> 48 THEN
  RAISE EXCEPTION 'Esperados 48 produtos; transação abortada';
 END IF;

-- DOWN ID 3024 | TECIDO VELUDO - ALUMINIO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3024
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - ALUMINIO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3024; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3024 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3024'; END IF;

-- DOWN ID 3025 | TECIDO VELUDO - BLUEBERRY - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048600; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3025
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - BLUEBERRY - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3025; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3025 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3025'; END IF;

-- DOWN ID 3026 | TECIDO VELUDO - BOTANIC - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398049100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3026
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - BOTANIC - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3026; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3026 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3026'; END IF;

-- DOWN ID 3027 | TECIDO VELUDO - BRANCO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398001700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3027
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - BRANCO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3027; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3027 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3027'; END IF;

-- DOWN ID 3028 | TECIDO VELUDO - CACAU - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398035600; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3028
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - CACAU - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3028; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3028 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3028'; END IF;

-- DOWN ID 3029 | TECIDO VELUDO - CAPPUCCINO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048400; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3029
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - CAPPUCCINO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3029; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3029 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3029'; END IF;

-- DOWN ID 3030 | TECIDO VELUDO - LATTE - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048000; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3030
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - LATTE - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3030; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3030 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3030'; END IF;

-- DOWN ID 3031 | TECIDO VELUDO - MERLOT - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048200; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3031
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - MERLOT - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3031; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3031 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3031'; END IF;

-- DOWN ID 3032 | TECIDO VELUDO - NUDE - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398034600; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3032
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - NUDE - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3032; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3032 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3032'; END IF;

-- DOWN ID 3033 | TECIDO VELUDO - PRETO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398009100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3033
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - PRETO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3033; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3033 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3033'; END IF;

-- DOWN ID 3034 | TECIDO VELUDO - TERRACOTA - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398032400; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3034
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - TERRACOTA - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3034; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3034 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3034'; END IF;

-- DOWN ID 3035 | TECIDO VELUDO - TITANIO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398033600; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3035
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - TITANIO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3035; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3035 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3035'; END IF;

-- DOWN ID 3036 | TECIDO VELUDO - TOMATO- 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398049000; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3036
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - TOMATO- 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3036; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3036 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3036'; END IF;

-- DOWN ID 3037 | TECIDO VELUDO - TUSCANY - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048500; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3037
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - TUSCANY - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3037; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3037 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3037'; END IF;

-- DOWN ID 3038 | TECIDO VELUDO - VERDE MINERAL - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA VELUDO.pdf, página 1, código 040398048300; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL,
    grupo_tecnico = E'TECIDOS_PERSIANAS_ROLO_ROMANA_PAINEL'
WHERE empresa_id = 1
  AND id = 3038
  AND nome IS NOT DISTINCT FROM E'TECIDO VELUDO - VERDE MINERAL - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3038; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3038 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores', E'grupo_tecnico']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3038'; END IF;

-- DOWN ID 3043 | 11317 - VOIL LISO - (01)BRANCO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293001701; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Tabela cortina importado 18-01-24.pdf, página 2, código 078293001700; DESCRIÇÃO NORMALIZADA EXATA; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3043
  AND nome IS NOT DISTINCT FROM E'11317 - VOIL LISO - (01)BRANCO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3043; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3043 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3043'; END IF;

-- DOWN ID 3044 | 11319-14385 - VOIL LISO - (31)ROSA BEBE - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293031600; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3044
  AND nome IS NOT DISTINCT FROM E'11319-14385 - VOIL LISO - (31)ROSA BEBE - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3044; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3044 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3044'; END IF;

-- DOWN ID 3045 | 11320-10003 - VOIL LISO - (24)AZUL BEBE - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293031500; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3045
  AND nome IS NOT DISTINCT FROM E'11320-10003 - VOIL LISO - (24)AZUL BEBE - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3045; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3045 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3045'; END IF;

-- DOWN ID 3046 | 11321 - VOIL LISO - (32)AREIA - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293031900; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3046
  AND nome IS NOT DISTINCT FROM E'11321 - VOIL LISO - (32)AREIA - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3046; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3046 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3046'; END IF;

-- DOWN ID 3047 | 11330-13330 - VOIL LISO - (02)PRETO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293009100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3047
  AND nome IS NOT DISTINCT FROM E'11330-13330 - VOIL LISO - (02)PRETO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3047; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3047 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3047'; END IF;

-- DOWN ID 3048 | 11332 - VOIL LISO - (27)PALHA - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293032000; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3048
  AND nome IS NOT DISTINCT FROM E'11332 - VOIL LISO - (27)PALHA - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3048; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3048 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3048'; END IF;

-- DOWN ID 3049 | 12085 - VOIL LISO - (39)MARROM - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293010400; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3049
  AND nome IS NOT DISTINCT FROM E'12085 - VOIL LISO - (39)MARROM - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3049; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3049 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3049'; END IF;

-- DOWN ID 3050 | 12725 - VOIL LISO - (16)TIFFANY - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293035300; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3050
  AND nome IS NOT DISTINCT FROM E'12725 - VOIL LISO - (16)TIFFANY - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3050; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3050 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3050'; END IF;

-- DOWN ID 3051 | 14286-10006 - VOIL LISO - (25)CINZA CLARO - 3,00M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040293031700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3051
  AND nome IS NOT DISTINCT FROM E'14286-10006 - VOIL LISO - (25)CINZA CLARO - 3,00M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3051; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3051 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3051'; END IF;

-- DOWN ID 3052 | 11336 - VOIL XADREZ - (01)BRANCO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040294001700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3052
  AND nome IS NOT DISTINCT FROM E'11336 - VOIL XADREZ - (01)BRANCO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3052; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3052 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3052'; END IF;

-- DOWN ID 3053 | 11337 - VOIL XADREZ - (14)NEVE - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040294003700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3053
  AND nome IS NOT DISTINCT FROM E'11337 - VOIL XADREZ - (14)NEVE - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3053; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3053 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3053'; END IF;

-- DOWN ID 3054 | 11342 - VOIL XADREZ - (25)CINZA CLARO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040294031700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3054
  AND nome IS NOT DISTINCT FROM E'11342 - VOIL XADREZ - (25)CINZA CLARO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3054; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3054 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3054'; END IF;

-- DOWN ID 3055 | 11348 - VOIL XADREZ - BORDEAUX - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040294034300; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3055
  AND nome IS NOT DISTINCT FROM E'11348 - VOIL XADREZ - BORDEAUX - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3055; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3055 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3055'; END IF;

-- DOWN ID 3056 | 11351 - VOIL XADREZ - (27)PALHA - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040294032000; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3056
  AND nome IS NOT DISTINCT FROM E'11351 - VOIL XADREZ - (27)PALHA - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3056; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3056 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3056'; END IF;

-- DOWN ID 3060 | 12087 - VOIL RUSTICO - (23)OFF WHITE - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040312031800; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3060
  AND nome IS NOT DISTINCT FROM E'12087 - VOIL RUSTICO - (23)OFF WHITE - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3060; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3060 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3060'; END IF;

-- DOWN ID 3061 | 12088 - VOIL RUSTICO - (01)BRANCO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040312001700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3061
  AND nome IS NOT DISTINCT FROM E'12088 - VOIL RUSTICO - (01)BRANCO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3061; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3061 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3061'; END IF;

-- DOWN ID 3062 | 12090 - VOIL RUSTICO - (22)KAKI - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040312031300; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3062
  AND nome IS NOT DISTINCT FROM E'12090 - VOIL RUSTICO - (22)KAKI - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3062; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3062 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3062'; END IF;

-- DOWN ID 3063 | 12094 - VOIL RUSTICO - (03)PRATA - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040312015100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3063
  AND nome IS NOT DISTINCT FROM E'12094 - VOIL RUSTICO - (03)PRATA - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3063; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3063 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3063'; END IF;

-- DOWN ID 3064 | 12095 - VOIL RUSTICO - (04)CINZA - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040312009800; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3064
  AND nome IS NOT DISTINCT FROM E'12095 - VOIL RUSTICO - (04)CINZA - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3064; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3064 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3064'; END IF;

-- DOWN ID 3065 | 12230 - LINHO VOIL I - (60)LINHO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040280014100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3065
  AND nome IS NOT DISTINCT FROM E'12230 - LINHO VOIL I - (60)LINHO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3065; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3065 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3065'; END IF;

-- DOWN ID 3066 | 12231 - LINHO VOIL II - (60)LINHO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040281014100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3066
  AND nome IS NOT DISTINCT FROM E'12231 - LINHO VOIL II - (60)LINHO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3066; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3066 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3066'; END IF;

-- DOWN ID 3067 | 12232 - LINHO VOIL III - (60)LINHO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040324014100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3067
  AND nome IS NOT DISTINCT FROM E'12232 - LINHO VOIL III - (60)LINHO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3067; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3067 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3067'; END IF;

-- DOWN ID 3068 | 12233 - LINHO VOIL IV - (60)LINHO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040282014100; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3068
  AND nome IS NOT DISTINCT FROM E'12233 - LINHO VOIL IV - (60)LINHO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3068; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3068 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3068'; END IF;

-- DOWN ID 3070 | 12241 - VOIL BORDADO ARABESCO - (01)BRANCO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040276001700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3070
  AND nome IS NOT DISTINCT FROM E'12241 - VOIL BORDADO ARABESCO - (01)BRANCO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3070; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3070 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3070'; END IF;

-- DOWN ID 3073 | 12247-14064 - VOIL TELA - (01)BRANCO - 2,80M
-- Fornecedor original: None; sugerido: AÇÃO DISTRIBUIDORA
-- Classificação original: grupo=Tecidos; técnico='TECIDOS_CORTINA'; tipo='TECIDO PARA CORTINA'
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: Tabela de cortinas 30-04-24.pdf, página 1, código 040311001700; CÓDIGO EXATO; Emissor impresso Tradição; vínculo Ação documentado na planilha histórica de importação, não pelo logotipo original. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET nome_fornecedor = NULL,
    fornecedores = NULL
WHERE empresa_id = 1
  AND id = 3073
  AND nome IS NOT DISTINCT FROM E'12247-14064 - VOIL TELA - (01)BRANCO - 2,80M'
  AND nome_fornecedor IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND fornecedores IS NOT DISTINCT FROM E'AÇÃO DISTRIBUIDORA'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3073; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3073 AND (to_jsonb(p) - ARRAY[E'nome_fornecedor', E'fornecedores']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'nome_fornecedor', E'fornecedores']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3073'; END IF;

-- DOWN ID 3541 | WILER - COZUMEL - ALGEDI (01)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 15; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 12; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Outras ocorrências: TABELA CORTINAS WILER CLIENTE.xlsx, MADRI, linha 41; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3541
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - ALGEDI (01)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3541; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3541 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3541'; END IF;

-- DOWN ID 3542 | WILER - COZUMEL - ALGEDI (02)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 16; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 13; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Outras ocorrências: TABELA CORTINAS WILER CLIENTE.xlsx, MADRI, linha 42; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3542
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - ALGEDI (02)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3542; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3542 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3542'; END IF;

-- DOWN ID 3545 | WILER - COZUMEL - ARCA (01)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 19; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 22; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3545
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - ARCA (01)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3545; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3545 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3545'; END IF;

-- DOWN ID 3546 | WILER - COZUMEL - ARCA (02)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 20; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 23; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Outras ocorrências: TABELA CORTINAS WILER CLIENTE.xlsx, MADRI, linha 56; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3546
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - ARCA (02)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3546; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3546 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3546'; END IF;

-- DOWN ID 3549 | WILER - COZUMEL - CORA (01)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 23; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 30; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3549
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - CORA (01)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3549; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3549 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3549'; END IF;

-- DOWN ID 3554 | WILER - COZUMEL - MELO (01)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 28; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 52; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3554
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - MELO (01)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3554; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3554 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3554'; END IF;

-- DOWN ID 3555 | WILER - COZUMEL - MELO (02)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 29; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 53; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3555
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - MELO (02)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3555; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3555 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3555'; END IF;

-- DOWN ID 3556 | WILER - COZUMEL - MIRA (01)
-- Fornecedor original: 'Wiler'; sugerido: WILER
-- Classificação original: grupo=TECIDOS_CORTINA; técnico=None; tipo=None
-- Classificação sugerida: técnico=TECIDOS_CORTINA; tipo=TECIDO PARA CORTINA
-- Evidência: TABELA CORTINAS WILER CLIENTE.xlsx, GERAL CORTINAS, linha 30; FORNECEDOR + COLEÇÃO + DESCRIÇÃO EXATOS; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | TABELA CORTINAS WILER CLIENTE.xlsx, COZUMEL, linha 54; CÓDIGO INDIVIDUAL REFERENCIADO NA LINHA AGRUPADA DA FONTE; Outras ocorrências: TABELA CORTINAS WILER CLIENTE.xlsx, MADRI, linha 17; Coluna TABELA da Wiler sem unidade/condição de custo explícita; não equiparada automaticamente ao custo ERP por ML. | Produto único por ocorrência da fonte; sem ambiguidade em qualquer linha deste ERP no CSV. Convenção de nome_fornecedor/fornecedores comprovada pelas linhas Wiler; ID do fornecedor não demonstrado no CSV, manter atual. modelo_tecnico preservado: tecido/componente não será convertido em produto fabricado CORTINA.
UPDATE public.produtos
SET grupo_tecnico = NULL,
    tipo_cortina_persiana = NULL
WHERE empresa_id = 1
  AND id = 3556
  AND nome IS NOT DISTINCT FROM E'WILER - COZUMEL - MIRA (01)'
  AND nome_fornecedor IS NOT DISTINCT FROM E'Wiler'
  AND fornecedores IS NOT DISTINCT FROM E'Wiler'
  AND grupo_tecnico IS NOT DISTINCT FROM E'TECIDOS_CORTINA'
  AND tipo_cortina_persiana IS NOT DISTINCT FROM E'TECIDO PARA CORTINA'
;
GET DIAGNOSTICS affected = ROW_COUNT;
IF affected <> 1 THEN RAISE EXCEPTION 'Estado inesperado no produto 3556; transação abortada'; END IF;
IF EXISTS (SELECT 1 FROM public.produtos p JOIN pg_temp.normalizacao_cortinas_snapshot s ON s.id=p.id WHERE p.empresa_id=1 AND p.id=3556 AND (to_jsonb(p) - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[]) IS DISTINCT FROM (s.original - ARRAY[E'grupo_tecnico', E'tipo_cortina_persiana']::text[])) THEN RAISE EXCEPTION 'Campo protegido alterado no produto 3556'; END IF;
END
$apply$;
-- Validação final somente leitura, antes do COMMIT.
SELECT id,nome,nome_fornecedor,fornecedores,grupo_tecnico,tipo_cortina_persiana,
 fornecedor_padrao_id,valor_custo,custo_final,preco_custo,preco_venda
FROM public.produtos WHERE empresa_id=1 AND id IN (3024, 3025, 3026, 3027, 3028, 3029, 3030, 3031, 3032, 3033, 3034, 3035, 3036, 3037, 3038, 3043, 3044, 3045, 3046, 3047, 3048, 3049, 3050, 3051, 3052, 3053, 3054, 3055, 3056, 3060, 3061, 3062, 3063, 3064, 3065, 3066, 3067, 3068, 3070, 3073, 3541, 3542, 3545, 3546, 3549, 3554, 3555, 3556) ORDER BY id;
COMMIT;
