# Serviços V1

## Escopo

O catálogo React usa a tabela `servicos`, sempre limitada pela empresa ativa.
Cada serviço tem código, descrição, categoria, unidade (`UN`, `ML`, `M2`,
`HORA` ou `SERVICO`), tipo de cálculo, custo, preço de venda, comissão
opcional, observações, situação e faixas tarifárias opcionais. Serviços não
são produtos e não movimentam estoque.

Orçamentos e pedidos podem referenciar o serviço por `servico_id`; a descrição,
unidade, quantidade, preço unitário, desconto e subtotal continuam copiados na
linha do documento. Esses valores são snapshots comerciais: alterar ou
inativar o cadastro não reprecifica documentos existentes. Serviços livres,
sem `servico_id`, continuam aceitos.

Para cobrança padrão, o preço unitário do catálogo é aplicado à quantidade
informada na unidade comercial escolhida. O subtotal permanece
`quantidade × preço unitário − desconto`, limitado a zero e arredondado em
centavos. A alteração manual do preço fica no documento e não muda o preço
padrão do catálogo.

## Lavagem por altura

Serviços da categoria Lavagem podem usar `FAIXA_ALTURA`, com unidade `UN`.
Cada faixa configurada contém altura máxima em centímetros e preço por peça.
Aplica-se a primeira faixa cujo limite seja maior ou igual à altura informada.
Altura ausente/inválida ou sem faixa correspondente bloqueia o cálculo padrão.
Não há faixas nem preços comerciais predefinidos. Um preço negociado no
documento prevalece sobre a tabela sem alterar o cadastro.

## API e instalação

Rotas: `GET /servicos/` (busca por `busca`, filtro `incluir_inativos`),
`GET /servicos/{id}`, `POST /servicos/` e `PUT /servicos/{id}`. Todas exigem
empresa ativa; códigos são únicos por empresa. A lista de seleção dos
documentos usa apenas serviços ativos.

`migrations/20261107_servicos_v1_up.sql` e
`migrations/20261107_servicos_v1_down.sql` são propostas aditivas. A migration
adiciona a tabela de catálogo e vínculos opcionais nas linhas de orçamento e
pedido. Não executar sem autorização; nenhuma migration ou dado operacional
foi alterado pela implementação local.
