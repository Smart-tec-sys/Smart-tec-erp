import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ApiOrder } from '../services/api'
import { budgetShareUrl, type BudgetShareChannel } from '../services/budgetShare'
import { downloadDirectSalePdf } from '../services/salePdf'
import './rowActionsMenu.css'

export function SaleShareDialog({ order, channel, onClose }: {
  order: ApiOrder
  channel: BudgetShareChannel
  onClose: () => void
}) {
  const [recipient, setRecipient] = useState('')
  const [busy, setBusy] = useState(false)
  const [prepared, setPrepared] = useState(false)
  const [error, setError] = useState('')
  const generating = useRef(false)
  const dialog = useRef<HTMLElement>(null)

  let href = '', recipientError = ''

  try {
    href = budgetShareUrl(
      channel, recipient,
      String(order.numero || order.id), false, 'Venda'
    )
  } catch (err) {
    recipientError = err instanceof Error ? err.message : String(err)
  }

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    dialog.current?.querySelector<HTMLButtonElement>('button')?.focus()

    function keys(event: KeyboardEvent) {
      if (event.key === 'Escape' && !generating.current) onClose()
      if (event.key !== 'Tab') return
      const controls = Array.from(
        dialog.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), a[href], input:not(:disabled)'
        ) ?? []
      )
      const first = controls[0], last = controls[controls.length - 1]
      if (!first || !dialog.current?.contains(document.activeElement)) {
        event.preventDefault()
        ;(first ?? dialog.current)?.focus()
        return
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }

    document.addEventListener('keydown', keys)
    return () => {
      document.removeEventListener('keydown', keys)
      previous?.focus()
    }
  }, [onClose])

  async function download() {
    if (generating.current) return
    generating.current = true
    setBusy(true)
    setError('')
    setPrepared(false)
    dialog.current?.focus()

    try {
      await downloadDirectSalePdf(order.id)
      setPrepared(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      generating.current = false
      setBusy(false)
    }
  }

  return createPortal(
    <div className="modal-overlay">
      <section ref={dialog} tabIndex={-1}
        className="budget-preview budget-share"
        role="dialog" aria-modal="true"
        aria-labelledby="sale-share-title" aria-busy={busy}>

        <header>
          <h2 id="sale-share-title">Compartilhar venda {order.numero}</h2>
          <button type="button" className="secondary-button"
            disabled={busy} onClick={onClose}>Fechar</button>
        </header>

        <p>PDF do cliente. Baixe o documento e anexe manualmente
          na conversa ou mensagem.</p>

        <label className="budget-share-field">
          {channel === 'whatsapp'
            ? 'Telefone com DDI e DDD'
            : 'E-mail do destinatario'}
          <input type={channel === 'whatsapp' ? 'tel' : 'email'}
            value={recipient} disabled={busy}
            autoComplete="off"
            onChange={e => setRecipient(e.target.value)}
            placeholder={channel === 'whatsapp'
              ? '5511999999999' : 'nome@empresa.com.br'} />
        </label>

        {recipientError && <p role="alert">{recipientError}</p>}

        <button type="button" className="primary-button"
          disabled={busy} onClick={() => void download()}>
          {busy ? 'Gerando PDF...' : 'Baixar PDF'}
        </button>

        {error && <div className="api-message error" role="alert">{error}</div>}

        {prepared && <div role="status">
          <p>Confira o PDF em Downloads. O envio deve ser
            confirmado manualmente.</p>
          {href && <a className="secondary-button" href={href}
            target="_blank" rel="noopener noreferrer">
            {channel === 'whatsapp'
              ? 'Abrir WhatsApp para anexar'
              : 'Abrir e-mail para anexar'}
          </a>}
        </div>}
      </section>
    </div>, document.body
  )
}
