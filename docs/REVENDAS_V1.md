# Revendas V1 — cadastro completo

## Persistência e compatibilidade

A migration `20261102_revendas_cadastro_completo_v1_up.sql` adiciona 21 colunas
à `public.parceiros_comerciais`, com preflight explícito para a tabela e a
referência tenant de `public.funcionarios`. Confere tipo, nulabilidade e
default de colunas existentes; valida constraints e índice parcial por
empresa/vendedor e restringe CEP persistido a oito dígitos. A migration é
aditiva, não copia nem infere dados e não executa preflight contra um baseline
de staging. A reversão remove somente colunas, constraints e índice dessa
versão; ela perde os valores preenchidos nessas colunas.

Os endpoints existentes de parceiros permanecem sob `/representantes/parceiros`.
O `POST` continua aceitando o payload rápido legado `{ "nome": "..." }`.
`GET /representantes/parceiros/{id}` consulta somente o tenant atual e
`PATCH /representantes/parceiros/{id}` atualiza apenas propriedades enviadas.
Campos opcionais explicitamente enviados como `null` são limpos; os campos
financeiros sem nulabilidade e os booleanos não aceitam `null`.

`tipo_pessoa` e `tipo_contribuinte` usam os valores definidos pelo contrato;
`situacao_cadastral` não substitui `ativo`. UF, contribuição/isencão e valores
financeiros são validados no backend. Documentos informados manualmente são
normalizados, mas não precisam passar por checksum para salvar o cadastro.
`limite_credito = null` representa limite
não definido e zero é um limite definido igual a zero.

## Consultas de cadastro

As rotas autenticadas `POST /consultas/cnpj` e `POST /consultas/cep` consultam
exclusivamente provedores permitidos pelo backend:

| Variável | Padrão | Alternativa |
| --- | --- | --- |
| `SMARTTEC_CNPJ_CONSULTA_PROVIDER` | `brasilapi` | `off` |
| `SMARTTEC_CEP_CONSULTA_PROVIDER` | `viacep` | `off` |

Adapters tipados separados integram BrasilAPI e ViaCEP. As chamadas usam
endpoints fixos, sem aceitar URL, host ou caminho enviado pelo cliente, e têm
timeout; documento/CEP retornado é comparado com a consulta. Respostas são
validadas por schema explícito (tipos, limites, CEP e UF); dados malformados
resultam em 502. A resposta limita os dados a campos cadastrais
permitidos e contém `dados`, `fonte` e `consultado_em`. No envelope CNPJ, o
telefone de origem é retornado em `telefone_comercial`; a tela o mapeia para a
coluna legada `telefone` ao salvar. O corpo de criação/edição permanece usando
os nomes canônicos `telefone`, `percentual_padrao`, `ativo` e `observacao`.
Ausências do provedor
permanecem ausentes — especialmente inscrição estadual e número de endereço;
não são inferidas. A rota CNPJ aceita identificadores numéricos ou alfanuméricos,
normaliza para maiúsculas e confere dígitos verificadores com valores ASCII-48,
pesos decrescentes de 2 a 9 e repetição em 9. A rota CEP exige oito dígitos.
Inscrição estadual só é retornada quando existe exatamente um registro ativo
com UF igual à UF validada do estabelecimento; registros inativos, de outra UF
ou ambíguos são omitidos.

Vendedor responsável é validado pela associação ao tenant, não pelo status ativo.
Assim, um vendedor existente que foi inativado continua selecionável quando já
está associado ao cadastro; vendedores de outra empresa permanecem rejeitados.

Respostas do provedor não são persistidas automaticamente. A aplicação cliente
decide se e quais dados pré-preencher; nenhuma credencial de consulta é enviada
ao frontend.

## Validação local

