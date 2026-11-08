-- Migration aditiva proposta para revisao. Nao executar sem autorizacao.
-- O tenant dos itens e derivado do documento no PostgreSQL, nunca do cliente.
BEGIN;

DO $preflight$
BEGIN
    IF current_setting('server_version_num')::INTEGER < 150000 THEN
        RAISE EXCEPTION
            'Pré-requisito: PostgreSQL 15+ para preservar empresa_id ao remover serviço opcional';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.orcamentos_itens i
        LEFT JOIN public.orcamentos o ON o.id = i.orcamento_id
        WHERE o.id IS NULL OR o.empresa_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Itens de orçamento sem documento ou empresa válida impedem a migração de Serviços V1';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM public.pedidos_itens i
        LEFT JOIN public.pedidos p ON p.id = i.pedido_id
        WHERE p.id IS NULL OR p.empresa_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'Itens de pedido sem documento ou empresa válida impedem a migração de Serviços V1';
    END IF;
END;
$preflight$;

CREATE TABLE servicos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    codigo VARCHAR(50) NOT NULL,
    descricao TEXT NOT NULL,
    categoria VARCHAR(80) NOT NULL,
    unidade VARCHAR(12) NOT NULL,
    tipo_calculo VARCHAR(30) NOT NULL DEFAULT 'POR_UNIDADE',
    custo NUMERIC(14,4) NOT NULL DEFAULT 0 CHECK (custo >= 0),
    preco_venda NUMERIC(14,4) NOT NULL DEFAULT 0 CHECK (preco_venda >= 0),
    comissao NUMERIC(8,4) CHECK (comissao IS NULL OR (comissao >= 0 AND comissao <= 100)),
    observacoes TEXT,
    situacao VARCHAR(10) NOT NULL DEFAULT 'ATIVO' CHECK (situacao IN ('ATIVO', 'INATIVO')),
    faixas_altura JSONB NOT NULL DEFAULT '[]'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_servicos_empresa_codigo UNIQUE (empresa_id, codigo),
    CONSTRAINT uq_servicos_id_empresa UNIQUE (id, empresa_id),
    CONSTRAINT ck_servicos_unidade CHECK (unidade IN ('UN', 'ML', 'M2', 'HORA', 'SERVICO')),
    CONSTRAINT ck_servicos_tipo_calculo CHECK (tipo_calculo IN ('POR_UNIDADE', 'FAIXA_ALTURA'))
);

CREATE INDEX ix_servicos_empresa_situacao_descricao
    ON servicos (empresa_id, situacao, descricao);

DO $document_keys$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        WHERE i.indrelid = 'public.orcamentos'::regclass
          AND i.indisunique
          AND i.indisvalid
          AND i.indisready
          AND i.indpred IS NULL
          AND i.indexprs IS NULL
          AND i.indnkeyatts = 2
          AND i.indnatts = 2
          AND i.indkey[0] = (
              SELECT attnum FROM pg_attribute
              WHERE attrelid = i.indrelid AND attname = 'id'
          )
          AND i.indkey[1] = (
              SELECT attnum FROM pg_attribute
              WHERE attrelid = i.indrelid AND attname = 'empresa_id'
          )
    ) THEN
        ALTER TABLE public.orcamentos
            ADD CONSTRAINT uq_orcamentos_id_empresa UNIQUE (id, empresa_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        WHERE i.indrelid = 'public.pedidos'::regclass
          AND i.indisunique
          AND i.indisvalid
          AND i.indisready
          AND i.indpred IS NULL
          AND i.indexprs IS NULL
          AND i.indnkeyatts = 2
          AND i.indnatts = 2
          AND i.indkey[0] = (
              SELECT attnum FROM pg_attribute
              WHERE attrelid = i.indrelid AND attname = 'id'
          )
          AND i.indkey[1] = (
              SELECT attnum FROM pg_attribute
              WHERE attrelid = i.indrelid AND attname = 'empresa_id'
          )
    ) THEN
        ALTER TABLE public.pedidos
            ADD CONSTRAINT uq_pedidos_id_empresa UNIQUE (id, empresa_id);
    END IF;
