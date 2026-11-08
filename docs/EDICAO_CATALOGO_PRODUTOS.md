# Revisao manual do catalogo de produtos

## Tela existente

`Cadastros > Produtos` ja oferece busca local, filtros, ordenacao, detalhes,
criacao e um formulario de edicao. A edicao existente altera nome, grupo
comercial, unidade de venda, cor/status, custo, margem e preco de venda, sempre
atualizando o registro pelo ID. Os demais dados do detalhe eram somente leitura.

Esta extensao acrescenta edicao de descricao, grupo/familia/modelo tecnicos,
unidades cadastradas e campos textuais legados de fornecedor. A lista permite
filtrar por grupo comercial, grupo tecnico, familia, modelo, unidade, cor e
fornecedor, e a busca considera descricao, codigos interno/fornecedor, modelo e
campos de fornecedor.

## Validacao e integridade

O backend valida limites e valores numericos, exige unidade de venda preenchida
quando alterada e valida grupo/familia/modelo contra uma fonte canonica isolada
por empresa. A migration inicializa essa fonte com os valores atualmente usados,
sem alterar produtos; a chave normalizada evita duplicacoes por caixa e espacos.
Grupo comercial e unidade de venda usam as opcoes auxiliares ativas da empresa.
Unidades de estoque/compra/controle aceitam valores ja usados no catalogo ou
opcoes ativas de unidade de venda. Nenhuma lista global de classificacoes
tecnicas e inventada e nenhum produto e reclassificado automaticamente.

Os campos de fornecedor do produto sao texto no modelo atual, nao chaves
estrangeiras. A edicao preserva essa representacao e nao cria nem altera
equivalencias tecnicas, que mantem seus proprios vinculos por produto e
fornecedor.

## Historico e valores documentais

Cada atualizacao efetiva grava usuario, data e valores anteriores/novos na
tabela `produtos_historico_alteracoes`, na mesma transacao da edicao. O ator
usa `usuarios.id` e exige vinculo com a empresa. Em DEV, a identidade so pode
ser configurada pelo servidor em `SMARTTEC_DEV_USER_ID`, com usuario e vinculo
ativos; `X-User-ID` nao determina o ator. O historico tem integridade referencial
com empresa/produto/usuario e impede exclusao fisica do produto enquanto houver
historico. Desativar o produto nao remove seus registros de auditoria.

Aplicacao futura, depois das migrations-base de empresas/produtos e
`empresa_usuarios`, deve seguir esta ordem:

1. `migrations/20261107_produtos_classificacoes_tecnicas_up.sql` (DOWN:
   `20261107_produtos_classificacoes_tecnicas_down.sql`): cria e preenche a
   lista canonica a partir dos valores atuais sem alterar produtos.
2. `migrations/20261108_produtos_historico_alteracoes_up.sql` (DOWN:
   `20261108_produtos_historico_alteracoes_down.sql`): cria o historico e suas
   FKs para empresa, produto e usuario/vinculo.

Ambas permanecem locais e nao foram executadas.

Orcamentos e pedidos armazenam descricao, unidade, quantidade e preco no item do
documento, e a edicao do catalogo nao atualiza esses itens. Ordens liberadas
conservam os calculos congelados na OP. Antes da liberacao, calculos tecnicos
pendentes continuam dependentes do produto atual e devem ser revisados antes
de liberar; esta edicao nao reescreve nem migra ordens existentes.

Nao ha atualizacao em lote, recriacao de produtos, alteracao de IDs ou mudanca
automatica de equivalencias. A revisao dos 3.866 registros deve ser feita pelo
usuario, produto a produto.
