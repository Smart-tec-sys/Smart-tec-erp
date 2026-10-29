import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { getOrder, getClients, getFuncionariosCadastro, getCommercialPartners, getRepresentatives, updateOrder, type ApiOrder, type OrderUpdate } from '../services/api'

type Props = { order: ApiOrder; onClose: () => void; onSaved: (order: ApiOrder) => void }
const links = ['cliente_id', 'vendedor_id', 'parceiro_id', 'representante_id'] as const
const labels = ['Cliente', 'Vendedor Smart-tec', 'Revenda', 'Representante']
const finalFields = ['cliente_final_nome', 'cliente_final_documento', 'cliente_final_telefone', 'cliente_final_email', 'cliente_final_endereco'] as const
const finalLabels = ['Cliente final', 'CPF/CNPJ', 'Telefone', 'E-mail', 'Endereço']
const strings = ['status', 'perfil_comercial', 'data_venda', 'prazo_entrega', 'canal_venda', 'observacao', 'observacao_interna'] as const
const stringLabels = ['Situação', 'Perfil comercial', 'Data da venda', 'Prazo de entrega', 'Canal de venda', 'Observações', 'Observação interna']
export function SaleEditDialog({ order, onClose, onSaved }: Props) {
  const [original, setOriginal] = useState<ApiOrder | null>(null)
  const [saleType, setSaleType] = useState<'DIRETA' | 'PARCEIRO'>('DIRETA')
  const [draft, setDraft] = useState<OrderUpdate>({})
  const [names, setNames] = useState<{ id: number; nome?: unknown }[][]>([[], [], [], []])
  const [available, setAvailable] = useState<boolean[]>([false, false, false, false])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    let cancelled = false
    const previous = document.activeElement as HTMLElement | null
    panel.current?.querySelector<HTMLButtonElement>('button')?.focus()
    void Promise.all([getOrder(order.id), Promise.allSettled([getClients(), getFuncionariosCadastro(), getCommercialPartners(), getRepresentatives()])]).then(([sale, lists]) => {
      if (cancelled) return
      setOriginal(sale)
      setSaleType(sale.parceiro_id != null ? 'PARCEIRO' : 'DIRETA')
      const fields: OrderUpdate = {}
      links.forEach(key => { fields[key] = sale[key] ?? null })
      strings.forEach(key => { if (key === 'status' || key === 'perfil_comercial') fields[key] = sale[key] ?? ''; else fields[key] = sale[key] ?? null })
      finalFields.forEach(key => { fields[key] = sale[key] ?? null })
      setDraft(fields)
      setNames(lists.map(result => result.status === 'fulfilled' ? result.value : []))
      setAvailable(lists.map(result => result.status === 'fulfilled'))
    }).catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)) })
    return () => { cancelled = true; previous?.focus() }
  }, [order.id])
  async function save() {
    if (!original || saving) return
    if (draft.cliente_id != null && draft.parceiro_id != null) { setError('Cliente direto e revenda não podem ser informados ao mesmo tempo. Altere o Tipo de venda para corrigir os vínculos.'); return }
    if (saleType === 'DIRETA' && draft.cliente_id == null) { setError('Venda direta exige cliente.'); return }
    if (saleType === 'PARCEIRO' && draft.parceiro_id == null) { setError('Selecione a revenda.'); return }
    setSaving(true); setError('')
    const changes: OrderUpdate = {}
    links.forEach(key => { if (draft[key] !== (original[key] ?? null)) changes[key] = draft[key] })
    strings.forEach(key => { if (draft[key] !== (original[key] ?? null)) { if (key === 'status' || key === 'perfil_comercial') changes[key] = draft[key] ?? ''; else changes[key] = draft[key] } })
    finalFields.forEach(key => { if (draft[key] !== (original[key] ?? null)) changes[key] = draft[key] })
    try { onSaved(await updateOrder(order.id, changes)) }
    catch (err) { setError(err instanceof Error ? err.message : String(err)) }
    finally { setSaving(false) }
  }
  return createPortal(<div className="modal-overlay"><section ref={panel} className="budget-preview" role="dialog" aria-modal="true" aria-labelledby="sale-edit-title" onKeyDown={event => {
    if (event.key === 'Escape' && !saving) onClose()
    if (event.key === 'Tab') {
      const controls = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)') || [])
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1)?.focus() }
      else if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0]?.focus() }
    }
  }}>
    <header><h2 id="sale-edit-title">Editar venda {order.numero || `#${order.id}`}</h2><button type="button" className="secondary-button" disabled={saving} onClick={onClose}>Cancelar</button></header>
    <p>Editar dados da venda. Itens, valores e orçamento de origem permanecem preservados.</p>
    {error && <div className="api-message error" role="alert">{error}</div>}
    {!original ? <p>Carregando venda...</p> : <form onSubmit={event => { event.preventDefault(); void save() }}>
      <div className="form-grid general-grid">
        <label className="field"><span>Tipo de venda</span><select disabled={saving} value={saleType} onChange={event => {
          const type = event.target.value === 'PARCEIRO' ? 'PARCEIRO' : 'DIRETA'
          setSaleType(type)
          setDraft(current => {
            const next = { ...current }
            if (type === 'PARCEIRO') next.cliente_id = null
            else { next.parceiro_id = null; finalFields.forEach(key => { next[key] = null }) }
            return next
          })
        }}><option value="DIRETA">Venda direta</option><option value="PARCEIRO">Venda por revenda</option></select></label>
        {links.map((key, index) => (key === 'cliente_id' && saleType === 'PARCEIRO') || (key === 'parceiro_id' && saleType === 'DIRETA') ? null : <label className="field" key={key}><span>{labels[index]}</span><select required={key === 'cliente_id' || key === 'parceiro_id'} disabled={saving || !available[index]} value={draft[key] ?? ''} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value ? Number(event.target.value) : null }))}>
          <option value="">—</option>
          {draft[key] != null && !names[index].some(item => item.id === draft[key]) && <option value={draft[key]!}>{labels[index]} #{draft[key]}</option>}
          {names[index].map(item => <option key={item.id} value={item.id}>{typeof item.nome === 'string' ? item.nome : `${labels[index]} #${item.id}`}</option>)}
        </select>{!available[index] && <small>Lista indisponível; vínculo preservado.</small>}</label>)}
        {saleType === 'PARCEIRO' && finalFields.map((key, index) => <label className="field" key={key}><span>{finalLabels[index]}</span><input disabled={saving} type={key === 'cliente_final_email' ? 'email' : 'text'} value={draft[key] ?? ''} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value || null }))} /></label>)}
        {strings.map((key, index) => <label className="field" key={key}><span>{stringLabels[index]}</span>
          {key === 'status' || key === 'perfil_comercial' ? <select disabled={saving} value={draft[key] ?? ''} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value }))}>
            {!['ABERTO', 'CONCLUIDO', 'CANCELADO', 'FATURADO', 'VAREJO', 'DECORADOR', 'CONSUMIDOR_FINAL'].includes(draft[key] || '') && <option value={draft[key] ?? ''}>{draft[key] || '—'}</option>}
            {(key === 'status' ? ['ABERTO', 'CONCLUIDO', 'CANCELADO', 'FATURADO'] : ['VAREJO', 'DECORADOR', 'CONSUMIDOR_FINAL']).map(value => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
          </select> : key.startsWith('observacao') ? <textarea disabled={saving} value={draft[key] ?? ''} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value || null }))} /> : <input disabled={saving} type={key === 'data_venda' || key === 'prazo_entrega' ? 'date' : 'text'} value={draft[key] ?? ''} onChange={event => setDraft(current => ({ ...current, [key]: event.target.value || null }))} />}
        </label>)}
      </div><button type="submit" className="primary-button" disabled={saving}>{saving ? 'Salvando...' : 'Salvar venda'}</button>
    </form>}
  </section></div>, document.body)
}
