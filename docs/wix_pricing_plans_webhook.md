# Wix Pricing Plans → Smart-tec ERP — Proteção de instalação (Etapa 3G)

Endpoint público: `POST /webhooks/wix/pricing-plans`.
Recebe, valida e diagnostica. Não acessa banco, não provisiona, não altera empresas,
usuários, planos, autenticação do ERP, checkout ou tabelas. A proteção de instalação
é uma alteração local; commit, push e publicação exigem autorização própria.

## Origem e formato

O corpo HTTP inteiro é um JWT compacto, não um JSON nem um token de autorização.
Os bytes são recebidos antes do parsing, limitados a 256 KiB, e verificados com
RS256 usando exclusivamente a chave RSA pública configurada no servidor.
Não são usadas chaves ou URLs fornecidas pelo token. A biblioteca verifica exp,
iat e nbf quando presentes. Não se inventam issuer/audience ausentes do contrato Wix.
Não há consulta externa durante a requisição.

Após a verificação: claim data → envelope com eventType/instanceId/data →
validação exata do instanceId permitido → data do evento → actionEvent.body.order.
Aceita strings JSON ou objetos nessas camadas. Exige event id, order id, planId,
entityId consistente, entityFqdn
wix.pricing_plans.v2.order e slug purchased.

Evento autorizado: `wix.pricing_plans.v2.order_purchased`.
Outros eventos recebem 403 e não são diagnosticados como compras.

## Configuração

Variáveis necessárias: `WIX_WEBHOOK_PUBLIC_KEY` e `WIX_ALLOWED_INSTANCE_ID`.
Obter a chave pública do app em Wix → Webhooks → Get Public Key (ou View ID & keys).
Usar PEM RSA, com quebras reais de linha ou sequências literais `\n`.
Não usar app secret, chave privada ou chave do Supabase. Nunca registrar a chave.
Não há alteração automática de .env. O bootstrap existente já carrega o ambiente.

`WIX_ALLOWED_INSTANCE_ID` deve conter o Instance ID completo da instalação
autorizada, obtido em Custom Apps → app → Manage → App Installations, conferindo
o site da mesma linha. App ID identifica o aplicativo; Site ID identifica o site;
Instance ID identifica a instalação desse aplicativo no site. Nenhum desses
outros campos substitui `instanceId` no envelope assinado.

A assinatura RS256 é verificada antes de interpretar o envelope e validar sua
instalação. O campo usado é `instanceId` dentro do claim `data` do JWT:
verificação da assinatura → parsing de `claims["data"]` → `envelope["instanceId"]`.
O campo pode ser lido somente dessa estrutura autenticada; headers, query,
claim de nível superior, dados do pedido, metadata SDK e identity.appId não
servem como alternativas.

O contrato REST fornece uma string, descrita nas referências de instância como
App instance GUID, sem regex, versão UUID ou regra textual de normalização
especificada para esse envelope. A comparação é exata e sensível à caixa:
não aplica trim, lowercase, conversão para UUID, hash ou normalização Unicode.
Como validação defensiva, configuração e identificador recebido precisam ser
strings não vazias, sem espaços ou caracteres de controle; rejeitar esses
valores não os transforma em identificadores válidos. Não impor um regex UUID
deduzido somente de exemplos.

Configuração ausente ou inválida falha fechada com 503. Identificador recebido
ausente, vazio, de outro tipo ou com espaços/controles recebe 400. Uma string
diferente da instalação permitida recebe 403, sem revelar nenhum dos valores.
As variáveis são lidas na requisição, sem carregar credenciais na importação.
Cada app configurado deve usar sua própria chave pública.

Esta proteção não vincula pedido, contato ou instalação a uma empresa Smart-tec
e não confirma pagamento. O Instance ID real não deve aparecer em código,
testes, documentação, respostas ou logs. Configuração no Render e publicação
desta alteração exigem autorização própria; não são executadas nesta etapa.

## Respostas

- 200: evento autorizado, validado e diagnosticado; corpo {"status":"received"}.
- 400: corpo vazio ou estrutura/campos/instanceId inválidos após assinatura válida.
- 401: JWT malformado, algoritmo diferente, assinatura inválida ou token expirado ou claim data obrigatória ausente/nula.
- 403: instalação diferente da permitida ou evento não autorizado.
- 413: corpo maior que 256 KiB.
- 503: chave pública ou WIX_ALLOWED_INSTANCE_ID ausente/inválida; falha fechada.

Resposta 200 reconhece recebimento, nunca pagamento, provisionamento ou liberação.
O processamento é local, sem banco ou chamadas de rede. Não há SLA medido de produção.

## Diagnóstico e privacidade

Logger: uvicorn.error.wix_webhooks, nível INFO.
Campos extraídos: event id, event type, order id, planId, planName,
buyer.memberId, buyer.contactId, status, lastPaymentStatus e subscriptionId.

event.id é uma string opaca obrigatória e não vazia, sem exigência de UUID.
Seu valor é preservado exatamente, incluindo caixa, espaços e caracteres Unicode,
sem trim, normalização, conversão ou hash. Apenas a string vazia é rejeitada;
strings compostas por espaços são não vazias. Campo ausente, null e tipos
diferentes de string recebem 400. O JSON do log escapa caracteres de controle
sem alterar o identificador original recuperável pelo parsing do JSON.
Order/plan/subscription IDs continuam validados como UUIDs.
memberId/contactId são registrados somente como fingerprints SHA-256 de UUIDs
normalizados; são pseudônimos para correlação, não anonimização definitiva.
planName só aparece em claro quando corresponde exatamente ao nome conhecido
para aquele planId; nomes divergentes/desconhecidos geram fingerprint.
Campos opcionais ausentes aparecem como null, sem inferir pagamento.
A lista permitida exclui emails, nomes de pessoas, formulários, preços, identidade,
instanceId, WIX_ALLOWED_INSTANCE_ID, JWT, chaves e corpo completo. Rejeições da
instalação registram apenas mensagens constantes, antes do diagnóstico do pedido. O JSON do log escapa caracteres de controle.
Restringir acesso e retenção dos logs de diagnóstico no servidor.

