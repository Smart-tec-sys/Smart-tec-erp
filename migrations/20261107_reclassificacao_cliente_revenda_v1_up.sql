BEGIN;

ALTER TABLE public.clientes
    ADD CONSTRAINT uq_clientes_id_empresa_reclassificacao
    UNIQUE (id, empresa_id);

ALTER TABLE public.parceiros_comerciais
    ADD COLUMN cliente_origem_id INTEGER;

ALTER TABLE public.parceiros_comerciais
    ADD CONSTRAINT uq_parceiros_id_empresa_reclassificacao
    UNIQUE (id, empresa_id),
    ADD CONSTRAINT uq_parceiros_empresa_cliente_origem
    UNIQUE (empresa_id, cliente_origem_id),
    ADD CONSTRAINT fk_parceiros_cliente_origem_empresa
    FOREIGN KEY (cliente_origem_id, empresa_id)
    REFERENCES public.clientes (id, empresa_id)
    ON DELETE RESTRICT;

CREATE TABLE public.cliente_reclassificacoes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    cliente_id INTEGER NOT NULL,
    parceiro_id INTEGER NOT NULL,
    categoria_anterior VARCHAR(20) NOT NULL DEFAULT 'CLIENTE',
    categoria_nova VARCHAR(20) NOT NULL DEFAULT 'REVENDA',
    usuario_id TEXT NOT NULL,
    registrado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_cliente_reclassificacoes_categorias
        CHECK (categoria_anterior = 'CLIENTE' AND categoria_nova = 'REVENDA'),
    CONSTRAINT fk_cliente_reclassificacoes_cliente_empresa
        FOREIGN KEY (cliente_id, empresa_id)
        REFERENCES public.clientes (id, empresa_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_cliente_reclassificacoes_parceiro_empresa
        FOREIGN KEY (parceiro_id, empresa_id)
        REFERENCES public.parceiros_comerciais (id, empresa_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_cliente_reclassificacoes_empresa
        FOREIGN KEY (empresa_id)
        REFERENCES public.empresas (id)
        ON DELETE RESTRICT
);

CREATE INDEX ix_cliente_reclassificacoes_empresa_cliente
    ON public.cliente_reclassificacoes (empresa_id, cliente_id, registrado_em DESC);

COMMIT;
