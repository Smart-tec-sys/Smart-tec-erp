# Producao V1 local

## Escopo

## Flag de publicacao (desligada por padrao)

Backend: `PRODUCAO_V1_ENABLED=false` por padrao. Somente `true` explicito
(sem diferenciar maiusculas/minusculas e com espacos externos removidos) habilita.
Dependencia global do router retorna 503 "Producao V1 desabilitada" antes de
resolver banco/tenant e antes de consultar tabelas. Inclui ficha e etiquetas.
Nao altera protecoes de autenticacao quando habilitada.

Frontend: `VITE_PRODUCAO_V1_ENABLED=false` por padrao, lida no build Vite.
Sem `true` explicito, acesso na Venda fica oculto, painel nao e montado e todos
os servicos de Producao recusam chamadas antes de HTTP/auth. A flag frontend
nao substitui o bloqueio backend. Alterar a flag exige rebuild do frontend.

Ativacao futura SOMENTE apos autorizacao de implantacao propria: conferir
destino e backup, aplicar migration autorizada, validar persistencia PostgreSQL,
autenticacao/tenant, unicidade, transicoes, ficha e etiquetas; entao habilitar
backend e frontend no mesmo ambiente. Nao habilitar para contornar schema
ausente. Nesta entrega nenhuma migration ou configuracao de ambiente foi alterada.
Codigo, fichas, etiquetas e SQL preparado permanecem preservados.

Testes da flag: `tests/test_producao_flag.py` verifica todas as rotas com
banco/tenant proibidos. `producao.test.cjs` sem variavel testa flag desligada;
`TEST_PRODUCAO_FLAG=true` executa contratos habilitados com mocks.
Consulte os resultados atualizados de testes desta revisao; nenhuma
configuracao de ambiente foi habilitada nesta etapa.

## Fluxo quando habilitada

Na visualizacao de Vendas, abrir **Producao V1**. Nenhuma consulta de producao
ocorre ate abrir o painel. A API usa `/producao` e o mesmo contexto autenticado
dos demais cadastros. Nao ha baixa/reserva de estoque, financeiro ou OS.

O status comercial (incluindo FATURADO ou CONCLUIDO) nunca autoriza fabricacao
por si so. Antes da OP, a venda precisa de duas acoes separadas: **aprovar para
fabricacao** e **liberar o pedido para fabricacao**. Cada acao exige usuario
identificado, tenant ativo e registra usuario/data UTC no historico do pedido.
Alteracao posterior dos dados do cabecalho ou cancelamento invalida as duas
autorizacoes e preserva o evento no historico. DEV sem identidade nao autoriza.
Nao se aceita usuario informado no corpo da requisicao. Pedidos sem orcamento
tambem podem seguir esse fluxo explicitamente.

Uma terceira confirmacao explicita cria a OP, somente depois das duas
autorizacoes. CANCELADO e estados comerciais nao suportados bloqueiam criacao,
liberacao tecnica e andamento. Uma OP por venda na V1; uma peca por
item/sequencia, com restricao unica no banco. Servicos nao geram pecas.
Quantidades fracionarias, nulas ou negativas sao recusadas.

Uma OP por venda na V1; uma peca por item/sequencia, com restricao unica no banco.
Servicos nao geram pecas. Quantidades fracionarias, nulas ou negativas
sao recusadas. Nao existe exclusao de OP. FKs preservam venda e itens referenciados;
edicoes comerciais que removem itens vinculados serao recusadas pelo banco.
Os status comerciais nao sao alterados pela Producao.

## Ficha e liberacao

Cliente, pedido, prazo, modelo, material, cor, medidas em metros, acionamento,
ambiente e observacoes sao copiados da venda/orcamento para snapshot e pecas.
O ambiente agora e um campo estruturado opcional em itens de orcamentos/vendas;
itens historicos sem este dado continuam sem preenchimento e precisam ser
conferidos na ficha antes da liberacao tecnica. Observacoes permanecem distintas.

Recalculo usa simuladores existentes, sempre com quantidade 1, sem confiar no
resultado tecnico enviado pelo navegador. A V1 somente permite liberacao tecnica
para **Cortina Wave** com dados de calculo validos, composicao completa, insumos
vinculados a produtos ativos da mesma empresa e custo industrial cadastrado.
Listas livres de componentes e outros modelos de prega ficam bloqueados.

**Modelos ainda bloqueados para operacao:**

- **Rolo manual:** falta BOM/equivalencias reais para tecido, tubo 32/38, fitas,
  base, espaguete, corrente, emenda, tampas e comando; cortes/consumo precisam
  validacao industrial.
- **Rolo motorizado:** falta BOM validada para motor, suporte/adaptador, controle,
  eixo/tubo compativel e equivalencias de corte.
- **Double Vision manual:** falta BOM/equivalencias reais para tecidos, tubo,
  comando, eixo/base, tampas, grapas, barra estabilizadora ou bando, espaguete,
  fita, corrente, emenda e pendulo.
