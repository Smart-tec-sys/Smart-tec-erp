# Etapa 4D.10 — catálogo interno e correspondência Wix (proposta)

Data: 17/10/2026. Consolidação 4D.13, incorporando 4D.11/4D.12: alterações restritas aos quatro arquivos
de proposta existentes; nenhuma execução autorizada. Código funcional preservado.

## Escopo e reconhecimento

Referência correta: `C:\Users\valmi\Smart-tec ERP`, HEAD observado
`1600477` (`diag: registra causa do health db no staging`). A pasta aberta
na conversa, `C:\Users\valmi\Documents\Smart-tec ERP`, tem outro estado
e não deve ser tratada como cópia equivalente. Há muitas alterações locais
e arquivos não versionados no projeto de referência, inclusive os módulos comerciais.

Foram lidos apenas arquivos locais relacionados e o estado Git. Não houve acesso
a PostgreSQL (5432 ou 55433), Render, Vercel ou Wix, execução de SQL, testes de
integração, importação da aplicação, commit, push, merge ou publicação.
O worktree Wix não foi inspecionado nem alterado.

Entrega isolada em `docs/propostas/etapa_4d_10/`, fora de `migrations/`:
- `01_arquitetura_decisoes.md`: arquitetura, evidências e pendências.
- `02_migration_up.proposta.sql`: alteração estrutural proposta.
- `03_migration_down.proposta.sql`: reversão conservadora proposta.
- `04_carga_comercial.proposta.sql`: quatro planos e oito vínculos propostos.

Cada SQL contém uma única instrução `DO`, com exceção incondicional antes
de qualquer DDL/DML. A carga também conserva marcadores explícitos e uma
checagem adicional de pendências. São rascunhos bloqueados, sem comandos para
execução. Retirar os bloqueios exige nova revisão e autorização expressa.

## Esquema conhecido, sem inferir o ambiente real

Fonte histórica: `backups/staging_schema_20260930_212044/smarttec_erp_dev_schema.sql`.
Esse snapshot não comprova o esquema atual de homologação ou produção.

| Objeto | Evidência local |
| --- | --- |
| `planos_saas` | `id INTEGER` com PK e sequência/default; `codigo VARCHAR(50) UNIQUE NOT NULL`; `nome VARCHAR(120)`, `produto VARCHAR(50)` e `periodicidade VARCHAR(20)` obrigatórios |
| Campos comerciais | `valor NUMERIC(12,2)` anulável e não negativo; `dias_trial INTEGER NOT NULL DEFAULT 7`; `ativo BOOLEAN NOT NULL DEFAULT true` |
| Periodicidade do plano | CHECK permite `MENSAL`, `ANUAL` ou `PERSONALIZADO` |
| `assinaturas_saas` | `empresa_id`, `plano_id`, `periodicidade` e `valor` próprios; datas de trial/vigência |
| Módulos | `plano_modulos_saas(plano_id,modulo_id,incluido)`; concessões em `empresa_modulos_saas` |
| Tempo | `criado_em`/`atualizado_em` são timestamps sem fuso, com default `now()` no snapshot |

A migration local `20261006_admin_assinaturas_ciclo_f1_up.sql` propõe estado
`PENDENTE`, forma de pagamento e ciclos de cobrança; sua presença no disco
não prova aplicação em nenhum banco. A consulta vazia a `planos_saas` no
Staging foi informada pelo usuário e não foi repetida; nada permite concluir
que produção esteja vazia.

## Estrutura proposta

1. Acrescentar `planos_saas.limite_usuarios INTEGER NULL`, sem default, com
   CHECK de valor não negativo. Não preencher planos antigos.
   `NULL` significa limite desconhecido; zero significa nenhuma vaga.
2. Criar `public.planos_saas_wix` com `wix_plan_id UUID PRIMARY KEY`,
   `plano_id INTEGER NOT NULL` com FK para `planos_saas(id)` e
   `periodicidade VARCHAR(20) NOT NULL`, restrita a `MENSAL`/`ANUAL`.
