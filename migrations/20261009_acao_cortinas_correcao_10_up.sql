-- 20261009_acao_cortinas_correcao_10 (UP): corrige fornecedor/classificacao de 10 tecidos AÇÃO existentes.
-- Custo-base: preco FRACIONADO da tabela AÇÃO 30/04/2024, pelo codigo original exato.
-- Custo_final soma despesas atuais; despesas nao sao alteradas.
-- Nao altera valor_venda, fornecedor_padrao_id nem grupo_produto.
BEGIN;

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040306031900',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 19.56, custo_final = 19.56 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3039 AND empresa_id = 1 AND nome = '10263-14936 - LN TELA - (32)AREIA - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040306031800',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 19.56, custo_final = 19.56 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3040 AND empresa_id = 1 AND nome = '12020-15521 - LN TELA - (23)OFF WHITE - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040306031300',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 19.56, custo_final = 19.56 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3041 AND empresa_id = 1 AND nome = '12076 - LN TELA - (22)KAKI - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040306000200',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 19.56, custo_final = 19.56 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3042 AND empresa_id = 1 AND nome = '12737-12021-14425 - LN TELA NATURAL - (08)BEGE - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040292001700',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 8.73, custo_final = 8.73 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3057 AND empresa_id = 1 AND nome = '11779-12965 - SATIM AMASSADO - (01)BRANCO - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040292000200',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 8.73, custo_final = 8.73 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3058 AND empresa_id = 1 AND nome = '12964 - SATIM AMASSADO - (08)BEGE - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040292031400',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 8.73, custo_final = 8.73 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3059 AND empresa_id = 1 AND nome = '12967-11770 - SATIM AMASSADO - (44)FERRUGEM - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040277001700',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 23.35, custo_final = 23.35 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3069 AND empresa_id = 1 AND nome = '12239 - BORDADO BUQUE - (01)BRANCO - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040305014100',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 27.63, custo_final = 27.63 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3071 AND empresa_id = 1 AND nome = '12245 - PARATI - (60)LINHO - 2,80M';

UPDATE produtos SET nome_fornecedor = 'AÇÃO DISTRIBUIDORA', fornecedores = 'AÇÃO DISTRIBUIDORA', codigo_fornecedor = '040374014100',
  grupo_tecnico = 'TECIDOS_CORTINA', tipo_cortina_persiana = 'TECIDO PARA CORTINA',
  valor_custo = 20.21, custo_final = 20.21 + COALESCE(despesas_acessorias, 0) + COALESCE(outras_despesas, 0)
WHERE id = 3072 AND empresa_id = 1 AND nome = '12246 - CAMBURI - (60)LINHO - 3,00M';

-- Conferencia: deve retornar 10
SELECT count(*) AS atualizados FROM produtos WHERE id IN (3039,3040,3041,3042,3057,3058,3059,3069,3071,3072) AND nome_fornecedor = 'AÇÃO DISTRIBUIDORA' AND grupo_tecnico = 'TECIDOS_CORTINA';

COMMIT;
