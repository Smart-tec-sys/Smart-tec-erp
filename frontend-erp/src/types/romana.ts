import type { ApiProduct, BudgetProduct, CommercialType } from './budget'

const normalize = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replaceAll('_', ' ')
export function romanaKind(p: Pick<ApiProduct, 'modelo_tecnico' | 'modelo' | 'nome'>): 'MANUAL' | 'MOTORIZADA' | null {
  const text = normalize(`${p.modelo_tecnico || ''} ${p.modelo || ''} ${p.nome}`)
  if (!text.includes('ROMANA') || text.includes('TETO')) return null
  if (text.includes('MOTORIZ')) return 'MOTORIZADA'
  return ['ROMANA', 'ROMANA MANUAL'].includes(normalize(p.modelo_tecnico || '')) ? 'MANUAL' : null
}
export type RomanaResult = {
  modelo: string; quantidade_pecas: number; area_total: number
  fabricacao_por_peca: Record<string, unknown>
  defaults_utilizados: { tipo_corrente: string; tipo_comando: string }
  custo_tecnico: null; custo_cadastrado: number | null; preco_unitario: number; subtotal: number
  preco_disponivel: boolean; origem_preco: string; alertas: string[]; aviso: string
}
export type RomanaState = { key: string; result?: RomanaResult; error?: string }
export const romanaKey = (p: BudgetProduct, profile: CommercialType) => JSON.stringify([p.productId, p.width, p.height, p.quantity, p.discount, profile])
