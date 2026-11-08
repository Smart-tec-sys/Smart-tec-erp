-- Historico auditavel das edicoes do catalogo de produtos.
-- Preparada para revisao; nao executar sem autorizacao e validacao do destino.
BEGIN;

ALTER TABLE produtos
    ADD CONSTRAINT uq_produtos_id_empresa UNIQUE (id, empresa_id);

CREATE TABLE produtos_historico_alteracoes (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    produto_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    alteracoes JSONB NOT NULL,
    CONSTRAINT ck_produto_historico_alteracoes_objeto
        CHECK (jsonb_typeof(alteracoes) = 'object'),
    CONSTRAINT fk_produto_historico_produto_empresa
        FOREIGN KEY (produto_id, empresa_id)
        REFERENCES produtos(id, empresa_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_produto_historico_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_produto_historico_empresa_usuario
        FOREIGN KEY (empresa_id, usuario_id)
        REFERENCES empresa_usuarios(empresa_id, usuario_id)
        ON DELETE RESTRICT
);

CREATE INDEX ix_produtos_historico_empresa_produto_data
    ON produtos_historico_alteracoes (empresa_id, produto_id, criado_em DESC, id DESC);

COMMIT;
