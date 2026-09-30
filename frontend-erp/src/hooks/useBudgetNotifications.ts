import { useCallback, useEffect, useState } from 'react'
import { getBudgets } from '../services/api'
import type { ApiBudget } from '../types/budget'

export function useBudgetNotifications(
  activeView: string,
  refreshKey: number,
) {
  const [budgets, setBudgets] = useState<ApiBudget[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  const refresh = useCallback(() => {
    setRevision((value) => value + 1)
  }, [])

  useEffect(() => {
    window.addEventListener('focus', refresh)

    return () => {
      window.removeEventListener('focus', refresh)
    }
  }, [refresh])

  useEffect(() => {
    let active = true

    setLoading(true)
    setError('')

    getBudgets()
      .then((data) => {
        if (!active) return
        setBudgets(data)
      })
      .catch((err) => {
        if (!active) return

        setError(
          err instanceof Error
            ? err.message
            : 'N?o foi poss?vel carregar os or?amentos.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [activeView, refreshKey, revision])

  return {
    budgets,
    loading,
    error,
    refresh,
  }
}

export type BudgetNotificationsState =
  ReturnType<typeof useBudgetNotifications>
