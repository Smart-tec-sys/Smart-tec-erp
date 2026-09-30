import type { ApiProduct, BudgetProduct, CommercialType } from './budget'

const normalize = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replaceAll('_', ' ')

export function romanaTetoKind(p: Pick<ApiProduct, 'modelo_tecnico' | 'modelo' | 'nome'>): 'MANUAL_BASTAO' | 'MANUAL_CORRENTE' | 'MOTORIZADA' | null {
  const text = normalize(`${p.modelo_tecnico || ''} ${p.modelo || ''} ${p.nome}`)
  if (!text.includes('ROMANA') || !text.includes('TETO')) return null
  if (text.includes('MOTORIZ')) return 'MOTORIZADA'
  return 'MANUAL_BASTAO'
}

export type RomanaTetoResult = {
  modelo: string
  quantidade_modulos: number
  area_real_m2: number
  area_faturavel_m2: number
  minimo_faturavel_aplicado: boolean
  fabricacao_por_modulo: Record<string, unknown>
  custo_tecnico: null
  custo_cadastrado: number | null
  preco_unitario: number
  subtotal: number
  preco_disponivel: boolean
  alertas: string[]
  origem_preco: string
  aviso: string
  tecido_custo_resolvido?: {
    familia: string
    cor: string
    largura_modulo_m: number
    largura_tecido_selecionada_m: number | null
    codigo_fonte: string | null
    produto_fonte_id: number | null
    custo_tecido_m2: number | null
    status: string
  }
}

export type RomanaTetoState = { key: string; result?: RomanaTetoResult; error?: string }

export const romanaTetoKey = (p: BudgetProduct, profile: CommercialType) =>
  JSON.stringify([
    p.productId,
    p.width,
    p.height,
    p.quantity,
    p.discount,
    profile,
    p.acao_acionamento || 'MANUAL_BASTAO',
    p.lado_comando || '',
    p.comprimento_bastao || '',
    p.comprimento_corrente_sem_fim || '',
    p.color || '',
  ])