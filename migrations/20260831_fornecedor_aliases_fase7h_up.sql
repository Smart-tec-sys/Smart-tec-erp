BEGIN;

CREATE TABLE fornecedor_aliases (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    alias_original VARCHAR(500) NOT NULL,
    alias_normalizado VARCHAR(500) NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    origem VARCHAR(500) NOT NULL,
    nivel_confianca VARCHAR(20) NOT NULL,
    status_revisao VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    observacoes TEXT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    revisado_por_usuario_id INTEGER NULL REFERENCES usuarios(id),
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_fornecedor_alias_original_nao_vazio CHECK (btrim(alias_original) <> ''),
    CONSTRAINT ck_fornecedor_alias_normalizado_nao_vazio CHECK (btrim(alias_normalizado) <> ''),
    CONSTRAINT ck_fornecedor_alias_tipo CHECK (
        tipo IN ('NOME_HISTORICO', 'NOME_IMPORTACAO', 'VARIANTE_GRAFIA', 'NOME_COMERCIAL', 'OUTRO')
    ),
    CONSTRAINT ck_fornecedor_alias_confianca CHECK (
        nivel_confianca IN ('FORTE', 'PROVAVEL', 'AMBIGUA')
    ),
    CONSTRAINT ck_fornecedor_alias_status CHECK (
        status_revisao IN ('PENDENTE', 'APROVADO', 'REJEITADO')
    )
);

CREATE INDEX ix_fornecedor_alias_fornecedor
    ON fornecedor_aliases (fornecedor_id);

CREATE INDEX ix_fornecedor_alias_empresa_fornecedor
    ON fornecedor_aliases (empresa_id, fornecedor_id);

CREATE UNIQUE INDEX uq_fornecedor_alias_ativo_empresa_normalizado
    ON fornecedor_aliases (empresa_id, alias_normalizado)
    WHERE ativo;

CREATE FUNCTION validar_tenant_fornecedor_alias()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM fornecedores
        WHERE id = NEW.fornecedor_id
          AND empresa_id = NEW.empresa_id
    ) THEN
        RAISE EXCEPTION 'fornecedor não pertence à empresa do alias';
    END IF;

    IF NEW.revisado_por_usuario_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM empresa_usuarios
        WHERE usuario_id = NEW.revisado_por_usuario_id
          AND empresa_id = NEW.empresa_id
          AND ativo
    ) THEN
        RAISE EXCEPTION 'revisor não pertence à empresa do alias';
    END IF;

    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_tenant_fornecedor_alias
BEFORE INSERT OR UPDATE ON fornecedor_aliases
FOR EACH ROW EXECUTE FUNCTION validar_tenant_fornecedor_alias();

INSERT INTO fornecedor_aliases (
    empresa_id, fornecedor_id, alias_original, alias_normalizado, tipo, origem,
    nivel_confianca, status_revisao, observacoes, ativo, revisado_por_usuario_id
)
VALUES
    (
        1, 2, 'A‡Æo Distribuidora', 'ao distribuidora', 'NOME_HISTORICO',
        'cadastro legado de fornecedores', 'FORTE', 'APROVADO',
        'Nome legado com provável corrupção histórica de encoding. Forma comercial provável: Ação Distribuidora.',
        TRUE, 1
    ),
    (
        1, 2, 'Ação Distribuidora', 'acao distribuidora', 'NOME_COMERCIAL',
        'TABELA AÇÃO ATUAL 05.10.2020.pdf', 'FORTE', 'APROVADO',
        'Telefone documental: (11) 3756-0909; WhatsApp: (11) 9.5966-8427; '
        'e-mail: atendimento@acaopersianas.com.br; SHA-256: '
        '5cabbdf6ae93353845f2e5c6336658682fc57c1016cbc8235d599bd7656af8d8.',
        TRUE, 1
    );

REVOKE ALL ON fornecedor_aliases FROM PUBLIC;
REVOKE ALL ON SEQUENCE fornecedor_aliases_id_seq FROM PUBLIC;

COMMIT;
