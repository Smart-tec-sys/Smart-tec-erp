import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Loader2, UserPlus, X } from 'lucide-react'
import { createCommercialPartner, createRepresentative } from '../services/api'

export const CREATE_COMMERCIAL_VALUE = '__create_commercial__'
export type CommercialRegistration = 'revenda' | 'representante'
type RecordName = { id: number; nome: string; percentual_padrao?: number }

// Mesmo fluxo do cadastro rápido de Cliente: modal, salvar, inserir na lista e selecionar.
export function CommercialRegistrationDialog({ entity, onClose, onCreated }: {
  entity: CommercialRegistration; onClose: () => void; onCreated: (record: RecordName) => void
}) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const savingRef = useRef(false)
  const title = entity === 'revenda' ? 'Cadastrar nova revenda' : 'Cadastrar novo representante'
  const close = () => { if (!savingRef.current) onClose() }
  async function save() {
    if (savingRef.current || !name.trim()) return
    savingRef.current = true; setSaving(true); setError('')
    try {
      const record = await (entity === 'revenda' ? createCommercialPartner : createRepresentative)({ nome: name.trim() })
      onCreated({ ...record, nome: String(record.nome) })
      onClose()
    } catch (err) { setError(err instanceof Error ? err.message : String(err)) }
    finally { savingRef.current = false; setSaving(false) }
  }
  return createPortal(<div className="modal-overlay" onClick={close}>
    <div className="modal-container" role="dialog" aria-modal="true" aria-label={title} onClick={e => e.stopPropagation()}>
      <div className="modal-header"><h3><UserPlus size={16} /> {title}</h3><button type="button" className="modal-close" aria-label="Fechar cadastro" onClick={close} disabled={saving}><X size={16} /></button></div>
      <form className="modal-form" onSubmit={e => { e.preventDefault(); void save() }}>
        <div className="modal-field"><label htmlFor="commercial-registration-name">Nome *</label><input id="commercial-registration-name" type="text" value={name} onChange={e => { setName(e.target.value); setError('') }} placeholder={entity === 'revenda' ? 'Nome da revenda' : 'Nome do representante'} autoFocus disabled={saving} /></div>
        {error && <div className="modal-error" role="alert">{error}</div>}
        <div className="modal-actions"><button type="button" className="secondary-button" onClick={close} disabled={saving}>Cancelar</button><button type="submit" className="primary-button" disabled={saving || !name.trim()}>{saving ? <><Loader2 size={14} className="spinning" /> Salvando...</> : <><UserPlus size={14} /> Salvar e selecionar</>}</button></div>
      </form>
    </div>
  </div>, document.body)
}