3. Usar `UNIQUE(plano_id,periodicidade)`: uma oferta Wix por categoria/ciclo.
   Um UUID só identifica um plano/ciclo. Uma eventual substituição de oferta
   ou múltiplos sites exige desenho e revisão próprios, preservando histórico.
   FK com `ON UPDATE RESTRICT ON DELETE RESTRICT`, sem remoção em cascata.
4. Manter quatro categorias internas, compartilhadas pelas ofertas mensais
   e anuais. A assinatura registra ciclo e valor efetivamente contratados.
   A migration não altera `assinaturas_saas` nem cria restrição de unicidade
   por empresa: a regra de uma assinatura comercial por empresa permanece
   no fluxo existente e precisa de validação própria antes da integração.
5. Resolver IDs internos por `codigo`; novos IDs vêm exclusivamente do
   gerador já existente, após validação. Não escolher IDs numéricos fixos.
   Não criar nem ajustar sequência nesta proposta.

Não há migração de dados anteriores, módulos ou assinaturas. A tabela de ofertas
não identifica o comprador: o mesmo plano pode ser contratado por várias empresas.

## Catálogo informado para revisão

Os nomes abaixo são rótulos internos propostos. Valores são referência das ofertas
informadas pelo usuário, não uma escolha para `planos_saas.valor`.

| Código interno | Nome | Usuários | Mensal (BRL) | Anual (BRL, total por ano) |
| --- | --- | ---: | ---: | ---: |
| SMARTTEC_VISITA_CONNECT | Visita Connect | 2 | 99,90 | 959,04 |
| SMARTTEC_ERP_ESSENCIAL | ERP Essencial | 2 | 119,90 | 1.151,04 |
| SMARTTEC_ERP_PROFISSIONAL | ERP Profissional | 3 | 159,90 | 1.535,04 |
| SMARTTEC_PRIME_CONNECT | Prime Connect | 4 | 219,90 | 2.111,04 |

| Wix planId | Código interno | Ciclo |
| --- | --- | --- |
| 1c973b08-47e1-4dcd-ab73-8cc4a8831fea | SMARTTEC_VISITA_CONNECT | MENSAL |
| 57fe070c-5e20-41a6-b118-6b32773fecf9 | SMARTTEC_ERP_ESSENCIAL | MENSAL |
| 6fec4ea9-a428-4507-be8c-516b3cbda075 | SMARTTEC_ERP_PROFISSIONAL | MENSAL |
| 6522d0b2-63bd-43f9-bb40-cb95154cc2f2 | SMARTTEC_PRIME_CONNECT | MENSAL |
| ca5c9f3b-cd24-45be-866e-7703fa62ab53 | SMARTTEC_VISITA_CONNECT | ANUAL |
| 435f12fb-dcee-4f75-a5eb-af67de7c1720 | SMARTTEC_ERP_ESSENCIAL | ANUAL |
| 73f654cf-9c5b-4b71-8881-4a7cd20fe024 | SMARTTEC_ERP_PROFISSIONAL | ANUAL |
| 76ecce76-0c79-48d0-bb81-a5e22c9f5e8a | SMARTTEC_PRIME_CONNECT | ANUAL |

As quatro ofertas anuais permanecem ocultas no Wix; recorrência anual até
cancelamento, sem período gratuito, conforme retomada. Esses dados não são
publicados nem aplicados.

## Decisões de preparação aprovadas na 4D.13

| Código interno | Produto | Periodicidade do catálogo | Trial (dias) | Valor | Ativo | Usuários |
| --- | --- | --- | ---: | --- | --- | ---: |
| SMARTTEC_VISITA_CONNECT | VISITA_CONNECT | PERSONALIZADO | 0 | NULL | false | 2 |
| SMARTTEC_ERP_ESSENCIAL | ERP_ESSENCIAL | PERSONALIZADO | 0 | NULL | false | 2 |
| SMARTTEC_ERP_PROFISSIONAL | ERP_PROFISSIONAL | PERSONALIZADO | 0 | NULL | false | 3 |
| SMARTTEC_PRIME_CONNECT | PRIME_CONNECT | PERSONALIZADO | 0 | NULL | false | 4 |

