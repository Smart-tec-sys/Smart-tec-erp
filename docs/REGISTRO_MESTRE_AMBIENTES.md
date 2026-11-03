# Registro mestre de ambientes Smart-tec ERP

Ultima verificacao: 2026-11-03, America/Sao_Paulo (UTC-03).
Este registro e documental: nao renomeia servicos, bancos, repositorios ou branches.
Sem credenciais, URLs de conexao completas, contatos ou dados de clientes.

## Identificacao permanente

| ID documental | Finalidade | Situacao comprovada |
| --- | --- | --- |
| SMARTTEC-PERSIANAS-OPERACIONAL | Operacao da fabrica Smart-tec Persianas | Referencia operacional local em `smarttec_erp_dev`; servico operacional remoto: **NAO CONFIRMADO** |
| SMARTTEC-ASSINANTES-PRODUCAO | Producao comercial multiempresa dos assinantes | Destino de producao independente: **NAO CONFIRMADO**; nao classificar o site com nome "assinantes" como producao apenas pelo nome |
| SMARTTEC-STAGING | Homologacao antes de producao | Frontend Render confirmado na branch `staging`; vinculo real da API/banco remoto: ver limites abaixo |
| SMARTTEC-BETA-LEGADO | Demonstracao Beta separada, nao operacional | Repositorio/servico separados informados anteriormente; configuracao atual nao revalidada neste marco |
| SMARTTEC-DEV-LOCAL | Desenvolvimento, testes e validacao local | Frontend/API locais ativos; PostgreSQL local confirmado em leitura |

Dois IDs podem referenciar a mesma instalacao fisica em papeis distintos:
OPERACIONAL identifica a finalidade dos dados da fabrica; DEV-LOCAL identifica
a execucao atual. Isso nao comprova um ambiente operacional remoto separado.
O banco com dados reais nao e banco descartavel de teste.

## Vinculos, infraestrutura e versoes

### SMARTTEC-PERSIANAS-OPERACIONAL

- Banco real local confirmado: PostgreSQL `smarttec_erp_dev`.
- Servidor: `localhost:5432` (conexao confirmou IPv6 loopback `::1`), PostgreSQL 18.6.
- Catalogo: 3.866 produtos na leitura deste marco.
- Repositorio local: `Smart-tec-sys/Smart-tec-erp`.
- Execucao atual compartilhada com DEV-LOCAL: frontend `http://127.0.0.1:5188/`,
  backend `http://127.0.0.1:8000/`, FastAPI `app.main:app`, frontend React/Vite.
- Branch de preservacao: `seguranca/marco-operacional-2026-11-03`.
- Commit-base: `b1828e1ca96fbc7f20aacc53bc96d696489ff4f4`.
- Commit do codigo preservado: commit que adiciona o marco abaixo; sua
  identidade Git e o recibo pos-commit identificam o snapshot sem hash circular.
- Frontend/backend/banco operacionais remotos: **NAO CONFIRMADO**.
- Backup e validacoes: mesmos artefatos locais abaixo. Nao copiar estes dados
  para assinantes, staging ou Beta sem plano de isolamento e autorizacao.

### SMARTTEC-ASSINANTES-PRODUCAO

- Finalidade: producao multiempresa; banco, host, repositorio/branch/commit
  de um destino de producao independente: **NAO CONFIRMADO**.
- URL em uso pelo usuario:
  `https://smart-tec-erp-assinantes-web.onrender.com/`.
  O painel atual vincula esse servico a `staging`; portanto seu mapeamento
  comprovado neste registro e SMARTTEC-STAGING, nao producao independente.
- Backend, banco real, ultima validacao funcional e backups de producao:
  **NAO CONFIRMADO**. Nao promover o dump operacional local para esse destino.

### SMARTTEC-STAGING

- Frontend: Render Static Site `smart-tec-erp-assinantes-web`,
  ID existente `srv-dbhhjiou01pc73bbuqvg`.
