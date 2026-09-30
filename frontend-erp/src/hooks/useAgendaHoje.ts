import { useCallback, useEffect, useState } from 'react'
import { AGENDA_LIMIT, assinarAtualizacaoAgenda, dataLocal, limiteDia, listarAgenda, type AgendaEvento } from '../services/agenda'

export function useAgendaHoje(activeView: string, refreshKey: number, empresaId?: number) {
  const [today, setToday] = useState(() => dataLocal(new Date()))
  const [revision, setRevision] = useState(0)
  const [events, setEvents] = useState<AgendaEvento[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [limited, setLimited] = useState(false)
  const refresh = useCallback(() => {
    setToday(dataLocal(new Date()))
    setRevision(value => value + 1)
  }, [])

  useEffect(() => assinarAtualizacaoAgenda(refresh), [refresh])

  useEffect(() => {
    // Keep an open dashboard on the current local day, including after sleep.
    const checkDay = () => setToday(dataLocal(new Date()))
    const timer = window.setInterval(checkDay, 30_000)
    window.addEventListener('focus', refresh)
    document.addEventListener('visibilitychange', checkDay)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', refresh)
      document.removeEventListener('visibilitychange', checkDay)
    }
  }, [refresh])

  useEffect(() => {
    const currentDay = dataLocal(new Date())
    if (today !== currentDay) { setToday(currentDay); return }
    const controller = new AbortController()
    setLoading(true)
    setError('')
    setEvents([])
    setLimited(false)
    // This shared summary must not invalidate itself when its request completes.
    listarAgenda({ inicio_de: limiteDia(today), inicio_ate: limiteDia(today, true) }, controller.signal, false)
      .then(data => {
        if (controller.signal.aborted) return
        setLimited(data.length >= AGENDA_LIMIT)
        setEvents(data
          .filter(event => dataLocal(new Date(event.inicio)) === today && event.status !== 'CANCELADO' && event.status !== 'ARQUIVADO')
          .sort((a, b) => Date.parse(a.inicio) - Date.parse(b.inicio)))
      })
      .catch(err => {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Não foi possível carregar a agenda.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [activeView, refreshKey, empresaId, today, revision])

  return { today, events, loading, error, limited, refresh }
}

export type AgendaHoje = ReturnType<typeof useAgendaHoje>
