-- Fonte canonica por empresa; os produtos existentes nao sao alterados.
BEGIN;

CREATE TABLE classificacoes_tecnicas_produtos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    tipo VARCHAR(30) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    nome_normalizado VARCHAR(255) NOT NULL,
    CONSTRAINT ck_classificacao_tecnica_tipo
        CHECK (tipo IN ('grupo_tecnico', 'familia_tecnica', 'modelo_tecnico')),
    CONSTRAINT uq_classificacao_tecnica_empresa_tipo_nome
        UNIQUE (empresa_id, tipo, nome_normalizado)
);

WITH candidatos AS (
    SELECT
        p.empresa_id,
        c.tipo,
        REGEXP_REPLACE(BTRIM(c.nome), '\s+', ' ', 'g') AS nome,
        LOWER(REGEXP_REPLACE(BTRIM(c.nome), '\s+', ' ', 'g')) AS nome_normalizado,
        p.id AS produto_id
    FROM produtos AS p
    CROSS JOIN LATERAL (
        VALUES
            ('grupo_tecnico', p.grupo_tecnico),
            ('familia_tecnica', p.familia_tecnica),
            ('modelo_tecnico', p.modelo_tecnico)
    ) AS c(tipo, nome)
    WHERE p.empresa_id IS NOT NULL
      AND c.nome IS NOT NULL
      AND BTRIM(c.nome) <> ''
),
canonicas AS (
    SELECT DISTINCT ON (empresa_id, tipo, nome_normalizado)
        empresa_id, tipo, nome, nome_normalizado
    FROM candidatos
    ORDER BY empresa_id, tipo, nome_normalizado, produto_id
)
INSERT INTO classificacoes_tecnicas_produtos
    (empresa_id, tipo, nome, nome_normalizado)
SELECT empresa_id, tipo, nome, nome_normalizado
FROM canonicas;

COMMIT;
