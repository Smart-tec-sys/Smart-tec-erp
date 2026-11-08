import { apiConfig, request } from './api'
import { getApiAuthHeaders } from './auth'
import { exigirProducaoHabilitada } from './producaoFlag'

export const statusProducao = ['AGUARDANDO', 'CORTE', 'MONTAGEM', 'CONFERENCIA', 'CONCLUIDA'] as const
export type StatusProducao = typeof statusProducao[number]
export type ModoFabricacao = 'AUTOMATICA' | 'MANUAL_SUPERVISIONADA'
export type ComponentePecaProducao = {
  id: number
  produto_id: number
  descricao: string
  codigo_interno: string | null
  quantidade: number | string
  unidade: string
  comprimento_corte: number | string | null
  custo_unitario: number | string
  origem_custo: 'CADASTRO' | 'INFORMADO'
  observacoes: string
}
export type RevisaoFichaProducao = {
  versao: number
  usuario: string
  justificativa: string
  antes: Record<string, unknown>
  depois: Record<string, unknown>
  criado_em: string
}
export type ProdutoComponenteProducao = {
  id: number
  codigo_interno: string | null
  descricao: string
  unidade: string | null
  custo_unitario: number | null
}
export type PecaProducao = {
  id: number
  codigo: string
  pedido_item_id: number
  sequencia: number
  modelo: string | null
  tecido: string | null
  cor: string | null
  largura: string | number
  altura: string | number
  quantidade: string | number
  acionamento: string | null
  ambiente: string
  observacoes: string
  modo_fabricacao: ModoFabricacao
  especificacoes_fabricacao: Record<string, string>
  versao_ficha: number
  conferido_por: string | null
  conferido_em: string | null
  componentes: ComponentePecaProducao[]
  revisoes: RevisaoFichaProducao[]
  status: StatusProducao
  historico: { de: StatusProducao; para: StatusProducao; usuario: string; em: string }[]
}
export type OrdemProducao = {
  id: number
  pedido_id: number
  confirmado_por: string
  confirmado_em: string
  liberado_por: string | null
  liberado_em: string | null
  status: StatusProducao
  pendencias: string[]
  pecas: PecaProducao[]
  calculos_por_peca: Record<string, unknown>
}
export type AutorizacaoProducao = {
  pedido_id: number
  aprovado_por: string | null
  aprovado_em: string | null
  liberado_por: string | null
  liberado_em: string | null
  historico: { acao: string; usuario: string | null; em: string }[]
}

const requestProducao: typeof request = (...args) => {
  exigirProducaoHabilitada()
  return request(...args)
}

export const listarProducao = (pedidoId: number) =>
  requestProducao<OrdemProducao[]>(`/producao/?pedido_id=${pedidoId}`)
export const obterAutorizacaoProducao = (pedidoId: number) =>
  requestProducao<AutorizacaoProducao>(`/producao/vendas/${pedidoId}/autorizacao`)
export const aprovarProducao = (pedidoId: number) =>
  requestProducao<AutorizacaoProducao>(`/producao/vendas/${pedidoId}/aprovar`, { method: 'POST' })
export const liberarPedidoProducao = (pedidoId: number) =>
  requestProducao<AutorizacaoProducao>(`/producao/vendas/${pedidoId}/liberar-fabricacao`, { method: 'POST' })
export const criarProducao = (pedidoId: number) =>
  requestProducao<OrdemProducao>(`/producao/vendas/${pedidoId}`, {
    method: 'POST', body: JSON.stringify({ confirmar_fabricacao: true }),
  })
export const listarCatalogoComponentes = (busca = '') =>
  requestProducao<ProdutoComponenteProducao[]>(
    `/producao/catalogo-componentes?q=${encodeURIComponent(busca)}`,
  )
export const liberarProducao = (ordemId: number) =>
  requestProducao<OrdemProducao>(`/producao/${ordemId}/liberar`, {
    method: 'POST', body: JSON.stringify({ confirmar_fabricacao: true }),
  })
export type AtualizacaoPeca = {
  ambiente?: string
  largura?: number
  altura?: number
  quantidade?: number
  observacoes?: string
  especificacoes_fabricacao?: Record<string, string>
  modo_fabricacao?: ModoFabricacao
  justificativa: string
}
export type DadosComponenteProducao = {
  produto_id: number
  quantidade: number
  unidade: string
  comprimento_corte?: number | null
  custo_unitario?: number | null
  observacoes: string
  justificativa: string
}
export const salvarPeca = (ordemId: number, pecaId: number, dados: AtualizacaoPeca) =>
  requestProducao<OrdemProducao>(`/producao/${ordemId}/pecas/${pecaId}`, {
    method: 'PATCH', body: JSON.stringify(dados),
  })
export const adicionarComponentePeca = (ordemId: number, pecaId: number, dados: DadosComponenteProducao) =>
  requestProducao<OrdemProducao>(`/producao/${ordemId}/pecas/${pecaId}/componentes`, {
    method: 'POST', body: JSON.stringify(dados),
  })
export const atualizarComponentePeca = (
  ordemId: number, pecaId: number, componenteId: number, dados: DadosComponenteProducao,
) => requestProducao<OrdemProducao>(
  `/producao/${ordemId}/pecas/${pecaId}/componentes/${componenteId}`,
  { method: 'PATCH', body: JSON.stringify(dados) },
)
export const removerComponentePeca = (
  ordemId: number, pecaId: number, componenteId: number, justificativa: string,
) => requestProducao<OrdemProducao>(
  `/producao/${ordemId}/pecas/${pecaId}/componentes/${componenteId}`,
  { method: 'DELETE', body: JSON.stringify({ justificativa }) },
)
export const conferirPeca = (ordemId: number, pecaId: number, justificativa: string) =>
  requestProducao<OrdemProducao>(`/producao/${ordemId}/pecas/${pecaId}/conferir`, {
    method: 'POST', body: JSON.stringify({ confirmar_conferencia: true, justificativa }),
  })
export const avancarPeca = (ordemId: number, peca: PecaProducao) => {
  exigirProducaoHabilitada()
  const index = statusProducao.indexOf(peca.status)
  if (index < 0 || index === statusProducao.length - 1) throw new Error('Peça sem próxima etapa.')
  return requestProducao<OrdemProducao>(`/producao/${ordemId}/pecas/${peca.id}/status`, {
    method: 'POST', body: JSON.stringify({ status_atual: peca.status, status: statusProducao[index + 1] }),
  })
}

export async function carregarDocumentoProducao(ordemId: number, pecaId?: number): Promise<string> {
  exigirProducaoHabilitada()
  const path = pecaId == null ? 'ficha' : `pecas/${pecaId}/etiqueta`
  const response = await fetch(`${apiConfig.baseUrl}/producao/${ordemId}/${path}`, {
    headers: await getApiAuthHeaders(),
  })
  if (!response.ok) throw new Error(`Documento de produção: HTTP ${response.status}. ${await response.text()}`)
  return response.text()
}

export async function carregarEtiquetasLoteProducao(ordemId: number): Promise<string> {
  exigirProducaoHabilitada()
  const response = await fetch(`${apiConfig.baseUrl}/producao/${ordemId}/etiquetas`, {
    headers: await getApiAuthHeaders(),
  })
  if (!response.ok) throw new Error(`Etiquetas de produção: HTTP ${response.status}. ${await response.text()}`)
  return response.text()
}