- **Double Vision motorizado:** falta regra/BOM validada para motor, suporte,
  controle, tubo e componentes compativeis.
- **Romana manual:** o motor informa regras pendentes; faltam BOM/equivalencias
  validadas para tecido, varetas/tampas, guias/passadores, corda 1 mm,
  espaguetes, corrente e comando.
- **Romana motorizada:** falta calculo de producao e BOM validada de motor e
  componentes compativeis.

Nenhum destes modelos e liberado por haver simulacao ou preco comercial.
Nao foram criadas receitas alternativas nem alterados motores de outros modulos.

Ao liberar, os calculos por peca sao congelados e os campos da ficha tornam-se
imutaveis. Etapas sequenciais: AGUARDANDO, CORTE, MONTAGEM, CONFERENCIA, CONCLUIDA.
Requisicoes desatualizadas nao avancam a mesma etapa duas vezes.

## Producao Editavel V1 (proposta local)

Antes da liberacao da OP, a ficha pode entrar explicitamente em
`MANUAL_SUPERVISIONADA`. Nessa modalidade, ambiente, medidas, quantidade,
observacoes e especificacoes tecnicas pertencem somente a OP; pedido, orcamento,
precos e autorizacoes comerciais nao sao atualizados. Uma ficha manual nao pode
voltar ao modo automatico. Medidas, quantidade e especificacoes nao podem ser
alteradas no modo automatico para evitar que o calculo comercial congelado seja
confundido com uma recalculacao tecnica.

Componentes manuais sao selecionados no catalogo de produtos ativos da empresa.
O backend valida empresa, situacao, unidade e custo; cada inclusao,
substituicao ou remocao grava snapshot de ficha antes/depois, usuario,
justificativa e versao. O custo pode vir do cadastro do produto ou ser
explicitamente informado. A edicao invalida a conferencia tecnica anterior.
Nao ha baixa/reserva de estoque e a composicao resultante e sempre identificada
como `MANUAL_NAO_HOMOLOGADA`, nunca como BOM industrial validada.

Cada peca manual exige especificacoes, ao menos um componente e conferencia
tecnica identificada antes da liberacao. A aprovacao e a liberacao comercial do
pedido continuam sendo acoes separadas e anteriores; a liberacao tecnica da OP
continua sendo uma terceira acao. A ficha e as etiquetas existentes exibem
quantidade, especificacoes e aviso de composicao manual nao homologada.

`migrations/20261107_producao_editavel_v1_up.sql` e sua migration DOWN estao
somente propostas e nao foram executadas. O UP adiciona quantidade, modo,
especificacoes, versao e conferencia em `producao_pecas`, alem das tabelas de
componentes e revisoes e validacao de vinculo entre empresa, OP, peca e produto.
O DOWN recusa remover dados manuais em uso. Aplicacao futura depende das
migrations anteriores da Producao V1, backup, autorizacao e revisao do destino.
Nenhuma migration, feature flag ou dado real foi alterado nesta etapa.

Ficha HTML autenticada, com cliente, indicacao de nao liberada e pendencias;
impressao no navegador. Etiqueta individual e lote de pecas liberadas reutilizam
o renderizador de `modulos/produtos_etiquetas.py`, layout Completo 90 x 60 mm.
Cada etiqueta contem codigo proprio da OP/linha/sequencia, pedido, cliente,
ambiente, modelo, medidas e observacoes. Valores sao escapados antes de renderizar.
O codigo de barras visual continua sendo o do gerador legado, nao um novo
codigo de barras industrial certificado.
QR Code usa a dependencia opcional do gerador legado; se ausente, a propria
etiqueta exibe a indisponibilidade. Nao ha identificador de cliente inventado.

## Instalacao pendente

`migrations/20261103_producao_v1_up.sql` esta apenas preparada: cria duas tabelas,
restricoes de unicidade e validacao dos vinculos. A migration aditiva
`20261107_producao_v1_operacao_up.sql` requer a primeira e acrescenta os campos
de aprovacao/liberacao, historico e ambiente em itens; tambem preserva autorizacao
de OP legada sem marcar OP nao liberada como liberada. Seu rollback recusa apagar
autorizacoes ou ambientes ja registrados. Nenhuma migration e executada no startup.
Sem instalacao, API informa 503 explicitamente; os demais fluxos continuam iguais.

Testes usam exclusivamente SQLite em memoria e respostas simuladas.
Backend: `python -m pytest -q -p no:cacheprovider tests/test_producao_v1.py`.
O cliente HTTP dos testes requer `httpx` (nao e dependencia da API em execucao).
Frontend: `node tests/producao.test.cjs` e `npm run build`, em `frontend-erp`.
Harness visual: servir `tests/producao.browser.html` pelo Vite; intercepta todas
as requisicoes com dados sinteticos e nao usa a API configurada.
Nenhum teste deve executar a migration ou acessar dados operacionais.
Validacao local completa com persistencia real fica pendente de autorizacao de
instalacao em banco de teste apropriado e acesso autenticado.
