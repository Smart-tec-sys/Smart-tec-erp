import { Plus, Search, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { ColumnManager } from '../components/ColumnManager'
import { RowActionsMenu } from '../components/RowActionsMenu'
import { ZeroNumberInput } from '../components/ZeroNumberInput'
import {
  createFinanceTitle,
  deleteFinanceTitle,
  getClientesCadastro,
  getFinanceIndicators,
  getFornecedoresCadastro,
  listFinanceBaixas,
  listFinanceRecords,
  listFinanceTitles,
  payFinanceTitle,
  reverseFinanceBaixa,
  updateFinanceTitle,
  type CadastroRecord,
  type FinanceBaixa,
  type FinanceIndicators,
  type FinanceRecord,
  type FinanceResource,
  type FinanceTipo,
  type FinanceTitle,
  type FinanceTitleFilters,
  type FinanceTitlePayload,
} from '../services/api'

export type RenderCadastro = (
  resource: FinanceResource,
  context: { records: FinanceRecord[]; accounts: FinanceRecord[] },
  onCreated: (record: FinanceRecord) => void,
  onClose: () => void,
) => ReactNode

type Props = {
  kind: FinanceTipo
  focusPedidoId?: number | null
  onClearFocus?: () => void
  renderCadastro: RenderCadastro
}
type Cadastros = Record<FinanceResource, FinanceRecord[]>
type People = { id: number; nome: string }[]
type Filters = {
  de: string; ate: string; status: string; vencimento: string; pessoa: string
  conta: string; forma: string; plano: string; centro: string; q: string
}

const NEW = '__new__'
const EMPTY_FILTERS: Filters = { de: '', ate: '', status: '', vencimento: '', pessoa: '', conta: '', forma: '', plano: '', centro: '', q: '' }
const EMPTY_CADASTROS: Cadastros = { 'contas-financeiras': [], 'formas-pagamento': [], 'plano-contas': [], situacoes: [], 'centros-custo': [] }
const ORIGENS: Record<string, string> = { VENDA: 'Venda', CONTABILIDADE: 'Contabilidade', RT: 'RT', MANUAL: 'Manual' }
const BLOCK_REASON = 'Títulos de RT e Contabilidade devem ser baixados pelo módulo de origem.'

const money = (value: unknown) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const today = () => new Date().toLocaleDateString('sv-SE')
const fmtDate = (value?: string | null) => value ? value.slice(0, 10).split('-').reverse().join('/') : '—'
const round2 = (value: number) => Math.round(value * 100) / 100

function apiError(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error)
  const detail = raw.match(/"detail":"([^"]+)"/)
  if (detail) return detail[1]
  const first = raw.match(/"msg":"([^"]+)"/)
  if (first) return first[1]
  return raw.replace(/^API \d+:\s*/, '')
}

function personName(list: People, id?: number | null) { return list.find(p => p.id === id)?.nome }
const toPeople = (rows: CadastroRecord[]): People => rows.map(r => ({ id: r.id, nome: String(r.nome ?? r.razao_social ?? `#${r.id}`) }))

function statusInfo(title: FinanceTitle, kind: FinanceTipo) {
  if (title.status === 'PAGO') return { label: kind === 'R' ? 'Recebido' : 'Pago', css: 'budget-status-approved' }
  if (title.status === 'CANCELADO') return { label: 'Cancelado', css: 'budget-status-cancelled' }
  if (title.vencimento && title.vencimento.slice(0, 10) < today()) return { label: 'Vencido', css: 'budget-status-open' }
  if (Number(title.valor_pago) > 0) return { label: 'Parcial', css: 'budget-status-pending' }
  return { label: 'Aberto', css: 'budget-status-pending' }
}

function Modal({ title, onClose, busy, children, wide }: { title: string; onClose: () => void; busy?: boolean; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && !busy) onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose, busy])
  return createPortal(<div className="modal-overlay">
    <section className="budget-preview" role="dialog" aria-modal="true" aria-label={title} style={wide ? { width: 'min(100%, 1000px)' } : { width: 'min(100%, 720px)' }}>
      <header>
        <h2>{title}</h2>
        <button type="button" className="secondary-button" disabled={busy} onClick={onClose}>Fechar</button>
      </header>
      {children}
    </section>
  </div>, document.body)
}

