ALTER TABLE orcamentos_itens
    DROP COLUMN IF EXISTS dados_tecnicos;

ALTER TABLE orcamentos
    DROP COLUMN IF EXISTS observacao_interna;
