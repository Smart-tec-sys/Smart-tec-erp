import { useEffect, useRef, useState } from 'react'
import { CalendarDays, ChevronRight, Clock, Plus } from 'lucide-react'
import type { AgendaHoje } from '../hooks/useAgendaHoje'

export function HeaderAgenda({ onOpen, onNew, agenda }: {
  onOpen: () => void
  onNew: () => void
  agenda: AgendaHoje
}) {
  const [open, setOpen] = useState(false)
  const { events: activeEvents, loading, error, limited, refresh } = agenda
  const wrapperRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) setOpen(false)
    }
    function handleKey(event: KeyboardEvent) {
      if (open && event.key === 'Escape') {
        setOpen(false)
        wrapperRef.current?.querySelector<HTMLButtonElement>('.agenda-header-button')?.focus()
      }
    }
    document.addEventListener('mousedown', handleOutside)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleOutside)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open])

  function navigate(action: () => void) { setOpen(false); action() }


  return <div className="header-agenda" ref={wrapperRef}>
    <button type="button" className={`icon-button agenda-header-button${open ? ' active' : ''}`}
      aria-label="Agenda" aria-expanded={open} aria-controls="header-agenda-panel" onClick={() => { setOpen(value => !value); refresh() }}>
      <CalendarDays size={18} />
      {!loading && !error && activeEvents.length > 0 && <span className="agenda-header-badge">{activeEvents.length > 9 ? '9+' : activeEvents.length}</span>}
    </button>
    {open && <div className="agenda-header-panel" id="header-agenda-panel">
      <div className="agenda-header-panel-head">
        <div><strong>Agenda</strong><span>Compromissos de hoje</span></div>
        <button type="button" className="agenda-header-add" aria-label="Novo compromisso" title="Novo compromisso" onClick={() => navigate(onNew)}><Plus size={17} /></button>
      </div>
      <div className="agenda-header-content">
        {loading && <div className="agenda-header-state" role="status">Carregando agenda...</div>}
        {!loading && error && <div className="agenda-header-state agenda-header-error" role="alert">{error}</div>}
        {!loading && !error && activeEvents.length === 0 && <div className="agenda-header-empty">
          <CalendarDays size={28} /><strong>Nenhum compromisso para hoje</strong><span>Sua agenda está livre neste momento.</span>
        </div>}
        {!loading && !error && activeEvents.map(event => <div className="agenda-header-event" key={event.id}>
          <div className="agenda-header-time"><Clock size={14} /><span>{event.dia_inteiro ? 'Dia inteiro' : new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date(event.inicio))}</span></div>
          <div className="agenda-header-event-copy"><strong>{event.titulo}</strong><span>{event.cliente_nome || event.responsavel_nome || event.categoria}</span></div>
        </div>)}
        {!loading && !error && limited && <div className="agenda-header-state">Limite de compromissos atingido. Consulte a Agenda e refine os filtros.</div>}
      </div>
      <button type="button" className="agenda-header-footer" onClick={() => navigate(onOpen)}><span>Ver agenda completa</span><ChevronRight size={16} /></button>
    </div>}
  </div>
}