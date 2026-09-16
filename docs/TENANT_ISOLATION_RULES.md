# Regras de isolamento por empresa

## Regra central

Todo dado comercial pertence exatamente a uma empresa. Funções e unidades do
núcleo técnico são globais. Um identificador numérico isolado nunca autoriza
acesso: o recurso também deve corresponder à empresa do contexto autenticado.

## Contexto

`TenantContext` contém `empresa_id`, usuário opcional e origem. Em produção, a
empresa deverá vir de autenticação ou sessão validada no servidor. Query string
não é fonte de identidade. O header preparado na Fase 2 existe apenas como ponte
explícita de desenvolvimento/teste e ainda não está ligado às rotas.

`LEGACY_UNSCOPED` mantém o ERP atual operável enquanto as tabelas não foram
migradas. Ele é temporário e não satisfaz `require_tenant`; qualquer operação
nova que prometa isolamento deve exigir empresa explícita.

## Regras de acesso

1. Listagens devem começar pelo filtro de `empresa_id`.
2. Busca, alteração e exclusão por ID também devem validar `empresa_id`.
3. Recursos com `empresa_id NULL` são legados, não globais, e não aparecem em
   operações tenant-aware.
4. Produto, fornecedor, cliente e orçamento de outra empresa geram
   `TenantAccessError`.
5. Itens de orçamento herdam o escopo pelo cabeçalho; não duplicam
   `empresa_id`. Toda consulta direta aos itens deve passar pelo orçamento.
6. O catálogo técnico global pode ser lido por todas as empresas.
7. Nenhum catálogo comercial é herdado ao criar empresa.

## Escritas e relacionamentos

Novas escritas tenant-aware deverão preencher `empresa_id` pelo contexto, nunca
por campo livre enviado pelo cliente. Relações comerciais precisam validar que
ambos os lados pertencem à mesma empresa. A futura FK de fornecedor padrão do
produto depende de saneamento e foi adiada.

## Unicidade

Já segura na migration preparada:

- `empresas.slug` globalmente único;
- `empresa_portfolio (empresa_id, modelo_tecnico)` único.

Adiadas até auditoria dos dados legados:

- produto por `(empresa_id, codigo_interno)`;
- fornecedor por `(empresa_id, documento)` ou código definido;
- numeração de orçamento por empresa.

## Cache e sessão

Todo cache comercial deve incluir `empresa_id`. `tenant_cache_key` estabelece o
formato para caches novos e recusa o modo legado. Trocar de empresa exige limpar
ou abandonar chaves antigas. Nunca usar variável global mutável para a empresa
atual.

## Critério para remover o modo legado

`LEGACY_UNSCOPED` só poderá ser removido após migration revisada/executada,
atribuição auditada dos dados existentes, ativação das colunas nos modelos e
serviços, propagação de autenticação e testes negativos em todas as rotas.
