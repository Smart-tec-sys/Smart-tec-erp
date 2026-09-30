import type { ApiProduct, BudgetProduct, CommercialType } from './budget'

const normalize = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replaceAll('_', ' ')

export function doubleVisionKind(p: Pick<ApiProduct, 'modelo_tecnico' | 'modelo' | 'nome'>): 'MANUAL' | 'MOTORIZADA' | null {
  const text = normalize(`${p.modelo_tecnico || ''} ${p.modelo || ''} ${p.nome}`)
  if (!text.includes('DOUBLE VISION')) return null
  if (text.includes('MOTORIZ')) return 'MOTORIZADA'
  const mt = normalize(p.modelo_tecnico || '')
  if (mt === 'DOUBLE VISION' || mt === 'DOUBLE VISION MANUAL') return 'MANUAL'
  if (text.includes(' DOUBLE VISION ') || text.startsWith('DOUBLE VISION ') || text.endsWith(' DOUBLE VISION')) return 'MANUAL'
  return null
}

export type DoubleVisionResult = {
  modelo: string
  quantidade_pecas: number
  area_total: number
  bitola_tecnica: string
  estado_validacao: 'permitido' | 'requer_validacao' | 'bloqueado'
  requer_validacao_tecido_fornecedor: boolean
  permitido: boolean
  motivo_bloqueio: string | null
  largura_maxima_padrao_m: number
  largura_maxima_excepcional_m: number
  fabricacao_por_peca: Record<string, unknown>
  componentes_tecnicos: Record<string, unknown> & {
    // Quantidade autoritativa por peça, retornada pelo serviço Double Vision.
    clips: { quantidade_un: number; regra: string }
  }
  custo_tecnico: number | null
  custo_cadastrado: number | null
  preco_unitario: number
  subtotal: number
  preco_disponivel: boolean
  origem_preco: string
  alertas: string[]
  aviso: string
}

export type DoubleVisionState = { key: string; result?: DoubleVisionResult; error?: string }

export const doubleVisionKey = (p: BudgetProduct, profile: CommercialType) =>
  JSON.stringify([p.productId, p.width, p.height, p.quantity, p.discount, profile])