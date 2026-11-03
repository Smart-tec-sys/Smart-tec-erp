# Orcamentos de Cortinas e PDF local

## Acesso

Usar o frontend atual do repositorio principal com `VITE_API_URL` apontando
para a API local. O ambiente validado usa `http://127.0.0.1:5188` e API
`http://127.0.0.1:8000`, modo DEV local, empresa 1 do `smarttec_erp_dev`.
Nao usar modo DEV em servico publicado ou expor essas portas na rede.

Fluxo: Orcamentos > Novo orcamento > selecionar tabela comercial > cliente >
Cortina de tecido > fornecedor/colecao/tecido > modelo, medidas e cor >
adicionar componentes e quantidades por peca > conferir simulacao > salvar >
acoes do orcamento > visualizar > Gerar PDF.

## Tabelas preservadas

- Consumidor Final: custo calculado x 2,5.
- Varejo: custo calculado x 2,0.
- Decorador: custo calculado x 1,5.

Nenhum multiplicador foi alterado. Em novo orcamento a tabela exige selecao
explicita antes de salvar; valores anteriores a essa selecao sao provisorios.
Na reabertura, a tabela vem do documento salvo. PDF recarrega o documento
persistido antes de exportar, e mostra a tabela comercial, tecido, modelo,
cor, medidas, quantidade em unidades, preco por peca e total.
Orcamentos antigos sem perfil mostram "Nao informada", sem inventar uma tabela.

O PDF em modo autenticado continua usando a sessao e os vinculos existentes.
Em DEV consulta `/empresa/atual`, com o mesmo contexto de empresa da API;
nao simula login, nao escolhe outra empresa nem relaxa autenticacao publicada.

## Validacao e limites

Teste integrado de salvar/reabrir usa somente SQLite em memoria, catalogo
e cliente ficticios. A numeracao PostgreSQL e substituida somente nesse teste.
Teste de PDF pode consumir as fixtures ficticias persistidas usando
`CURTAIN_PDF_FIXTURE_OUTPUT`, sem acessar dados reais.

Cenario: duas cortinas 2 x 2 m, fator 2,5, tecido 3 m, cabeca 10 cm, barra
dupla de 15 cm; tecido 4,8 m por peca, custo tecido 48, trilho 40,
rodizios 10, entretela 5 e mao de obra 70: custo 173 por peca.
Totais: Decorador 519; Varejo 692; Consumidor Final 865, sem descontos.
Sao valores sinteticos de teste, nunca proposta para a cliente real.

Nao foram criados cadastros, orcamentos ou outros registros no PostgreSQL
durante a validacao. O usuario pode salvar um novo orcamento real apos conferir
cliente, tecido/cor, largura real do rolo, modelo, medidas, acessorios,
quantidades e tabela. Os componentes sao selecionados manualmente conforme
o fluxo existente; nao ha inclusao automatica ou nova receita de fabricacao.
Transporte e pagamento continuam com as limitacoes sinalizadas na tela.
No Orcamento, cada componente pode informar opcionalmente `Unidades por
embalagem`. Quantidade por peca continua em unidades individuais; o backend
divide o custo cadastrado pelo tamanho inteiro positivo da embalagem, sem
aceitar custo enviado pelo navegador. Exemplo: pacote de 500 a custo 50,
64 rodizios por peca => custo unitario 0,10 e custo total 6,40.
Sem conversao informada, o comportamento anterior permanece identico.
O fator e os custos calculados ficam no JSON tecnico salvo/reaberto, sem
migration nem alteracao do produto ou estoque. Trocar o produto limpa o fator
para nao reutilizar embalagem de outro componente. A entrada de conversao
fica habilitada somente no Orcamento, nao na tela de Venda. A conversao nao
constitui validacao de receita para liberar fabricacao.
O Orcamento tambem permite selecionar explicitamente a base da costureira:
`ALTURAS_TECIDO` cobra 35 por altura cortada (`ceil(largura * fator /
largura_tecido)`), por peca. A base fica em `baseMaoObra` no JSON tecnico e
e recalculada no servidor. Sem selecao, documentos anteriores conservam a
regra `ALTURA_VERTICAL_150` (altura vertical / 1,50, arredondada acima).
Exemplo confirmado: larguras 3,63 / 3,20 / 1,60, fator 2,5 e tecido 3 m
resultam em 4 / 3 / 2 alturas, custos de costureira 140 / 105 / 70.
Nao foram executadas migrations, importacoes, publicacoes ou alteracoes em
Revendas, Producao, etiquetas ou Wix nesta correcao.