type SelectProps = {
  label: string
  value: number | null | undefined
  options: { id: number; nome: string; ativo?: boolean }[]
  empty: string
  disabled?: boolean
  onChange: (value: number | null) => void
  onNew?: () => void
}
function CadastroSelect({ label, value, options, empty, disabled, onChange, onNew }: SelectProps) {
  return <label className="field"><span>{label}</span>
    <select disabled={disabled} value={value == null ? '' : String(value)} onChange={event => {
      if (event.target.value === NEW) onNew?.()
      else onChange(event.target.value ? Number(event.target.value) : null)
    }}>
      <option value="">{empty}</option>
      {options.filter(o => o.ativo !== false || o.id === value).map(o => <option key={o.id} value={o.id}>{o.nome}{o.ativo === false ? ' (inativo)' : ''}</option>)}
      {onNew && !disabled && <option value={NEW}>+ Cadastrar novo</option>}
    </select>
  </label>
}

type DialogContext = {
  kind: FinanceTipo
  cadastros: Cadastros
  people: People
  renderCadastro: RenderCadastro
  onCadastroCreated: (resource: FinanceResource, record: FinanceRecord) => void
}

function formasFor(kind: FinanceTipo, formas: FinanceRecord[]) {
  return formas.filter(f => !f.disponivel_para || f.disponivel_para === 'AMBOS' || f.disponivel_para === (kind === 'R' ? 'RECEBER' : 'PAGAR'))
}

