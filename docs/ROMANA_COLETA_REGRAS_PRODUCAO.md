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

- gomos sempre ímpares e varetas sempre pares (`varetas = gomos - 1`);
- iniciar com 5 gomos e aumentar `N` em 2 somente quando `G` ultrapassar aproximadamente 35 cm;
- não existe limite inferior rígido para `G`: peças menores podem ter gomos menores;
- usar inicialmente a diferença `D = 2 cm`;
- calcular `G = (altura - D) / N` e `primeiro = G + D`;
- todos os demais gomos, inclusive o último, são iguais a `G`;
- `D` permanece parametrizado entre 2 e 5 cm, mas fica em 2 enquanto a distribuição estiver adequada;
- compensação no último não é usada para a Romana individual comum;
- referência de base de `2,5 cm` integrada ao último gomo, nunca somada como trecho adicional.

A paridade é mecânica: os passadores são instalados exclusivamente nas varetas pares (`2, 4, 6...`) e a última vareta precisa receber passadores. Gomos ímpares produzem uma quantidade par de varetas, garantindo que a última vareta esteja naturalmente nessa sequência.

### Altura pronta e corte de tecido

As duas contas são independentes. Com 7 gomos e 6 varetas, 180 cm usam aproximadamente `27,4286 + (6 × 25,4286) = 180 cm`, com corte de `187 cm`. Para 200 cm: `30,2857 + (6 × 28,2857) = 200 cm`, com corte de `207 cm`. Em 240 cm: `36 + (6 × 34) = 240 cm`.

A dobra de cabeceira e a reserva da fita plástica pertencem somente ao corte. Não existe compensação por acomodação/dilatação do tecido. A distribuição ainda precisa de validação física antes de avançar para varetas, cordões, carretéis, cabeceira, base ou comando.

Fórmula formal do corte longitudinal:

`corte = altura pronta + 2,5 + (quantidade de varetas × 0,5) + 1,5`.

Como `varetas = gomos - 1`, a sobra total é `4,0 + ((gomos - 1) × 0,5)`. Existe um acréscimo de `0,5 cm` em cada trecho que termina em vareta: primeiro gomo e intermediários. O último gomo não recebe acréscimo porque não existe uma vareta após ele. Essa regra não calcula largura, bainhas laterais, perdas ou consumo em área.

### Passadores e cavaletes

Passadores são instalados somente nas varetas pares, incluindo obrigatoriamente a última. A quantidade de passadores por vareta é igual à quantidade de cavaletes/linhas: até 140 cm = 2; acima de 140 até 220 cm = 3; acima de 220 até 260 cm = 4; acima de 260 até 300 cm = 5. O total é `varetas pares selecionadas × cavaletes`. Posição horizontal, cordões e consumo continuam pendentes.

### Posições auxiliares das varetas

A posição de cada vareta é a soma acumulada dos gomos anteriores. Existem `gomos - 1` posições; o trecho entre a última posição e a altura pronta corresponde ao último gomo. Essa saída serve somente para marcação, conferência e futura ficha de produção. Ela não altera a distribuição e não representa comprimento ou consumo de vareta.

### Próxima regra: conjuntos alinhados

Ainda não implementada: em conjuntos lado a lado, a peça mais alta será a mestre; peças menores herdarão posições comuns e compensarão a diferença no último gomo. Essa regra exige validação própria, especialmente para Romana de teto.
