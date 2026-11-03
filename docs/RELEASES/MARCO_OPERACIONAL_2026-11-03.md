# Marco operacional local - 2026-11-03

Ambientes documentais: **SMARTTEC-PERSIANAS-OPERACIONAL** (finalidade dos dados)
e **SMARTTEC-DEV-LOCAL** (execucao). Nao e release publicada.
Identificacao dos cinco ambientes, evidencias e checklist:
[Registro mestre](../REGISTRO_MESTRE_AMBIENTES.md).

## Identidade do snapshot

- Repositorio: `Smart-tec-sys/Smart-tec-erp`.
- Branch local: `seguranca/marco-operacional-2026-11-03`, criada de `staging`.
- Commit-base: `b1828e1ca96fbc7f20aacc53bc96d696489ff4f4`.
- Commit deste marco: commit que adiciona este documento. Resolucao exata:
  `git log -1 --format=%H -- docs/RELEASES/MARCO_OPERACIONAL_2026-11-03.md`.
  O recibo externo pos-commit grava o SHA final sem autorreferencia circular.
- Banco real confirmado somente em leitura: `smarttec_erp_dev`,
  `localhost:5432`, PostgreSQL 18.6, 3.866 produtos.
- Frontend `http://127.0.0.1:5188/`; API `http://127.0.0.1:8000/`.
- Nenhuma alteracao de conexao, gravacao operacional ou migration nesta tarefa.

## Codigo preservado

### Orcamentos de Cortinas

Fluxo cliente/tecido/modelo/medidas/componentes/calculo/salvar/reabrir/PDF,
tabelas Consumidor Final x2,5, Varejo x2 e Decorador x1,5 preservadas.
Conversao explicita de embalagem calcula custo por unidade sem alterar produto.
Base opt-in da costureira por altura cortada; sem opt-in, legado preservado.
Instalacao e componentes mantem valores salvos; exportacao nao grava no banco.
Detalhes: [Orcamentos e PDF local](../ORCAMENTOS_CORTINAS_PDF_LOCAL.md).

### Tres PDFs com separacao automatica

- Cliente Final: dados comerciais, tecido/cor, ambientes reconhecidos,
  medidas, precos finais, pagamento, prazo e garantia; sem base industrial,
  custos, acrescimo do parceiro, percentuais internos ou ficha de fabricacao.
- Revenda: base Smart-tec, acrescimo comercial, preco final e repasses,
  sem custos de fabricacao, costureira, componentes, resultado ou instrucoes.
- Interno Smart-tec: observacoes comerciais/internas, ficha tecnica por
  peca, componentes, consumo, embalagem, mao de obra e custos salvos.
- Allowlist de dados externos; blocos canonicos de pagamento e repasse
  conferidos. Textos nao classificados sao omitidos com aviso, nao copiados.
- Rateio de precos finais por item fecha centavos com o total aprovado,
  somente na apresentacao. Nao altera registros ou condicoes comerciais.
- Tres PDFs do orcamento 1006 gerados pelo renderer atual, abertos e
  conferidos em todas as paginas; exclusao de dados privados nos externos
  validada por texto extraido. PDFs e snapshots privados ficam fora do Git.

### Regras comerciais

Multiplicador Decorador e acrescimo da revenda sao conceitos separados.
Parceiro acrescenta percentual SOBRE base Smart-tec, nao divide recebido/lucro.
Exemplo de regressao: base 1.000 + 50% (500) = 1.500; cartao com acrescimo
simples de 7,2% = 1.608, em 3x536. Desconto proporcional 5%: cliente 1.425,
Smart-tec 950 e parceiro 475. Reserva financeira nao e lucro da fabrica;
tarifa efetiva depende de conciliacao. Regra global legada por dentro preservada.
Atualizacao especifica de condicoes usa tenant, lock e guardas contra
concorrencia, sem recriar itens ou alterar outros orcamentos.

### Revendas V1

Cadastro completo, modal com rolagem, preenchimento assistido e protecao de
campos manuais. BrasilAPI principal, CNPJa complementar somente com opt-in,
tambem em 429/timeout/indisponibilidade temporaria. CNPJ retornado validado,
nome fantasia vazio preservado, celular nao inferido. Timeout, bloqueio
temporario e cinco consultas/minuto por processo, sem logar contatos.
Endpoint compartilhado e consumidores sem opt-in preservados. Testes usam mocks.
Detalhes e limites: [Revendas V1](../REVENDAS_V1.md).

### Producao V1 e etiquetas

OP ligada a venda/empresa ativa, confirmacao explicita com usuario/data/hora,
pecas individualizadas e unicidade. Venda cancelada bloqueada; concluida
pode gerar OP mediante confirmacao sem duplicidade. Etapas aguardando, corte,
montagem, conferencia e concluida, sem alterar status comercial.
Ficha e bloqueios por insumos/calculos incompletos; sem baixa/reserva de estoque,
sem efeitos em financeiro ou OS. Etiqueta reutiliza layout existente,
com escape HTML e Streamlit importado apenas nas funcoes de tela.
Detalhes: [Producao V1](../PRODUCAO_V1.md).

