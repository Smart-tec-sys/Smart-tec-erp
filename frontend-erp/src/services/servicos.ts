import { request } from './api'

export type UnidadeServico = 'UN' | 'ML' | 'M2' | 'HORA' | 'SERVICO'
export type TipoCalculoServico = 'POR_UNIDADE' | 'FAIXA_ALTURA'
export type FaixaAlturaServico = { altura_max_cm: number; preco_unitario: number }
export type Servico = {
  id: number
  empresa_id: number
  codigo: string
  descricao: string
  categoria: string
  unidade: UnidadeServico
  tipo_calculo: TipoCalculoServico
  custo: number
  preco_venda: number
  comissao: number | null
  observacoes: string | null
  situacao: 'ATIVO' | 'INATIVO'
  faixas_altura: FaixaAlturaServico[]
  criado_em?: string | null
  atualizado_em?: string | null
}
export type ServicoPayload = Omit<Servico, 'id' | 'empresa_id' | 'criado_em' | 'atualizado_em'>

export const listarServicos = (busca = '', incluirInativos = true) =>
  request<Servico[]>(`/servicos/?incluir_inativos=${incluirInativos}${busca.trim() ? `&busca=${encodeURIComponent(busca.trim())}` : ''}`)
export const criarServico = (payload: ServicoPayload) =>
  request<Servico>('/servicos/', { method: 'POST', body: JSON.stringify(payload) })
export const atualizarServico = (id: number, payload: ServicoPayload) =>
  request<Servico>(`/servicos/${id}`, { method: 'PUT', body: JSON.stringify(payload) })

export function precoServicoParaAltura(servico: Pick<Servico, 'tipo_calculo' | 'preco_venda' | 'faixas_altura'>, alturaCm: number): number {
  if (servico.tipo_calculo !== 'FAIXA_ALTURA') return Number(servico.preco_venda)
  if (!Number.isFinite(alturaCm) || alturaCm <= 0) throw new Error('Informe uma altura positiva em centímetros.')
  const faixa = [...servico.faixas_altura]
    .sort((a, b) => a.altura_max_cm - b.altura_max_cm)
    .find(item => alturaCm <= item.altura_max_cm)
  if (!faixa) throw new Error('A tabela de lavagem não possui faixa para a altura informada.')
  return Number(faixa.preco_unitario)
}

export function subtotalServico(quantidade: number, precoUnitario: number, desconto: number): number {
  return Math.round(Math.max(0, quantidade * precoUnitario - desconto) * 100) / 100
}