function TitleDialog({ ctx, title, mode, onClose, onSaved }: {
  ctx: DialogContext
  title: FinanceTitle | null
  mode: 'create' | 'edit' | 'view'
  onClose: () => void
  onSaved: (message: string) => void
}) {
  const { kind, cadastros, people, renderCadastro, onCadastroCreated } = ctx
  const readOnly = mode === 'view'
  const lockedValues = !!title && (title.vinculado || title.status === 'PAGO' || Number(title.valor_pago) > 0)
  const lockValues = readOnly || lockedValues
  const defaultSituacao = cadastros.situacoes.find(s => s.ativo && s.padrao && !s.quitado && (s.tipo === 'AMBOS' || s.tipo === (kind === 'R' ? 'RECEBER' : 'PAGAR')))
  const [draft, setDraft] = useState(() => ({
    descricao: title?.descricao ?? '',
    competencia: title?.competencia?.slice(0, 10) ?? '',
    valor_original: Number(title?.valor_original ?? title?.valor ?? 0),
    desconto: Number(title?.desconto ?? 0),
    juros: Number(title?.juros ?? 0),
    vencimento: title?.vencimento?.slice(0, 10) ?? '',
    pessoa: (kind === 'R' ? title?.cliente_id : title?.fornecedor_id) ?? null as number | null,
    conta: title?.conta_financeira_id ?? null as number | null,
    forma: title?.forma_pagamento_id ?? null as number | null,
    plano: title?.plano_conta_id ?? null as number | null,
    centro: title?.centro_custo_id ?? null as number | null,
    situacao: title ? title.situacao_financeira_id ?? null : defaultSituacao?.id ?? null as number | null,
    categoria: title?.categoria ?? '',
    observacao: title?.observacao ?? '',
  }))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState<FinanceResource | null>(null)
  const set = <K extends keyof typeof draft>(key: K, value: (typeof draft)[K]) => setDraft(current => ({ ...current, [key]: value }))
  const liquido = round2(draft.valor_original - draft.desconto + draft.juros)
  const planoTipo = kind === 'R' ? 'RECEITA' : 'DESPESA'
  const situacaoTipo = kind === 'R' ? 'RECEBER' : 'PAGAR'
  const situacoes = cadastros.situacoes.filter(s => !s.quitado && (s.tipo === 'AMBOS' || s.tipo === situacaoTipo))
  const planos = cadastros['plano-contas'].filter(p => !p.tipo || p.tipo === planoTipo)
  const creatingContext = { records: creating ? cadastros[creating] : [], accounts: cadastros['contas-financeiras'] }

  function created(record: FinanceRecord) {
    if (!creating) return
    onCadastroCreated(creating, record)
    if (creating === 'contas-financeiras') set('conta', record.id)
    if (creating === 'formas-pagamento') set('forma', record.id)
    if (creating === 'plano-contas') set('plano', record.id)
    if (creating === 'centros-custo') set('centro', record.id)
    if (creating === 'situacoes') set('situacao', record.id)
    setCreating(null)
  }

  async function save() {
    if (saving || readOnly) return
    if (!draft.descricao.trim()) { setError('Informe a descrição.'); return }
    if (!draft.vencimento) { setError('Informe o vencimento.'); return }
    if (!lockedValues && liquido <= 0) { setError('O valor líquido deve ser maior que zero.'); return }
    const payload: FinanceTitlePayload = {
      descricao: draft.descricao.trim(),
      competencia: draft.competencia || null,
      vencimento: draft.vencimento,
      conta_financeira_id: draft.conta,
      forma_pagamento_id: draft.forma,
      plano_conta_id: draft.plano,
      centro_custo_id: draft.centro,
      situacao_financeira_id: draft.situacao,
      categoria: draft.categoria.trim() || null,
      observacao: draft.observacao.trim() || null,
    }
    if (!lockedValues) {
      payload.valor_original = draft.valor_original
      payload.desconto = draft.desconto
      payload.juros = draft.juros
      if (kind === 'R') payload.cliente_id = draft.pessoa
      else payload.fornecedor_id = draft.pessoa
    }
    setSaving(true); setError('')
    try {
      if (title) await updateFinanceTitle(title.id, payload)
      else await createFinanceTitle({ ...payload, tipo: kind })
      onSaved(title ? 'Lançamento atualizado.' : 'Lançamento criado.')
    } catch (err) { setError(apiError(err)) } finally { setSaving(false) }
  }

  const heading = mode === 'create' ? (kind === 'R' ? 'Nova conta a receber' : 'Nova conta a pagar') : mode === 'edit' ? 'Editar lançamento' : 'Detalhes do lançamento'
  const pessoaLabel = kind === 'R' ? 'Cliente' : 'Fornecedor'
  return <>
    <Modal title={heading} onClose={onClose} busy={saving} wide>
      {error && <div className="api-message error" role="alert">{error}</div>}
      {lockedValues && !readOnly && <div className="api-message" role="status">
        {title?.vinculado ? 'Título originado de outro módulo: valores e pessoa ficam protegidos; os metadados financeiros podem ser editados.' : 'Título com baixa: valores e pessoa ficam protegidos.'}
      </div>}
      <form onSubmit={event => { event.preventDefault(); void save() }}>
        <div className="form-grid general-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
          <label className="field" style={{ gridColumn: '1 / -1' }}><span>Descrição *</span>
            <input disabled={readOnly} value={draft.descricao} onChange={e => set('descricao', e.target.value)} maxLength={255} /></label>
          <label className="field"><span>Competência</span>
            <input type="date" disabled={readOnly} value={draft.competencia} onChange={e => set('competencia', e.target.value)} /></label>
          <label className="field"><span>Vencimento *</span>
            <input type="date" disabled={readOnly} value={draft.vencimento} onChange={e => set('vencimento', e.target.value)} /></label>
          <label className="field"><span>Valor original</span>
            <ZeroNumberInput disabled={lockValues} value={draft.valor_original} onValueChange={v => set('valor_original', v)} /></label>
          <label className="field"><span>Desconto</span>
            <ZeroNumberInput disabled={lockValues} value={draft.desconto} onValueChange={v => set('desconto', v)} /></label>
          <label className="field"><span>Juros</span>
            <ZeroNumberInput disabled={lockValues} value={draft.juros} onValueChange={v => set('juros', v)} /></label>
          <label className="field"><span>Valor líquido</span>
            <input readOnly disabled value={money(lockedValues && title ? title.valor : liquido)} /></label>
          <CadastroSelect label={pessoaLabel} disabled={lockValues} value={draft.pessoa} options={ctx.people} empty={`Sem ${pessoaLabel.toLowerCase()}`} onChange={v => set('pessoa', v)} />
          <CadastroSelect label="Conta financeira" disabled={readOnly} value={draft.conta} options={cadastros['contas-financeiras']} empty="Sem conta" onChange={v => set('conta', v)} onNew={() => setCreating('contas-financeiras')} />
          <CadastroSelect label="Forma de pagamento" disabled={readOnly} value={draft.forma} options={formasFor(kind, cadastros['formas-pagamento'])} empty="Sem forma" onChange={v => set('forma', v)} onNew={() => setCreating('formas-pagamento')} />
          <CadastroSelect label="Plano de contas" disabled={readOnly} value={draft.plano} options={planos.map(p => ({ id: p.id, nome: `${p.codigo ? `${p.codigo} — ` : ''}${p.nome}`, ativo: p.ativo }))} empty="Sem plano" onChange={v => set('plano', v)} onNew={() => setCreating('plano-contas')} />
          <CadastroSelect label="Centro de custo" disabled={readOnly} value={draft.centro} options={cadastros['centros-custo']} empty="Sem centro" onChange={v => set('centro', v)} onNew={() => setCreating('centros-custo')} />
          <CadastroSelect label="Situação" disabled={readOnly} value={draft.situacao} options={situacoes} empty="Sem situação" onChange={v => set('situacao', v)} onNew={() => setCreating('situacoes')} />
          <label className="field"><span>Categoria</span>
            <input disabled={readOnly || (!!title && title.vinculado)} value={draft.categoria} onChange={e => set('categoria', e.target.value)} maxLength={80} /></label>
          {title && <label className="field"><span>Origem</span>
            <input disabled readOnly value={`${ORIGENS[title.origem] ?? title.origem}${title.pedido_numero ? ` · ${title.pedido_numero}` : ''}`} /></label>}
          {title && <label className="field"><span>Valor recebido/pago · Saldo</span>
            <input disabled readOnly value={`${money(title.valor_pago)} · ${money(title.saldo)}`} /></label>}
          <label className="field" style={{ gridColumn: '1 / -1' }}><span>Observação</span>
            <textarea rows={3} disabled={readOnly} value={draft.observacao} onChange={e => set('observacao', e.target.value)} /></label>
        </div>
        {!readOnly && <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
          <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>Cancelar</button>
          <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Salvando...' : 'Salvar'}</button>
        </div>}
      </form>
    </Modal>
    {creating && renderCadastro(creating, creatingContext, created, () => setCreating(null))}
  </>
}

