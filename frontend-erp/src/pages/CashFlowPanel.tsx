import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  getCashFlowDaily,
  getCashFlowMovements,
  getCashFlowSummary,
  listFinanceRecords,
  type CashFlowDay,
  type CashFlowFilters,
  type CashFlowMovement,
  type CashFlowSummary,
  type FinanceRecord,
} from '../services/api'

const ORIGENS: Record<string, string> = { VENDA: 'Venda', CONTABILIDADE: 'Contabilidade', RT: 'RT', MANUAL: 'Manual' }
const money = (value: unknown) => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
const num = (value: unknown) => Number(value || 0)
const iso = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const fmtDate = (value: string) => value.slice(0, 10).split('-').reverse().join('/')
const monthRange = (reference: Date, shift = 0) => {
  const first = new Date(reference.getFullYear(), reference.getMonth() + shift, 1)
  const last = new Date(first.getFullYear(), first.getMonth() + 1, 0)
  return { de: iso(first), ate: iso(last) }
}
const tone = (value: unknown) => (num(value) < 0 ? 'var(--color-danger)' : undefined)

function apiError(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error)
  return raw.match(/"detail":"([^"]+)"/)?.[1] ?? raw.replace(/^API \d+:\s*/, '')
}

function CashFlowChart({ days }: { days: CashFlowDay[] }) {
  const width = 800
  const height = 240
  const pad = { left: 56, right: 12, top: 14, bottom: 26 }
  if (!days.length) return null
  const values = days.flatMap(d => [num(d.recebimentos), num(d.pagamentos), num(d.saldo_dia), num(d.saldo_previsto)])
  const max = Math.max(0, ...values)
  const min = Math.min(0, ...values)
  const span = max - min || 1
  const x = (index: number) => pad.left + ((index + 0.5) / days.length) * (width - pad.left - pad.right)
  const y = (value: number) => pad.top + (1 - (value - min) / span) * (height - pad.top - pad.bottom)
  const slot = (width - pad.left - pad.right) / days.length
  const bar = Math.max(1, Math.min(14, slot / 3))
  const line = (pick: (d: CashFlowDay) => number) => days.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(pick(d)).toFixed(1)}`).join(' ')
  const ticks = [max, (max + min) / 2, min]
  const labelEvery = Math.max(1, Math.ceil(days.length / 8))
  return <div className="cashflow-chart" role="img" aria-label="Gráfico de entradas, saídas e saldo por dia">
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ display: 'block', maxHeight: 280 }}>
      {ticks.map((tick, i) => <g key={i}>
        <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke="#e6e8eb" strokeWidth={1} />
        <text x={pad.left - 6} y={y(tick) + 3} textAnchor="end" fontSize={9} fill="#6b7480">{Math.round(tick).toLocaleString('pt-BR')}</text>
      </g>)}
      <line x1={pad.left} x2={width - pad.right} y1={y(0)} y2={y(0)} stroke="#9aa1a9" strokeWidth={1} />
      {days.map((d, i) => <g key={d.data}>
        {num(d.recebimentos) > 0 && <rect x={x(i) - bar - 0.5} width={bar} y={Math.min(y(num(d.recebimentos)), y(0))} height={Math.abs(y(0) - y(num(d.recebimentos)))} fill="#2f8f5b"><title>{`${fmtDate(d.data)} · Entradas ${money(d.recebimentos)}`}</title></rect>}
        {num(d.pagamentos) > 0 && <rect x={x(i) + 0.5} width={bar} y={Math.min(y(num(d.pagamentos)), y(0))} height={Math.abs(y(0) - y(num(d.pagamentos)))} fill="#d9363e"><title>{`${fmtDate(d.data)} · Saídas ${money(d.pagamentos)}`}</title></rect>}
        {i % labelEvery === 0 && <text x={x(i)} y={height - 8} textAnchor="middle" fontSize={9} fill="#6b7480">{d.data.slice(8, 10)}/{d.data.slice(5, 7)}</text>}
      </g>)}
      <path d={line(d => num(d.saldo_previsto))} fill="none" stroke="#a8751b" strokeWidth={1.5} strokeDasharray="4 3" />
      <path d={line(d => num(d.saldo_dia))} fill="none" stroke="#2b2f36" strokeWidth={2} />
    </svg>
    <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 10, color: 'var(--color-muted)', marginTop: 6 }}>
      <span><i style={{ display: 'inline-block', width: 10, height: 10, background: '#2f8f5b', marginRight: 4 }} />Entradas</span>
      <span><i style={{ display: 'inline-block', width: 10, height: 10, background: '#d9363e', marginRight: 4 }} />Saídas</span>
      <span><i style={{ display: 'inline-block', width: 14, height: 2, background: '#2b2f36', marginRight: 4, verticalAlign: 'middle' }} />Saldo realizado</span>
      <span><i style={{ display: 'inline-block', width: 14, height: 0, borderTop: '2px dashed #a8751b', marginRight: 4, verticalAlign: 'middle' }} />Saldo previsto</span>
    </div>
  </div>
}

export function CashFlowPanel() {
  const [period, setPeriod] = useState(() => monthRange(new Date()))
  const [conta, setConta] = useState('')
  const [centro, setCentro] = useState('')
  const [plano, setPlano] = useState('')
  const [origem, setOrigem] = useState('')
  const [modo, setModo] = useState<'ambos' | 'realizado' | 'previsto'>('ambos')
  const [hideEmpty, setHideEmpty] = useState(false)
  const [cadastros, setCadastros] = useState<{ contas: FinanceRecord[]; centros: FinanceRecord[]; planos: FinanceRecord[] }>({ contas: [], centros: [], planos: [] })
  const [summary, setSummary] = useState<CashFlowSummary | null>(null)
  const [days, setDays] = useState<CashFlowDay[]>([])
  const [movements, setMovements] = useState<CashFlowMovement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    Promise.all([listFinanceRecords('contas-financeiras'), listFinanceRecords('centros-custo'), listFinanceRecords('plano-contas')])
      .then(([contas, centros, planos]) => { if (alive) setCadastros({ contas, centros, planos }) })
      .catch(err => { if (alive) setError(apiError(err)) })
    return () => { alive = false }
  }, [])

  const filters = useMemo<CashFlowFilters>(() => ({
    data_inicial: period.de, data_final: period.ate, modo,
    conta_financeira_id: conta ? Number(conta) : undefined,
    centro_custo_id: centro ? Number(centro) : undefined,
    plano_conta_id: plano ? Number(plano) : undefined,
    origem: origem || undefined,
  }), [period, conta, centro, plano, origem, modo])

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([getCashFlowSummary(filters), getCashFlowDaily(filters), getCashFlowMovements(filters)])
      .then(([resumo, diario, movs]) => { if (alive) { setSummary(resumo); setDays(diario); setMovements(movs.itens); setError('') } })
      .catch(err => { if (alive) { setSummary(null); setDays([]); setMovements([]); setError(apiError(err)) } })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [filters])

  const shiftMonth = (shift: number) => setPeriod(current => monthRange(new Date(`${current.de}T12:00:00`), shift))
  const shownDays = hideEmpty ? days.filter(d => num(d.recebimentos) || num(d.pagamentos) || num(d.recebimentos_previstos) || num(d.pagamentos_previstos)) : days
  const consolidated = !conta

  const cards = [
    { id: 'saldo', label: 'Saldo realizado', value: summary?.saldo_realizado, hint: `Inicial ${money(summary?.saldo_inicial)}`, tone: 'tone-dark' },
    { id: 'recebimentos', label: 'Recebimentos', value: summary?.recebimentos, hint: `Previstos ${money(summary?.recebimentos_previstos)}`, tone: 'tone-green' },
    { id: 'pagamentos', label: 'Pagamentos', value: summary?.pagamentos, hint: `Previstos ${money(summary?.pagamentos_previstos)}`, tone: '' },
    { id: 'previsto', label: 'Saldo previsto', value: summary?.saldo_previsto, hint: 'Realizado + previsto do período', tone: 'tone-gold' },
  ]

  return <>
    <section className="panel" style={{ marginBottom: 14, padding: 16 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
        <button type="button" className="secondary-button" aria-label="Mês anterior" onClick={() => shiftMonth(-1)}><ChevronLeft size={14} /></button>
        <strong style={{ minWidth: 190, textAlign: 'center', fontSize: 12 }}>{fmtDate(period.de)} a {fmtDate(period.ate)}</strong>
        <button type="button" className="secondary-button" aria-label="Próximo mês" onClick={() => shiftMonth(1)}><ChevronRight size={14} /></button>
        <button type="button" className="secondary-button" onClick={() => setPeriod(monthRange(new Date()))}>Este mês</button>
      </div>
      <div className="form-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
        <label className="field"><span>Período inicial</span><input type="date" value={period.de} max={period.ate} onChange={e => e.target.value && setPeriod(p => ({ ...p, de: e.target.value }))} /></label>
        <label className="field"><span>Período final</span><input type="date" value={period.ate} min={period.de} onChange={e => e.target.value && setPeriod(p => ({ ...p, ate: e.target.value }))} /></label>
        <label className="field"><span>Exibir</span>
          <select value={modo} onChange={e => setModo(e.target.value as typeof modo)}>
            <option value="ambos">Realizado e previsto</option><option value="realizado">Somente realizado</option><option value="previsto">Somente previsto</option>
          </select></label>
        <label className="field"><span>Conta financeira</span>
          <select value={conta} onChange={e => setConta(e.target.value)}>
            <option value="">Consolidado (todas)</option>{cadastros.contas.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select></label>
        <label className="field"><span>Centro de custo</span>
          <select value={centro} onChange={e => setCentro(e.target.value)}>
            <option value="">Todos</option>{cadastros.centros.map(r => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select></label>
        <label className="field"><span>Plano de contas</span>
          <select value={plano} onChange={e => setPlano(e.target.value)}>
            <option value="">Todos</option>{cadastros.planos.map(r => <option key={r.id} value={r.id}>{r.codigo ? `${r.codigo} — ` : ''}{r.nome}</option>)}
          </select></label>
        <label className="field"><span>Origem</span>
          <select value={origem} onChange={e => setOrigem(e.target.value)}>
            <option value="">Todas</option>{Object.entries(ORIGENS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
      </div>
      {error && <div className="api-message error" role="alert">{error}</div>}
      {summary && !summary.saldo_inicial_contas_incluido && <div className="api-message" role="status">Com filtro de centro de custo, plano de contas ou origem, o saldo inicial das contas não é considerado.</div>}
    </section>

    <div className="metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }} aria-label="Resumo do fluxo de caixa">
      {cards.map(card => <div key={card.id} className={`metric-card ${card.tone}`} style={{ minHeight: 0 }}>
        <div className="metric-top"><span>{card.label}{card.id === 'saldo' ? (consolidated ? ' · consolidado' : '') : ''}</span></div>
        <strong data-testid={`fluxo-${card.id}`} style={{ color: tone(card.value) }}>{summary ? money(card.value) : '—'}</strong>
        <div className="metric-delta"><span style={{ marginLeft: 0 }}>{summary ? card.hint : ' '}</span></div>
      </div>)}
    </div>
    {summary && (num(summary.atrasados_receber) > 0 || num(summary.atrasados_pagar) > 0) && <div className="api-message" role="status" style={{ marginBottom: 14 }}>
      Em aberto com vencimento anterior ao período (fora do saldo previsto): a receber {money(summary.atrasados_receber)} · a pagar {money(summary.atrasados_pagar)}.
    </div>}

    <section className="panel" style={{ marginBottom: 14, padding: 16 }}>
      <div className="section-title"><div><h2>Entradas, saídas e saldo</h2><p>Valores realizados por dia; linha tracejada = saldo previsto.</p></div></div>
      {loading && !days.length ? <div className="empty-state">Carregando...</div> : <CashFlowChart days={days} />}
    </section>

    <section className="budget-table-panel panel" style={{ marginBottom: 14 }}>
      <div className="budget-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <div className="section-title" style={{ margin: 0 }}><div><h2>Visão diária</h2></div></div>
        <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 10 }}><input type="checkbox" checked={hideEmpty} onChange={e => setHideEmpty(e.target.checked)} />Ocultar dias sem movimento</label>
      </div>
      <div className="table-wrap budget-table-wrap" style={{ overflowX: 'auto' }}>
        <table className="budget-table" data-testid="fluxo-diario">
          <thead><tr><th>Data</th><th>Saldo inicial</th><th>Recebimentos</th><th>Pagamentos</th><th>Saldo do dia</th><th>Receb. previstos</th><th>Pagam. previstos</th><th>Saldo previsto</th></tr></thead>
          <tbody>
            {shownDays.map(d => <tr key={d.data}>
              <td><strong>{fmtDate(d.data)}</strong></td><td style={{ color: tone(d.saldo_inicial) }}>{money(d.saldo_inicial)}</td>
              <td>{money(d.recebimentos)}</td><td>{money(d.pagamentos)}</td><td style={{ color: tone(d.saldo_dia) }}>{money(d.saldo_dia)}</td>
              <td>{money(d.recebimentos_previstos)}</td><td>{money(d.pagamentos_previstos)}</td><td style={{ color: tone(d.saldo_previsto) }}>{money(d.saldo_previsto)}</td>
            </tr>)}
          </tbody>
        </table>
        {!loading && !shownDays.length && <div className="empty-state">Nenhum dia para exibir.</div>}
      </div>
    </section>

    <section className="budget-table-panel panel">
      <div className="budget-toolbar"><div className="section-title" style={{ margin: 0 }}><div><h2>Movimentações do período</h2></div></div></div>
      <div className="table-wrap budget-table-wrap" style={{ overflowX: 'auto' }}>
        <table className="budget-table" data-testid="fluxo-movimentos">
          <thead><tr><th>Data</th><th>Descrição</th><th>Tipo</th><th>Origem</th><th>Conta</th><th>Valor</th><th>Situação</th><th>Título / baixa</th></tr></thead>
          <tbody>
            {movements.map(m => <tr key={`${m.natureza}-${m.titulo_id}-${m.baixa_id ?? 'x'}-${m.data}`}>
              <td>{fmtDate(m.data)}</td><td><strong>{m.descricao}</strong></td>
              <td>{m.tipo === 'R' ? 'Recebimento' : 'Pagamento'}</td><td>{ORIGENS[m.origem] ?? m.origem}</td><td>{m.conta}</td>
              <td style={{ color: m.tipo === 'P' ? 'var(--color-danger)' : undefined }}>{m.tipo === 'P' ? '− ' : ''}{money(m.valor)}</td>
              <td><span className={`budget-status ${m.natureza === 'REALIZADO' ? 'budget-status-approved' : 'budget-status-pending'}`}><span />{m.situacao}</span></td>
              <td>Título #{m.titulo_id}{m.baixa_id ? ` · baixa #${m.baixa_id}` : ''}</td>
            </tr>)}
          </tbody>
        </table>
        {!loading && !movements.length && !error && <div className="empty-state">Nenhuma movimentação no período.</div>}
      </div>
      <div className="budget-table-footer"><span>Mostrando <strong>{movements.length}</strong> movimentação(ões)</span></div>
    </section>
  </>
}
