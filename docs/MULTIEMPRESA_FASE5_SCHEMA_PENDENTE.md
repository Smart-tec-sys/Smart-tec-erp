# Fase 5 — schema pendente para isolamento

Nenhuma migration foi criada. As tabelas abaixo não possuem `empresa_id` e não
podem receber ativação tenant-aware segura nesta fase.

| Tabela | Uso atual | Volume DEV | Estratégia futura | Risco atual |
|---|---|---:|---|---|
| `funcionarios` | Cadastro/API de funcionários | 4 | `empresa_id` nullable, associação controlada e depois obrigatória | Vazamento integral entre empresas |
| `transportadoras` | Cadastro/API de transportadoras | 3 | Mesmo padrão de ownership dos fornecedores | Vazamento integral entre empresas |
| `opcoes_auxiliares` | Configurações comerciais por categoria | 84 | Definir quais categorias são globais e quais são por empresa antes da migration | Configuração de uma empresa visível a outra |
| `compras` | Estrutura comercial ainda parcial | não contado nesta fase | Tenant no cabeçalho e herança nos itens | Compras cruzadas |
| `pedidos` | Estrutura comercial ainda parcial | não contado nesta fase | Tenant no cabeçalho e herança nos itens | Pedidos cruzados |
| `financeiro` | Estrutura comercial ainda parcial | não contado nesta fase | Tenant obrigatório e vínculos coerentes | Exposição financeira crítica |

Serviços, vendas, estoque, produção, notas fiscais e relatórios não apresentam
um CRUD persistido completo e isolável no estado atual. Devem ser modelados na
fase de schema, preservando herança por cabeçalho quando houver itens.
