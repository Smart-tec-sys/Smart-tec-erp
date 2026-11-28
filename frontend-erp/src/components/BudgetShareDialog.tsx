import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ApiBudget } from '../types/budget'
import { budgetShareOptions, budgetShareUrl, downloadBudgetForShare } from '../services/budgetShare'
import type { BudgetShareChannel } from '../services/budgetShare'
import type { BudgetPdfMode } from '../services/budgetPdfData'
import './rowActionsMenu.css'

export function BudgetShareDialog({ budget, channel, onClose }: { budget: ApiBudget; channel: BudgetShareChannel; onClose: () => void }) {
  const options = budgetShareOptions(budget.parceiro_id != null)
  const [mode, setMode] = useState<BudgetPdfMode>(options[0].mode)
  const [recipient, setRecipient] = useState('')
  const [internalConfirmed, setInternalConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [prepared, setPrepared] = useState<{ filename: string; number: string; warnings: string[] } | null>(null)
  const generating = useRef(false)
  const dialog = useRef<HTMLElement>(null)
  const internal = mode === 'reseller_internal'
  let href = '', recipientError = ''
  try { href = budgetShareUrl(channel, recipient, prepared?.number ?? budget.numero, internal) }
  catch (err) { recipientError = err instanceof Error ? err.message : String(err) }

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()
    function keys(event: KeyboardEvent) {
      if (event.key === 'Escape' && !generating.current) onClose()
      if (event.key !== 'Tab') return
      const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], select:not(:disabled), input:not(:disabled)') ?? [])
      const first = controls[0], last = controls[controls.length - 1]
      if (!first || !dialog.current?.contains(document.activeElement)) { event.preventDefault(); (first ?? dialog.current)?.focus(); return }
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', keys)
    return () => { document.removeEventListener('keydown', keys); previous?.focus() }
  }, [onClose])

  async function download() {
    if (generating.current) return
    generating.current = true; setBusy(true); setError(''); setPrepared(null); dialog.current?.focus()
    try {
      const result = await downloadBudgetForShare(budget.id, mode, internalConfirmed)
      setPrepared({ filename: result.filename, number: String(result.budget.numero || result.budget.id), warnings: result.warnings })
    } catch (err) { setError(err instanceof Error ? err.message : 'Não foi possível preparar o PDF.') }
    finally { generating.current = false; setBusy(false) }
  }

  return createPortal(<div className="modal-overlay"><section ref={dialog} tabIndex={-1} className="budget-preview budget-share" role="dialog" aria-modal="true" aria-labelledby="budget-share-title" aria-busy={busy}>
    <header><h2 id="budget-share-title">Compartilhar orçamento #{budget.numero}</h2><button type="button" className="secondary-button" disabled={busy} onClick={onClose}>Fechar</button></header>
    <p>{channel === 'whatsapp' ? 'WhatsApp' : 'E-mail'}: baixe o PDF, abra a conversa ou mensagem e anexe o arquivo manualmente. Esta tela não envia mensagens nem anexos automaticamente.</p>
    <label className="budget-share-field">Tipo de PDF<select value={mode} disabled={busy} onChange={event => { setMode(event.target.value as BudgetPdfMode); setPrepared(null); setInternalConfirmed(false); setRecipient(''); setError('') }}>
      {options.map(option => <option key={option.mode} value={option.mode}>{option.label}</option>)}
    </select></label>
    {mode === 'reseller_commercial' && <p role="note">PDF Revenda contém repasses comerciais. Destine-o à revenda; para o consumidor, selecione PDF Cliente Final.</p>}
    {internal && <div role="note"><p><strong>Documento interno: contém informações financeiras e técnicas. Não enviar ao cliente.</strong></p>
      <label><input type="checkbox" checked={internalConfirmed} disabled={busy} onChange={event => { setInternalConfirmed(event.target.checked); setPrepared(null) }} /> Confirmo que o destinatário pertence à equipe interna Smart-tec.</label></div>}
    <label className="budget-share-field">{channel === 'whatsapp' ? 'Telefone com DDI e DDD (opcional)' : 'E-mail do destinatário (opcional)'}
      <input type={channel === 'whatsapp' ? 'tel' : 'email'} value={recipient} disabled={busy} autoComplete="off" onChange={event => setRecipient(event.target.value)} placeholder={channel === 'whatsapp' ? '5511999999999' : 'nome@empresa.com.br'} /></label>
    {recipientError && <p role="alert">{recipientError}</p>}
    <button type="button" className="primary-button" disabled={busy || (internal && !internalConfirmed)} onClick={() => void download()}>{busy ? 'Gerando PDF...' : 'Baixar PDF'}</button>
    {error && <div className="api-message error" role="alert">{error}</div>}
    {prepared && <div role="status"><p>Download solicitado: {prepared.filename}. Confira o arquivo em Downloads e anexe-o manualmente. O envio ainda precisa ser realizado por você.</p>
      {prepared.warnings.length > 0 && <p>{prepared.warnings.join(' ')}</p>}
      {href && <a className="secondary-button" href={href} target="_blank" rel="noopener noreferrer">{channel === 'whatsapp' ? 'Abrir WhatsApp para anexar' : 'Abrir e-mail para anexar'}</a>}
    </div>}
  </section></div>, document.body)
}
