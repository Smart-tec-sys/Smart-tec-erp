# Matriz de acoplamentos e filtros de tenant

Classificação:

- **A** — núcleo técnico universal;
- **B** — configuração da empresa;
- **C** — catálogo comercial;
- **D** — acoplamento indevido entre camadas.

## Matriz arquivo por arquivo

| Arquivo/função | Dados envolvidos | Classe | Diagnóstico | Ação futura |
|---|---|---|---|---|
| `app/services/romana_calculo_producao.py` | Fórmulas, posições, quantidades | A | Núcleo matemático puro | Manter global/versionado |
| Mesmo arquivo | IDs 272, 273, 660, 661, 667, 668 e tampas | D | Catálogo Smart-tec dentro do motor | Mover para equivalências do tenant |
| Mesmo arquivo | Seleções de corrente/comando | A/B | Opção técnica universal; escolha pertence à operação da empresa | Separar regra e decisão |
| `app/services/romana_teto_calculo_producao.py` | Geometria mestre e alinhamento | A | Sem catálogo/custo | Manter diagnóstico global |
| `app/services/romana_grupo_alinhado.py` | Alinhamento de grupo | A | Sem catálogo identificado | Manter técnico |
| `app/services/motor_calculo_produtos.py` | Quantidades Rolô | A | Fórmulas técnicas | Extrair motor puro |
| Mesmo arquivo `_add` | código, nome, custo unitário/total | C/D | Valorização comercial dentro do motor | Criar serviço de valorização posterior |
| `modulos/produtos.py:texto_produto_motor` | nome, SKU, grupo, material, cor, observações | C/D | Texto comercial usado como identidade técnica | Substituir por função/equivalência aprovada |
| `produto_candidato_*` e pontuações | fornecedor Ação, JPTEC, Smart antigo | B/C/D | Política da Smart-tec tratada como regra geral | Mover para política/configuração do tenant |
| `produto_candidato_chave_motor` | nome/grupo/modelo | D | Função inferida por termos | Usar vínculo estruturado |
| `montar_catalogo_motor_por_produtos` | produtos e custos | C | Resolve catálogo global atual | Filtrar por tenant e equivalência |
| `montar_receita_base_rolo_manual_para_produto` | Produto Base + produtos | D | Produto Base substitui configuração técnica | Criar receita abstrata + configuração |
| `aplicar_conversao_importacao` | nome, custo, unidade, fornecedor | C/D | Conversão e heurística específicas misturadas | Staging e regra de conversão explícita |
| `inferir_modelo/grupo/familia` | nomes comerciais | D | Classificação automática gravável | Tornar sugestão revisável |
| `embutir_receita_tecnica_observacoes` | IDs, nomes, códigos e custos | D | Receita estruturada em texto livre | Migrar para tabelas próprias |
| Ferramentas em massa de Produtos | catálogo inteiro | C/D | Sem limite de empresa | Exigir tenant e autorização |
| `modulos/orcamentos.py:detectar_modelo_calculo_orcamento` | nome/registro | D | Modelo detectado por produto comercial | Usar função/modelo vinculado |
| `montar_receita_double_vision` | regras e nomes comerciais fixos | A/D | Matemática e marcas/nomes na mesma função | Separar receita e resolução comercial |
| `calcular_valor_produto_por_tipo_venda` | preço/margem | C | Regra comercial | Manter por tenant, fora do núcleo |
| Payload de orçamento | `produto_id`, preço, grupo/modelo | C/B | Fotografia comercial e técnica | Preservar histórico + validar tenant |
| `app/models/produto.py` | técnico, comercial, custo, estoque | C/D | Muitas responsabilidades na mesma entidade | Introduzir equivalências e preços separados |
| `app/models/fornecedor.py` | fornecedor global | C | Sem empresa | Adicionar tenant no futuro |
| `app/models/cliente.py` | cliente global | C | Sem empresa | Adicionar tenant no futuro |
| `app/models/orcamento.py` | cliente/produto global | C | Sem empresa | Isolar cabeçalho e itens |
| `produto_service.py:get_all/get_by_id` | todos os produtos | C/D | Sem filtro de tenant | Exigir contexto de empresa |
| Serviços cliente/fornecedor | cadastros globais | C/D | Sem filtro de tenant | Exigir contexto de empresa |
| `utils/api_client.py` | endpoints CRUD globais | C/D | Nenhum contexto de empresa | Propagar tenant no backend/autenticação |
| Endpoints `receitas-base` no client | receita | A/B | Cliente existe, backend não identificado | Implementar somente em fase posterior |
| `modulos/estoque.py` | produto/estoque | C/D | Catálogo global | Filtrar tenant em todas as operações |
| `modulos/producao.py` | listas e filtros | B/C | Usa produtos globais | Isolar empresa e portfólio |

