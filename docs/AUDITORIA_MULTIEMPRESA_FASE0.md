# Auditoria multiempresa — Fase 0

> Continuidade: a Fase 1 formalizou o núcleo técnico global e a Fase 2 preparou
> a base de tenant com ativação em duas etapas. Consulte
> `docs/NUCLEO_TECNICO_FASE1.md` e `docs/MULTIEMPRESA_FASE2.md`. Esta auditoria
> permanece como fotografia anterior às implementações.

Data da auditoria: 2026-08-28. Escopo: código local e banco `smarttec_erp_dev`, somente leitura. Esta fase não altera comportamento produtivo.

## Resumo executivo

O ERP possui bons núcleos matemáticos para Romana e Romana de teto, um motor Rolô que recebe catálogo por parâmetro e várias regras embutidas nas telas. O principal impedimento multiempresa é que funções técnicas, produtos comerciais, custos e preferências da Smart-tec Persianas ainda convivem nas mesmas estruturas. Não existe `empresa_id`, `tenant_id` ou `company_id` no schema DEV.

O banco contém 3.441 produtos, todos no catálogo global atual. Há 33 produtos com receita JSON serializada em `observacoes`. O motor da Romana expõe IDs comerciais; o Rolô recebe produtos comerciais e calcula custos; `modulos/produtos.py` resolve componentes por nome, código, fornecedor, Produto Base e observações.

## Inventário dos motores

| Família | Arquivo/função principal | Entradas e saídas | Dependências comerciais | Estado |
|---|---|---|---|---|
| Romana manual | `app/services/romana_calculo_producao.py` — `calcular_producao_romana`, `calcular_distribuicao_fabricacao_romana` | Largura, altura, quantidade, corrente e comando; retorna geometria, consumo e referências | IDs 272, 273, 660, 661, 667, 668 e tampas; não usa fornecedor/custo/nome | ATIVO, com acoplamento de catálogo |
| Grupo de Romanas | `app/services/romana_grupo_alinhado.py` — `calcular_grupo_alinhado_romana` | Peças e posição no conjunto; retorna alinhamento | Sem catálogo identificado | PARCIAL |
| Romana de teto | `app/services/romana_teto_calculo_producao.py` — `calcular_grupo_romana_teto` | Peças, instalação e geometria mestre; retorna alinhamento diagnóstico | Sem produto, fornecedor, custo ou nome comercial | DIAGNÓSTICO |
| Rolô | `app/services/motor_calculo_produtos.py` — `calcular_produto_sob_medida`, `_calcular_rolo` | Modelo, dimensões, quantidade, catálogo e opções; retorna componentes e custo | Recebe código, nome, unidade e custo; soma custo dentro do motor | ATIVO |
| Receita Rolô | `modulos/produtos.py` — `montar_receita_base_rolo_manual_para_produto` e resolvedores | Produto Base + lista comercial; retorna carrinho com IDs/custos | Nome, SKU, fornecedor, observações, cor, Produto Base e preferências hardcoded | ATIVO/LEGADO |
| Double Vision | `modulos/orcamentos.py` — `montar_receita_double_vision` | Dimensões, quantidade, bandô, cor e motor; retorna lista de componentes por nomes | Nomes comerciais fixos, como kit Ação Premium e corrente Juta Bola 10 | ATIVO, embutido na UI |
| Orçamento por área | `modulos/orcamentos.py` — `calcular_item_produto_orcamento` | Modelo, dimensões e quantidade; retorna área | Detecta modelo por nome/registro comercial | ATIVO |
| Horizontal | Caminhos genéricos em `modulos/produtos.py` e classificadores | Catálogo e chaves inferidas | Nomes, grupos e Produto Base | PARCIAL |
| Vertical | Classificadores e motor genérico | Catálogo comercial | Nomes e grupos | PARCIAL |
| Painel | Classificadores e motor genérico | Catálogo comercial | Nomes e grupos | PARCIAL |
| Cortinas | Classificadores e motor genérico | Catálogo comercial | Nomes, grupos e unidades | PARCIAL |
| Shangrila | Classificadores por termos em `modulos/produtos.py` | Produto comercial | Nome comercial identifica família | LEGADO/PARCIAL |
| Motorização | Regras e campos em Produtos/Orçamentos | Produto, torque, tensão, uso | Produto e especificações comerciais | PARCIAL |
| Demais famílias | `_calcular_generico` | Maior dimensão ou área conforme unidade | Depende do catálogo fornecido e seus custos | LEGADO/GENÉRICO |

## Romana — comportamento caracterizado

Os novos testes congelam largura de 120 cm e alturas 180, 200 e 240 cm. Cobrem gomos, varetas, primeiro e demais gomos, posições, passadores, tampas, cavaletes, corda, espaguetes, corrente e comando.

