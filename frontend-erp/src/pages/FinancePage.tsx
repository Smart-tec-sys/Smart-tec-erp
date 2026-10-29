import { Plus, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { ColumnManager } from '../components/ColumnManager'
import { RowActionsMenu } from '../components/RowActionsMenu'
import { CashFlowPanel } from './CashFlowPanel'
import { FinanceTitlesPanel, type RenderCadastro } from './FinanceTitlesPanel'
import {
  createFinanceRecord,
  deleteFinanceRecord,
  listFinanceRecords,
  updateFinanceRecord,
  type FinancePayload,
  type FinanceRecord,
  type FinanceResource,
} from '../services/api'

type Option = { value: string; label: string }
type Column = { id: string; label: string; render: (r: FinanceRecord, all: FinanceRecord[], accounts: FinanceRecord[]) => string }
type FieldKind = 'text' | 'number' | 'select' | 'parent' | 'textarea' | 'account' | 'bool'
type Field = { key: keyof FinancePayload; label: string; kind: FieldKind; options?: Option[]; required?: boolean; wide?: boolean }
type Tab = { id: FinanceResource; label: string; singular: string; newLabel: string; columns: Column[]; fields: Field[]; defaults: FinancePayload }

const option = (value: string, label: string): Option => ({ value, label })
const money = (v: unknown) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const label = (options: Option[], value?: string) => options.find(o => o.value === value)?.label || value || '—'

const ACCOUNT_TYPES = [option('BANCO', 'Banco'), option('CAIXA', 'Caixa')]
const PAYMENT_TYPES = [option('DINHEIRO', 'Dinheiro'), option('PIX', 'PIX'), option('BOLETO', 'Boleto'), option('CARTAO', 'Cartão'), option('TRANSFERENCIA', 'Transferência'), option('OUTRO', 'Outro')]
const PLAN_TYPES = [option('RECEITA', 'Receita'), option('DESPESA', 'Despesa')]
const AVAILABLE_FOR = [option('AMBOS', 'Pagar e receber'), option('RECEBER', 'Somente receber'), option('PAGAR', 'Somente pagar')]
const STATUS_TYPES = [option('AMBOS', 'Receber e pagar'), option('RECEBER', 'Receber'), option('PAGAR', 'Pagar')]

const TABS: Tab[] = [
  {
    id: 'contas-financeiras', label: 'Contas / Caixa', singular: 'conta', newLabel: 'Nova conta',
    columns: [
      { id: 'nome', label: 'Nome', render: r => r.nome },
      { id: 'tipo', label: 'Tipo', render: r => label(ACCOUNT_TYPES, r.tipo) },
      { id: 'banco', label: 'Banco', render: r => r.banco || '—' },
      { id: 'agencia', label: 'Agência', render: r => r.agencia || '—' },
      { id: 'numero_conta', label: 'Conta', render: r => r.numero_conta || '—' },
      { id: 'saldo_inicial', label: 'Saldo inicial', render: r => money(r.saldo_inicial) },
    ],
    fields: [
      { key: 'nome', label: 'Nome', kind: 'text', required: true },
      { key: 'tipo', label: 'Tipo', kind: 'select', options: ACCOUNT_TYPES },
      { key: 'banco', label: 'Banco', kind: 'text' },
      { key: 'agencia', label: 'Agência', kind: 'text' },
      { key: 'numero_conta', label: 'Número da conta', kind: 'text' },
      { key: 'saldo_inicial', label: 'Saldo inicial', kind: 'number' },
      { key: 'observacao', label: 'Observação', kind: 'textarea', wide: true },
    ],
    defaults: { nome: '', tipo: 'BANCO', banco: '', agencia: '', numero_conta: '', saldo_inicial: 0, observacao: '', ativo: true },
  },
  {
    id: 'formas-pagamento', label: 'Formas de pagamento', singular: 'forma de pagamento', newLabel: 'Nova forma',
    columns: [
      { id: 'nome', label: 'Nome', render: r => r.nome },
      { id: 'tipo', label: 'Tipo', render: r => label(PAYMENT_TYPES, r.tipo) },
      { id: 'conta', label: 'Conta padrão', render: (r, _all, accounts) => accounts.find(a => a.id === r.conta_financeira_id)?.nome || '—' },
      { id: 'disponivel_para', label: 'Disponível para', render: r => label(AVAILABLE_FOR, r.disponivel_para) },
    ],
    fields: [
      { key: 'nome', label: 'Nome', kind: 'text', required: true },
      { key: 'tipo', label: 'Tipo', kind: 'select', options: PAYMENT_TYPES },
      { key: 'conta_financeira_id', label: 'Conta financeira padrão', kind: 'account' },
      { key: 'disponivel_para', label: 'Disponível para', kind: 'select', options: AVAILABLE_FOR },
    ],
    defaults: { nome: '', tipo: 'OUTRO', conta_financeira_id: null, disponivel_para: 'AMBOS', ativo: true },
  },
  {
    id: 'plano-contas', label: 'Plano de contas', singular: 'conta do plano', newLabel: 'Nova conta',
    columns: [
      { id: 'codigo', label: 'Código', render: r => r.codigo || '' },
      { id: 'nome', label: 'Nome', render: r => r.nome },
      { id: 'tipo', label: 'Tipo', render: r => label(PLAN_TYPES, r.tipo) },
      { id: 'pai', label: 'Conta pai', render: (r, all) => { const pai = all.find(item => item.id === r.pai_id); return pai ? `${pai.codigo} — ${pai.nome}` : '—' } },
    ],
    fields: [
      { key: 'codigo', label: 'Código', kind: 'text', required: true },
      { key: 'nome', label: 'Nome', kind: 'text', required: true },
      { key: 'tipo', label: 'Tipo', kind: 'select', options: PLAN_TYPES },
      { key: 'pai_id', label: 'Conta pai', kind: 'parent' },
    ],
    defaults: { codigo: '', nome: '', tipo: 'RECEITA', pai_id: null, ativo: true },
  },
  {
    id: 'situacoes', label: 'Situações', singular: 'situação', newLabel: 'Nova situação',
    columns: [
      { id: 'nome', label: 'Nome', render: r => r.nome },
      { id: 'tipo', label: 'Aplicação', render: r => label(STATUS_TYPES, r.tipo) },
      { id: 'quitado', label: 'Quitado', render: r => r.quitado ? 'Sim' : 'Não' },
      { id: 'padrao', label: 'Padrão', render: r => r.padrao ? 'Sim' : 'Não' },
    ],
    fields: [
      { key: 'nome', label: 'Nome', kind: 'text', required: true },
      { key: 'tipo', label: 'Aplicação', kind: 'select', options: STATUS_TYPES },
      { key: 'quitado', label: 'Quitado?', kind: 'bool' },
      { key: 'padrao', label: 'Padrão?', kind: 'bool' },
    ],
    defaults: { nome: '', tipo: 'AMBOS', quitado: false, padrao: false, ativo: true },
  },
  {
    id: 'centros-custo', label: 'Centros de custo', singular: 'centro de custo', newLabel: 'Novo centro',
    columns: [
      { id: 'nome', label: 'Nome', render: r => r.nome },
      { id: 'observacao', label: 'Observação', render: r => r.observacao || '—' },
    ],
    fields: [
      { key: 'nome', label: 'Nome', kind: 'text', required: true },
      { key: 'observacao', label: 'Observação', kind: 'textarea', wide: true },
    ],
    defaults: { nome: '', observacao: '', ativo: true },
  },
]

const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

function friendlyError(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error)
  const match = raw.match(/"detail":"([^"]+)"/)
  if (match) return match[1]
  if (raw.includes('API 404') && raw.includes('Not Found')) return 'Serviço do Financeiro indisponível. Verifique se a migration da F1 foi aplicada e o backend atualizado.'
  if (raw.includes('API 500')) return 'Erro no servidor. Verifique se as tabelas do Financeiro foram criadas no banco.'
  return raw
}

