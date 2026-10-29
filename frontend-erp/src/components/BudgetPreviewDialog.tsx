import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { getBudget } from '../services/api'
import type { ApiBudget } from '../types/budget'
import { formatCurrency } from '../types/budget'
import { budgetPdfFilename } from '../services/budgetPdfData'
import type { BudgetPdfMode } from '../services/budgetPdfData'
import './rowActionsMenu.css'

export function BudgetPreviewDialog({ id, onClose }: { id: number; onClose: () => void }) {
  const [budget, setBudget] = useState<ApiBudget | null>(null)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLElement>(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const generating = useRef(false)
  async function exportPdf(mode: BudgetPdfMode) {
    if (!budget || generating.current) return
    generating.current = true; setPdfBusy(true); setPdfError('')
    try {
      const { generateBudgetPdf, loadBudgetPdfContext, downloadBudgetPdf } = await import('../services/budgetPdf')
      const context = await loadBudgetPdfContext(budget)
      const blob = await generateBudgetPdf(budget, mode, context)
      downloadBudgetPdf(blob, budgetPdfFilename(String(budget.numero || budget.id), mode))
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : 'Não foi possível gerar o PDF.')
    } finally { generating.current = false; setPdfBusy(false) }
  }
  useEffect(() => {
    let cancelled = false
    const previous = document.activeElement as HTMLElement | null
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()
    void getBudget(id).then(data => { if (!cancelled) setBudget(data) }).catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)) })
    function keys(event: KeyboardEvent) {
      if (event.key === 'Escape' && !generating.current) onClose()
      if (event.key === 'Tab') {
        const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], select, input, textarea, [tabindex="0"]') ?? [])
        const first = controls[0], last = controls[controls.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }
    document.addEventListener('keydown', keys)
    return () => { cancelled = true; document.removeEventListener('keydown', keys); previous?.focus() }
  }, [id, onClose])
  return createPortal(<div className="modal-overlay"><section ref={dialog} className="budget-preview" role="dialog" aria-modal="true" aria-labelledby="budget-preview-title">
    <header><h2 id="budget-preview-title">Orçamento {budget ? `#${budget.numero}` : `#${id}`}</h2><button type="button" className="secondary-button" disabled={pdfBusy} onClick={onClose}>Fechar</button></header>
    {error ? <div className="api-message error" role="alert">{error}</div> : !budget ? <p>Carregando orçamento...</p> : <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }} aria-label="PDF do orçamento">
        {budget.parceiro_id == null ? <button type="button" className="primary-button" disabled={pdfBusy} onClick={() => void exportPdf('direct')}>Gerar PDF</button> : <>
          <button type="button" className="secondary-button" disabled={pdfBusy} onClick={() => void exportPdf('reseller_internal')}>PDF interno da Revenda</button>
          <button type="button" className="primary-button" disabled={pdfBusy} onClick={() => void exportPdf('reseller_client')}>PDF Cliente Final</button>
        </>}
        {pdfBusy && <span role="status">Gerando PDF...</span>}
      </div>
      {pdfError && <div className="api-message error" role="alert">{pdfError}</div>}
      <dl><div><dt>Cliente</dt><dd>{budget.cliente_nome || (budget.cliente_id == null ? '—' : `Cliente #${budget.cliente_id}`)}</dd></div><div><dt>Status</dt><dd>{budget.status}</dd></div><div><dt>Perfil comercial</dt><dd>{budget.perfil_comercial || '—'}</dd></div><div><dt>Validade</dt><dd>{budget.validade || '—'}</dd></div></dl>
      <h3>Itens do orçamento</h3><div className="table-wrap"><table><thead><tr><th>Descrição</th><th>Quantidade</th><th>Medidas</th><th>Unidade</th><th>Preço unitário</th><th>Desconto</th><th>Subtotal</th></tr></thead><tbody>{budget.itens.map((item, index) => <tr key={item.id ?? index}><td>{item.descricao}<small>{item.observacao_item}</small></td><td>{item.quantidade}</td><td>{item.largura} × {item.altura}</td><td>{item.unidade || '—'}</td><td>{formatCurrency(Number(item.preco_unitario))}</td><td>{formatCurrency(Number(item.desconto))}</td><td>{formatCurrency(Number(item.subtotal))}</td></tr>)}</tbody></table>{!budget.itens.length && <p>Nenhum item.</p>}</div>
      <dl><div><dt>Total</dt><dd>{formatCurrency(Number(budget.total))}</dd></div><div><dt>Desconto</dt><dd>{formatCurrency(Number(budget.desconto))}</dd></div><div><dt>Total final</dt><dd><strong>{formatCurrency(Number(budget.total_final))}</strong></dd></div></dl>
      <h3>Observações</h3><p>{budget.observacao || '—'}</p><h3>Observação interna</h3><p>{budget.observacao_interna || '—'}</p>
    </>}
  </section></div>, document.body)
}