Os oito UUIDs e suas correspondências MENSAL/ANUAL foram preservados.
Os produtos são classificações obrigatórias do catálogo, até 50 caracteres no
esquema conhecido; não criam enums nem precisam coincidir com o produto dos módulos.
Preço e ciclo de contratação continuam determinados pela oferta efetivamente
verificada e registrados na assinatura. O valor de referência NULL não é preço
zero e não é aceito como valor de contrato. Os novos planos permanecem inativos.

São valores explícitos da carga. O default histórico de sete dias na estrutura
não é alterado: a carga fornece zero. Nenhum plano antigo é ajustado. Nenhuma
assinatura, módulo, observação ou bloqueio comercial é ativado pela proposta
ou pelo simples recebimento de `Order Purchased`.

## Periodicidade e trial após a 4D.11

- `AdminSubscriptionPanel.tsx` exige escolha explícita de MENSAL/ANUAL para
  novos contratos, sem converter PERSONALIZADO em MENSAL. Trocar plano/ciclo
  limpa o preço; o catálogo não preenche o valor contratado.
- `subscriptions.prepare_contract` grava ciclo e valor explícitos. A entrada
  de contrato, `_period` e os calendários aceitam somente MENSAL/ANUAL.
  Cobrança e confirmação usam o ciclo da assinatura, não o do catálogo.
- Resta uma cópia em `app/routes/admin.py::admin_iniciar_trial`:
  `plano.periodicidade` seria gravado no trial. Para plano ativo com
  `dias_trial` inteiro igual a zero, a proteção 4D.11 responde HTTP 409 antes
  dessa escrita. Plano inativo é recusado antes com HTTP 404.
- Portanto, PERSONALIZADO foi aprovado para ESTES quatro novos planos com
  `dias_trial=0`, sem generalizar segurança para planos antigos com trial permitido.
  Trials/contratos anteriores não são reescritos por esta preparação.
- `payload.dias` ainda tem padrão sete e intervalo 1–30 nos caminhos legados
  permitidos. Trial sem plano ou com configuração desconhecida continua no
  comportamento anterior. Não existe proibição global de trial nesta etapa.

As correções 4D.11 já estão no código local; esta etapa apenas as referencia.
Não altera endpoint, painel, calendário, autenticação ou cobrança.

## Impedimentos de cadastro, distintos da ativação comercial

O checklist da carga distingue decisões de preparação já aprovadas de evidências
ainda necessárias:

| Item | Estado na 4D.13 |
| --- | --- |
| Produto dos quatro planos | Aprovado e preenchido conforme tabela acima |
| Periodicidade do catálogo | PERSONALIZADO aprovado, condicionado a trial zero nos quatro planos e às correções 4D.11 |
| Dias de trial | Zero aprovado e fornecido explicitamente; proteção efetiva limitada ao plano selecionado |
| Composição comercial e integração dos módulos | Base Essencial/Profissional aprovada; Visita/Prime ainda sujeitos à homologação; integração comercial não comprovada |
| Esquema real de destino | Não validado; requer autorização específica para consulta somente leitura |

As três primeiras confirmações declarativas estão verdadeiras no SQL; as duas
últimas permanecem falsas. A referência de revisão completa continua pendente.
Preencher parâmetros não comprova cadastro atual dos módulos, integração ou
esquema real. UP e DOWN também exigem referência de revisão do esquema real.
Todos preservam a exceção incondicional inicial, sem execução autorizada.

`valor=NULL` e `ativo=false` estão aprovados e registrados explicitamente no JSON.
Um plano anterior ativo, com outro valor ou limite NULL será conflito; não será
desativado, sobrescrito ou preenchido automaticamente. Conciliar registros
anteriores exige decisão separada.

O registro histórico `backups/painel_smarttec/fase1_v1_20260929_005448.txt`,
linhas 46–54, documenta estes nove códigos:
- Produto ERP: CLIENTES, ESTOQUE, FINANCEIRO, ORCAMENTOS, PRODUTOS,
  TABELAS_FORNECEDORES e VENDAS.
