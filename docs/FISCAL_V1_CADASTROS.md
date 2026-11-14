# Fiscal V1 — Cadastros em revisão

Configuração fiscal por empresa em `empresas.configuracoes.fiscal_nfe` e tabela separada `fiscal_produtos` por empresa/produto (FK composta). O cadastro de preços, custos, SKU e orçamentos não é alterado.

**Rotas previstas após migração e deploy de homologação**:
- GET/PATCH `/fiscal/cadastros/empresa`
- GET/PATCH `/fiscal/cadastros/produtos/{produto_id}`
- GET `/pedidos/{pedido_id}/fiscal/preparacao-nfe`

Leituras requerem tenant autenticado. Gravações exigem vínculo ativo OWNER/ADMIN. Não há transmissão nem certificado; os códigos informados são apenas campos declaratórios (validam formato, não conformidade legal), sem cálculo de impostos. Os códigos devem ser conferidos pelo contador e com tabelas vigentes. A pré-validação da nota ainda retorna `NAO_APTO_EMISSAO`.

**Migração:** `migrations/20261114_fiscal_v1_cadastros_up.sql` é opt-in, depende de `uq_produtos_id_empresa`. O SQL não foi aplicado em nenhum Render. Testar em uma instância isolada antes da ativação; rollback do DOWN remove cadastros fiscais da versão 1 e só pode ser executado com backup/autorização.

**Limitações conhecidas:** Sem captura de IE do destinatário, sem cadastro completo de impostos por item, sem cálculos de ICMS/PIS/COFINS/IPI/IBS/CBS, sem regras por UF/CFOP, sem assinatura, XML ou SEFAZ. Série de homologação cadastrada aqui não reserva número de nota. Nenhum vínculo com a NFS-e da plataforma Smart-tec.