## IDs hardcoded relevantes

| ID | Produto no DEV | Classe correta | Estado atual |
|---:|---|---|---|
| 660 | Espaguete 2,5 mm | C | Dentro do motor Romana — D |
| 661 | Espaguete 3,0 mm | C | Dentro do motor Romana — D |
| 272 | Comando com redução | C | Dentro do motor Romana — D |
| 273 | Comando normal | C | Dentro do motor Romana — D |
| 667/668 | Guias de corda | C | Dentro do motor Romana — D |
| 292, 294, 920–923, 2598 | Tampas de vareta | C | Dentro do motor Romana — D |
| 2269 | Cavalete Romana mancal | C | Candidato conceitual, não hardcoded no motor |
| 666 | Carretel longo | C | Candidato conceitual, não hardcoded no motor |

## Consultas e operações que exigirão filtro

### Backend

- `produto_service.get_all`, `get_by_id`, `create`, `update`, `delete`;
- serviços equivalentes de fornecedor, cliente, funcionário e transportadora;
- listagem, criação e atualização de orçamentos;
- qualquer lookup por `produto_id`, não apenas listagens;
- opções auxiliares que forem locais à empresa.

### Frontend/API client

- `get_produtos`, paginação e resumo;
- `get_produtos_todos` e caches derivados;
- seletores por nome e ID;
- produtos/componentes de baú;
- clientes, fornecedores e orçamentos;
- receitas-base e receita de produto;
- tabelas de preço e filtros salvos.

### Produtos e ferramentas

- `buscar_produtos_api` e `buscar_produto_por_id`;
- filtros de listagem/exportação;
- ajustes de valores;
- classificação e edição em massa;
- aplicação em massa de receitas;
- clonagem;
- importação e deduplicação;
- carrinho de receita e `smarttec_ultima_receita_tecnica` em sessão.

### Estoque e operação

- saldos e movimentações;
- compras e itens;
- pedidos e itens;
- relatórios;
- produção e seletores de insumo.

## Constraints futuras mínimas

1. `empresa_id NOT NULL` nas entidades comerciais após migração.
2. Índices compostos começando por `empresa_id` nas buscas frequentes.
3. Unicidade de código, documento ou número no escopo correto da empresa.
4. FKs de produto/fornecedor/cliente coerentes com a mesma empresa.
5. Equivalência única por empresa, produto e função, respeitando vigência.
6. Política de autorização que não dependa somente de filtro na UI.
7. Testes negativos de acesso cruzado por ID.

## Caches e sessão

Toda chave de cache ou sessão com dados comerciais deverá incluir a empresa. Listas globais, última receita e resultados de busca podem vazar dados mesmo quando a consulta original estiver correta. O contexto de tenant deve participar da chave e ser invalidado na troca de empresa.

## Critério de saída da Fase 0

- Motores e acoplamentos inventariados.
- Comportamento Romana/Rolô protegido por testes.
- Receitas ocultas quantificadas, sem extração.
- Schema e modelos comparados.
- Funções provisórias registradas.
- Nenhuma alteração produtiva ou de banco.