- Produto SHOWCASE: SMART_SHOWCASE.
- Produto VISITA_TECNICA: VISITA_TECNICA.

Esse registro não prova o catálogo atual do destino. Na mesma fonte,
`plano_modulos_saas` estava vazio: não comprova quais módulos pertencem aos planos.
Não atribuir funcionalidades por nome de categoria nem usar fixtures de testes
como catálogo comercial.

## Composição comercial aprovada e em homologação

| Plano | Composição | Estado |
| --- | --- | --- |
| ERP Essencial | CLIENTES, PRODUTOS, ORCAMENTOS, VENDAS | Base comercial aprovada; conferir códigos/estado no destino antes de vincular |
| ERP Profissional | Essencial + FINANCEIRO | Base comercial aprovada; mesma validação técnica |
| Visita Connect | CLIENTES + VISITA_TECNICA | Sujeita à homologação da integração |
| Prime Connect | Profissional + VISITA_TECNICA + SMART_SHOWCASE | Sujeita à homologação da integração |

Não criar vínculos em `plano_modulos_saas` nesta etapa. Uma futura proposta de
vínculos deve resolver IDs por códigos verificados e detectar conflitos.
Estoque e Tabelas de Fornecedores mantêm a participação planejada sob análise;
ausência de homologação não representa exclusão comercial nem inclusão confirmada.

## Investigação local dos módulos próprios — 4D.13

Inspeção somente leitura; nenhum aplicativo foi iniciado. Não houve build,
testes de aplicação, chamada a Supabase, consulta a banco ou verificação de
disponibilidade de publicação. Não se presume que uma árvore local seja a versão
publicada. A orientação do plugin Supabase foi usada apenas para leitura do código;
nenhum comando de servidor, CLI ou migration foi executado.

### Aplicativo com Visita Técnica e Smart Showcase

Localizado em `C:\Users\valmi\Smart-tec Visita Técnica\frontend`.
Apesar do nome da pasta, o AGENTS.md se identifica como Smart Showcase e o
`src/App.tsx` reúne os dois produtos na mesma aplicação React/Vite.

| Evidência local | Comprovação e limite |
| --- | --- |
| `src/App.tsx:370–409` | Rotas /nova-visita, /smart-showcase, /projetos, /historico e /relatorio-visita/:visitId sob o mesmo ProtectedRoute |
| `src/pages/Home.tsx`, export NovaVisita; conclusão em torno da linha 2056 | Implementação de visita com cliente, ambientes, medições, fotos e conclusão com relatório; não é apenas o item de agenda do ERP |
| `src/pages/SmartShowcase.tsx` e componentes de projeção | Implementação própria de projeção visual, modelos e restauração de projetos; sua existência não comprova homologação de cada recurso |
| `src/auth/AuthContext.tsx:40–94` | Login Supabase, user_profiles vinculado a companies e verificação de usuário/empresa ativos |
| `src/components/ProtectedRoute.tsx:6–53` | Exige sessão, perfil e empresa; não consulta assinatura nem separa direito VISITA_TECNICA de SMART_SHOWCASE |
| `src/auth/authTypes.ts:21–29` | Company.plan usa beta/basic/professional/enterprise, sem correspondência implementada com os quatro códigos internos do ERP |
| `src/services/smartShowcase/supabaseProjectStorageAdapter.ts:120–148,211–215` | Projetos salvos via Supabase em projections, com company_id/created_by_user_id UUID e filtro por empresa |
| `src/services/visitReportStorage.ts` e `visitHistoryStorage.ts` | Relatórios em IndexedDB; histórico/rascunhos em armazenamento local do navegador, além dos projetos remotos |
| `src/pages/HistoryPage.tsx:27–29,75–83` | Lista local sem filtro por companyId nesses trechos; segregação na troca de empresa/usuário precisa de correção ou comprovação específica |
| `frontend/package.json` e `frontend/vercel.json` | Scripts de desenvolvimento/build/preview e configuração de SPA para hospedagem; não comprovam publicação ativa |

