import { dataLocal, type AgendaEvento } from './agenda'

export interface AgendaNotification {
  id: number
  tipo: 'ATRASADO' | 'PROXIMO'
  mensagem: string
  titulo: string
  inicio: string
}

export function derivarNotificacoesAgenda(events: AgendaEvento[], now = new Date()): AgendaNotification[] {
  const today = dataLocal(now)
  const timestamp = now.getTime()
  return events.flatMap<AgendaNotification>(event => {
    const inicio = new Date(event.inicio)
    const difference = inicio.getTime() - timestamp
    if (event.status !== 'AGENDADO' || !Number.isFinite(difference) || dataLocal(inicio) !== today || difference > 60 * 60_000) return []
    const atrasado = difference < 0
    return [{
      id: event.id,
      tipo: atrasado ? 'ATRASADO' : 'PROXIMO',
      mensagem: atrasado ? 'Compromisso atrasado' : difference === 0 ? 'Compromisso agora' : `Compromisso em ${Math.ceil(difference / 60_000)} min`,
      titulo: event.titulo,
      inicio: event.inicio,
    }]
  }).sort((a, b) => {
    if (a.tipo !== b.tipo) return a.tipo === 'ATRASADO' ? -1 : 1
    const order = Date.parse(a.inicio) - Date.parse(b.inicio)
    return (a.tipo === 'ATRASADO' ? -order : order) || a.id - b.id
  })
}
