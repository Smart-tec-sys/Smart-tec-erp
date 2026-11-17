# Fiscal V1 — AWS KMS + Render OIDC (adaptação, **não ativada**)

## Implementado

- \`app/services/fiscal_kms_aws.py\` implementa \`ProvedorKms\` com \`boto3\`, usando \`kms.encrypt\` e \`kms.decrypt\` para **apenas a DEK aleatória de 32 bytes**. O PFX e sua senha **não são enviados à AWS**: são cifrados localmente via AES-256-GCM, com AAD vinculado à empresa, e ficam apenas no envelope cifrado.
- EncryptionContext inclui \`smarttec:purpose=smarttec-fiscal-a1-envelope-v1\` e \`smarttec:empresa_id=<id>\`, valores **não secretos**, potencialmente visíveis no AWS CloudTrail.
- O serviço exige ARN completo de chave KMS simétrica e OIDC do Render com papel da mesma conta AWS, região compatível, ambiente exclusivamente \`staging\`, autenticação do ERP em \`authenticated\` e a flag \`SMARTTEC_FISCAL_A1_KMS_ADAPTER_ENABLED=1\`.
- Rejeita credenciais AWS estáticas por variáveis de ambiente e falha fechado em produção, DEV, sem token OIDC ou sem KMS.
- O status da aba Certificado digital indica \`INATIVO\` ou \`CONFIGURACAO_OIDC_DETECTADA_NAO_VERIFICADA\`. **A detecção não é um teste real de credenciais, IAM ou KMS!**
- O componente não cria contas, papéis, chaves, cobranças ou infraestrutura na AWS. O conector de Render atual não oferece configuração de identidade AWS. Não há upload nem assinatura real habilitada.

## Configuração a executar quando tivermos conta AWS e Render com suporte OIDC

A documentação do Render exige um **workspace Pro ou superior** para autenticação gerenciada OIDC. Isso **não foi confirmado no workspace Smart-tec**.

1. Na conta AWS autorizada, criar chave simétrica de **criptografia/decriptografia KMS** com rotação, política restrita e auditoria AWS CloudTrail. **Não criar chaves dentro do repositório nem enviá-las ao chat.**
2. No IAM, cadastrar \`https://oidc.render.com/{WORKSPACE_ID}\` com audiência \`sts.amazonaws.com\`. Criar role que confia no serviço **staging dedicado**, restringindo o \`sub\` OIDC exatamente ao service ID escolhido; nunca permitir wildcard no workspace inteiro. Dar apenas \`kms:Encrypt\` e \`kms:Decrypt\` sobre o ARN da chave apropriada; restringir contextos \`smarttec:purpose\` e, quando possível, o escopo de empresas. Incluir permissões mínimas na **key policy**.
3. Adicionar apenas ao serviço staging dedicado \`AWS_ROLE_ARN\`; **Render injeta automaticamente** \`AWS_WEB_IDENTITY_TOKEN_FILE\`. Não definir este último manualmente.
4. No servidor staging, configurar \`AWS_REGION\`, \`SMARTTEC_FISCAL_A1_KMS_KEY_ARN\`, \`SMARTTEC_AUTH_MODE=authenticated\`, \`SMARTTEC_ENV=staging\` e flag \`SMARTTEC_FISCAL_A1_KMS_ADAPTER_ENABLED=1\`; instalar \`boto3\`. Esta flag **não habilita importação nem emissão**.
5. Validar OIDC + \`kms:Encrypt\`/\`Decrypt\` com **DEK fictícia**, sem certificados reais, sem apresentar nenhum segredo/log. Só depois homologar infraestrutura com cofre, auditoria, política de retenção/remoção e recuperação segura.

**ATENÇÃO:** o \`staging\` antigo compartilha uma branch defasada por dezenas de commits. Não trocar sua branch indiscriminadamente. Preferir ambiente isolado e aprovado, e não implantar no ERP operacional da Smart-tec Persianas.

## Pendente antes de receber PFX real

Validação completa de cadeia e revogação ICP-Brasil; operações de upload com autenticação reforçada, rate-limit e auditoria; armazenamento de envelopes e migração no banco de homologação; avaliação dos controles do Render/OIDC; recuperação segura e eliminação dos segredos em memória; aprovação do fluxo fiscal pela contabilidade, XSD oficial, emissão SEFAZ homologada e autorização explícita de produção.

Documentos: Render, [Managed Auth with OpenID Connect](https://render.com/docs/oidc); AWS KMS SDK [Encrypt](https://docs.aws.amazon.com/boto3/latest/reference/services/kms/client/encrypt.html) e [Decrypt](https://docs.aws.amazon.com/boto3/latest/reference/services/kms/client/decrypt.html).