Não foi encontrada consulta ao catálogo comercial do ERP, seus vínculos de módulos
ou confirmação financeira no frontend investigado. O guard atual dá aos dois
produtos a mesma condição geral de acesso. Isso não atende, sozinho, à separação
Visita Connect versus Prime Connect.

Existe migration local de proteção de perfis
`supabase/migrations/20260810170500_fix_user_profiles_privilege_escalation.sql`.
Ela não prova aplicação no destino nem comprova as políticas de projects,
projections ou Storage. Filtros do cliente e estado active não são prova de
direito de acesso derivado da assinatura do ERP.

### Outra árvore de Visita Técnica

Também foi localizada `C:\Users\valmi\Smart-tec\src`, cujo package.json
nomeia o projeto smart-tec-visita-tecnica. `src/App.tsx` expõe dashboard e
/nova-visita sem guard de autenticação. `AppLayout.tsx` usa o nome fixo
"Persianas Modelo" e `NovaVisita.tsx::salvarRascunho` apenas atualiza estado
de interface. Essa árvore é preliminar em comparação ao frontend acima e não
deve ser adotada como referência de integração comercial sem confirmação
da versão oficial.

### Compatibilidade de identidade e integrações faltantes

O ERP também verifica tokens Supabase, mas resolve identidade externa para usuário
e vínculo empresarial persistidos: `app/auth/dependencies.py`,
`app/auth/service.py` e `app/tenant/context.py`. Sua empresa interna é INTEGER;
o adaptador dos produtos próprios exige companyId UUID. Não converter nem igualar
esses IDs por suposição. Mesmo provedor não comprova mesmo projeto/issuer/audience.

Antes de liberar acesso comercial:
1. Confirmar a árvore/deployment oficiais e a compatibilidade da origem dos tokens,
   sem copiar credenciais ou presumir sessão compartilhada entre aplicações.
2. Definir mapeamento inequívoco, validado no servidor, entre companies UUID dos
   produtos próprios e empresas INTEGER do ERP, incluindo vínculo do usuário.
3. Definir contrato de autorização por módulo e empresa, derivado de assinatura,
   ciclo, pagamento verificável e concessões aprovadas; não usar Company.plan,
   status active ou Order Purchased como substitutos.
4. Aplicar autorização nos serviços de persistência/Storage/RLS pertinentes,
   além da interface. Os produtos acessam Supabase diretamente: bloquear apenas
   o menu ou adicionar chamada de consulta ao ERP no navegador é insuficiente.
5. Definir expiração/revalidação, suspensão/reembolso e comportamento offline,
   incluindo histórico, rascunhos e relatórios locais; validar isolamento na troca
   de empresa/usuário e preservar dados já existentes.
6. Com autorização específica, comprovar políticas e concessões reais antes dos
   testes de integração. Nenhuma dessas integrações é implementada nesta etapa.

### Estoque e Tabelas de Fornecedores

`ESTOQUE` consta no registro histórico, mas `modulos/estoque.py:64` indica
integração futura; a navegação React não abre página própria de Estoque.
Campos e notificações de estoque em Produtos não comprovam um módulo completo
de movimentação e saldo. Não há evidência suficiente para liberá-lo comercialmente.

`TABELAS_FORNECEDORES` também consta historicamente. Existem CRUD de fornecedores
e importação de produtos/planilhas em `modulos/produtos.py`, mas não foi comprovada
a identidade dessa funcionalidade com um módulo comercial completo de tabelas,
seus direitos e persistência. Confirmar escopo e implementação antes de liberar.

Clientes, Produtos, Orçamentos, Vendas/Pedidos e Financeiro possuem implementação
correspondente no frontend e nas rotas do ERP. Visita Técnica e Smart Showcase
também possuem implementação própria comprovada no código local. Em todos os
casos, o cadastro comercial atual no destino, a disponibilidade publicada e o
fluxo de direitos de acesso permanecem sujeitos à homologação.

