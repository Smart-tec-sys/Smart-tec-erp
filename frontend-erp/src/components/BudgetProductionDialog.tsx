import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { prepareBudgetProduction } from '../services/budgetProduction'
import type { ApiOrder } from '../services/api'
import { ProducaoPanel } from './ProducaoPanel'
import './rowActionsMenu.css'

export function BudgetProductionDialog({ budgetId, onClose }: { budgetId: number; onClose: () => void }) {
  const [order, setOrder] = useState<ApiOrder | null>(null)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLElement>(null)
  useEffect(() => {
    let cancelled = false
    const previous = document.activeElement as HTMLElement | null
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()
    prepareBudgetProduction(budgetId).then(result => { if (!cancelled) setOrder(result.order) })
      .catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)) })
    function keys(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab') return
      const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], select:not(:disabled), input:not(:disabled), textarea:not(:disabled), iframe') ?? [])
      const first = controls[0], last = controls[controls.length - 1]
      if (!first || !dialog.current?.contains(document.activeElement)) { event.preventDefault(); (first ?? dialog.current)?.focus(); return }
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', keys)
    return () => { cancelled = true; document.removeEventListener('keydown', keys); previous?.focus() }
  }, [budgetId, onClose])
  return createPortal(<div className="modal-overlay"><section ref={dialog} tabIndex={-1} className="budget-preview" role="dialog" aria-modal="true" aria-labelledby="budget-production-title">
    <header><h2 id="budget-production-title">Produção do orçamento</h2><button type="button" className="secondary-button" onClick={onClose}>Fechar</button></header>
    <p>Integração local com a venda vinculada. Aprovação, liberação e criação da OP exigem confirmação no módulo de Produção. As etiquetas de rastreabilidade ficam disponíveis após a liberação técnica.</p>
    {error ? <p className="api-message error" role="alert">{error}</p> : order ? <>
      <p>Venda #{order.numero || order.id} · Orçamento #{order.orcamento_numero || budgetId}</p>
      <ProducaoPanel key={order.id} pedidoId={order.id} statusVenda={order.status || ''} />
    </> : <p role="status">Localizando a venda vinculada...</p>}
  </section></div>, document.body)
}
