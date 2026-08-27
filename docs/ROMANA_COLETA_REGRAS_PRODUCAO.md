# Romana — coleta de regras reais de produção

Registrar para Romana e Romana de teto, sem estimar valores:

- largura, altura/comprimento e quantidade;
- tecido, cor e eventuais limitações dimensionais;
- acionamento manual ou motorizado e lado do comando;
- quantidade e espaçamento dos gomos;
- regra da quantidade e corte das varetas;
- sobra e consumo adicional de tecido;
- cabeceira, eixo e base utilizados;
- cordões, carretéis e guias: tipos, posições e quantidades;
- comando manual compatível;
- motor, controle, torque e acessórios quando motorizada;
- diferenças produtivas específicas da Romana de teto;
- perdas, arredondamentos e unidades de consumo;
- sequência de montagem e componentes opcionais.

Até essas regras serem confirmadas, o orçamento usa somente área comercial e preço de venda informado. Isso não representa custo ou receita de produção.

## Regra V1 confirmada — geometria dos gomos da Romana padrão manual

Para a altura pronta `H`, em centímetros:

- `N = arredondamento comercial de H / 25`, nunca menor que 1;
- `G = H / (N - 0,5)`;
- `B = G / 2`;
- o resultado possui `N - 1` gomos inteiros e um gomo inferior/base de tamanho `B`.

Essa regra calcula somente a geometria dos gomos. Ela não calcula preço, consumo de tecido, varetas ou componentes. A Romana de teto e a Romana motorizada permanecem com regra produtiva pendente.

## Regras a confirmar com a produção

- relação entre número de gomos e número de varetas;
- posição da primeira vareta;
- posição da última vareta;
- largura da vareta em relação à largura pronta;
- quantidade de linhas verticais de cordão por largura;
- espaçamento máximo entre cordões;
- consumo de corda;
- número de carretéis;
- sobra superior de tecido;
- sobra inferior de tecido;
- tecido consumido por cada bolsa de vareta;
- acabamento inferior;
- especificação e descontos técnicos da cabeceira;
- especificação e descontos técnicos da base;
- tipo, lado e dimensionamento do comando;
- diferenças produtivas entre Romana padrão e Romana de teto;
- regras específicas para motorização.

Até a confirmação, o sistema não deve estimar nenhuma dessas regras.

## Regra V2 inicial — distribuição prática de fabricação

A fabricação V2 permanece separada da geometria V1 e se aplica somente à Romana padrão manual.

- gomos sempre pares e varetas sempre ímpares (`varetas = gomos - 1`);
- seleção parte da aproximação geométrica V1 e a ajusta para par; se a aproximação for ímpar, prefere o par inferior para manter gomos maiores; se já for par, preserva essa referência;
- a distribuição candidata precisa manter o padrão entre `25 e 35 cm` e um último gomo coerente;
- primeiro gomo pronto entre `padrão + 2 cm` e `padrão + 6 cm`, por função visual/mecânica;
- intermediários prontos iguais ao padrão selecionado;
- a diferença de fechamento vai primeiro para o primeiro gomo dentro da faixa permitida;
- o restante que violaria a faixa do primeiro vai para o último gomo, compensador secundário;
- referência de base de `2,5 cm` integrada ao último gomo, nunca somada como trecho adicional.

A paridade é mecânica: os gomos intermediários alternam durante o recolhimento, escondendo-se atrás do primeiro e à frente do último. A corda fica presa na última vareta. Uma quantidade ímpar de gomos termina a alternância na posição errada.

### Altura pronta e corte de tecido

As duas contas são independentes. Para 180 cm prontos: `35 + (5 × 29) = 180 cm`; em 179 cm, o primeiro cai para `34 cm` e a compensação permanece nele. Para 200 cm prontos: `27 + (6 × 25) + 23 = 200 cm`; em 199 cm, o primeiro permanece no mínimo de `padrão + 2` e o último cai para `22 cm`. Para o corte de 200 cm: `2,5 + 27,5 + (6 × 25,5) + 23 + 1,5 = 207,5 cm`.

A dobra de cabeceira e a reserva da fita plástica pertencem somente ao corte. Não existe compensação por acomodação/dilatação do tecido. A distribuição ainda precisa de validação física antes de avançar para varetas, cordões, carretéis, cabeceira, base ou comando.

Fórmula formal do corte longitudinal:

`corte = altura pronta + 2,5 + (quantidade de varetas × 0,5) + 1,5`.

Como `varetas = gomos - 1`, a sobra total é `4,0 + ((gomos - 1) × 0,5)`. Existe um acréscimo de `0,5 cm` em cada trecho que termina em vareta: primeiro gomo e intermediários. O último gomo não recebe acréscimo porque não existe uma vareta após ele. Essa regra não calcula largura, bainhas laterais, perdas ou consumo em área.

### Posições auxiliares das varetas

A posição de cada vareta é a soma acumulada dos gomos anteriores. Existem `gomos - 1` posições; o trecho entre a última posição e a altura pronta corresponde ao último gomo. Essa saída serve somente para marcação, conferência e futura ficha de produção. Ela não altera a distribuição e não representa comprimento ou consumo de vareta.