São condições separadas de ATIVAÇÃO: vínculo inequívoco empresa–assinatura,
confirmação financeira verificável, coerência da oferta/ciclo/valor, convenção
temporal histórica comprovada, idempotência e tratamento de cancelamentos e
reembolsos. Não transformá-las em campos fictícios da carga de catálogo.
Mesmo que os cinco impedimentos de cadastro sejam resolvidos, a carga não satisfaz
essas condições e não autoriza acesso.

## Compatibilidade com o código atual

- `app/auth/seat_limits.py`: recebe um resolvedor injetado, não lê
  `limite_usuarios` diretamente. Limite ausente não autoriza expansão.
  O novo campo prepara armazenamento; um resolvedor futuro terá de validar
  assinatura/empresa/evidências sem modificar essa interface.
- `app/auth/membership_service.py`: criação e reativação mantêm
  `resolver_limite=None` por padrão. Nenhuma chamada ou rota é alterada.
- `app/tenant/commercial_observer_integration.py`: apenas OFF está habilitado.
  Nenhum observador, pool ou bloqueio é ativado por estes arquivos.
- `app/admin/subscriptions.py`: `prepare_contract` recebe ciclo e valor
  explícitos e cria contrato `PENDENTE`; `_period` aceita apenas MENSAL/ANUAL.
  Não derivar valor/ciclo efetivos do campo genérico do catálogo.
- `app/routes/admin.py`: recusa novo trial para plano com zero explícito antes
  da cópia de periodicidade. Caminhos legados permitidos mantêm payload.dias.
  O catálogo administrativo ainda não expõe `limite_usuarios`.
- `AdminSubscriptionPanel.tsx`: após 4D.11 exige ciclo explícito para novos
  contratos e limpa preço ao trocar plano/ciclo. Contratos existentes preservam
  seus termos e visualização. Nenhum frontend é modificado nesta etapa.
- `app/routes/webhooks_wix.py` e `docs/wix_pricing_plans_webhook.md`:
  webhook diagnóstico sem persistência/provisionamento; constante
  `PLAN_MAPPING` atual referencia os quatro mensais e não lê a nova tabela.
  Ofertas anuais continuam sem integração comercial automática.
- `app/tenant/commercial_evidence.py`: exige evidência financeira e
  convenção temporal comprovada; cadastrar oferta não produz essa evidência.

FastAPI, Streamlit, frontend React e importadores não recebem mudanças de código.
Compatibilidade é avaliação estática dos arquivos locais, não validação do banco
real nem prova de funcionamento da integração futura.

## Segurança, conflitos e reversão

`Order Purchased` não comprova liquidação. Não liberar assinatura, módulos
ou acesso pelo evento, por estado ACTIVE ou por status financeiro isolado.
A futura integração exigirá evidência financeira verificável, coerência de
plano/ciclo/valor e vínculo inequívoco com a empresa, além de idempotência
durável e tratamento de cancelamentos, reembolsos e eventos fora de ordem.

O UP recusa objetos prévios ou estado parcial, em vez de adotá-los com
`IF NOT EXISTS`. Suas pré-condições agora verificam:
- Forma persistente das tabelas, RLS/políticas, tipos, nulidade, defaults e ausência
  de identidade/coluna gerada nas colunas utilizadas; catálogo com as onze colunas históricas.
- PKs individuais e unicidade efetiva de código, índices válidos e não parciais.
- FKs de assinatura e composição de módulos: colunas/destino, tipos, ações,
  correspondência, validação e ausência de adiamento; dependências adicionais bloqueiam.
- Definições efetivas dos CHECKs de periodicidade, trial e valor, e da periodicidade
  da assinatura. Permitir PERSONALIZADO no CHECK não significa aprová-lo comercialmente.
- Gerador `public.planos_saas_id_seq`, default nextval, vínculo OWNED BY e configuração
  histórica inteira; nenhuma leitura de último valor ou ajuste de sequência.
- Ausência de novas estruturas conflitantes, triggers de usuário/regras no catálogo,
  políticas ou event triggers habilitados que exijam análise específica.

