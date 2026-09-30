BEGIN;

CREATE TABLE empresa_equivalencias_tecnicas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    funcao_tecnica VARCHAR(100) NOT NULL,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    fornecedor_id INTEGER NULL REFERENCES fornecedores(id),
    prioridade INTEGER NOT NULL DEFAULT 100,
    preferencial BOOLEAN NOT NULL DEFAULT FALSE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    configuracoes_locais JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_equivalencias_funcao_nao_vazia CHECK (btrim(funcao_tecnica) <> ''),
    CONSTRAINT ck_equivalencias_prioridade CHECK (prioridade >= 0)
);

CREATE UNIQUE INDEX uq_equivalencias_combinacao
    ON empresa_equivalencias_tecnicas (
        empresa_id, funcao_tecnica, produto_id, COALESCE(fornecedor_id, 0)
    );

CREATE UNIQUE INDEX uq_equivalencias_preferencial_ativa
    ON empresa_equivalencias_tecnicas (empresa_id, funcao_tecnica)
    WHERE preferencial AND ativo;

CREATE INDEX ix_equivalencias_empresa_funcao
    ON empresa_equivalencias_tecnicas (empresa_id, funcao_tecnica);
CREATE INDEX ix_equivalencias_produto ON empresa_equivalencias_tecnicas (produto_id);
CREATE INDEX ix_equivalencias_fornecedor ON empresa_equivalencias_tecnicas (fornecedor_id);

CREATE FUNCTION validar_tenant_equivalencia_tecnica()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM produtos
        WHERE id = NEW.produto_id AND empresa_id = NEW.empresa_id
    ) THEN
        RAISE EXCEPTION 'produto não pertence à empresa da equivalência';
    END IF;

    IF NEW.fornecedor_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM fornecedores
        WHERE id = NEW.fornecedor_id AND empresa_id = NEW.empresa_id
    ) THEN
        RAISE EXCEPTION 'fornecedor não pertence à empresa da equivalência';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_tenant_equivalencia_tecnica
BEFORE INSERT OR UPDATE ON empresa_equivalencias_tecnicas
FOR EACH ROW EXECUTE FUNCTION validar_tenant_equivalencia_tecnica();

COMMIT;
