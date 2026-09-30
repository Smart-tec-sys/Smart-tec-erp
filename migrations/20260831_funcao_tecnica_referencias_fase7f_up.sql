BEGIN;

CREATE TABLE funcao_tecnica_referencias (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    fornecedor_id INTEGER NULL REFERENCES fornecedores(id),
    funcao_tecnica VARCHAR(100) NOT NULL,
    nome_referencia VARCHAR(500) NOT NULL,
    nome_normalizado VARCHAR(500) NOT NULL,
    codigo_referencia VARCHAR(150) NULL,
    unidade_referencia VARCHAR(50) NULL,
    tipo_referencia VARCHAR(40) NOT NULL DEFAULT 'CATALOGO_FORNECEDOR',
    nivel_confianca VARCHAR(20) NOT NULL,
    status_revisao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    atributos_referencia JSONB NOT NULL DEFAULT '{}'::jsonb,
    origem VARCHAR(500) NOT NULL,
    origem_localizador VARCHAR(200) NULL,
    origem_hash VARCHAR(64) NULL,
    observacoes TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    revisado_por_usuario_id INTEGER NULL REFERENCES usuarios(id),
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_referencia_funcao_nao_vazia CHECK (btrim(funcao_tecnica) <> ''),
    CONSTRAINT ck_referencia_nome_nao_vazio CHECK (btrim(nome_referencia) <> ''),
    CONSTRAINT ck_referencia_nome_normalizado_nao_vazio CHECK (btrim(nome_normalizado) <> ''),
    CONSTRAINT ck_referencia_confianca CHECK (
        nivel_confianca IN ('FORTE', 'PROVAVEL', 'AMBIGUA')
    ),
    CONSTRAINT ck_referencia_status CHECK (
        status_revisao IN ('PENDENTE', 'APROVADA', 'REJEITADA')
    )
);

CREATE INDEX ix_referencia_empresa_funcao
    ON funcao_tecnica_referencias (empresa_id, funcao_tecnica);

CREATE INDEX ix_referencia_empresa_fornecedor
    ON funcao_tecnica_referencias (empresa_id, fornecedor_id);

CREATE UNIQUE INDEX uq_referencia_contextual
    ON funcao_tecnica_referencias (
        empresa_id,
        funcao_tecnica,
        COALESCE(fornecedor_id, 0),
        nome_normalizado,
        COALESCE(codigo_referencia, ''),
        COALESCE(NULLIF(origem_hash, ''), lower(btrim(origem))),
        md5(atributos_referencia::text)
    );

CREATE FUNCTION validar_tenant_funcao_tecnica_referencia()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.fornecedor_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM fornecedores
        WHERE id = NEW.fornecedor_id
          AND empresa_id = NEW.empresa_id
    ) THEN
        RAISE EXCEPTION 'fornecedor não pertence à empresa da referência';
    END IF;

    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_tenant_funcao_tecnica_referencia
BEFORE INSERT OR UPDATE ON funcao_tecnica_referencias
FOR EACH ROW EXECUTE FUNCTION validar_tenant_funcao_tecnica_referencia();

REVOKE ALL ON funcao_tecnica_referencias FROM PUBLIC;
REVOKE ALL ON SEQUENCE funcao_tecnica_referencias_id_seq FROM PUBLIC;

COMMIT;