## Complementos de custo: arquivos e verificacao

- [cortina_simulacao.py](../app/services/cortina_simulacao.py): conversao de
  embalagem e base explicita da costureira no calculo e recarga do JSON tecnico.
- [budget.ts](../frontend-erp/src/types/budget.ts) e
  [curtainComponents.ts](../frontend-erp/src/utils/curtainComponents.ts):
  tipos, invalidacao da simulacao e custo unitario convertido.
- [CurtainComponents.tsx](../frontend-erp/src/components/CurtainComponents.tsx)
  e [curtainComponents.css](../frontend-erp/src/components/curtainComponents.css):
  entrada opcional da embalagem, validacao e apresentacao.
- [CurtainSimulation.tsx](../frontend-erp/src/components/CurtainSimulation.tsx),
  [BudgetProductRow.tsx](../frontend-erp/src/components/BudgetProductRow.tsx) e
  [NewBudgetPage.tsx](../frontend-erp/src/pages/NewBudgetPage.tsx): transporte dos
  fatores ao servidor e opcoes de custo habilitadas somente no Orcamento.
- [test_cortina_componentes_livres.py](../tests/test_cortina_componentes_livres.py),
  [test_cortina_custo_motor.py](../tests/test_cortina_custo_motor.py) e
  [test_orcamento_cortina_pdf_local.py](../tests/test_orcamento_cortina_pdf_local.py):
  custo, entradas invalidas, preservacao do produto e salvar/reabrir em SQLite.
- [curtainComponents.test.cjs](../frontend-erp/tests/curtainComponents.test.cjs)
  e [curtainFabricSelectionMotor.test.cjs](../frontend-erp/tests/curtainFabricSelectionMotor.test.cjs):
  calculo convertido, limpeza na troca de produto, payload e chave de simulacao.

Validacao direcionada: 78 testes backend, 13 scripts frontend de Cortinas/PDF
e build TypeScript/Vite aprovados. Nenhuma migration necessaria. Criacao de um
orcamento real no banco local depende de confirmacao explicita do usuario;
nao deve ser confundida com os testes isolados acima.

## Acrescimo da revenda e condicoes comerciais

O perfil Decorador (custo industrial x 1,5) determina os valores-base da
Smart-tec. E independente de `percentual_parceiro`, que representa um
acrescimo SOBRE o valor-base Smart-tec, nunca uma divisao do recebido/lucro.
A composicao existente permanece: base Smart-tec + acrescimo parceiro = preco
comercial (sem RT ou taxa fixa). O acrescimo nao reduz a base da fabrica.

Exemplo obrigatorio: Smart-tec 1.000 + parceiro 50% (500) = cliente 1.500.
Cartao com acrescimo simples de 7,2%: 1.608, em 3 x 536; reserva financeira
108, sem considera-la receita/lucro da fabrica. Desconto proporcional de 5%:
cliente 1.425, Smart-tec 950 e parceiro 475.

O helper [condicoes_revenda.py](../app/services/condicoes_revenda.py) usa
Decimal e ROUND_HALF_UP para centavos. A parcela final absorve diferencas
de arredondamento; no desconto, o valor do parceiro absorve o residual para
fechar exatamente com o recebido.

