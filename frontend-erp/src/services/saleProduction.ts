import { getOrder, type ApiOrder } from './api'
import { getApiAuthHeaders } from './auth'
import { budgetProductionDisabledReason, budgetProductionEnabled } from './budgetProduction'

// Reuse the local-only gate already used by Orçamentos; this never enables a flag.
export const saleProductionEnabled = budgetProductionEnabled
export const saleProductionDisabledReason = budgetProductionDisabledReason

export function saleProductionReason(order: ApiOrder): string | undefined {
  if (!saleProductionEnabled) return saleProductionDisabledReason
  if (!['APROVADO', 'FATURADO', 'CONCLUIDO'].includes(order.status || '')) return 'Venda cancelada ou com situação não suportada para fabricação.'
  if (!order.itens.some(item => (item.tipo_item || 'PRODUTO').toUpperCase() !== 'SERVICO')) return 'Esta venda contém somente serviços; instalação não gera peças de fabricação.'
  return undefined
}

export async function prepareSaleProduction(saleId: number) {
  if (!saleProductionEnabled) throw new Error(saleProductionDisabledReason)
  const companyId = (await getApiAuthHeaders())['X-Empresa-ID']
  if (!companyId || !Number.isInteger(Number(companyId)) || Number(companyId) <= 0) throw new Error('Empresa ativa não encontrada.')
  const order = await getOrder(saleId)
  if ((await getApiAuthHeaders())['X-Empresa-ID'] !== companyId) throw new Error('A empresa ativa mudou. Abra novamente a integração de produção.')
  if (order.id !== saleId || (order.empresa_id != null && String(order.empresa_id) !== companyId)) throw new Error('Venda incompatível com a empresa ativa.')
  const reason = saleProductionReason(order)
  if (reason) throw new Error(reason)
  return order
}
