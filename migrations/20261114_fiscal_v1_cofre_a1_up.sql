-- Cofre A1 apenas em staging/CI após revisão; NÃO executar em produção.
-- Nunca armazenar PFX/senha/chave mestra em texto claro.
BEGIN;
DO $preflight$
BEGIN
  IF to_regclass('public.empresas') IS NULL THEN
    RAISE EXCEPTION 'Tabela empresas ausente; cofre A1 bloqueado.';
  END IF;
  IF to_regclass('public.fiscal_certificados_cofre') IS NOT NULL THEN
    RAISE EXCEPTION 'Tabela cofre A1 já existe: revisar esquema antes de aplicar.';
  END IF;
END;
$preflight$;
CREATE TABLE fiscal_certificados_cofre (
  empresa_id INTEGER PRIMARY KEY REFERENCES empresas(id) ON DELETE CASCADE,
  versao SMALLINT NOT NULL DEFAULT 1,
  key_id VARCHAR(160) NOT NULL,
  chave_envelopada BYTEA NOT NULL,
  nonce BYTEA NOT NULL,
  conteudo_cifrado BYTEA NOT NULL,
  criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_fiscal_cofre_versao CHECK (versao = 1),
  CONSTRAINT ck_fiscal_cofre_nonce CHECK (octet_length(nonce) = 12),
  CONSTRAINT ck_fiscal_cofre_chave CHECK (octet_length(chave_envelopada) BETWEEN 32 AND 4096),
  CONSTRAINT ck_fiscal_cofre_ciphertext CHECK (octet_length(conteudo_cifrado) BETWEEN 20 AND 135000)
);
COMMENT ON TABLE fiscal_certificados_cofre IS
  'Envelope AES-256-GCM por empresa + chave de dados envelopada por KMS externo. Sem emissão.';
COMMIT;