function BaixaDialog({ ctx, title, onClose, onSaved }: { ctx: DialogContext; title: FinanceTitle; onClose: () => void; onSaved: (message: string) => void }) {
  const { kind, cadastros } = ctx
  const saldo = Number(title.saldo)
  const [data, setData] = useState({
    data_baixa: today(), valor: saldo, juros: 0, desconto: 0,
    conta: title.conta_financeira_id ?? null as number | null,
    forma: title.forma_pagamento_id ?? null as number | null,
    observacao: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState<FinanceResource | null>(null)
  const set = <K extends keyof typeof data>(key: K, value: (typeof data)[K]) => setData(current => ({ ...current, [key]: value }))
  const quitacao = round2(data.valor - data.juros + data.desconto)
  const restante = round2(saldo - quitacao)
  const verbo = kind === 'R' ? 'Receber' : 'Pagar'

  function created(record: FinanceRecord) {
    if (!creating) return
    ctx.onCadastroCreated(creating, record)
    if (creating === 'contas-financeiras') set('conta', record.id)
    if (creating === 'formas-pagamento') set('forma', record.id)
    setCreating(null)
  }

  async function save() {
    if (saving) return
    if (!data.data_baixa) { setError('Informe a data da baixa.'); return }
    if (data.valor <= 0) { setError('O valor da baixa deve ser maior que zero.'); return }
    if (data.juros < 0 || data.desconto < 0) { setError('Juros e desconto não podem ser negativos.'); return }
    if (quitacao <= 0) { setError('O valor da baixa, descontados os juros, deve ser maior que zero.'); return }
    if (quitacao > saldo + 0.001) { setError(`A baixa excede o saldo do título (${money(saldo)}).`); return }
    setSaving(true); setError('')
    try {
      await payFinanceTitle(title.id, {
        data_baixa: data.data_baixa, valor: data.valor, juros: data.juros, desconto: data.desconto,
        conta_financeira_id: data.conta, forma_pagamento_id: data.forma, observacao: data.observacao.trim() || null,
      })
      onSaved(restante <= 0.001 ? 'Baixa registrada. Título quitado.' : 'Baixa parcial registrada.')
    } catch (err) { setError(apiError(err)) } finally { setSaving(false) }
  }

  return <>
    <Modal title={`${verbo} · ${title.descricao}`} onClose={onClose} busy={saving}>
      {error && <div className="api-message error" role="alert">{error}</div>}
      <form onSubmit={event => { event.preventDefault(); void save() }}>
        <div className="form-grid general-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          <label className="field"><span>Data da baixa *</span>
            <input type="date" value={data.data_baixa} onChange={e => set('data_baixa', e.target.value)} /></label>
          <label className="field"><span>Valor da baixa *</span>
            <ZeroNumberInput value={data.valor} onValueChange={v => set('valor', v)} /></label>
          <label className="field"><span>Juros</span>
            <ZeroNumberInput value={data.juros} onValueChange={v => set('juros', v)} /></label>
          <label className="field"><span>Desconto</span>
            <ZeroNumberInput value={data.desconto} onValueChange={v => set('desconto', v)} /></label>
          <CadastroSelect label="Conta financeira" value={data.conta} options={cadastros['contas-financeiras']} empty="Padrão da forma/título" onChange={v => set('conta', v)} onNew={() => setCreating('contas-financeiras')} />
          <CadastroSelect label="Forma de pagamento" value={data.forma} options={formasFor(kind, cadastros['formas-pagamento'])} empty="Forma do título" onChange={v => set('forma', v)} onNew={() => setCreating('formas-pagamento')} />
          <label className="field" style={{ gridColumn: '1 / -1' }}><span>Observação</span>
            <textarea rows={2} value={data.observacao} onChange={e => set('observacao', e.target.value)} /></label>
        </div>
        <div className="api-message" role="status" style={{ marginTop: 12 }}>
          Saldo atual <strong>{money(saldo)}</strong> · Quitação desta baixa <strong>{money(quitacao)}</strong> (valor − juros + desconto) · Saldo após <strong>{money(Math.max(restante, 0))}</strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
          <button type="button" className="secondary-button" disabled={saving} onClick={onClose}>Cancelar</button>
          <button type="submit" className="primary-button" disabled={saving}>{saving ? 'Salvando...' : `Confirmar ${verbo.toLowerCase()}`}</button>
        </div>
      </form>
    </Modal>
    {creating && ctx.renderCadastro(creating, { records: cadastros[creating], accounts: cadastros['contas-financeiras'] }, created, () => setCreating(null))}
  </>
}

function BaixasDialog({ ctx, title, onClose, onChanged }: { ctx: DialogContext; title: FinanceTitle; onClose: () => void; onChanged: () => void }) {
  const [rows, setRows] = useState<FinanceBaixa[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    setLoading(true)
    try { setRows(await listFinanceBaixas(title.id)); setError('') }
    catch (err) { setError(apiError(err)) } finally { setLoading(false) }
  }, [title.id])
  useEffect(() => { void load() }, [load])
  const nome = (list: FinanceRecord[], id?: number | null) => list.find(r => r.id === id)?.nome ?? '—'

  async function reverse(row: FinanceBaixa) {
    if (busyId !== null || !window.confirm(`Estornar a baixa de ${money(row.valor)} em ${fmtDate(row.data_baixa)}? A baixa será mantida no histórico como estornada.`)) return
    setBusyId(row.id); setError('')
    try { await reverseFinanceBaixa(row.id); await load(); onChanged() }
    catch (err) { setError(apiError(err)) } finally { setBusyId(null) }
  }

  return <Modal title={`Baixas · ${title.descricao}`} onClose={onClose} busy={busyId !== null} wide>
    {error && <div className="api-message error" role="alert">{error}</div>}
    <div className="table-wrap budget-table-wrap">
      <table className="budget-table">
        <thead><tr><th>Data</th><th>Valor</th><th>Juros</th><th>Desconto</th><th>Conta</th><th>Forma</th><th>Observação</th><th>Situação</th><th /></tr></thead>
        <tbody>
          {rows.map(row => <tr key={row.id}>
            <td>{fmtDate(row.data_baixa)}</td><td>{money(row.valor)}</td><td>{money(row.juros)}</td><td>{money(row.desconto)}</td>
            <td>{nome(ctx.cadastros['contas-financeiras'], row.conta_financeira_id)}</td>
            <td>{nome(ctx.cadastros['formas-pagamento'], row.forma_pagamento_id)}</td>
            <td>{row.observacao || '—'}</td>
            <td><span className={`budget-status ${row.ativa ? 'budget-status-approved' : 'budget-status-cancelled'}`}><span />{row.ativa ? 'Ativa' : 'Estornada'}</span></td>
            <td>{row.ativa && <button type="button" className="secondary-button" disabled={busyId !== null} onClick={() => void reverse(row)}>Estornar</button>}</td>
          </tr>)}
        </tbody>
      </table>
      {loading && <div className="empty-state">Carregando...</div>}
      {!loading && !rows.length && !error && <div className="empty-state">Nenhuma baixa registrada.</div>}
    </div>
  </Modal>
}

export function FinanceTitlesPanel({ kind, focusPedidoId, onClearFocus, renderCadastro }: Props) {
  const [cadastros, setCadastros] = useState<Cadastros>(EMPTY_CADASTROS)
  const [people, setPeople] = useState<People>([])
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [debouncedQ, setDebouncedQ] = useState('')
  const [titles, setTitles] = useState<FinanceTitle[]>([])
  const [indicators, setIndicators] = useState<FinanceIndicators | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [dialog, setDialog] = useState<{ type: 'form' | 'pay' | 'baixas'; mode?: 'create' | 'edit' | 'view'; title: FinanceTitle | null } | null>(null)
  const isReceber = kind === 'R'
  const noun = isReceber ? 'cliente' : 'fornecedor'

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(filters.q.trim()), 300)
    return () => window.clearTimeout(timer)
  }, [filters.q])
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 3500)
    return () => window.clearTimeout(timer)
  }, [notice])

  useEffect(() => {
    let alive = true
    const resources: FinanceResource[] = ['contas-financeiras', 'formas-pagamento', 'plano-contas', 'situacoes', 'centros-custo']
    Promise.all([
      Promise.all(resources.map(resource => listFinanceRecords(resource))),
      (isReceber ? getClientesCadastro() : getFornecedoresCadastro()).catch(() => [] as CadastroRecord[]),
    ]).then(([lists, pessoas]) => {
      if (!alive) return
      setCadastros(Object.fromEntries(resources.map((resource, index) => [resource, lists[index]])) as Cadastros)
      setPeople(toPeople(pessoas))
    }).catch(err => { if (alive) setError(apiError(err)) })
    return () => { alive = false }
  }, [isReceber])

  const query = useMemo<FinanceTitleFilters>(() => {
    const id = (value: string) => value ? Number(value) : undefined
    return {
      tipo: kind,
      vencimento_inicial: focusPedidoId ? undefined : filters.de || undefined,
      vencimento_final: focusPedidoId ? undefined : filters.ate || undefined,
      cliente_id: isReceber ? id(filters.pessoa) : undefined,
      fornecedor_id: isReceber ? undefined : id(filters.pessoa),
      pedido_id: focusPedidoId || undefined,
      conta_financeira_id: id(filters.conta),
      forma_pagamento_id: id(filters.forma),
      plano_conta_id: id(filters.plano),
      centro_custo_id: id(filters.centro),
      q: debouncedQ || undefined,
    }
  }, [kind, isReceber, filters, debouncedQ, focusPedidoId])

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([
      listFinanceTitles({ ...query, status: filters.status || undefined, vencimento_status: filters.vencimento || undefined }),
      getFinanceIndicators(query),
    ]).then(([rows, cards]) => {
      if (!alive) return
      setTitles(rows); setIndicators(cards); setError('')
    }).catch(err => { if (alive) { setTitles([]); setIndicators(null); setError(apiError(err)) } })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [query, filters.status, filters.vencimento, reloadKey])

  const reload = () => setReloadKey(key => key + 1)
  const setFilter = (key: keyof Filters, value: string) => setFilters(current => ({ ...current, [key]: value }))
  const onCadastroCreated = useCallback((resource: FinanceResource, record: FinanceRecord) => {
    // Uma conta criada dentro do diálogo de forma chega por este mesmo callback.
    const target: FinanceResource = resource === 'formas-pagamento' && record.disponivel_para === undefined ? 'contas-financeiras' : resource
    setCadastros(current => ({ ...current, [target]: [...current[target], record] }))
  }, [])

  const ctx: DialogContext = { kind, cadastros, people, renderCadastro, onCadastroCreated }
  const hasFilters = JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS)
  const closeDialog = () => setDialog(null)

  async function remove(title: FinanceTitle) {
    if (busyId !== null || !window.confirm(`Excluir o lançamento "${title.descricao}"? Esta ação não pode ser desfeita.`)) return
    setBusyId(title.id); setError('')
    try { await deleteFinanceTitle(title.id); setNotice('Lançamento excluído.'); reload() }
    catch (err) { setError(apiError(err)) } finally { setBusyId(null) }
  }

  const columns = [
    { id: 'descricao', label: 'Descrição', defaultVisible: true },
    { id: 'pessoa', label: isReceber ? 'Cliente' : 'Fornecedor', defaultVisible: true },
    { id: 'vencimento', label: 'Vencimento', defaultVisible: true },
    { id: 'valor', label: 'Valor', defaultVisible: true },
    { id: 'pago', label: isReceber ? 'Valor recebido' : 'Valor pago', defaultVisible: true },
    { id: 'saldo', label: 'Saldo', defaultVisible: true },
    { id: 'status', label: 'Status', defaultVisible: true },
    { id: 'situacao', label: 'Situação', defaultVisible: false },
    { id: 'origem', label: 'Origem / categoria', defaultVisible: true },
    { id: 'conta', label: 'Conta', defaultVisible: false },
    { id: 'actions', label: 'Ações', defaultVisible: true },
  ]
  const name = (list: FinanceRecord[], id?: number | null) => list.find(r => r.id === id)?.nome

  const cards: { id: string; label: string; data?: { quantidade: number; total: number | string }; tone: string; apply: () => void; active: boolean }[] = [
    { id: 'total', label: 'Total do período', data: indicators?.total_periodo, tone: 'tone-dark', apply: () => setFilters(f => ({ ...f, status: '', vencimento: '' })), active: !filters.status && !filters.vencimento },
    { id: 'vencidos', label: 'Vencidos', data: indicators?.vencidos, tone: '', apply: () => setFilters(f => ({ ...f, status: '', vencimento: 'VENCIDO' })), active: filters.vencimento === 'VENCIDO' },
    { id: 'hoje', label: 'Vencem hoje', data: indicators?.vencem_hoje, tone: 'tone-gold', apply: () => setFilters(f => ({ ...f, status: '', vencimento: 'HOJE' })), active: filters.vencimento === 'HOJE' },
    { id: 'avencer', label: 'A vencer', data: indicators?.a_vencer, tone: 'tone-dark', apply: () => setFilters(f => ({ ...f, status: '', vencimento: 'A_VENCER' })), active: filters.vencimento === 'A_VENCER' },
    { id: 'quitados', label: isReceber ? 'Recebidos' : 'Pagos', data: indicators?.quitados, tone: 'tone-green', apply: () => setFilters(f => ({ ...f, status: 'PAGO', vencimento: '' })), active: filters.status === 'PAGO' },
  ]

  return <>
    <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }} aria-label="Indicadores">
      {cards.map(card => <button key={card.id} type="button" className={`metric-card ${card.tone}`} aria-pressed={card.active} onClick={card.apply}
        style={{ minHeight: 0, textAlign: 'left', cursor: 'pointer', borderColor: card.active ? 'var(--color-primary)' : undefined }}>
        <div className="metric-top"><span>{card.label}</span></div>
        <strong data-testid={`indicador-${card.id}`}>{card.data ? money(card.data.total) : '—'}</strong>
        <div className="metric-delta"><span style={{ marginLeft: 0 }}>{card.data ? `${card.data.quantidade} lançamento(s)` : ' '}</span></div>
      </button>)}
    </div>

    <section className="budget-table-panel panel">
      <div className="budget-toolbar" style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <label className="budget-search"><Search size={16} /><input placeholder="Buscar por descrição" value={filters.q} onChange={e => setFilter('q', e.target.value)} /></label>
        <button type="button" className="primary-button" onClick={() => setDialog({ type: 'form', mode: 'create', title: null })}><Plus size={14} /> {isReceber ? 'Nova conta a receber' : 'Nova conta a pagar'}</button>
      </div>
      {focusPedidoId && <div className="api-message" role="status" style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'space-between' }}>
        <span>Exibindo os lançamentos da venda selecionada{titles[0]?.pedido_numero ? ` (${titles[0].pedido_numero})` : ''}. O período não é aplicado.</span>
        <button type="button" className="clear-filter" onClick={onClearFocus}><X size={12} /> Ver todos</button>
      </div>}
      <div className="form-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', margin: '10px 0', padding: '0 16px' }}>
        <label className="field"><span>Vencimento de</span><input type="date" disabled={!!focusPedidoId} value={filters.de} onChange={e => setFilter('de', e.target.value)} /></label>
        <label className="field"><span>Vencimento até</span><input type="date" disabled={!!focusPedidoId} value={filters.ate} onChange={e => setFilter('ate', e.target.value)} /></label>
        <label className="field"><span>Status</span>
          <select value={filters.status} onChange={e => setFilter('status', e.target.value)}>
            <option value="">Todos</option><option value="ABERTO">Aberto</option><option value="PAGO">{isReceber ? 'Recebido' : 'Pago'}</option><option value="CANCELADO">Cancelado</option>
          </select></label>
        <label className="field"><span>{isReceber ? 'Cliente' : 'Fornecedor'}</span>
          <select value={filters.pessoa} onChange={e => setFilter('pessoa', e.target.value)}>
            <option value="">Todos</option>{people.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
          </select></label>
        <label className="field"><span>Conta financeira</span>
          <select value={filters.conta} onChange={e => setFilter('conta', e.target.value)}>
            <option value="">Todas</option>{cadastros['contas-financeiras'].map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select></label>
        <label className="field"><span>Forma de pagamento</span>
          <select value={filters.forma} onChange={e => setFilter('forma', e.target.value)}>
            <option value="">Todas</option>{cadastros['formas-pagamento'].map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select></label>
        <label className="field"><span>Plano de contas</span>
          <select value={filters.plano} onChange={e => setFilter('plano', e.target.value)}>
            <option value="">Todos</option>{cadastros['plano-contas'].map(r => <option key={r.id} value={r.id}>{r.codigo ? `${r.codigo} — ` : ''}{r.nome}</option>)}
          </select></label>
        <label className="field"><span>Centro de custo</span>
          <select value={filters.centro} onChange={e => setFilter('centro', e.target.value)}>
            <option value="">Todos</option>{cadastros['centros-custo'].map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select></label>
      </div>
      {hasFilters && <button type="button" className="clear-filter" onClick={() => setFilters(EMPTY_FILTERS)}>Limpar filtros</button>}
      {error && <div className="api-message error" role="alert">{error}</div>}
      {notice && <div className="api-message" role="status">{notice}</div>}
      <div className="table-wrap budget-table-wrap">
        <ColumnManager storageKey={`smarttec:columns:finance:titulos:${kind}`} lockedColumns={['descricao', 'actions']} columns={columns}>
          <table className="budget-table">
            <thead><tr>{columns.map(column => <th key={column.id}>{column.id === 'actions' ? '' : column.label}</th>)}</tr></thead>
            <tbody>
              {titles.map(title => {
                const status = statusInfo(title, kind)
                const pessoa = isReceber ? title.cliente_nome ?? personName(people, title.cliente_id) : title.fornecedor_nome ?? personName(people, title.fornecedor_id)
                return <tr key={title.id} onDoubleClick={() => setDialog({ type: 'form', mode: 'view', title })}>
                  <td><strong>{title.descricao}</strong></td>
                  <td>{pessoa || '—'}</td>
                  <td>{fmtDate(title.vencimento)}</td>
                  <td>{money(title.valor)}</td>
                  <td>{money(title.valor_pago)}</td>
                  <td>{money(title.saldo)}</td>
                  <td><span className={`budget-status ${status.css}`}><span />{status.label}</span></td>
                  <td>{name(cadastros.situacoes, title.situacao_financeira_id) || '—'}</td>
                  <td>{ORIGENS[title.origem] ?? title.origem}{title.pedido_numero ? ` · ${title.pedido_numero}` : ''}{title.categoria && <small style={{ display: 'block' }}>{title.categoria}</small>}</td>
                  <td>{name(cadastros['contas-financeiras'], title.conta_financeira_id) || '—'}</td>
                  <td><RowActionsMenu module="finance" label={title.descricao} busy={busyId !== null}
                    onView={() => setDialog({ type: 'form', mode: 'view', title })}
                    onEdit={() => setDialog({ type: 'form', mode: 'edit', title })}
                    payLabel={isReceber ? 'Receber / Registrar baixa' : 'Pagar / Registrar baixa'}
                    onPay={title.pode_baixar ? () => setDialog({ type: 'pay', title }) : undefined}
                    payReason={title.status === 'PAGO' ? 'Título já quitado.' : title.status === 'CANCELADO' ? 'Título cancelado.' : BLOCK_REASON}
                    onViewPayments={() => setDialog({ type: 'baixas', title })}
                    onDelete={title.pode_excluir ? () => void remove(title) : undefined}
                    deleteReason="Não é possível excluir: título vinculado, pago ou com baixas." /></td>
                </tr>
              })}
            </tbody>
          </table>
        </ColumnManager>
        {loading && <div className="empty-state">Carregando...</div>}
        {!loading && !titles.length && !error && <div className="empty-state">{focusPedidoId ? 'Esta venda ainda não possui conta a receber.' : `Nenhuma conta a ${isReceber ? 'receber' : 'pagar'} encontrada.`}</div>}
      </div>
      <div className="budget-table-footer"><span>Mostrando <strong>{titles.length}</strong> lançamento(s) · {noun}s: {people.length}</span></div>
    </section>

    {dialog?.type === 'form' && <TitleDialog ctx={ctx} title={dialog.title} mode={dialog.mode ?? 'create'} onClose={closeDialog}
      onSaved={message => { closeDialog(); setNotice(message); reload() }} />}
    {dialog?.type === 'pay' && dialog.title && <BaixaDialog ctx={ctx} title={dialog.title} onClose={closeDialog}
      onSaved={message => { closeDialog(); setNotice(message); reload() }} />}
    {dialog?.type === 'baixas' && dialog.title && <BaixasDialog ctx={ctx} title={dialog.title} onClose={closeDialog} onChanged={reload} />}
  </>
}
