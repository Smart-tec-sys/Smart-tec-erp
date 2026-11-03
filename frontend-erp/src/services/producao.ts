import { apiConfig, request } from './api'
import { getApiAuthHeaders } from './auth'
import { exigirProducaoHabilitada } from './producaoFlag'

export const statusProducao = ['AGUARDANDO', 'CORTE', 'MONTAGEM', 'CONFERENCIA', 'CONCLUIDA'] as const
export type StatusProducao = typeof statusProducao[number]
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
  acionamento: string | null
  ambiente: string
  observacoes: string
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

const requestProducao: typeof request = (...args) => {
  exigirProducaoHabilitada()
  return request(...args)
}

export const listarProducao = (pedidoId: number) =>
  requestProducao<OrdemProducao[]>(`/producao/?pedido_id=${pedidoId}`)
export const criarProducao = (pedidoId: number) =>
  requestProducao<OrdemProducao>(`/producao/vendas/${pedidoId}`, {
    method: 'POST', body: JSON.stringify({ confirmar_fabricacao: true }),
  })
export const liberarProducao = (ordemId: number) =>
  requestProducao<OrdemProducao>(`/producao/${ordemId}/liberar`, {
    method: 'POST', body: JSON.stringify({ confirmar_fabricacao: true }),
  })
export const salvarPeca = (ordemId: number, pecaId: number, ambiente: string, observacoes: string) =>
  requestProducao<OrdemProducao>(`/producao/${ordemId}/pecas/${pecaId}`, {
    method: 'PATCH', body: JSON.stringify({ ambiente, observacoes }),
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
