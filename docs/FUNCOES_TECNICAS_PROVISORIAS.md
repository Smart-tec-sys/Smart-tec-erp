# Funções técnicas provisórias

> Atualização da Fase 1: o catálogo formal paralelo está em
> `app/technical/catalog.py`. Este documento permanece como memória da
> auditoria e inventário de lacunas; em caso de diferença, o catálogo em código
> representa as funções já formalizadas. Nenhum vínculo comercial foi criado.

Catálogo conceitual extraído do comportamento atual. Não é tabela, seed nem contrato definitivo. Códigos em minúsculas são chaves legadas do motor Rolô e deverão ser normalizados futuramente.

## Romana manual

| Código provisório | Unidade | Regra/responsabilidade | Situação |
|---|---|---|---|
| `CORDA_ROMANA_1MM` | M | Última vareta + 5 cm, por cavalete | Técnica; produto pendente |
| `ESPAGUETE_ROMANA_2_5MM` | M | Cabeceira e todas as varetas | Técnica; ID 660 acoplado atualmente |
| `ESPAGUETE_BASE_ROMANA_3MM` | M | Um comprimento na base | Técnica; ID 661 acoplado atualmente |
| `GUIA_CORDA_ROMANA` | UN técnica | Guias conforme passadores | Técnica; IDs 667/668 acoplados |
| `TAMPA_VARETA_ROMANA` | UN | Duas por vareta | Técnica; vários IDs por cor acoplados |
| `CAVALETE_CARRETEL_ROMANA` | UN | Linha de comando conforme faixa de largura | Provisória; IDs 2269/666 são candidatos comerciais, não regra |
| `COMANDO_NORMAL_ROMANA` | UN/CJ técnica | Um por Romana | Técnica; ID 273 acoplado |
| `COMANDO_REDUCAO_ROMANA` | UN/CJ técnica | Alternativa recomendada acima de 220 cm | Técnica; ID 272 acoplado |
| `CORRENTE_SEM_FIM_PRONTA_ROMANA` | UN | Uma corrente, medida comercial de referência | Técnica; produto deve ser resolvido por tenant |
| `CORRENTE_JUTA_BOLA10_PERSONALIZADA` | M/UN técnica | Alternativa exclusiva com medida informada | Técnica; sem produto automático |
| `TECIDO_ROMANA` | M²/ML conforme regra futura | Corpo da peça | Pendente de formalização |

## Rolô manual

| Chave atual | Código técnico sugerido | Unidade típica | Observação |
|---|---|---|---|
| `tecido` | `TECIDO_ROLO` | M² | Material/coleção devem permanecer atributos comerciais |
| `tubo_32` | `TUBO_ROLO_32MM` | ML | Alternativa por compatibilidade/largura |
| `tubo_38` | `TUBO_ROLO_38MM` | ML | Alternativa por compatibilidade/largura |
| `tubo` | `TUBO_ROLO_COMPATIVEL` | ML | Chave genérica legada |
| `fita_tubo` | `FITA_TUBO_ROLO` | ML | Hoje descrita por nome/dimensão |
| `base` | `BASE_ROLO` | ML | Alternativa a `perfil` no motor atual |
| `perfil` | `PERFIL_BASE_ROLO` | ML | Semântica se sobrepõe a `base` |
| `fita_base` | `FITA_BASE_ROLO` | ML | Fita plástica da base |
| `espaguete_base` | `ESPAGUETE_BASE_ROLO` | ML | Hoje associado a 3 mm por texto |
| `corrente` | `CORRENTE_BOLA10_ROLO` | ML/UN | Produto comercial não deve fazer parte da função |
| `emenda_corrente` | `EMENDA_CORRENTE_ROLO` | UN | Quantidade fixa atual |
| `tampa_base` | `TAMPA_BASE_ROLO` | UN | Duas por peça no motor atual |
| `comando_32` | `COMANDO_ROLO_32MM` | KIT | Atualmente há preferência por código/nome Ação |
| `comando_38` | `COMANDO_ROLO_38MM` | KIT | Atualmente há preferência por código/nome Ação |
| `comando` | `COMANDO_ROLO_COMPATIVEL` | KIT | Fallback legado |

## Double Vision

Funções provisórias observadas na receita embutida em Orçamentos:

- `TECIDO_DOUBLE_VISION`;
- `TUBO_DOUBLE_VISION_32MM`;
- `TUBO_DOUBLE_VISION_38MM`;
- `TUBO_DOUBLE_VISION_41MM`;
- `COMANDO_DOUBLE_VISION`;
- `CORRENTE_BOLA10_DOUBLE_VISION`;
- `EMENDA_CORRENTE_DOUBLE_VISION`;
- `EIXO_BASE_DOUBLE_VISION`;
- `BASE_CUNHA_DOUBLE_VISION`;
- `TAMPA_EIXO_DOUBLE_VISION`;
- `TAMPA_BASE_DOUBLE_VISION`;
- `GRAPA_DOUBLE_VISION_40MM`;
- `BARRA_ESTABILIZADORA_DOUBLE_VISION`;
- `BANDO_DOUBLE_VISION`;
- `TAMPA_BANDO_DOUBLE_VISION`;
- `ESPAGUETE_DOUBLE_VISION_2_5MM`;
- `FITA_PLASTICA_DOUBLE_VISION_1_5MM`;
- `MOTOR_DOUBLE_VISION`;
- `SUPORTE_ADAPTADOR_MOTOR_DOUBLE_VISION`;
- `CONTROLE_MOTOR`.

Os nomes “Ação Premium”, “Juta” e descrições completas observados na receita atual são comerciais e não devem integrar os códigos globais.

## Famílias parciais

Chaves e grupos já encontrados, mas ainda sem contrato produtivo completo:

- tecidos de Rolô/Romana/Painel;
- tecidos e componentes Double Vision;
- componentes Horizontal;
- lâminas Horizontal e Vertical;
- componentes Vertical;
- componentes Painel;
- componentes Cortinas;
- tecidos Cortinas;
- componentes Plissada;
- componentes Celular;
- componentes Shangrila;
- componentes Externa;
- componentes Toldo;
- motores;
- acessórios de motor;
- baús compartilhados.

## Atributos que não são função técnica

Manter fora do código da função:

- fornecedor e marca;
- coleção comercial;
- nome/SKU/código de barras;
- cor comercial;
- custo, preço e margem;
- estoque;
- prioridade do fornecedor;
- produto preferencial da empresa.

Esses dados pertencem ao catálogo comercial ou à equivalência técnica do tenant.

## Regras para formalização futura

1. Código técnico global, estável e versionado.
2. Unidade técnica explícita.
3. Atributos requeridos separados do nome.
4. Alternativas exclusivas modeladas por grupo de escolha.
5. Nenhum ID comercial na definição global.
6. Várias equivalências comerciais por tenant.
7. Compatibilidade e aprovação auditáveis.
