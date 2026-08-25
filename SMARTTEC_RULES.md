# Smart-tec ERP - Regras do Projeto

Este documento consolida regras tecnicas e de negocio ja identificadas para o
projeto Smart-tec ERP.

## Regras de Desenvolvimento

- Ler os arquivos relacionados antes de propor ou executar alteracoes.
- Verificar impacto em FastAPI, Streamlit, banco, importadores e dados.
- Explicar o plano ao usuario antes de editar arquivos.
- Aguardar confirmacao explicita antes de qualquer alteracao.
- Nao alterar arquivos nao relacionados a tarefa.
- Preservar o estilo atual do projeto.
- Manter nomes em portugues quando estiver alterando codigo existente.
- Evitar reestruturacoes amplas sem decisao explicita.
- Usar SQL direto e fluxo de conexao existente quando a tarefa envolver banco.
- Testar a alteracao sempre que possivel antes de finalizar.

## Regras de Banco

- O banco principal identificado no codigo e PostgreSQL.
- A conexao principal usa `psycopg2` em `backend/database.py`.
- As configuracoes devem vir do `.env`.
- Evitar credenciais hardcoded.
- O arquivo `banco.db` SQLite existe na raiz, mas nao foi identificado como
  banco principal do codigo atual.

## Regras de Clientes

Tipos identificados:

- `Cliente final`;
- `Lojista`;
- `Representante`.

Regras identificadas nos routers FastAPI:

- `Lojista` sempre precisa de documento.
- `Representante` direto, sem `lojista_id`, precisa de documento.
- `Representante` vinculado a um lojista pode ter documento opcional.
- `Cliente final` nao exige documento.

## Regras de Produtos

- Produto precisa ter nome.
- Produto possui preco.
- No Streamlit tambem aparecem os campos `sku`, `estoque`, `categoria` e
  `grupo_produto`.
- Produtos cujo nome comeca com `ROLÔ` ou `ROLO` seguido do tipo/modelo/tecido
  devem ser classificados como produto final, nao como tecido/componente.
  Exemplos confirmados: `ROLÔ SCREEN`, `ROLÔ BK`, `ROLÔ TRANSLÚCIDO`,
  `ROLÔ BK NAPOLES` e `ROLÔ SCREEN NAPOLES`.
- Tecido puro, sem `ROLÔ` ou `ROLO` no inicio do nome, continua sendo
  tecido/componente.

## Regras de Orcamentos

Funcionalidades identificadas nos routers:

- listar orcamentos com itens;
- criar orcamento;
- duplicar orcamento;
- editar orcamento;
- excluir orcamento.

Duplicacao de orcamento permite informar nova margem. Se a margem nao for
informada, usa a margem original.

## Regras de Pedidos

Funcionalidades identificadas nos routers:

- listar pedidos com itens;
- criar pedido manual;
- gerar pedido a partir de orcamento;
- atualizar pedido;
- deletar pedido.

Status padrao identificado:

- `em_aberto`.

## Regras de Producao

`modulos/producao.py` possui regras de baixa de estoque:

- componentes com nome contendo `tecido` ou `screen` usam consumo por area;
- componentes com nome contendo `tubo`, `base`, `perfil`, `trilho`, `guia` ou
  `eixo` usam consumo pela largura;
- demais componentes usam a quantidade base da composicao.

# Padrão Oficial de Nomenclatura dos Produtos

## Produtos Finais

Sempre iniciar pelo tipo comercial.

### Persiana Rolô

- Persiana Rolô Screen
- Persiana Rolô Blackout
- Persiana Rolô Translúcida
- Persiana Rolô Motorizada

### Persiana Double Vision

- Persiana Double Vision
- Persiana Double Vision Motorizada

Regra:

`Double Vision` sozinho representa apenas tecido.

### Persiana Romana

- Persiana Romana Screen
- Persiana Romana Blackout
- Persiana Romana Translúcida
- Persiana Romana Motorizada

### Persiana Romana de Teto

- Persiana Romana de Teto Screen
- Persiana Romana de Teto Blackout
- Persiana Romana de Teto Translúcida
- Persiana Romana de Teto Motorizada

### Persiana Painel

- Persiana Painel Screen
- Persiana Painel Blackout
- Persiana Painel Translúcida

### Persiana Horizontal

- Persiana Horizontal Alumínio
- Persiana Horizontal Madeira

### Persiana Vertical

- Persiana Vertical Tecido
- Persiana Vertical PVC

### Cortinas

- Cortina Wave
- Cortina Tradicional
- Cortina Ripplefold
- Cortina Motorizada

## Tecidos

Nunca utilizar os prefixos:

- Persiana
- Cortina

Exemplos:

- Screen
- Blackout
- Double Vision
- Linho
- PVC
- Jacquard

## Componentes

Nunca utilizar os prefixos:

- Persiana
- Cortina

Exemplos:

- Tubo
- Motor
- Corrente
- Suporte
- Kit Comando
- Base
- Tampa
- Fita
- Espaguete

## Regra do Motor SmartTec

O motor deverá identificar automaticamente:

- Produto Final
- Tecido
- Componente

utilizando principalmente:

- Tipo do Produto
- Modelo Técnico
- Grupo Técnico
- Família Técnica

O nome comercial servirá apenas para apresentação ao usuário.
