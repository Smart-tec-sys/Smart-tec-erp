# Romana de teto V1 — diagnóstica

`ROMANA_TETO_V1 = DIAGNOSTICA`

Esta versão não está liberada como motor definitivo de produção. Seu serviço é
separado da Romana comum e recebe a geometria da peça mestre explicitamente; ele
não promove a fórmula da Romana comum a regra da Romana de teto.

## Regras validadas

- a maior peça é a mestre;
- fora e dentro do vão são contextos distintos;
- gomos são ímpares e varetas são pares;
- a quantidade de varetas corresponde a gomos menos um;
- passadores ficam somente nas varetas pares;
- a última vareta recebe passadores;
- nenhuma posição de vareta pode ficar fora da peça;
- não existe reprovação automática baseada em último gomo menor que 50%.

## Hipóteses ainda pendentes

- fórmula própria da geometria da peça mestre de teto;
- aceitabilidade visual de um último gomo muito pequeno;
- regra definitiva de aumento da menor peça fora do vão;
- componentes específicos da Romana de teto;
- percurso de corda, trilho e carrinhos;
- corte de tecido específico da Romana de teto.

Os resultados de alinhamento são diagnósticos para validação de fabricação. Eles
não aplicam receita, não calculam preço e não autorizam produção automática.

## Limites de integração

O motor não altera Orçamentos, Produtos, Rolô ou a Romana comum. A disponibilidade
comercial de `ROMANA_TETO` permanece independente desta validação produtiva.