As definições de CHECK são copiadas do snapshot local de PostgreSQL 18.6 e comparadas
com `pg_get_constraintdef`, normalizando somente espaços. Diferença de versão ou
formatação pode bloquear a proposta: revisar a evidência real, sem relaxar a checagem
automaticamente. Nomes/defaults/identidade do gerador também exigem confirmação
no destino. Nenhuma dessas premissas foi comprovada em banco nesta etapa.

Após sua futura criação autorizada, o UP registrará no comentário da nova tabela
um JSON com origem `SMARTTEC_ETAPA_4D_10B_V2` e definições efetivas das cinco tabelas:
catálogo, mapeamento, assinaturas, composição de módulos e módulos. Inclui colunas,
defaults, CHECK/FK/PK/UNIQUE, índices, triggers, regras, políticas, ACL, dependências,
configuração do gerador, banco e versão. Não inclui linhas comerciais nem último
valor da sequência. O comentário da própria tabela é excluído da comparação para
evitar autorreferência.

Carga e DOWN usam a mesma consulta estrutural e recusam divergência desse registro,
inclusive mudanças de definição com nomes/quantidades preservados. Marcador antigo,
ausente ou inválido é recusado. Esse JSON é uma referência de origem no mesmo
destino, não um histórico de migrations nem proteção contra adulteração deliberada;
a evidência revisada e a ausência de consumidores externos continuam obrigatórias.
Mudanças legítimas de esquema, permissões ou versão também provocam recusa conservadora.

A carga usa códigos e UUIDs informados. Sob trava transacional das duas tabelas,
conteúdo existente idêntico é preservado; qualquer divergência aborta a instrução
inteira. Não há UPDATE/DELETE nem sobrescrita por conflito. O gerador de IDs pode
deixar lacunas em caso de falha; não corrigir sequência automaticamente.
A carga também confere quatro códigos e oito associações únicas e exige valor NULL
e estado inativo. Composição de módulos e decisões pendentes não são inferidas.
Triggers, permissões, políticas e defaults reais precisam de inspeção prévia.

O DOWN exige origem reconhecida, igualdade das definições efetivas, mapeamento
vazio, todos os limites nulos e ausência de dependências adicionais. Recusa RLS
ou políticas nas tabelas cujos dados seriam verificados, impedindo confiar em
leitura parcial. Não decide pela quantidade/nome de objetos. Não remove os quatro planos nem limpa
mapeamentos para forçar reversão. Depois de uma carga bem-sucedida, ficará
bloqueado pelos próprios dados: preservar e planejar correção futura.
Usa RESTRICT e trava as tabelas; uma falha desfaz a instrução.
O banco não detecta todo consumidor externo ou SQL dinâmico; comprovar ausência
de uso e revisar a forma exata dos objetos antes de autorizar qualquer DOWN.

## Revisão estática e próximo passo mínimo

Conferir quatro códigos, limites 2/2/3/4 e oito UUIDs/ciclos contra a retomada;
verificar marcadores, bloqueios e separação entre estrutura e carga;
conferir restrições propostas com o snapshot e os consumidores locais.
Esta revisão não inclui execução SQL, conexão, parse pelo servidor ou ensaio de rollback.

Próximo passo mínimo: confirmar a versão oficial dos produtos próprios e autorizar,
separadamente, validação somente leitura do esquema e códigos de módulos no destino.
Os parâmetros de preparação e a base Essencial/Profissional já estão aprovados;
não reabrir essas decisões. Visita/Prime dependem da integração comercial descrita
acima. Depois, preparar proposta de vínculos por códigos e plano de autorização,
ainda sem executar SQL ou liberar acesso.

A homologação de cadastro inativo é distinta da homologação de acesso: nenhuma
carga de catálogo comprova identidade empresarial ou direito de uso nos produtos.
Os bloqueios SQL permanecem até autorização expressa de execução. Esta revisão
não inclui parse pelo servidor, ensaio de UP/carga/DOWN ou build dos módulos próprios.
Encerrar esta etapa aqui; nenhuma alteração adicional está autorizada.
