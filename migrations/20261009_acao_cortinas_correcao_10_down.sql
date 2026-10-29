-- 20261009_acao_cortinas_correcao_10 (DOWN): restaura os valores anteriores dos 10 produtos.
-- Restaura tambem valor_custo e custo_final originais capturados em consulta somente leitura.
BEGIN;

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 6.35, custo_final = 6.35
WHERE id = 3039 AND empresa_id = 1 AND nome = '10263-14936 - LN TELA - (32)AREIA - 2,80M' AND codigo_fornecedor = '040306031900';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 6.35, custo_final = 6.35
WHERE id = 3040 AND empresa_id = 1 AND nome = '12020-15521 - LN TELA - (23)OFF WHITE - 2,80M' AND codigo_fornecedor = '040306031800';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 6.35, custo_final = 6.35
WHERE id = 3041 AND empresa_id = 1 AND nome = '12076 - LN TELA - (22)KAKI - 2,80M' AND codigo_fornecedor = '040306031300';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 6.35, custo_final = 6.35
WHERE id = 3042 AND empresa_id = 1 AND nome = '12737-12021-14425 - LN TELA NATURAL - (08)BEGE - 2,80M' AND codigo_fornecedor = '040306000200';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 2.9964, custo_final = 2.9964
WHERE id = 3057 AND empresa_id = 1 AND nome = '11779-12965 - SATIM AMASSADO - (01)BRANCO - 2,80M' AND codigo_fornecedor = '040292001700';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 2.9964, custo_final = 2.9964
WHERE id = 3058 AND empresa_id = 1 AND nome = '12964 - SATIM AMASSADO - (08)BEGE - 2,80M' AND codigo_fornecedor = '040292000200';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 2.9964, custo_final = 2.9964
WHERE id = 3059 AND empresa_id = 1 AND nome = '12967-11770 - SATIM AMASSADO - (44)FERRUGEM - 2,80M' AND codigo_fornecedor = '040292031400';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'COMPONENTES_MOTORES', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 8.0179, custo_final = 8.0179
WHERE id = 3069 AND empresa_id = 1 AND nome = '12239 - BORDADO BUQUE - (01)BRANCO - 2,80M' AND codigo_fornecedor = '040277001700';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 1.1439, custo_final = 1.1439
WHERE id = 3071 AND empresa_id = 1 AND nome = '12245 - PARATI - (60)LINHO - 2,80M' AND codigo_fornecedor = '040305014100';

UPDATE produtos SET nome_fornecedor = NULL, fornecedores = NULL, codigo_fornecedor = NULL,
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 6.4767, custo_final = 6.4767
WHERE id = 3072 AND empresa_id = 1 AND nome = '12246 - CAMBURI - (60)LINHO - 3,00M' AND codigo_fornecedor = '040374014100';

COMMIT;