END;
$document_keys$;

ALTER TABLE orcamentos_itens
    ADD COLUMN servico_id INTEGER REFERENCES servicos(id) ON DELETE SET NULL,
    ADD COLUMN empresa_id INTEGER REFERENCES empresas(id) ON DELETE RESTRICT;
ALTER TABLE pedidos_itens
    ADD COLUMN servico_id INTEGER REFERENCES servicos(id) ON DELETE SET NULL,
    ADD COLUMN empresa_id INTEGER REFERENCES empresas(id) ON DELETE RESTRICT;

UPDATE orcamentos_itens AS item
SET empresa_id = documento.empresa_id
FROM orcamentos AS documento
WHERE documento.id = item.orcamento_id;
UPDATE pedidos_itens AS item
SET empresa_id = documento.empresa_id
FROM pedidos AS documento
WHERE documento.id = item.pedido_id;

ALTER TABLE orcamentos_itens
    ALTER COLUMN empresa_id SET NOT NULL,
    ADD CONSTRAINT fk_orcamentos_itens_documento_empresa_servicos_v1
        FOREIGN KEY (orcamento_id, empresa_id)
        REFERENCES orcamentos(id, empresa_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_orcamentos_itens_servico_empresa_v1
        FOREIGN KEY (servico_id, empresa_id)
        REFERENCES servicos(id, empresa_id);
ALTER TABLE pedidos_itens
    ALTER COLUMN empresa_id SET NOT NULL,
    ADD CONSTRAINT fk_pedidos_itens_documento_empresa_servicos_v1
        FOREIGN KEY (pedido_id, empresa_id)
        REFERENCES pedidos(id, empresa_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_pedidos_itens_servico_empresa_v1
        FOREIGN KEY (servico_id, empresa_id)
        REFERENCES servicos(id, empresa_id);

CREATE FUNCTION definir_empresa_orcamento_item_servico_v1() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_empresa_id INTEGER;
BEGIN
    SELECT empresa_id
    INTO v_empresa_id
    FROM orcamentos
    WHERE id = NEW.orcamento_id
    FOR KEY SHARE;

    IF NOT FOUND OR v_empresa_id IS NULL THEN
        RAISE EXCEPTION 'Item e orçamento devem pertencer a uma empresa válida';
    END IF;

    NEW.empresa_id := v_empresa_id;
    RETURN NEW;
END;
$$;

CREATE FUNCTION definir_empresa_pedido_item_servico_v1() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
DECLARE
    v_empresa_id INTEGER;
BEGIN
    SELECT empresa_id
    INTO v_empresa_id
    FROM pedidos
    WHERE id = NEW.pedido_id
    FOR KEY SHARE;

    IF NOT FOUND OR v_empresa_id IS NULL THEN
        RAISE EXCEPTION 'Item e pedido devem pertencer a uma empresa válida';
    END IF;

    NEW.empresa_id := v_empresa_id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER definir_empresa_orcamento_item_servico
    BEFORE INSERT OR UPDATE OF orcamento_id, empresa_id, servico_id
    ON orcamentos_itens
    FOR EACH ROW EXECUTE FUNCTION definir_empresa_orcamento_item_servico_v1();
CREATE TRIGGER definir_empresa_pedido_item_servico
    BEFORE INSERT OR UPDATE OF pedido_id, empresa_id, servico_id
    ON pedidos_itens
    FOR EACH ROW EXECUTE FUNCTION definir_empresa_pedido_item_servico_v1();

CREATE INDEX ix_orcamentos_itens_servico ON orcamentos_itens(servico_id);
CREATE INDEX ix_pedidos_itens_servico ON pedidos_itens(servico_id);

COMMIT;