| Altura | Gomos | Varetas | Primeiro gomo | Demais | Última vareta | Corda total | Esp. 2,5 | Esp. 3,0 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 180 cm | 7 | 6 | 27,428571 cm | 25,428571 cm | 154,571429 cm | 3,191429 m | 8,295 m | 1,19 m |
| 200 cm | 7 | 6 | 30,285714 cm | 28,285714 cm | 171,714286 cm | 3,534286 m | 8,295 m | 1,19 m |
| 240 cm | 7 | 6 | 36 cm | 34 cm | 206 cm | 4,22 m | 8,295 m | 1,19 m |

Também ficam caracterizados os acoplamentos atuais: comando normal ID 273, espaguetes IDs 660/661, guias IDs 667/668 e tampas IDs 292, 294, 920–923 e 2598.

## Rolô — comportamento caracterizado

Os testes usam catálogo sintético, sem banco, para congelar o motor atual em uma peça de 2 × 2 m, quantidade 2 e perda padrão de 5%.

| Componente | Quantidade atual |
|---|---:|
| Tecido | 8,8946 m² |
| Tubo | 3,95 ML |
| Fita do tubo | 3,95 ML |
| Perfil/base | 3,95 ML |
| Fita da base | 3,94 ML |
| Espaguete da base | 3,94 ML |
| Corrente | 6 ML |
| Emenda | 6 UN |
| Tampa da base | 4 UN |
| Comando | 2 KIT |

Com os custos sintéticos registrados no teste, o total atual é 170,9755. Há cenários isolados para tubo 32 e tubo 38. Também fica caracterizado que, se as duas chaves forem fornecidas, `_pegar` prioriza `tubo_32` pela ordem das chaves, não pela largura.

## Receitas em observações

Marcadores atuais:

```text
[[SMARTTEC_RECEITA_TECNICA_JSON]]
[[/SMARTTEC_RECEITA_TECNICA_JSON]]
```

Foram encontrados 33 produtos com esse bloco. A versão gravada é 1 e o tipo é `receita_tecnica_produto`. Cada item pode conter:

- `produto_id` comercial;
- código e nome comercial;
- custo unitário;
- categoria técnica informal;
- família, unidade e cor.

Portanto, as receitas contêm IDs, nomes, códigos e custos. Não foram extraídas nesta fase. O inventário foi limitado a contagem e presença estrutural para evitar exposição desnecessária.

## Produtos e fornecedores

### Produtos

- Total: 3.441.
- Nome preenchido: 3.441.
- Código interno preenchido: 3.434.
- Grupo técnico preenchido: 3.441.
- Modelo técnico preenchido: 1.086.
- Família técnica preenchida: 3.
- Produto Base preenchido: 562.
- Custo e valor de venda preenchidos: 3.441.
- Produto com fornecedor estruturado ou textual: 0.
- Produtos sem fornecedor: 3.441.
- Grupos de nomes duplicados: 483, com 564 registros excedentes.
- Grupos de códigos internos duplicados: 475, com 1.548 registros excedentes.

O preenchimento integral de `grupo_tecnico` não prova validação: importação e saneamento inferem grupos pelo nome.

### Fornecedores

- Total: 3.
- Campos: identidade, tipo, situação, documento, contatos, endereço e observações.
- `produtos.fornecedor_padrao_id` existe no schema, mas está vazio em todos os produtos.
- Não existe FK entre `produtos.fornecedor_padrao_id` e `fornecedores.id`.
- Campos textuais de fornecedor em produtos também estão vazios.
- Um nome de fornecedor apresenta mojibake no banco, sinal de risco de encoding.

## Schema real x SQLAlchemy

| Entidade | Resultado | Severidade |
|---|---|---|
| `produtos` | Schema contém colunas legadas, categoria, timestamps, motor e `fornecedor_padrao_id` ausentes em `ProdutoDB` | CRÍTICA |
| `produtos` | Modelo contém os principais campos novos, mas não representa toda a tabela real | CRÍTICA |
| `fornecedores` | Modelo e schema observado estão alinhados | MENOR |
| `clientes` | Modelo e schema observado estão alinhados | MENOR |
| `orcamentos` | Modelo e schema estão alinhados | MENOR |
| `orcamentos_itens` | Atributos `preco_unitario`/`subtotal` mapeiam corretamente colunas `preco_unit`/`total` | MENOR |

Colunas relevantes do schema de produtos não modeladas incluem `categoria_id`, campos legados de preço/estoque, timestamps, atributos de motor e `fornecedor_padrao_id`. A deriva impede que `create_all` seja tratado como definição confiável do schema e aumenta o risco de migrations incompletas.

## Consultas que precisarão de tenant

