-- Fiscal V1: cadastros fiscais por SKU, sem emissão de NF-e.
-- REVISAR E TESTAR EM STAGING. NÃO EXECUTAR AUTOMATICAMENTE EM PRODUÇÃO.
-- Exige uq_produtos_id_empresa existente (documento de identidade composta por empresa).
BEGIN;

DO $preflight$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.produtos'::regclass AND conname = 'uq_produtos_id_empresa'
      AND contype = 'u'
  ) THEN
    RAISE EXCEPTION 'Pré-requisito ausente: uq_produtos_id_empresa.';
  END IF;
END;
$preflight$;

CREATE TABLE fiscal_produtos (
  empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
  produto_id INTEGER NOT NULL,
  ncm VARCHAR(8),
  cfop_padrao_saida VARCHAR(4),
  cest VARCHAR(7),
  origem_mercadoria VARCHAR(1),
  cst_icms VARCHAR(2),
  csosn VARCHAR(3),
  cst_pis VARCHAR(2),
  cst_cofins VARCHAR(2),
  cst_ibs_cbs VARCHAR(3),
  cclass_trib_ibs_cbs VARCHAR(6),
  atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_fiscal_produtos PRIMARY KEY (empresa_id, produto_id),
  CONSTRAINT fk_fiscal_produto_tenant
    FOREIGN KEY (produto_id, empresa_id) REFERENCES produtos(id, empresa_id)
    ON DELETE CASCADE,
  CONSTRAINT ck_fiscal_produto_ncm CHECK (ncm IS NULL OR ncm ~ '^[0-9]{8}$'),
  CONSTRAINT ck_fiscal_produto_cfop CHECK (cfop_padrao_saida IS NULL OR cfop_padrao_saida ~ '^[0-9]{4}$'),
  CONSTRAINT ck_fiscal_produto_cest CHECK (cest IS NULL OR cest ~ '^[0-9]{7}$'),
  CONSTRAINT ck_fiscal_produto_origem CHECK (origem_mercadoria IS NULL OR origem_mercadoria ~ '^[0-8]$'),
  CONSTRAINT ck_fiscal_produto_ibscbs CHECK (cst_ibs_cbs IS NULL OR cst_ibs_cbs ~ '^[0-9]{3}$'),
  CONSTRAINT ck_fiscal_produto_cclass CHECK (cclass_trib_ibs_cbs IS NULL OR cclass_trib_ibs_cbs ~ '^[0-9]{6}$')
);

COMMENT ON TABLE fiscal_produtos IS 'Metadados de classificação fiscal, não representa NF-e autorizada e não armazena certificado.';

COMMIT;
