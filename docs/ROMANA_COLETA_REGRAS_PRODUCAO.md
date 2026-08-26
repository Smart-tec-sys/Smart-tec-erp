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
