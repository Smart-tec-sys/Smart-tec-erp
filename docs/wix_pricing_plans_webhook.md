# Wix Pricing Plans → Smart-tec ERP — Etapa 1

Endpoint público: `POST /webhooks/wix/pricing-plans`.
Recebe, valida e diagnostica. Não acessa banco, não provisiona, não altera empresas,
usuários, planos, autenticação, checkout ou tabelas. Nenhum commit faz parte desta etapa.

## Origem e formato

O corpo HTTP inteiro é um JWT compacto, não um JSON nem um token de autorização.
Os bytes são recebidos antes do parsing, limitados a 256 KiB, e verificados com
RS256 usando exclusivamente a chave RSA pública configurada no servidor.
Não são usadas chaves ou URLs fornecidas pelo token. A biblioteca verifica exp,
iat e nbf quando presentes. Não se inventam issuer/audience ausentes do contrato Wix.
Não há consulta externa durante a requisição.

Após a verificação: claim data → envelope com eventType/instanceId/data →
data do evento → actionEvent.body.order. Aceita strings JSON ou objetos nessas
camadas. Exige event id, order id, planId, entityId consistente, entityFqdn
wix.pricing_plans.v2.order e slug purchased.

Evento autorizado: `wix.pricing_plans.v2.order_purchased`.
Outros eventos recebem 403 e não são diagnosticados como compras.

## Configuração

Variável necessária: `WIX_WEBHOOK_PUBLIC_KEY`.
Obter a chave pública do app em Wix → Webhooks → Get Public Key (ou View ID & keys).
Usar PEM RSA, com quebras reais de linha ou sequências literais `\n`.
Não usar app secret, chave privada ou chave do Supabase. Nunca registrar a chave.
O commit-base nao carrega .env automaticamente; forneca as variaveis pelo ambiente do processo.

A assinatura confirma a origem Wix para o app da chave. Esta etapa não faz
vinculação de instanceId/site/contato a uma empresa; isso depende da Etapa 2.
Cada app configurado deve usar sua própria chave pública.

## Respostas

- 200: evento autorizado, validado e diagnosticado; corpo {"status":"received"}.
- 400: corpo vazio ou estrutura/campos inválidos após assinatura válida.
- 401: JWT malformado, algoritmo diferente, assinatura inválida ou token expirado ou claim data obrigatória ausente/nula.
- 403: evento não autorizado.
- 413: corpo maior que 256 KiB.
- 503: chave pública ausente ou inválida; falha fechada.

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
JWT, chaves e corpo completo. O JSON do log escapa caracteres de controle.
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

Na raiz C:/Users/valmi/Smart-tec-ERP-wix-staging, usando o ambiente existente:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
& "C:/Users/valmi/Smart-tec ERP/.venv/Scripts/python.exe" -m pytest tests/test_webhooks_wix.py -q -p no:cacheprovider
$env:WIX_WEBHOOK_PUBLIC_KEY = Get-Content "C:\caminho\wix-public-key.pem" -Raw
& "C:/Users/valmi/Smart-tec ERP/.venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O app completo precisa da configuração existente de inicialização, sem alterações
nesta etapa. Os testes carregam somente o router e não inicializam banco ou Auth.
Usam uma chave RSA efêmera de teste, nunca credenciais reais.

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

- [About Webhooks](https://dev.wix.com/docs/build-apps/develop-your-app/api-integrations/events-and-webhooks/about-webhooks)
- [Verify Requests Received from Wix](https://dev.wix.com/docs/build-apps/develop-your-app/auth/verify-requests-received-from-wix)
- [Estrutura de eventos](https://dev.wix.com/docs/api-reference/articles/work-with-wix-apis/platform/about-the-structure-of-webhooks)
- [Order Purchased](https://dev.wix.com/docs/api-reference/business-solutions/pricing-plans/orders/order-purchased)
- [About Orders](https://dev.wix.com/docs/api-reference/business-solutions/pricing-plans/orders/introduction)