Backend, a partir da raiz:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_revendas_v1 -v
```

A suíte usa banco simulado e mocks de HTTP. A importação da API também foi
verificada com conexões SQLAlchemy e requisições HTTP bloqueadas, sem abrir
conexão com banco. As migrations não foram executadas.

Frontend:

```powershell
cd frontend-erp
node tests\revendas.test.cjs
node tests\budgetPdf.test.cjs
npm run build
```

Os testes Node e o build passaram. O harness isolado
`frontend-erp/tests/revendas.browser.html` e
`frontend-erp/tests/revendas.browser.tsx` foi executado via Vite local, usando
somente mocks de fetch; o servidor foi parado após a execução. Eventos React
reais verificaram preservação de razão social manual em consulta CNPJ atrasada,
preservação de logradouro/número manuais na consulta CEP, proteção de dados
existentes contra sugestões, crédito null versus zero e gravação manual após
falha de consulta. Nenhuma chamada real a CNPJ, CEP ou backend foi realizada.

O formulário usa os 21 campos canônicos e mantém a distinção entre null e zero.
UF é validada pela aplicação; não foi adicionada constraint de UF no banco.

Regressão comercial: a suíte Revendas junto às suítes de composição comercial de
pedidos e precificação de orçamentos passou com 41 testes. Essas suítes usam
fixtures locais; `PYTHONPATH` deve incluir a raiz e a pasta `tests`.
O build mantém o aviso já existente de bundles acima de 500 kB.

Antes de publicar esta versão, aplicar a migration UP aprovada no destino e
validar os cadastros. O código novo de gravação depende das colunas V1; não
publicar o frontend/backend novo sobre o schema antigo. A disponibilidade real
dos provedores não foi testada nesta etapa; falhas não impedem cadastro manual.

## Aplicacao temporaria protegida

`POST /diag/run-revendas-v1-up` aceita somente request sem corpo/query, com
`X-Diagnostic-Token` correspondente a `DIAG_DB_TARGET_TOKEN` no backend.
Sem token configurado a rota fica desabilitada. Remover a rota e o segredo
apos aplicar e validar a publicacao.

O executor usa exclusivamente o UP fixo desta versao, com SHA-256 revisado
(normalizando apenas CRLF/LF). Usa a engine interna, exige
`current_database() = smarttec_erp_staging`, verifica colunas preexistentes e
preserva a contagem de parceiros sob lock na mesma transacao do DDL. Apos
COMMIT confere as 21 colunas, constraints, indice e contagem em READ ONLY.
Falha pos-COMMIT e reportada como grave; nao reverte a migration aplicada.
Executar em janela sem cadastros concorrentes para evitar divergencia de
contagem durante a conferencia posterior. Nenhum DRY RUN separado foi criado.

Teste simulado:
`.\.venv\Scripts\python.exe -m unittest tests.test_diag_revendas_v1_up`.
Criar a rota nao executa a migration. Nao chamar este endpoint sem autorizacao.

## Modal e cobertura de dados CNPJ

O modal de Revendas usa portal em `document.body`, header/footer fora do corpo
rolavel, layout flex e limite pela viewport (`vh`/`dvh`). Apenas
`.revenda-modal-body` possui rolagem vertical. O fundo fica travado durante a
abertura; posicao de rolagem, estilos inline e foco anterior sao restaurados ao
fechar. Os estilos sao exclusivos de Revendas, sem mudar outros cadastros.
O modal tem altura definida limitada pela viewport. O corpo usa
`overflow-y: scroll`, trilho cinza e thumb contrastante; em navegadores WebKit
a largura e de 14px. Sistemas que usam scrollbars sobrepostas ainda podem
controlar sua visibilidade conforme a preferencia do sistema operacional.

Validacao local no harness com mocks: viewport 1366x650, wheel, arraste da barra,
PageDown, acesso a Observacoes e header/footer imoveis; viewport 390x667 sem
overflow horizontal e com campos inferiores acessiveis. Fundo inicialmente
rolado em 400px voltou a 400px depois de fechar.

Validacao adicional pela entrada real `index.html`/`App`, via menu Revendas e
Nova revenda (nao pela pagina do harness): 1366x650 com wheel, arraste da barra
e PageDown; header/footer permaneceram em y=16/y=561. Em 390x667, modal entre
y=8 e y=659, barra com 15px no Chromium, sete blocos acessiveis, Fiscal e
Financeiro expandidos e Observacoes editavel. Chamadas HTTP foram substituidas
por respostas sinteticas no navegador; nao houve banco nem salvamento real.
Foi validado preenchimento de contatos/endereco, preservacao de nome fantasia
e email editados durante consulta e aviso de campos ausentes na fonte.
Isso nao substitui validacao da versao publicada em staging apos autorizacao
de publicacao.

O adapter BrasilAPI le `nome_fantasia` e `email`; string vazia ou null nao
e convertida em dado ficticio. O frontend preserva campos manuais e informa
quais campos prioritarios a fonte nao retornou. Os dois telefones sao
aproveitados em `telefone_comercial`, separados por ` / `, sem duplicar numeros
equivalentes nem presumir que o segundo e celular. O tipo de logradouro
e acrescentado quando retornado e ainda nao presente no logradouro.
Situacao numerica RFB e normalizada quando nao houver descricao textual.
O endereco restante e mapeado diretamente quando disponivel. Nao ha captura
do payload especifico consultado em staging; nao se pode afirmar quais valores
a fonte forneceu naquela consulta.

A implementacao publica atual da BrasilAPI encaminha CNPJ ao Minha Receita;
usar Minha Receita como segunda fonte nao representa enriquecimento independente.
Um adapter CNPJa e candidato a fallback, sujeito a aprovacao, cobertura e limites
do plano. Nenhum segundo provider foi implementado nesta etapa. Consultas de
documentacao publica nao executaram consultas empresariais nem acesso a banco.
