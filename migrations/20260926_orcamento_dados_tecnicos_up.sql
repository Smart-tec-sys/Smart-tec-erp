ALTER TABLE orcamentos
    ADD COLUMN IF NOT EXISTS observacao_interna TEXT;

ALTER TABLE orcamentos_itens
    ADD COLUMN IF NOT EXISTS dados_tecnicos JSONB;
