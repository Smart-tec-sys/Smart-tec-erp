import type { ApiBudget } from '../types/budget'

export type BudgetNotificationType =
  | 'ORCAMENTO_VENCIDO'
  | 'ORCAMENTO_VENCE_HOJE'
  | 'ORCAMENTO_VENCE_EM_BREVE'

export interface BudgetNotification {
  id: string
  budgetId: number
  tipo: BudgetNotificationType
  mensagem: string
  titulo: string
  detalhe: string
  validade: string
  priority: number
}

function dateKey(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDateOnly(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)

  if (!match) return null

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])

  const date = new Date(year, month - 1, day, 12, 0, 0)

  return Number.isNaN(date.getTime()) ? null : date
}

function diffDays(from: Date, to: Date) {
  const fromNoon = new Date(
    from.getFullYear(),
    from.getMonth(),
    from.getDate(),
    12,
  )

  const toNoon = new Date(
    to.getFullYear(),
    to.getMonth(),
    to.getDate(),
    12,
  )

  return Math.round(
    (toNoon.getTime() - fromNoon.getTime()) / 86_400_000,
  )
}

export function derivarNotificacoesOrcamentos(
  budgets: ApiBudget[],
  now = new Date(),
): BudgetNotification[] {
  const todayKey = dateKey(now)

  return budgets
    .flatMap<BudgetNotification>((budget) => {
      if (
        String(budget.status || '').trim().toUpperCase() !== 'EM_ABERTO' ||
        !budget.validade
      ) {
        return []
      }

      const validity = parseDateOnly(budget.validade)

      if (!validity) return []

      const validityKey = dateKey(validity)
      const days = diffDays(now, validity)

      const client =
        budget.cliente_nome?.trim() ||
        'Cliente não informado'

      const title = `Orçamento ${budget.numero}`

      if (validityKey < todayKey) {
        return [{
          id: `budget-overdue-${budget.id}`,
          budgetId: budget.id,
          tipo: 'ORCAMENTO_VENCIDO',
          mensagem: 'Orçamento vencido',
          titulo: title,
          detalhe: client,
          validade: budget.validade,
          priority: 1,
        }]
      }

      if (validityKey === todayKey) {
        return [{
          id: `budget-today-${budget.id}`,
          budgetId: budget.id,
          tipo: 'ORCAMENTO_VENCE_HOJE',
          mensagem: 'Orçamento vence hoje',
          titulo: title,
          detalhe: client,
          validade: budget.validade,
          priority: 2,
        }]
      }

      if (days >= 1 && days <= 3) {
        return [{
          id: `budget-soon-${budget.id}`,
          budgetId: budget.id,
          tipo: 'ORCAMENTO_VENCE_EM_BREVE',
          mensagem:
            days === 1
              ? 'Orçamento vence amanh?'
              : `Orçamento vence em ${days} dias`,
          titulo: title,
          detalhe: client,
          validade: budget.validade,
          priority: 3,
        }]
      }

      return []
    })
    .sort((a, b) => {
      if (a.priority !== b.priority) {
        return a.priority - b.priority
      }

      return (
        a.validade.localeCompare(b.validade) ||
        a.budgetId - b.budgetId
      )
    })
}
