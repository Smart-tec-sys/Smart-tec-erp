-- SMART-TEC PERSIANAS — preparação para cadastro Picasso BK.
-- IMPORTANTE: NÃO EXECUTAR COMO MIGRATION AUTOMÁTICA.
-- Um único produto acabado para a coleção; cinco tecidos BK são opções de cor.
-- A Rolô Translúcida 4109 não possui receita técnica em observacoes.
-- É obrigatório validar no ERP o vínculo de tecido e o simulador ANTES de ativar vendas.
-- Esta consulta é somente leitura, para conferir a base antes da clonagem pela API/tela.
SELECT p.id, p.nome, p.empresa_id, p.grupo_tecnico, p.modelo_tecnico,
       p.valor_custo, p.custo_final, p.valor_venda,
       p.observacoes IS NOT NULL AS tem_receita_em_observacoes
FROM produtos p WHERE p.id = 4109 AND p.empresa_id = 1;

SELECT id,nome,valor_custo,custo_final,unidade_venda
FROM produtos
WHERE empresa_id=1 AND id IN (1367,1368,1369,1370,1371)
ORDER BY id;

-- A diferença de custo de tecido observada é 33.824 - 19.72 = 14.104/m².
-- NÃO presumir que custo acabado = 89.90 + 14.104 sem validar a composição.
-- NÃO duplicar produto por cor nem alterar a Rolô Translúcida.
-- Não criar registros automaticamente enquanto a integração de tecido/receita
-- do novo produto com o orçamento não estiver comprovada.