| Área | Arquivos/funções |
|---|---|
| Produtos CRUD | `app/services/produto_service.py`, `app/routes/produto.py`, `utils/api_client.py` |
| Listagem/paginação/busca | `get_produtos`, `get_produtos_todos`, `get_produtos_resumo`, `buscar_produtos_api`, `aplicar_filtros_produtos` |
| Fornecedores | `fornecedor_service.py`, rotas, API client e `modulos/fornecedor.py` |
| Clientes | `cliente_service.py`, rotas, API client e `modulos/cliente.py` |
| Orçamentos | serviços/rotas, `modulos/orcamentos.py`, seletores de cliente/produto |
| Estoque | `modulos/estoque.py`, movimentações e consultas por produto |
| Preços | campos do produto, tabelas de venda e cálculo em Produtos/Orçamentos |
| Importadores | `carregar_planilha_importacao_produtos`, deduplicação e `importar_produtos_dataframe` |
| Ferramentas em massa | receitas Rolô, ajuste de valores, classificação e edição em massa |
| Receitas | JSON em observações, carrinho em sessão e endpoints futuros de receitas-base |
| Caches/sessão | listas de produtos, última receita técnica e carrinhos Streamlit |
| Seletores | busca por nome, produto, fornecedor, grupo e componentes do baú |

Todas as buscas por ID também precisarão validar que o registro pertence ao tenant atual; filtrar apenas listagens não é suficiente.

## Importadores

| Tipo | Entrada/saída | Comportamento atual | Risco multiempresa |
|---|---|---|---|
| Excel | Abas via `pandas.read_excel` → DataFrames → API | Grava no catálogo; classifica e converte automaticamente; deduplica por código/nome | Não possui tenant |
| CSV | Separador automático ou `;` → DataFrame → API | Mesmo fluxo do Excel | Não possui tenant |
| PDF Ação | Parser específico → DataFrame preparado → API | Fornecedor e categorias específicos; converte custo/unidade | Regra de um fornecedor dentro do importador global |
| Saneamento | Produtos já importados | Infere modelo, grupo, família e cor por nomes | Pode transformar sugestão em identidade técnica |
| Massa | Seleção/lista global → atualizações API | Ajusta preços, grupos e receitas | Pode atingir produtos de outra empresa sem filtro |

Nenhum importador foi executado nesta auditoria.

## Isolamento conceitual A x B

Função técnica global:

```text
ESPAGUETE_ROMANA_2_5MM
quantidade técnica para 120 × 200 cm = 8,295 m
```

| Camada | Empresa A | Empresa B conceitual |
|---|---|---|
| Produto | ID 660, Smart-tec Persianas | Produto B-ESP-25, não gravado |
| Fornecedor | Catálogo atual/pendente de vínculo | Fornecedor B, conceitual |
| Custo | R$ 1,44/ML no DEV | Custo B conceitual distinto |
| Saída do motor | 8,295 m | 8,295 m |

O exemplo prova que a matemática pode ser idêntica enquanto produto, fornecedor e custo variam. Os dados da Empresa B são apenas rótulos conceituais e não foram inseridos no banco.

## Plano de migração definitivo

1. **Caracterização e inventário** — manter estes testes e completar cobertura dos motores parciais.
2. **Núcleo técnico formal** — criar códigos estáveis, unidades e receitas abstratas sem IDs comerciais.
3. **Contexto multiempresa** — criar empresas, autenticação e isolamento antes de copiar qualquer catálogo.
4. **Tenant Smart-tec Persianas** — associar o legado atual ao primeiro tenant, inicialmente sem mudar IDs.
5. **Equivalências técnicas** — criar vínculo produto ↔ função, com aprovação e alternativas.
6. **Receitas estruturadas** — migrar os 33 JSONs, preservando fotografia e auditabilidade.
7. **Importação por tenant** — staging, fornecedor, deduplicação e sugestões revisáveis.
8. **Migrar Rolô** — separar quantidade técnica, resolução comercial e valorização.
9. **Migrar Romana** — retirar IDs do motor e transformá-los em equivalências do primeiro tenant.
10. **Demais famílias** — substituir classificadores/nome por motores e funções explícitas.
11. **Onboarding zerado** — provar novo tenant sem fornecedores, produtos, custos ou coleções.
12. **Desligar legado** — remover fallback em observações e inferência por nome somente após comparação integral.

## Riscos e controles

- Preservar IDs e snapshots de orçamento durante migração.
- Não confiar em `grupo_tecnico` inferido sem revisão.
- Migrar receitas de observações de forma idempotente.
- Separar unidade de compra, unidade técnica e fator de conversão.
- Resolver deriva entre schema e modelos antes de migrations multiempresa.
- Aplicar tenant em leitura, escrita, cache, sessão e busca por ID.
- Manter adaptadores por fornecedor fora do núcleo universal.
- Implantar leitura dupla e relatórios de divergência antes de desligar o legado.

## Garantias

- Somente `smarttec_erp_dev` foi consultado.
- Somente `SELECT` foi usado e as transações terminaram em `ROLLBACK`.
- Nenhum importador, saneamento ou `create_all` foi executado.
- Nenhum motor produtivo foi alterado nesta fase.
