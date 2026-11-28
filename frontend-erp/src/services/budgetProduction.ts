import { apiConfig, getBudget, getOrder, getOrders } from './api'
import { getApiAuthHeaders } from './auth'
import { exigirProducaoHabilitada, producaoV1Enabled } from './producaoFlag'

function localApi() {
  try {
    const url = new URL(apiConfig.baseUrl)
    return ['http:', 'https:'].includes(url.protocol) && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
  } catch { return false }
}

// This entry point is prepared only for local development. Never enables the flag.
export const budgetProductionEnabled = producaoV1Enabled && import.meta.env.DEV === true && localApi()
export const budgetProductionDisabledReason = 'Produção requer a feature flag existente, desenvolvimento local e API local. Não está liberada no ambiente oficial.'

export async function prepareBudgetProduction(budgetId: number) {
  exigirProducaoHabilitada()
  if (!budgetProductionEnabled) throw new Error(budgetProductionDisabledReason)
  const companyId = (await getApiAuthHeaders())['X-Empresa-ID']
  if (!companyId) throw new Error('Empresa ativa não encontrada.')
  async function sameCompany() {
    if ((await getApiAuthHeaders())['X-Empresa-ID'] !== companyId) throw new Error('A empresa ativa mudou. Abra novamente a integração de produção.')
  }
  const budget = await getBudget(budgetId)
  await sameCompany()
  if (budget.status !== 'APROVADO') throw new Error('Apenas orçamentos aprovados podem seguir para produção.')
  const linked = (await getOrders()).filter(order => order.orcamento_id === budgetId)
  await sameCompany()
  if (!linked.length) throw new Error('Gere e confirme a venda deste orçamento antes de abrir a produção. Nenhuma venda foi criada automaticamente.')
  if (linked.length !== 1) throw new Error('Há mais de uma venda vinculada. Confira os vínculos antes de continuar.')
  const order = await getOrder(linked[0].id)
  await sameCompany()
  if (order.orcamento_id !== budgetId || (order.empresa_id != null && String(order.empresa_id) !== companyId)) throw new Error('Venda incompatível com o orçamento ou com a empresa ativa.')
  if (!['ABERTO', 'FATURADO', 'CONCLUIDO'].includes(order.status || '')) throw new Error('Venda cancelada ou com situação não suportada para fabricação.')
  return { budget, order }
}