const NEW_ACCOUNT = '__new_account__'

function RecordDialog({ tab, record, records, accounts, nested = false, onClose, onSaved, onAccountCreated }: {
  tab: Tab
  record: FinanceRecord | null
  records: FinanceRecord[]
  accounts: FinanceRecord[]
  nested?: boolean
  onClose: () => void
  onSaved: (message: string) => void
  onAccountCreated?: (account: FinanceRecord) => void
}) {
  const [draft, setDraft] = useState<FinancePayload>(() => record
    ? Object.fromEntries(tab.fields.map(f => [f.key, record[f.key as keyof FinanceRecord] ?? (f.kind === 'parent' ? null : '')])) as FinancePayload
    : { ...tab.defaults })
  const [active, setActive] = useState(record ? record.ativo : true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [newAccountOpen, setNewAccountOpen] = useState(false)
  const parents = records.filter(r => r.id !== record?.id)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && !saving && !newAccountOpen) onClose() }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); previous?.focus() }
  }, [onClose, saving, newAccountOpen])

  async function save() {
    if (saving) return
    for (const field of tab.fields) {
      if (field.required && !String(draft[field.key] ?? '').trim()) { setError(`Informe: ${field.label}.`); return }
    }
    const payload: FinancePayload = { ...draft, ativo: active }
    if ('saldo_inicial' in payload) payload.saldo_inicial = Number(String(payload.saldo_inicial ?? 0).replace(',', '.')) || 0
    setSaving(true); setError('')
    try {
      if (record) await updateFinanceRecord(tab.id, record.id, payload)
      else {
        const created = await createFinanceRecord(tab.id, payload)
        if (nested && onAccountCreated) { onAccountCreated(created); return }
      }
      onSaved(record ? 'Cadastro atualizado com sucesso.' : 'Cadastro criado com sucesso.')
    } catch (err) { setError(friendlyError(err)) } finally { setSaving(false) }
  }

  return createPortal(<div className="modal-overlay">
    <section className="budget-preview" role="dialog" aria-modal="true" aria-labelledby="finance-dialog-title">
      <header>
        <h2 id="finance-dialog-title">{record ? `Editar ${tab.singular}` : tab.newLabel}</h2>
        <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>Cancelar</button>
      </header>
      {error && <div className="api-message error" role="alert">{error}</div>}
      <form onSubmit={event => { event.preventDefault(); void save() }}>
        <div className="form-grid general-grid">
          {tab.fields.map(field => {
            const value = draft[field.key] as string | number | null | undefined
            const set = (next: string | number | null) => setDraft(current => ({ ...current, [field.key]: next }))
            return <label key={field.key} className="field" style={field.wide ? { gridColumn: '1 / -1' } : undefined}>
              <span>{field.label}{field.required ? ' *' : ''}</span>
              {field.kind === 'select' && <select value={String(value ?? '')} onChange={e => set(e.target.value)}>{field.options?.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select>}
              {field.kind === 'parent' && <select value={value == null ? '' : String(value)} onChange={e => set(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Sem conta pai</option>
                {parents.map(p => <option key={p.id} value={p.id}>{p.codigo} — {p.nome}</option>)}
              </select>}
              {field.kind === 'account' && <select value={value == null ? '' : String(value)} onChange={e => { if (e.target.value === NEW_ACCOUNT) setNewAccountOpen(true); else set(e.target.value ? Number(e.target.value) : null) }}>
                <option value="">Sem conta padrão</option>
                {accounts.filter(a => a.ativo || a.id === value).map(a => <option key={a.id} value={a.id}>{a.nome}{a.ativo ? '' : ' (inativa)'}</option>)}
                <option value={NEW_ACCOUNT}>+ Cadastrar nova conta</option>
              </select>}
              {field.kind === 'bool' && <select value={value ? 'SIM' : 'NAO'} onChange={e => setDraft(current => ({ ...current, [field.key]: e.target.value === 'SIM' }))}><option value="NAO">Não</option><option value="SIM">Sim</option></select>}
              {field.kind === 'textarea' && <textarea rows={3} value={String(value ?? '')} onChange={e => set(e.target.value)} />}
              {(field.kind === 'text' || field.kind === 'number') && <input
                type="text" inputMode={field.kind === 'number' ? 'decimal' : undefined} value={String(value ?? '')}
                onFocus={event => { if (field.kind === 'number' && Number(String(event.target.value).replace(',', '.')) === 0) event.target.select() }}
                onChange={e => set(e.target.value)} />}
            </label>
          })}
          <label className="field"><span>Situação</span>
            <select value={active ? 'ATIVO' : 'INATIVO'} onChange={e => setActive(e.target.value === 'ATIVO')}>
              <option value="ATIVO">Ativo</option><option value="INATIVO">Inativo</option>
            </select>
          </label>
        </div>
        <div className="form-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
          <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>Cancelar</button>
          <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>
      </form>
    </section>
    {newAccountOpen && <RecordDialog tab={TABS[0]} record={null} records={accounts} accounts={accounts} nested
      onClose={() => setNewAccountOpen(false)}
      onSaved={() => setNewAccountOpen(false)}
      onAccountCreated={account => { setNewAccountOpen(false); onAccountCreated?.(account); setDraft(current => ({ ...current, conta_financeira_id: account.id })) }} />}
  </div>, document.body)
}

type Section = 'R' | 'P' | 'fluxo' | 'cadastros'
export type FinanceFocus = { pedidoId: number; nonce: number }

export function FinancePage({ focus, onClearFocus }: { focus?: FinanceFocus | null; onClearFocus?: () => void }) {
  const [section, setSection] = useState<Section>('R')
  const [tabId, setTabId] = useState<FinanceResource>('contas-financeiras')
  const tab = TABS.find(t => t.id === tabId) || TABS[0]
  const [records, setRecords] = useState<FinanceRecord[]>([])
  const [accounts, setAccounts] = useState<FinanceRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const [dialog, setDialog] = useState<{ record: FinanceRecord | null } | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = useCallback(async (resource: FinanceResource) => {
    setLoading(true); setError('')
    try {
      setRecords(await listFinanceRecords(resource))
      if (resource === 'formas-pagamento') setAccounts(await listFinanceRecords('contas-financeiras'))
    }
    catch (err) { setRecords([]); setError(friendlyError(err)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { setQuery(''); setNotice(''); if (section === 'cadastros') void load(tabId) }, [tabId, load, section])
  useEffect(() => { if (focus) setSection('R') }, [focus])
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 3500)
    return () => window.clearTimeout(timer)
  }, [notice])

  const shown = useMemo(() => {
    const term = normalize(query)
    return records.filter(r => !term || normalize(tab.columns.map(c => c.render(r, records, accounts)).join(' ')).includes(term))
  }, [records, query, tab, accounts])

  async function toggle(record: FinanceRecord) {
    setBusyId(record.id); setError('')
    try { await updateFinanceRecord(tab.id, record.id, { ativo: !record.ativo }); await load(tab.id) }
    catch (err) { setError(friendlyError(err)) } finally { setBusyId(null) }
  }

  async function remove(record: FinanceRecord) {
    if (busyId !== null || !window.confirm(`Excluir "${record.nome}"? Esta ação não pode ser desfeita.`)) return
    setBusyId(record.id); setError('')
    try { await deleteFinanceRecord(tab.id, record.id); setNotice('Cadastro excluído.'); await load(tab.id) }
    catch (err) { setError(friendlyError(err)) } finally { setBusyId(null) }
  }

  const columnsConfig = [
    ...tab.columns.map((c, index) => ({ id: c.id, label: c.label, defaultVisible: true, locked: index === 0 })),
    { id: 'status', label: 'Situação', defaultVisible: true },
    { id: 'actions', label: 'Ações', defaultVisible: true },
  ]

  const renderCadastro: RenderCadastro = (resource, context, onCreated, onClose) => <RecordDialog
    tab={TABS.find(t => t.id === resource) || TABS[0]} record={null} records={context.records} accounts={context.accounts} nested
    onClose={onClose} onSaved={onClose} onAccountCreated={onCreated} />

  const SECTIONS: { id: Section; label: string }[] = [{ id: 'R', label: 'Contas a receber' }, { id: 'P', label: 'Contas a pagar' }, { id: 'fluxo', label: 'Fluxo de caixa' }, { id: 'cadastros', label: 'Cadastros financeiros' }]

  return <div className="finance-page">
    <section className="panel" style={{ marginBottom: 14 }}>
      <div className="section-title">
        <div><h2>Financeiro</h2><p>Contas a receber, contas a pagar, fluxo de caixa e cadastros base do financeiro.</p></div>
      </div>
      <div role="tablist" aria-label="Áreas do Financeiro" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: section === 'cadastros' ? 10 : 0 }}>
        {SECTIONS.map(s => <button key={s.id} type="button" role="tab" aria-selected={s.id === section}
          className={s.id === section ? 'primary-button' : 'secondary-button'} onClick={() => setSection(s.id)}>{s.label}</button>)}
      </div>
      {section === 'cadastros' && <div role="tablist" aria-label="Cadastros do Financeiro" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {TABS.map(t => <button key={t.id} type="button" role="tab" aria-selected={t.id === tabId}
          className={t.id === tabId ? 'primary-button' : 'secondary-button'} onClick={() => setTabId(t.id)}>{t.label}</button>)}
      </div>}
    </section>

    {section === 'fluxo' && <CashFlowPanel />}

    {(section === 'R' || section === 'P') && <FinanceTitlesPanel key={`-${focus?.nonce ?? 0}`} kind={section} renderCadastro={renderCadastro}
      focusPedidoId={section === 'R' ? focus?.pedidoId : null} onClearFocus={onClearFocus} />}

    {section === 'cadastros' && <section className="budget-table-panel panel">
      <div className="budget-toolbar" style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
        <label className="budget-search"><Search size={16} /><input placeholder={`Buscar em ${tab.label.toLowerCase()}`} value={query} onChange={e => setQuery(e.target.value)} /></label>
        <button type="button" className="primary-button" onClick={() => setDialog({ record: null })}><Plus size={14} /> {tab.newLabel}</button>
      </div>
      {error && <div className="api-message error" role="alert">{error}</div>}
      {notice && <div className="api-message" role="status">{notice}</div>}
      <div className="table-wrap budget-table-wrap">
        <ColumnManager storageKey={`smarttec:columns:finance:${tab.id}`} lockedColumns={[tab.columns[0].id, 'actions']} columns={columnsConfig}>
          <table className="budget-table">
            <thead><tr>{tab.columns.map(c => <th key={c.id}>{c.label}</th>)}<th>Situação</th><th /></tr></thead>
            <tbody>
              {shown.map(r => <tr key={r.id} onDoubleClick={() => setDialog({ record: r })}>
                {tab.columns.map((c, index) => <td key={c.id}>{index === 0 ? <strong>{c.render(r, records, accounts)}</strong> : c.render(r, records, accounts)}</td>)}
                <td><span className={`budget-status ${r.ativo ? 'budget-status-approved' : 'budget-status-cancelled'}`}><span />{r.ativo ? 'Ativo' : 'Inativo'}</span></td>
                <td><RowActionsMenu module="finance" label={r.nome} onEdit={() => setDialog({ record: r })}
                  onToggle={() => void toggle(r)} toggleLabel={r.ativo ? 'Inativar' : 'Ativar'}
                  onDelete={() => void remove(r)} busy={busyId !== null} /></td>
              </tr>)}
            </tbody>
          </table>
        </ColumnManager>
        {loading && <div className="empty-state">Carregando...</div>}
        {!loading && !shown.length && !error && <div className="empty-state">Nenhum cadastro encontrado.</div>}
      </div>
      <div className="budget-table-footer"><span>Mostrando <strong>{shown.length}</strong> de {records.length}</span></div>
    </section>}

    {section === 'cadastros' && dialog && <RecordDialog tab={tab} record={dialog.record} records={records} accounts={accounts}
      onAccountCreated={account => setAccounts(current => [...current, account])}
      onClose={() => setDialog(null)}
      onSaved={message => { setDialog(null); setNotice(message); void load(tab.id) }} />}
  </div>
}
