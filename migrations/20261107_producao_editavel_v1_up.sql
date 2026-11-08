-- Migration aditiva proposta para fichas editaveis e composicao manual supervisionada.
-- Requer 20261103_producao_v1_up.sql e 20261107_producao_v1_operacao_up.sql.
-- PREPARADA SOMENTE. Nao executar sem autorizacao, backup e validacao do destino.
BEGIN;

ALTER TABLE producao_pecas
    ADD COLUMN quantidade NUMERIC(12,3) NOT NULL DEFAULT 1,
    ADD COLUMN modo_fabricacao VARCHAR(30) NOT NULL DEFAULT 'AUTOMATICA',
    ADD COLUMN especificacoes_fabricacao JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN versao_ficha INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN conferido_por VARCHAR(100),
    ADD COLUMN conferido_em TIMESTAMPTZ,
    ADD CONSTRAINT ck_producao_quantidade CHECK (quantidade > 0),
    ADD CONSTRAINT ck_producao_modo_fabricacao
        CHECK (modo_fabricacao IN ('AUTOMATICA','MANUAL_SUPERVISIONADA')),
    ADD CONSTRAINT ck_producao_versao_ficha CHECK (versao_ficha > 0);

CREATE TABLE producao_componentes (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    ordem_id INTEGER NOT NULL REFERENCES ordens_producao(id) ON DELETE RESTRICT,
    peca_id INTEGER NOT NULL REFERENCES producao_pecas(id) ON DELETE RESTRICT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    descricao TEXT NOT NULL,
    codigo_interno VARCHAR(100),
    quantidade NUMERIC(12,3) NOT NULL,
    unidade VARCHAR(50) NOT NULL,
    comprimento_corte NUMERIC(12,3),
    custo_unitario NUMERIC(14,4) NOT NULL,
    origem_custo VARCHAR(20) NOT NULL,
    observacoes TEXT NOT NULL DEFAULT '',
    CONSTRAINT ck_producao_componente_quantidade CHECK (quantidade > 0),
    CONSTRAINT ck_producao_componente_corte
        CHECK (comprimento_corte IS NULL OR comprimento_corte > 0),
    CONSTRAINT ck_producao_componente_custo CHECK (custo_unitario >= 0),
    CONSTRAINT ck_producao_componente_origem_custo
        CHECK (origem_custo IN ('CADASTRO','INFORMADO'))
);
CREATE INDEX ix_producao_componentes_peca ON producao_componentes(peca_id);

CREATE TABLE producao_revisoes_ficha (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    ordem_id INTEGER NOT NULL REFERENCES ordens_producao(id) ON DELETE RESTRICT,
    peca_id INTEGER NOT NULL REFERENCES producao_pecas(id) ON DELETE RESTRICT,
    versao INTEGER NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    justificativa TEXT NOT NULL,
    antes JSONB NOT NULL,
    depois JSONB NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_producao_ficha_versao UNIQUE (peca_id, versao),
    CONSTRAINT ck_producao_revisao_versao CHECK (versao > 1)
);
CREATE INDEX ix_producao_revisoes_peca ON producao_revisoes_ficha(peca_id);

CREATE FUNCTION validar_vinculo_componente_producao_v1() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM producao_pecas p
        JOIN ordens_producao op ON op.id = p.ordem_id
        JOIN produtos produto ON produto.id = NEW.produto_id
        WHERE p.id = NEW.peca_id
          AND op.id = NEW.ordem_id
          AND op.empresa_id = NEW.empresa_id
          AND produto.empresa_id = NEW.empresa_id
    ) THEN
        RAISE EXCEPTION 'Componente, produto, peca e ordem devem pertencer a mesma empresa';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_componente_producao_empresa
    BEFORE INSERT OR UPDATE ON producao_componentes
    FOR EACH ROW EXECUTE FUNCTION validar_vinculo_componente_producao_v1();

CREATE FUNCTION validar_vinculo_revisao_producao_v1() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM producao_pecas p
        JOIN ordens_producao op ON op.id = p.ordem_id
        WHERE p.id = NEW.peca_id
          AND op.id = NEW.ordem_id
          AND op.empresa_id = NEW.empresa_id
    ) THEN
        RAISE EXCEPTION 'Revisao, peca e ordem devem pertencer a mesma empresa';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_revisao_producao_empresa
    BEFORE INSERT OR UPDATE ON producao_revisoes_ficha
    FOR EACH ROW EXECUTE FUNCTION validar_vinculo_revisao_producao_v1();

COMMIT;