## Duplicidade

event.id é a chave de futura idempotência e aparece como event_id no log,
preservando exatamente a string original, sem normalização de UUID.
Reenvios válidos recebem 200 e geram novamente o mesmo event_id; não há deduplicação
durável, cache, tabela ou garantia de processamento único nesta etapa.
O comentário ETAPA 2 na rota marca o local de futura gravação atômica e unicidade
antes de qualquer efeito comercial. A persistência exige nova autorização.

## Pedido não equivale a pagamento confirmado

Order Purchased dispara quando o pedido é pago integralmente, quando pelo menos
um ciclo é pago, quando um pedido offline é criado mesmo sem pagamento, ou quando
um pedido gratuito é criado. ACTIVE também não comprova recebimento financeiro.
lastPaymentStatus pode ser PAID, UNPAID, PENDING, FAILED, REFUNDED,
NOT_APPLICABLE ou UNDEFINED. Em pedidos offline, esse status é atualizado
manualmente pelo usuário Wix; PAID isolado não é comprovação externa.

Eventos de atualização, cancelamento, ciclos e pagamento são relevantes para
uma futura conciliação, mas não são aceitos por esta rota. A documentação Orders
descreve um fluxo com Payment Event, correlação do wixAppId do Pricing Plans e
wixAppOrderId, seguido de Get Order. Seleção de eventos, fonte de comprovação,
reembolsos e política de liberação ficam para a Etapa 2.

## Referência comercial (sem aplicação nesta etapa)

| planId | Plano | Usuários |
| --- | --- | --- |
| 1c973b08-47e1-4dcd-ab73-8cc4a8831fea | Smart-tec Visita Connect | 2 |
| 57fe070c-5e20-41a6-b118-6b32773fecf9 | Smart-tec ERP Essencial | 2 |
| 6fec4ea9-a428-4507-be8c-516b3cbda075 | Smart-tec ERP Profissional | 3 |
| 6522d0b2-63bd-43f9-bb40-cb95154cc2f2 | Smart-tec Prime Connect | 4 |

Uma assinatura por empresa. O controle de usuários pertence exclusivamente
ao Smart-tec, não ao Wix. PLAN_MAPPING é apenas uma constante de referência;
não autoriza nem limita usuários. Um planId desconhecido pode ser diagnosticado
sem ganhar qualquer efeito comercial.

## Teste local

Na raiz C:\Users\valmi\Smart-tec ERP, usando o ambiente existente:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
& .venv/Scripts/python.exe -m pytest tests/test_webhooks_wix.py -q -p no:cacheprovider
$env:WIX_WEBHOOK_PUBLIC_KEY = Get-Content "C:\caminho\wix-public-key.pem" -Raw
$env:WIX_ALLOWED_INSTANCE_ID = Read-Host "Instance ID completo da instalação autorizada"
& .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O app completo precisa da configuração existente de inicialização, sem alterações
nesta etapa. Os testes carregam somente o router e não inicializam banco ou Auth.
Usam uma chave RSA efêmera e identificadores fictícios, nunca credenciais ou
Instance IDs reais. HTTP e DNS são bloqueados antes de importar o router e durante
os testes. Autoload de plugins, cache pytest e gravação de pyc ficam desabilitados.

Com um JWT recente assinado pelo Wix salvo localmente (não colocar em logs):

```powershell
curl.exe -i -X POST "http://127.0.0.1:8000/webhooks/wix/pricing-plans" -H "Content-Type: text/plain" --data-binary "@C:\caminho\wix-event.jwt"
```

Sem assinatura válida, o resultado esperado é 401. Não enviar JSON comum.
Teste real do Wix requer callback HTTPS acessível externamente e configuração
manual do webhook; localhost sozinho não recebe chamadas do Wix.
A etapa não publica endpoint nem modifica checkout.

## Pendências para Etapa 2

Persistência idempotente, vinculação confiável à empresa, conciliação de pagamento,
tratamento de reenvios e ordem temporal, regras de uma assinatura por empresa,
cancelamentos/reembolsos e eventual provisionamento. Tudo exige nova autorização.

## Fontes oficiais

- [Webhook REST sem SDK](https://dev.wix.com/docs/build-apps/develop-your-app/develop-a-self-managed-app/webhooks/handle-events-with-webhooks-for-self-hosting-without-the-java-script-sdk)
- [About App Instances](https://dev.wix.com/docs/build-apps/develop-your-app/auth/app-instances/about-app-instances)
- [App Installations](https://dev.wix.com/docs/build-apps/manage-your-app/data-and-analytics/app-installations)
- [About Webhooks](https://dev.wix.com/docs/build-apps/develop-your-app/api-integrations/events-and-webhooks/about-webhooks)
- [Verify Requests Received from Wix](https://dev.wix.com/docs/build-apps/develop-your-app/auth/verify-requests-received-from-wix)
- [Estrutura de eventos](https://dev.wix.com/docs/api-reference/articles/work-with-wix-apis/platform/about-the-structure-of-webhooks)
- [Order Purchased](https://dev.wix.com/docs/api-reference/business-solutions/pricing-plans/orders/order-purchased)
- [About Orders](https://dev.wix.com/docs/api-reference/business-solutions/pricing-plans/orders/introduction)
