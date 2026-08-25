# SMART-TEC ERP — Marco Oficial Pós-Stand-by

Data do marco: 25/08/2026

Árvore oficial reconhecida pelo usuário: `C:\Users\valmi\Smart-tec ERP`

Este documento registra o estado funcional preservado. Ele não contém senhas, tokens, URLs com credenciais ou outros segredos.

## Concluído

- Cadastros principais de clientes, fornecedores, funcionários, transportadoras e opções auxiliares.
- Produtos organizado nas abas Geral, Técnico, Composição / Receita, Valores, Estoque, Fiscal e Descrição.
- Listagem, busca, busca avançada, visualização, cadastro, edição e clonagem de produtos.
- Opções auxiliares de produtos.
- Tabelas de valores de venda.
- Documentação visual e técnica do projeto.

## Em ajuste

- Classificação técnica dos produtos.
- Modelo Técnico e Grupo Técnico.
- Conversões de unidade.
- Persistência e compatibilidade de regras técnicas.
- Problemas de encoding em dados legados.
- Integração do módulo de Orçamentos com os módulos posteriores.

## Em desenvolvimento

- Receita técnica.
- Baú de Componentes.
- Motor determinístico da Persiana Rolô manual.
- Aplicação em massa.
- Ferramentas de saneamento.
- Etiquetas.
- Importadores e exportadores.

## Não iniciado

- Vendas/Pedidos oficial.
- Ordens de Serviço.
- Estoque integrado.
- Financeiro integrado.
- Fluxo definitivo Orçamento → Pedido → O.S. → Estoque → Financeiro.

## Ambiente preservado

- Banco DEV: `smarttec_erp_dev`.
- Usuário de validação: `smarttec_frozen_ro`.
- Proteção: `default_transaction_read_only = on`.
- Produtos no momento do marco: 3441.
- Backend seguro: `app.main:app`, em `127.0.0.1:8100`.
- Frontend original: `app.py`, em `127.0.0.1:8601`.
- Banco original `smart-tec_erp`: isolado e não acessado durante a criação do marco.

## Próxima prioridade oficial

1. Continuar a classificação por Modelo Técnico e Grupo Técnico.
2. Validar a receita da Persiana Rolô manual.
3. Identificar e completar componentes faltantes.
4. Consolidar o Baú de Componentes.
5. Aplicar alterações em massa somente após validação controlada no banco DEV.

## Recuperação

O marco deve ser recuperável conjuntamente por cópia física, inventário SHA-256, dump do banco DEV, commit local, tag local e relatório externo de runtime.