- URL: `https://smart-tec-erp-assinantes-web.onrender.com/`.
- Painel consultado em 2026-11-03: repositorio `Smart-tec-sys/Smart-tec-erp`,
  branch `staging`, ultimo commit publicado exibido:
  `b1828e1ca96fbc7f20aacc53bc96d696489ff4f4`.
- Auto-Deploy **On Commit**, conforme confirmacao do usuario nesta sessao.
  Push nessa branch pode publicar automaticamente. Nenhum push autorizado neste marco.
- URL de API conhecida: `https://smart-tec-erp-staging.onrender.com/`;
  pagina compartilhada exibe resposta da API. Isso nao comprova qual API esta
  embutida no bundle frontend atual.
- API: repositorio, branch, commit implantado e vinculo efetivo com frontend:
  **NAO CONFIRMADO nesta verificacao**.
- Banco remoto: `smarttec_erp_staging` aparece como destino esperado no
  executor de diagnostico documentado em [Revendas V1](REVENDAS_V1.md);
  nome real via conexao ativa e servidor: **NAO CONFIRMADO neste marco**.
- Nao confundir esse nome esperado com `smarttec_erp_dev` ou com o recurso
  historicamente citado `smarttec-erp-beta-db`.
- Funcionalidades locais deste marco publicadas: **NAO CONFIRMADO**;
  o snapshot local diverge do commit publicado.
- Backups remotos e ultima validacao integrada autenticada: **NAO CONFIRMADO**.

### SMARTTEC-BETA-LEGADO

- Repositorio informado na sessao: `Smart-tec-sys/Smart-tec-erp-beta`.
- Frontend informado/URL compartilhada:
  `https://smart-tec-erp-beta-web.onrender.com/`.
- Branch, commit, backend conectado, banco real/host, estado atual dos
  bloqueios demo e backups: **NAO CONFIRMADO neste marco**.
- Nao usado na validacao operacional. Nao importar dados reais, reutilizar
  conexoes ou remover isolamento da demonstracao.

### SMARTTEC-DEV-LOCAL

- Pasta: `C:\Users\valmi\Smart-tec ERP`.
- Repositorio: `Smart-tec-sys/Smart-tec-erp`; branch de origem `staging`.
- Branch atual de seguranca: `seguranca/marco-operacional-2026-11-03`.
- Base Git: `b1828e1ca96fbc7f20aacc53bc96d696489ff4f4`.
- Codigo do marco e documento: [MARCO_OPERACIONAL_2026-11-03](RELEASES/MARCO_OPERACIONAL_2026-11-03.md).
  Para obter seu commit exato:
  `git log -1 --format=%H -- docs/RELEASES/MARCO_OPERACIONAL_2026-11-03.md`.
- Banco, servidor e URLs: mesmos confirmados em OPERACIONAL.
- Auth DEV somente loopback; nao equivale a homologacao autenticada publicada.
- Ultima validacao 2026-11-03: API `/health` retornou `ok`; frontend HTTP 200;
  198 testes backend + 49 subtestes, 15 scripts frontend e build aprovados.
- Situacao: alteracoes locais preservadas; nao publicadas por esta execucao.

## Funcionalidades e limites atuais

| Area | Pronto localmente | Pendente |
| --- | --- | --- |
| Orcamentos/Cortinas | Fluxo de calculo, salvar/reabrir, embalagem, custo por altura e tabelas comerciais | Homologacao autenticada no destino antes de publicar |
| PDFs | Cliente Final, Revenda comercial e Interno Smart-tec separados por projecao; precos/repasses/sigilo testados | Textos legados sem estrutura reconhecida exigem revisao/avisos; nao inferir condicoes ausentes |
| Revendas V1 | Modal/scroll, cadastro, protecao manual, BrasilAPI principal e CNPJa opt-in com resiliencia | Limite compartilhado/cache/provedor profissional antes de escalar; confirmar schema e publicacao de cada destino |
| Producao V1 | Codigo preservado; `PRODUCAO_V1_ENABLED` e `VITE_PRODUCAO_V1_ENABLED` desligadas por padrao, rotas bloqueadas antes de banco/tenant e controles ocultos | Migration preparada NAO executada; tabelas `ordens_producao`/`producao_pecas` nao instaladas; habilitar somente apos implantacao propria e validacao PostgreSQL autenticada |
| Etiquetas | Gerador/layout existente reutilizado, escape e testes de documento | Impressora fisica/QR opcional e codigo de barras industrial nao certificados nesta etapa |

