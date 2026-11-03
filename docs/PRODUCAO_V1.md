# Producao V1 local

## Escopo

Na visualizacao de Vendas, abrir **Producao V1**. Nenhuma consulta de producao
ocorre ate abrir o painel. A API usa `/producao` e o mesmo contexto autenticado
dos demais cadastros. Nao ha baixa/reserva de estoque, financeiro ou OS.

Confirmacao explicita permite OP de venda ABERTO, FATURADO ou CONCLUIDO.
CANCELADO e outros estados bloqueiam criacao, liberacao e andamento.
Usuario identificado e horario UTC do servidor sao registrados na confirmacao,
liberacao e transicoes. DEV sem identidade nao confirma fabricacao.
Nao se aceita usuario informado no corpo da requisicao.

Uma OP por venda na V1; uma peca por item/sequencia, com restricao unica no banco.
Servicos nao geram pecas. Quantidades fracionarias, nulas ou negativas
sao recusadas. Nao existe exclusao de OP. FKs preservam venda e itens referenciados;
edicoes comerciais que removem itens vinculados serao recusadas pelo banco.
Os status comerciais nao sao alterados pela Producao.

## Ficha e liberacao

Modelo, tecido/material, cor, medidas em metros e acionamento sao copiados da
venda, com snapshot dos parametros tecnicos. Ambiente e observacoes sao editados
por peca antes da liberacao. Dados ausentes devem ser corrigidos na origem antes
de criar a OP; nao existe revisao/cancelamento de OP nesta V1.

Recalculo usa os simuladores existentes, sempre com quantidade 1, sem confiar
no resultado tecnico enviado pelo navegador. Cortinas exigem composicao completa,
insumos do tenant ativos e sem lista livre sem validacao de funcoes obrigatorias.
Fallback de preco de venda nao substitui custo industrial para liberacao.
Rolo, Double Vision, Romana e modelos sem composicao industrial completa ficam
bloqueados para liberacao; a simulacao serve somente para consulta.
Nao foram criadas receitas alternativas nem corrigidos motores de outros modulos.

Ao liberar, os calculos por peca sao congelados e os campos da ficha tornam-se
imutaveis. Etapas sequenciais: AGUARDANDO, CORTE, MONTAGEM, CONFERENCIA, CONCLUIDA.
Requisicoes desatualizadas nao avancam a mesma etapa duas vezes.

Ficha HTML autenticada, com indicacao de nao liberada e pendencias; impressao
no navegador. Etiquetas por peca liberada reutilizam
`modulos/produtos_etiquetas.py::gerar_html_impressao`, layout Completo 90 x 60 mm.
Nao ha novo desenho de etiqueta. Valores sao escapados antes de renderizar.
O codigo de barras visual continua sendo o do gerador legado, nao um novo
codigo de barras industrial certificado.
QR Code usa a dependencia opcional do gerador legado; se ausente, a propria
etiqueta exibe a indisponibilidade. Nao ha identificador de cliente inventado.

## Instalacao pendente

`migrations/20261103_producao_v1_up.sql` esta apenas preparada: cria duas tabelas,
restricoes de unicidade e validacao dos vinculos. Nao modifica tabelas existentes,
nao preenche dados, nao e executada no startup. Revisar destino e backup antes de
qualquer autorizacao futura. Rollback preparado recusa remover tabelas com OP.
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
