import type { ApiBudget, ApiBudgetItem } from '../types/budget'
import { getBudget } from './api'
import { getApiAuthHeaders } from './auth'

type DraftItem = Pick<ApiBudgetItem, 'id' | 'tipo_item' | 'produto_id' | 'servico_id' | 'descricao' | 'codigo_interno' | 'grupo_tecnico' | 'modelo_tecnico' | 'quantidade' | 'largura' | 'altura' | 'area' | 'unidade' | 'cor' | 'ambiente' | 'observacao_item' | 'dados_tecnicos'>
export type BudgetServiceOrderDraft = {
  tipo: 'RASCUNHO_OS'
  empresa_id: number
  orcamento_id: number
  numero_orcamento: string
  cliente_id: number | null
  cliente_nome: string
  cliente_final: { nome: string; documento: string; telefone: string; email: string; endereco: string }
  observacao: string
  itens: DraftItem[]
}

export const serviceOrderBackendPending = 'A criação de OS depende de um módulo e uma rota persistente no backend. Nenhuma ordem de serviço foi criada.'

export function budgetToServiceOrderDraft(budget: ApiBudget, empresaId: number): BudgetServiceOrderDraft {
  if (!Number.isInteger(empresaId) || empresaId <= 0) throw new Error('Empresa ativa não encontrada para preparar a OS.')
  if ('empresa_id' in budget && budget.empresa_id != null && Number(budget.empresa_id) !== empresaId) throw new Error('O orçamento pertence a outra empresa.')
  return {
    tipo: 'RASCUNHO_OS', empresa_id: empresaId, orcamento_id: budget.id, numero_orcamento: String(budget.numero || budget.id),
    cliente_id: budget.cliente_id, cliente_nome: budget.cliente_nome || budget.cliente_final_nome || 'Cliente não informado',
    cliente_final: { nome: budget.cliente_final_nome || '', documento: budget.cliente_final_documento || '', telefone: budget.cliente_final_telefone || '', email: budget.cliente_final_email || '', endereco: budget.cliente_final_endereco || '' },
    observacao: budget.observacao || '',
    itens: budget.itens.map(item => structuredClone({
      id: item.id, tipo_item: item.tipo_item, produto_id: item.produto_id, servico_id: item.servico_id, descricao: item.descricao,
      codigo_interno: item.codigo_interno, grupo_tecnico: item.grupo_tecnico, modelo_tecnico: item.modelo_tecnico,
      quantidade: item.quantidade, largura: item.largura, altura: item.altura, area: item.area, unidade: item.unidade,
      cor: item.cor, ambiente: item.ambiente, observacao_item: item.observacao_item, dados_tecnicos: item.dados_tecnicos,
    })),
  }
}

export async function prepareBudgetServiceOrder(id: number) {
  const empresaId = Number((await getApiAuthHeaders())['X-Empresa-ID'])
  const budget = await getBudget(id)
  if (Number((await getApiAuthHeaders())['X-Empresa-ID']) !== empresaId) throw new Error('A empresa ativa mudou. Abra novamente o orçamento.')
  if (budget.id !== id) throw new Error('O orçamento retornado não corresponde ao solicitado.')
  return budgetToServiceOrderDraft(budget, empresaId)
}

export function serviceOrderDraftText(draft: BudgetServiceOrderDraft) {
  return `RASCUNHO INTERNO DE ORDEM DE SERVIÇO — OS NÃO CRIADA\n${serviceOrderBackendPending}\n\n${JSON.stringify(draft, null, 2)}\n`
}

export function downloadServiceOrderDraft(draft: BudgetServiceOrderDraft) {
  const blob = new Blob([serviceOrderDraftText(draft)], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob), link = document.createElement('a')
  link.href = url
  link.download = `Rascunho-OS-Orcamento-${draft.numero_orcamento.replace(/[^a-zA-Z0-9_-]/g, '-') || draft.orcamento_id}.txt`
  document.body.appendChild(link); link.click(); link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}