## Backups privados deste marco

Criados em 2026-11-03 entre 13:15:20 e 13:15:34 UTC-03.
Diretorio fora do Git:
`C:\Users\valmi\Smarttec-backups\MARCO_OPERACIONAL_2026-11-03_20261103T131520-0300`.

| Arquivo | Bytes | SHA-256 |
| --- | ---: | --- |
| SMARTTEC-DEV-LOCAL_codigo_pre_marco.zip | 1204060 | `a776666ef029588cb006301410350ced016cbaaca63ce793c506c5b0c44dfc73` |
| SMARTTEC-DEV-LOCAL_historico_pre_marco.bundle | 1697475 | `1e8116340f827fbe264d7cb0ad1f4d249ac3f6deb06585395c5d7566ade1e81c` |
| SMARTTEC-PERSIANAS-OPERACIONAL_smarttec_erp_dev.dump | 989809 | `e7cee45e36e835092038721065f101cafb2ab190d0d2b401adecb2155a355ce4` |

- ZIP: estado atual do codigo antes destes dois documentos; CRC e SHA-256
  por arquivo conferidos contra a origem. Exclui `.env` e variantes,
  planilhas, CSV, PDFs, bancos/dumps e arquivos locais nao classificados.
- Bundle inicial: historico Git anterior; `git bundle verify` aprovado.
  Historico pode conter dados legados: backup privado, nunca publicar como artefato.
- Dump PostgreSQL formato custom: `pg_restore --list` e leitura/descompressao
  integral aprovadas. `pg_dump` executado com transacoes somente leitura.
  Contem dados reais e exige armazenamento/acesso privado.
- Manifesto privado: `manifesto-backups.json`, mesmo diretorio, com data,
  caminhos, hashes e verificacoes. Nao inclui credenciais.
- Restauracao real: **NAO EXECUTADA**. Integridade de arquivo nao comprova
  recuperacao funcional. Testar restauracao somente em destino descartavel
  explicitamente autorizado.
- O bundle pos-commit e `recibo-marco-local.json` no mesmo diretorio vinculam
  o commit final ao backup inicial; nao e possivel embutir o proprio hash de
  commit em seu conteudo. Conferir recibo e `git bundle verify` antes de recuperar.
- Configuracao secreta e arquivos locais excluidos NAO sao recuperados pelo
  ZIP; manter `.env` existente privado e registrar acesso ao cofre antes de
  restaurar em outra maquina. Nenhum segredo foi copiado ao Git.
- Copia externa/offline e teste de restauracao: **PENDENTES**. Backup no mesmo
  disco nao protege contra perda fisica da maquina.

## Checklist curto de publicacao

- [ ] Registrar ID documental do destino, servicos/URLs e empresa/tenant.
- [ ] Conferir repositorio, branch e SHA exato aprovado; revisar Auto-Deploy.
- [ ] Confirmar banco real e servidor sem credenciais, isolamento e schema.
- [ ] Vincular backup do destino, data, caminho, tamanho, SHA-256 e recuperacao.
- [ ] Reexecutar testes/build do commit e validar autenticacao, PDFs externos,
      Revendas, Wix e bloqueios de Producao no destino.
- [ ] Obter autorizacoes separadas para migration, push e deploy; registrar
      plano de rollback, commit anterior e verificacoes pos-publicacao.

Nenhum recurso foi renomeado; nenhuma conexao foi alterada. Nenhuma migration,
importacao, restauracao, push ou deploy faz parte deste marco.