`20261103_producao_v1_up.sql` e DOWN sao codigo preparado, NAO executado.
`ordens_producao` e `producao_pecas` nao instaladas no banco local confirmado.
Sem instalacao, API deve informar indisponibilidade explicitamente.

## Validacao deste marco

Data: 2026-11-03 UTC-03. Sem chamadas reais repetitivas a provedores CNPJ.

- Backend: **198 testes e 49 subtestes aprovados**, cobrindo Cortinas/custos,
  precificacao/composicao, condicoes da revenda, salvar/reabrir, Revendas/CNPJ
  e Producao/documentos/etiquetas. SQLite em memoria e HTTP simulado.
- A primeira coleta falhou por `httpx` ausente no Python global. Reexecucao
  aprovada reutilizando dependencia isolada ja existente na sessao, sem
  instalacao e sem alterar manifests.
- Frontend: **15 scripts aprovados**, Cortinas/PDF, Revendas e Producao.
- `npm run build`: TypeScript/Vite aprovados. Aviso conhecido bundles >500 kB.
- `/health` local: `ok`; frontend HTTP 200.
- Tres PDFs reais validados na etapa anterior: Cliente1 pagina,
  Revenda2 paginas e Interno3 paginas A4; nenhum dado alterado na exportacao.

Comandos de referencia (raiz; dependencias de teste devem estar disponiveis):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH="$PWD\tests;$PWD"
python -m pytest -q -p no:cacheprovider --disable-warnings tests\test_cortina_componentes_livres.py tests\test_cortina_custo_motor.py tests\test_orcamento_cortina_pdf_local.py tests\test_condicoes_revenda.py tests\test_orcamento_precificacao_fase7s.py tests\test_orcamento_precificacao_backend_fase8b21.py tests\test_revendas_v1.py tests\test_cnpj_enriquecimento.py tests\test_producao_v1.py
Set-Location frontend-erp
$tests=Get-ChildItem tests -File | Where-Object { $_.Name -match '^(curtain.*|budgetPdf|revendas|producao)\.test\.cjs$' } | ForEach-Object { $_.FullName }
node --test $tests
npm run build
```

## Backups e recuperacao

Backups privados criados antes dos documentos deste marco, em
`C:\Users\valmi\Smarttec-backups\MARCO_OPERACIONAL_2026-11-03_20261103T131520-0300`.
Data: 2026-11-03T13:15:33-03:00.

| Tipo / arquivo | Bytes | SHA-256 |
| --- | ---: | --- |
| Codigo atual / SMARTTEC-DEV-LOCAL_codigo_pre_marco.zip | 1204060 | `a776666ef029588cb006301410350ced016cbaaca63ce793c506c5b0c44dfc73` |
| Historico / SMARTTEC-DEV-LOCAL_historico_pre_marco.bundle | 1697475 | `1e8116340f827fbe264d7cb0ad1f4d249ac3f6deb06585395c5d7566ade1e81c` |
| Banco / SMARTTEC-PERSIANAS-OPERACIONAL_smarttec_erp_dev.dump | 989809 | `e7cee45e36e835092038721065f101cafb2ab190d0d2b401adecb2155a355ce4` |

ZIP com CRC e hashes individuais conferidos; bundle com `git bundle verify`;
dump custom com `pg_restore --list` e descompressao/leitura integral aprovados.
Nenhuma restauracao real executada. Nao afirmar recuperacao funcional validada.
`manifesto-backups.json` contem inventario/hash por arquivo; recibo externo
`recibo-marco-local.json` e bundle pos-commit identificam o marco final.
Nao incluir esses arquivos, `.env`, dumps, planilhas ou PDFs no Git.
Arquivos locais anteriores excluidos permanecem no worktree, sem exclusao/reversao.
O ZIP nao inclui dados/segredos nem todo arquivo local nao classificado.

## Pendencias e gates de publicacao

1. Validar restauracao em banco descartavel autorizado e manter copia offline.
   Configuracao secreta deve ser recuperada de fonte privada, nunca deste Git.
2. Confirmar banco/host, commit e conexao real frontend/API de cada destino;
   producao independente de assinantes permanece NAO CONFIRMADA.
3. Homologar autenticacao, isolamento de empresas, Revendas, PDFs e Wix.
   Nao inferir prontidao de publicacao a partir de testes locais/mocks.
4. Producao: revisar e autorizar migration separadamente, testar persistencia
   PostgreSQL/autenticacao; receitas incompletas continuam bloqueadas.
5. Escala CNPJ: controle compartilhado entre instancias/cache e provedor
   profissional continuam pendentes; limite atual nao serve a milhares de assinantes.
6. Etiquetas: validar impressao fisica, QR opcional e identificacao industrial.
7. Vincular ID ambiente + SHA aprovado + banco confirmado + backup recuperavel
   + testes; aprovar migration/push/deploy separadamente. Auto-Deploy On Commit
   de staging exige cuidado; esta branch de seguranca nao foi publicada.

Este commit preserva codigo/documentacao, nao transforma recursos locais em
producao. Nenhuma migration, importacao, push ou deploy foi executado.
