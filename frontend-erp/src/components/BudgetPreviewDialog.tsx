import { commercialDisplayText } from '../utils/commercialDisplay'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { getBudget } from '../services/api'
import type { ApiBudget } from '../types/budget'
import { formatCurrency } from '../types/budget'
import type { BudgetPdfMode } from '../services/budgetPdfData'
import './rowActionsMenu.css'

export function BudgetPreviewDialog({ id, onClose }: { id: number; onClose: () => void }) {
  const [budget, setBudget] = useState<ApiBudget | null>(null)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLElement>(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfError, setPdfError] = useState('')
  const [pdfWarning, setPdfWarning] = useState('')
  const generating = useRef(false)
  const [pdfPreview, setPdfPreview] = useState<{
    blob: Blob; filename: string
  } | null>(null)
  const [previewUrl, setPreviewUrl] = useState('')

  useEffect(() => {
    if (!pdfPreview) {
      setPreviewUrl('')
      return
    }
    const url = URL.createObjectURL(pdfPreview.blob)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [pdfPreview])

  async function downloadPreview() {
    if (!pdfPreview) return
    const { downloadBudgetPdf } = await import('../services/budgetPdf')
    downloadBudgetPdf(pdfPreview.blob, pdfPreview.filename)
  }
  async function exportPdf(mode: BudgetPdfMode) {
    if (!budget || generating.current) return
    generating.current = true; setPdfBusy(true); setPdfError(''); setPdfWarning('')
    try {
      const { prepareSavedBudgetPdf } = await import('../services/budgetPdf')
      const result = await prepareSavedBudgetPdf(id, mode)
      setBudget(result.budget)
      setPdfPreview({
        blob: result.blob,
        filename: result.filename
      })
      setPdfWarning(result.warnings.join(' '))
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
    <header><h2 id="budget-preview-title">{commercialDisplayText(`Orçamento ${budget ? `#${budget.numero}` : `#${id}`}`, [budget?.numero || ''])}</h2><button type="button" className="secondary-button" disabled={pdfBusy} onClick={onClose}>Fechar</button></header>
    {pdfPreview && previewUrl ? (
      <div style={{display:'grid',gap:12}}>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <button type="button" className="secondary-button"
            onClick={() => setPdfPreview(null)}>
            Voltar ao orçamento
          </button>
          <button type="button" className="primary-button"
            onClick={() => void downloadPreview()}>
            Baixar PDF
          </button>
          <a href={previewUrl} target="_blank"
            rel="noopener noreferrer" className="secondary-button">
            Abrir para imprimir
          </a>
        </div>
        {pdfWarning && <p role="status">{pdfWarning}</p>}
        <iframe src={previewUrl} title="Visualização do PDF"
          style={{width:'100%',height:'60vh',border:'1px solid #ddd',borderRadius:6}} />
      </div>
    ) : error ? <div className="api-message error" role="alert">{error}</div> : !budget ? <p>Carregando orçamento...</p> : <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }} aria-label="PDF do orçamento">
        {budget.parceiro_id == null ? <button type="button" className="primary-button" disabled={pdfBusy} onClick={() => void exportPdf('direct')}>Gerar PDF</button> : <>
          <button type="button" className="secondary-button" disabled={pdfBusy} onClick={() => void exportPdf('reseller_commercial')}>PDF Revenda</button>
          <button type="button" className="secondary-button" disabled={pdfBusy} onClick={() => void exportPdf('reseller_internal')}>PDF Interno Smart-tec</button>
          <button type="button" className="primary-button" disabled={pdfBusy} onClick={() => void exportPdf('reseller_client')}>PDF Cliente Final</button>
        </>}
        {pdfBusy && <span role="status">Gerando PDF...</span>}
      </div>
      {pdfError && <div className="api-message error" role="alert">{pdfError}</div>}
      {pdfWarning && <p role="status">{pdfWarning}</p>}
      <dl><div><dt>Cliente</dt><dd>{commercialDisplayText(budget.cliente_nome || (budget.cliente_id == null ? '—' : `Cliente #${budget.cliente_id}`))}</dd></div><div><dt>Status</dt><dd>{budget.status}</dd></div><div><dt>Perfil comercial</dt><dd>{budget.perfil_comercial || '—'}</dd></div><div><dt>Validade</dt><dd>{budget.validade || '—'}</dd></div></dl>
      <h3 className="commercial-title">Itens do orçamento</h3><div className="table-wrap"><table><thead><tr><th>Descrição</th><th>Quantidade</th><th>Medidas</th><th>Unidade</th><th>Preço unitário</th><th>Desconto</th><th>Subtotal</th></tr></thead><tbody>{budget.itens.map((item, index) => <tr key={item.id ?? index}><td><span>{commercialDisplayText(item.descricao, [item.codigo_interno || ''])}</span><small>{item.observacao_item}</small></td><td>{item.quantidade}</td><td>{item.largura} × {item.altura}</td><td>{item.unidade || '—'}</td><td>{formatCurrency(Number(item.preco_unitario))}</td><td>{formatCurrency(Number(item.desconto))}</td><td>{formatCurrency(Number(item.subtotal))}</td></tr>)}</tbody></table>{!budget.itens.length && <p>Nenhum item.</p>}</div>
      <h3 className="commercial-title">Composição comercial</h3>
      <dl>
        <div><dt>Subtotal</dt><dd>{formatCurrency(Number(budget.total))}</dd></div>
        <div><dt>Desconto</dt><dd>{formatCurrency(Number(budget.desconto))}</dd></div>
        <div><dt>Valor interno</dt><dd>{formatCurrency(Number(budget.total_final))}</dd></div>

        {budget.valor_parceiro != null && Number(budget.valor_parceiro) > 0 &&
          <div><dt>Valor da revenda ({Number(budget.percentual_parceiro ?? 0)}%)</dt>
          <dd>{formatCurrency(Number(budget.valor_parceiro))}</dd></div>}

        {budget.incluir_rt && budget.valor_rt != null &&
          <div><dt>RT</dt><dd>{formatCurrency(Number(budget.valor_rt))}</dd></div>}

        {budget.base_protegida != null &&
          <div><dt>Base protegida</dt><dd>{formatCurrency(Number(budget.base_protegida))}</dd></div>}

        {budget.incluir_taxa_bancaria && budget.valor_taxa_bancaria != null &&
          <div><dt>Taxa bancária ({Number(budget.taxa_bancaria_percentual ?? 0)}%)</dt>
          <dd>{formatCurrency(Number(budget.valor_taxa_bancaria))}</dd></div>}

        <div style={{gridColumn:'1 / -1', borderTop:'2px solid #dc2626', paddingTop:12}}>
          <dt>Total do cliente</dt>
          <dd style={{fontSize:24,fontWeight:700}}>
            {budget.total_cliente_final != null
              ? formatCurrency(Number(budget.total_cliente_final))
              : budget.parceiro_id == null && !budget.incluir_rt && !budget.incluir_taxa_bancaria
                ? formatCurrency(Number(budget.total_final))
                : 'Não informado'}
          </dd>
        </div>
      </dl>

      <h3 className="commercial-title">Condições de pagamento</h3>
      {budget.pagamento_parcelas?.length ? <>
        <p>{budget.pagamento_modalidade === 'AVISTA' ? 'À vista'
          : budget.pagamento_modalidade === 'ENTRADA_SALDO' ? 'Entrada + saldo'
          : 'Parcelado'}</p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Parcela</th><th>Vencimento</th><th>Forma de pagamento</th><th>Valor</th></tr>
            </thead>
            <tbody>
              {budget.pagamento_parcelas.map((p,index) => (
                <tr key={index}>
                  <td>{p.tipo === 'ENTRADA' ? 'Entrada' : p.tipo === 'SALDO' ? 'Saldo' : p.numero}</td>
                  <td>{p.vencimento?.slice(0,10).split('-').reverse().join('/') || '—'}</td>
                  <td>{p.forma_pagamento_nome || `Forma #${p.forma_pagamento_id}`}</td>
                  <td>{formatCurrency(Number(p.valor))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </> : <p>Condição de pagamento não definida.</p>}

      <h3 className="commercial-title">Observações</h3><p>{budget.observacao || '—'}</p><h3 className="commercial-title">Observação interna</h3><p>{budget.observacao_interna || '—'}</p>
    </>}
  </section></div>, document.body)
}