`PATCH /orcamentos/{id}/condicoes-revenda` recebe a base, total-cliente e
data de atualizacao esperados para impedir sobrescrita concorrente. Atua
somente em revenda EM_ABERTO sem RT ou taxa fixa ativa. Reutiliza a composicao
existente e atualiza apenas valores comerciais e observacoes autorizadas,
sem recriar itens, alterar catalogo, vendas, financeiro ou Producao.
Nao exige migration. Calcula alternativas de pagamento e grava textos
publicos/internos nos campos de observacao ja existentes. Nao representa
pagamento escolhido, lancamento financeiro ou recebimento realizado.
Se valores/condicoes mudarem, o demonstrativo deve ser regenerado por essa
operacao; textos de condicoes nao sao recalculados ao editar texto livre.

A taxa fixa legada continua com calculo por dentro, sem alteracao global.
As alternativas autorizadas usam acrescimo simples por fora. Somar 7,2% nao
equivale a garantir liquido integral se o banco descontar 7,2% sobre o valor
final cobrado; tarifa efetiva depende de conciliacao do recebimento.

## Tres documentos com visibilidade separada

Orcamentos de revenda possuem tres botoes no gerador atual:

- Cliente Final (`reseller_client`): itens, modelo comercial, tecido, cor,
  medidas, ambientes reconhecidos, precos finais, pagamentos, prazo e garantia.
- Revenda (`reseller_commercial`): os mesmos dados comerciais, base Smart-tec,
  percentual/valor do acrescimo, total e repasses por alternativa de pagamento.
  Nao recebe custos, resultado, costureira, componentes ou instrucoes tecnicas.
- Interno Smart-tec (`reseller_internal`): composicao comercial, observacoes
  internas integrais e ficha por peca com dados da simulacao, componentes,
  embalagem, quantidades, custos, consumo, costureira e especificacoes Wave.
  O identificador legado foi preservado, mas o nome do arquivo agora e
  `Orcamento-N-Interno-Smart-tec.pdf`; nao e documento destinado a revenda.

Os dois documentos externos usam projecao por lista permitida; nao recebem
o JSON tecnico nem os textos livres de observacoes. Prazo/garantia e
pagamentos sao reconstruidos a partir dos blocos canonicos gravados pelo
endpoint de condicoes comerciais. O repasse e extraido somente da linha
estruturada correspondente e conferido contra as somas e valores salvos.
Dados divergentes ou blocos modificados impedem exportacao com erro explicito.
Observacoes legadas nao classificadas e ambientes fora da lista reconhecida
sao omitidos com aviso visivel na exportacao; nao sao considerados seguros
simplesmente por estarem no campo publico. Servicos externos nao copiam
observacoes livres. Cliente Final nunca recebe base Smart-tec, percentual
da revenda ou percentual financeiro. Nenhum externo recebe tabela industrial.

Precos finais dos itens externos sao rateados proporcionalmente aos subtotais
salvos. O metodo dos maiores restos distribui centavos, com desempate por
ordem do item, para a soma fechar exatamente com o total-cliente aprovado.
Exibe-se o preco final da linha, nao um preco unitario arredondado que possa
introduzir divergencia. Esse rateio e exclusivo da apresentacao: nao altera
precos-base, pagamentos, itens ou banco. Desconto proporcional e alternativas
de pagamento continuam os aprovados, nao cumulativos.

O fluxo direto (`direct`) permanece inalterado. A exportacao recarrega o
orcamento e verifica a empresa ativa antes/depois das consultas e da geracao.
As tres versoes nao exigem migration, gravacao no banco nem mudanca em Producao.

Para validar: `tests/test_condicoes_revenda.py` cobre exemplo obrigatorio,
cenario real, centavos, validacao, isolamento e persistencia somente SQLite;
`frontend-erp/tests/budgetPdf.test.cjs` cobre os tres destinos, o fluxo direto,
projecoes, precos, repasses, sigilo, falhas e PDFs A4 reais.
