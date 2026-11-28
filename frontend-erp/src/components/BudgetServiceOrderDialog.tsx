import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { downloadServiceOrderDraft, prepareBudgetServiceOrder, serviceOrderBackendPending } from '../services/budgetServiceOrder'
import type { BudgetServiceOrderDraft } from '../services/budgetServiceOrder'
import './rowActionsMenu.css'

export function BudgetServiceOrderDialog({ budgetId: id, onClose }: { budgetId: number; onClose: () => void }) {
  const [draft, setDraft] = useState<BudgetServiceOrderDraft | null>(null)
  const [error, setError] = useState('')
  const [downloaded, setDownloaded] = useState(false)
  const dialog = useRef<HTMLElement>(null)
  useEffect(() => {
    let cancelled = false
    const previous = document.activeElement as HTMLElement | null
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()
    void prepareBudgetServiceOrder(id).then(value => { if (!cancelled) setDraft(value) }).catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)) })
    function keys(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab') return
      const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href]') ?? [])
      const first = controls[0], last = controls[controls.length - 1]
      if (!first || !dialog.current?.contains(document.activeElement)) { event.preventDefault(); (first ?? dialog.current)?.focus(); return }
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', keys)
    return () => { cancelled = true; document.removeEventListener('keydown', keys); previous?.focus() }
  }, [id, onClose])
  return createPortal(<div className="modal-overlay"><section ref={dialog} tabIndex={-1} className="budget-preview" role="dialog" aria-modal="true" aria-labelledby="budget-os-title">
    <header><h2 id="budget-os-title">Preparar ordem de serviço</h2><button type="button" className="secondary-button" onClick={onClose}>Fechar</button></header>
    <p role="note">{serviceOrderBackendPending} Este rascunho usa o orçamento salvo e permite revisar cliente, vínculo e descrições antes da futura confirmação de criação.</p>
    {error ? <div className="api-message error" role="alert">{error}</div> : !draft ? <p role="status">Carregando orçamento salvo...</p> : <>
      <dl><div><dt>Orçamento de origem</dt><dd>#{draft.numero_orcamento} (ID {draft.orcamento_id})</dd></div><div><dt>Cliente</dt><dd>{draft.cliente_nome}{draft.cliente_id != null ? ` (ID ${draft.cliente_id})` : ''}</dd></div>
        {draft.cliente_final.nome && <div><dt>Cliente final</dt><dd>{draft.cliente_final.nome}</dd></div>}</dl>
      {draft.cliente_final.endereco && <p>Endereço: {draft.cliente_final.endereco}</p>}
      <div className="table-wrap"><table><thead><tr><th>Tipo</th><th>Descrição</th><th>Quantidade</th><th>Medidas</th></tr></thead><tbody>{draft.itens.map((item, index) => <tr key={item.id ?? index}><td>{item.tipo_item}</td><td>{item.descricao}{item.observacao_item && <small>{item.observacao_item}</small>}</td><td>{item.quantidade} {item.unidade || ''}</td><td>{item.largura} × {item.altura}</td></tr>)}</tbody></table></div>
      {draft.observacao && <p>{draft.observacao}</p>}
      <p>O rascunho baixado também preserva as especificações técnicas salvas dos itens. Ele não possui número de OS nem altera o orçamento.</p>
      <button type="button" className="secondary-button" onClick={() => { downloadServiceOrderDraft(draft); setDownloaded(true) }}>Baixar rascunho interno</button>
      {downloaded && <p role="status">Download do rascunho solicitado. Nenhuma OS foi criada.</p>}
    </>}
    <p><button type="button" className="primary-button" disabled title={serviceOrderBackendPending}>Confirmar criação de OS — backend pendente</button></p>
  </section></div>, document.body)
}
