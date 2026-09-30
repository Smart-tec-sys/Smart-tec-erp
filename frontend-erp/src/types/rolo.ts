import type { ApiProduct, BudgetProduct, CommercialType } from './budget'

const normalize = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replaceAll('_', ' ')

const COMPONENT_GROUPS = ['TUBO', 'COMANDO', 'ACESSORIO', 'ACESSÓRIO', 'CORRENTE', 'SUPORTE', 'TAMPA', 'PONTEIRA', 'BANDO', 'GUIA', 'EMENDA', 'BASE', 'LATERAL', 'PERFIL', 'EIXO', 'MOTOR', 'ACIONAMENTO', 'CONTROLADOR', 'RECEPTOR', 'TRANSMISSOR', 'BOTO', 'INTERRUPTOR', 'HASTE', 'VARAO', 'VARÃO', 'CABO', 'FIO', 'CONECTOR', 'TERMINAL', 'PLACA', 'CIRCUITO', 'SENSOR', 'BATERIA', 'CARREGADOR', 'FONTE', 'TRANSFORMADOR', 'DRIVER', 'MODULO', 'MÓDULO', 'CHAVE', 'RELE', 'RELÉ', 'CONTATO', 'FUSIVEL', 'FUSÍVEL', 'DISJUNTOR', 'CAPACITOR', 'RESISTOR', 'DIODO', 'TRANSISTOR', 'CI', 'MICROCONTROLADOR', 'PROGRAMADOR', 'TIMER', 'RELOGIO', 'RELÓGIO', 'CRONOMETRO', 'CRONÔMETRO']

const COMPONENT_FAMILIES = ['TUBO', 'COMANDO', 'ACESSORIO', 'ACESSÓRIO', 'CORRENTE', 'SUPORTE', 'TAMPA', 'PONTEIRA', 'BANDO', 'GUIA', 'EMENDA', 'BASE', 'LATERAL', 'PERFIL', 'EIXO', 'MOTOR', 'ACIONAMENTO', 'CONTROLADOR', 'RECEPTOR', 'TRANSMISSOR', 'BOTO', 'INTERRUPTOR', 'HASTE', 'VARAO', 'VARÃO', 'CABO', 'FIO', 'CONECTOR', 'TERMINAL', 'PLACA', 'CIRCUITO', 'SENSOR', 'BATERIA', 'CARREGADOR', 'FONTE', 'TRANSFORMADOR', 'DRIVER', 'MODULO', 'MÓDULO', 'CHAVE', 'RELE', 'RELÉ', 'CONTATO', 'FUSIVEL', 'FUSÍVEL', 'DISJUNTOR', 'CAPACITOR', 'RESISTOR', 'DIODO', 'TRANSISTOR', 'CI', 'MICROCONTROLADOR', 'PROGRAMADOR', 'TIMER', 'RELOGIO', 'RELÓGIO', 'CRONOMETRO', 'CRONÔMETRO']

const COMPONENT_TYPES = ['COMPONENTE', 'COMPONENT', 'PECA', 'PEÇA', 'ACESSORIO', 'ACESSÓRIO', 'INSUMO', 'MATERIA_PRIMA', 'MATÉRIA_PRIMA', 'MATERIA-PRIMA', 'MATÉRIA-PRIMA', 'SEMIACABADO', 'SEMI-ACABADO', 'SEMI ACABADO', 'SUBMONTAGEM', 'SUB-MONTAGEM', 'KIT_COMPONENTE', 'KIT_COMPONENT']

function isComponent(p: ApiProduct): boolean {
  const gt = normalize(p.grupo_tecnico || '')
  const ft = normalize(p.familia_tecnica || '')
  const tp = normalize(p.tipo_produto || '')
  const mt = normalize(p.modelo_tecnico || '')
  if (COMPONENT_GROUPS.some(g => gt === g || gt.startsWith(g + ' '))) return true
  if (COMPONENT_FAMILIES.some(f => ft === f || ft.startsWith(f + ' '))) return true
  if (COMPONENT_TYPES.some(t => tp === t || tp.startsWith(t + ' '))) return true
  if (COMPONENT_GROUPS.some(g => mt === g || mt.startsWith(g + ' ') || mt.endsWith(' ' + g) || mt.includes(' ' + g + ' '))) return true
  return false
}

export function roloKind(p: ApiProduct): 'MANUAL' | 'MOTORIZADA' | null {
  if (isComponent(p)) return null
  const text = normalize(`${p.modelo_tecnico || ''} ${p.modelo || ''} ${p.nome}`)
  if (!text.includes('ROL') && !text.includes('ROLÔ')) return null
  if (text.includes('MOTORIZ')) return 'MOTORIZADA'
  const mt = normalize(p.modelo_tecnico || '')
  if (mt.startsWith('ROLO') || mt.startsWith('ROLÔ')) return 'MANUAL'
  if (text.includes(' ROLO ') || text.includes(' ROLÔ ') || text.startsWith('ROLO ') || text.startsWith('ROLÔ ') || text.endsWith(' ROLO') || text.endsWith(' ROLÔ')) return 'MANUAL'
  return null
}

export function normalizeRoloDrive(value: string | undefined): 'manual' | 'motorizado' {
  if (!value) return 'manual'
  const v = value.trim().toLowerCase()
  if (v === 'motorizado' || v === 'motorizada') return 'motorizado'
  return 'manual'
}

export type RoloResult = {
  modelo: string
  tipo_acionamento: string
  quantidade_pecas: number
  area_real_m2: number
  area_faturavel_m2: number
  minimo_faturavel_aplicado: boolean
  bitola_tecnica: string
  acionamento_permitido: string
  requer_confirmacao_vendedor: boolean
  observacao_tecnica: string | null
  fabricacao_por_peca: Record<string, unknown>
  componentes_tecnicos: Record<string, unknown>
  custo_tecnico: number | null
  custo_cadastrado: number | null
  preco_unitario: number
  subtotal: number
  preco_disponivel: boolean
  origem_preco: string
  alertas: string[]
  aviso: string
}

export type RoloState = { key: string; result?: RoloResult; error?: string }

export const roloKey = (p: BudgetProduct, profile: CommercialType) =>
  JSON.stringify([p.productId, p.width, p.height, p.quantity, p.discount, profile, p.color || '', normalizeRoloDrive(p.acionamento)])