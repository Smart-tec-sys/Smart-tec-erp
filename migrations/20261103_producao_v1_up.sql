-- PREPARADA SOMENTE. Nao executar sem autorizacao e backup do destino.
BEGIN;

CREATE TABLE ordens_producao (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE RESTRICT,
    confirmado_por VARCHAR(100) NOT NULL,
    confirmado_em TIMESTAMPTZ NOT NULL,
    liberado_por VARCHAR(100),
    liberado_em TIMESTAMPTZ,
    snapshot JSON NOT NULL,
    CONSTRAINT uq_op_empresa_pedido UNIQUE (empresa_id, pedido_id)
);

CREATE TABLE producao_pecas (
    id SERIAL PRIMARY KEY,
    ordem_id INTEGER NOT NULL REFERENCES ordens_producao(id) ON DELETE RESTRICT,
    pedido_item_id INTEGER NOT NULL REFERENCES pedidos_itens(id) ON DELETE RESTRICT,
    sequencia INTEGER NOT NULL,
    modelo VARCHAR(100),
    tecido TEXT,
    cor VARCHAR(100),
    largura NUMERIC(12,3) NOT NULL,
    altura NUMERIC(12,3) NOT NULL,
    acionamento VARCHAR(100),
    ambiente VARCHAR(200) NOT NULL DEFAULT '',
    observacoes TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'AGUARDANDO',
    historico JSON NOT NULL DEFAULT '[]',
    CONSTRAINT uq_producao_item_peca UNIQUE (pedido_item_id, sequencia),
    CONSTRAINT ck_producao_sequencia CHECK (sequencia > 0),
    CONSTRAINT ck_producao_medidas CHECK (largura >= 0 AND altura >= 0),
    CONSTRAINT ck_producao_status CHECK (
        status IN ('AGUARDANDO','CORTE','MONTAGEM','CONFERENCIA','CONCLUIDA')
    )
);
CREATE INDEX ix_producao_pecas_ordem ON producao_pecas(ordem_id);

CREATE FUNCTION validar_vinculo_producao_v1() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'ordens_producao' THEN
        IF NOT EXISTS (
            SELECT 1 FROM pedidos WHERE id = NEW.pedido_id AND empresa_id = NEW.empresa_id
        ) THEN
            RAISE EXCEPTION 'Venda e OP devem pertencer a mesma empresa';
        END IF;
    ELSE
        IF NOT EXISTS (
            SELECT 1 FROM ordens_producao op JOIN pedidos_itens item ON item.pedido_id = op.pedido_id
            WHERE op.id = NEW.ordem_id AND item.id = NEW.pedido_item_id
        ) THEN
            RAISE EXCEPTION 'Peca deve pertencer a item da venda vinculada';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER validar_op_empresa BEFORE INSERT OR UPDATE ON ordens_producao
    FOR EACH ROW EXECUTE FUNCTION validar_vinculo_producao_v1();
CREATE TRIGGER validar_peca_venda BEFORE INSERT OR UPDATE ON producao_pecas
    FOR EACH ROW EXECUTE FUNCTION validar_vinculo_producao_v1();

COMMIT;
