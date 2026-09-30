# Núcleo técnico SmartTec — Fase 1

## Fronteira arquitetural

**NÚCLEO TÉCNICO ≠ CATÁLOGO COMERCIAL**

O núcleo técnico descreve o que a fabricação necessita: função, família,
quantidade, unidade, atributos, origem da regra, obrigatoriedade e alternativas.
Ele não escolhe itens de compra ou venda e não conhece fornecedor, códigos de
mercado, valores, estoque, empresa ou tenant.

Esta fase cria uma camada paralela. Os motores produtivos atuais não importam o
novo pacote e continuam retornando exatamente as estruturas anteriores.

## Estrutura

- `app/technical/models.py`: contratos imutáveis `TechnicalFunction` e
  `TechnicalRequirement`;
- `app/technical/units.py`: unidades universais de fabricação;
- `app/technical/functions.py`: conjuntos mínimos de códigos estáveis;
- `app/technical/catalog.py`: definições versionadas e validação automática;
- `app/technical/__init__.py`: interface pública do pacote.

Não há tabela, migration, acesso a banco ou conversão de unidade comercial.

## Contratos

`TechnicalFunction` define código, nome, família, unidade, descrição, atributos
requeridos e técnicos, estado, versão e eventual grupo de alternativa. A classe
e seus mapas são imutáveis.

`TechnicalRequirement` representa a futura saída pura dos motores: função,
quantidade, unidade, atributos, origem da regra, obrigatoriedade, alternativa e
observação técnica. Quantidades devem ser finitas e não negativas.

## Unidades técnicas

- `UN`: unidade;
- `M`: metro;
- `M2`: metro quadrado;
- `CJ`: conjunto;
- `KIT`: kit técnico.

Essas unidades são independentes das embalagens de compra e das unidades de
venda. Nenhuma conversão comercial foi implementada.

## Cobertura do catálogo

Romana possui as 17 funções solicitadas. Funções com regra já confirmada estão
ativas; tecido, vareta, cabeceira, eixo, base, tampa da base e pêndulo permanecem
`SEM_REGRA` quando ainda não existe cálculo completo.

Rolô possui as 12 chaves mínimas formalizadas em paralelo ao motor atual, sem
substituí-lo. Tubos e comandos usam grupos de alternativas técnicas.

Double Vision contém somente os conceitos observados na receita existente e
todos permanecem `PROVISORIA`. Horizontal, Vertical, Painel, Cortinas,
Shangrila e Motorização contêm apenas agrupamentos comprovados na auditoria,
marcados `PENDENTE_VALIDACAO`.

## Alternativas exclusivas

- `COMANDO_ROMANA`: comando normal ou com redução;
- `ACIONAMENTO_CORRENTE_ROMANA`: corrente pronta ou personalizada;
- `TUBO_ROLO`: tubo de 32 mm ou 38 mm;
- `COMANDO_ROLO`: comando compatível com tubo de 32 mm ou 38 mm.

O grupo registra exclusividade conceitual, mas não toma decisão nem resolve um
item comercial.

## Validação e portabilidade

O catálogo é validado na importação quanto a códigos únicos, famílias e
unidades válidas e ausência de termos próprios da camada comercial. Testes
também impedem referências aos identificadores atualmente acoplados nos motores.

O cenário de portabilidade cria uma necessidade de 8,295 M para
`ESPAGUETE_ROMANA_2_5MM`. Duas empresas podem mapear essa mesma necessidade para
itens comerciais diferentes em memória sem alterar a função, a quantidade ou a
unidade. O mapeamento é apenas uma simulação de teste e não cria resolução,
tenant ou persistência.

## Fora da Fase 1

Não foram criados empresa, tenant, vínculo entre item comercial e função,
receita no banco, resolução comercial, cálculo de valores, estoque, onboarding
ou migração. Os identificadores existentes nos motores também não foram
removidos. Esses trabalhos pertencem a fases posteriores.
