import { CheckCircle2, Clock3, Plus, WalletCards } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { BudgetTable } from '../components/BudgetTable'
import { BudgetPreviewDialog } from '../components/BudgetPreviewDialog'
import { BudgetShareDialog } from '../components/BudgetShareDialog'
import { BudgetServiceOrderDialog } from '../components/BudgetServiceOrderDialog'
import { BudgetProductionDialog } from '../components/BudgetProductionDialog'
import { convertBudgetToOrder, deleteBudget, duplicateBudget, getBudgets, updateBudgetStatus } from '../services/api'
import { budgetProductionDisabledReason, budgetProductionEnabled } from '../services/budgetProduction'
import type { BudgetPdfMode } from '../services/budgetPdfData'
import type { BudgetShareChannel } from '../services/budgetShare'
import type { ApiBudget } from '../types/budget'
import { formatCurrency } from '../types/budget'

export function BudgetsPage({ onNew, onOpen, refreshKey }: { onNew: () => void; onOpen: (id: number) => void; refreshKey: number }) {
  const [data, setData] = useState<ApiBudget[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [previewId, setPreviewId] = useState<number | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [actionError, setActionError] = useState('')
  const [sharing, setSharing] = useState<{ budget: ApiBudget; channel: BudgetShareChannel } | null>(null)
  const [serviceOrderId, setServiceOrderId] = useState<number | null>(null)
  const [productionId, setProductionId] = useState<number | null>(null)
  const [generatedSaleBudgetIds, setGeneratedSaleBudgetIds] = useState<Set<number>>(() => new Set())
  const [statusBudget, setStatusBudget] = useState<ApiBudget | null>(null)
  const [newStatus, setNewStatus] = useState('EM_ABERTO')
  const running = useRef(false)
  const closePreview = useCallback(() => setPreviewId(null), [])
  const closeShare = useCallback(() => setSharing(null), [])
  const closeServiceOrder = useCallback(() => setServiceOrderId(null), [])
  const closeProduction = useCallback(() => setProductionId(null), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true); setError('')
    getBudgets().then(budgets => { if (!cancelled) setData(budgets) })
      .catch(err => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [refreshKey])

  async function run(budget: ApiBudget, action: () => Promise<void>) {
    if (running.current) return
    running.current = true; setBusyId(budget.id); setActionError('')
    try { await action() }
    catch (err) { setActionError(err instanceof Error ? err.message : String(err)) }
    finally { running.current = false; setBusyId(null) }
  }

  async function removeBudget(budget: ApiBudget) {
    if (running.current || !window.confirm(`Excluir o orçamento #${budget.numero}? Esta ação não pode ser desfeita.`)) return
    await run(budget, async () => {
      await deleteBudget(budget.id)
      setData(current => current.filter(item => item.id !== budget.id))
    })
  }

  async function copyBudget(budget: ApiBudget) {
    if (running.current || !window.confirm(`Gerar uma cópia do orçamento #${budget.numero}, com novo número e situação em aberto?`)) return
    await run(budget, async () => {
      const copy = await duplicateBudget(budget.id)
      setData(current => [copy, ...current])
      onOpen(copy.id)
    })
  }

  async function saveBudgetStatus() {
    if (!statusBudget || running.current) return
    const budget = statusBudget
    await run(budget, async () => {
      const updated = await updateBudgetStatus(
        budget.id, newStatus, budget.status
      )
      setData(current => current.map(
        item => item.id === updated.id ? updated : item
      ))
      setStatusBudget(null)
    })
  }

  async function generateSale(budget: ApiBudget) {
    if (running.current) return
    if (budget.status !== 'APROVADO') { setActionError('Apenas orçamentos aprovados podem ser convertidos em venda.'); return }
    if (generatedSaleBudgetIds.has(budget.id)) { setActionError('Este orçamento já foi convertido em venda.'); return }
    if (!window.confirm(`Converter o orçamento aprovado #${budget.numero} em venda? Os dados salvos serão copiados para o pedido.`)) return
    await run(budget, async () => {
      const sale = await convertBudgetToOrder(budget.id)
      setGeneratedSaleBudgetIds(current => new Set(current).add(budget.id))
      window.alert(`Venda ${sale.numero || sale.id} gerada com sucesso.`)
    })
  }

  async function printBudget(budget: ApiBudget, mode: BudgetPdfMode) {
    if (running.current) return
    if ((budget.parceiro_id != null) === (mode === 'direct')) { setActionError('Tipo de PDF incompatível com este orçamento.'); return }
    await run(budget, async () => {
      const { prepareSavedBudgetPdf, downloadBudgetPdf } = await import('../services/budgetPdf')
      const result = await prepareSavedBudgetPdf(budget.id, mode)
      downloadBudgetPdf(result.blob, result.filename)
      if (result.warnings.length) window.alert(result.warnings.join(' '))
    })
  }

  const open = data.filter(budget => budget.status === 'EM_ABERTO')
  return <div className="budget-page">
    <section className="budget-page-heading page-heading"><div><p className="eyebrow">OPERAÇÃO COMERCIAL</p><h1>Orçamentos</h1><p className="heading-subtitle">Dados carregados diretamente do FastAPI.</p></div><button className="primary-button" onClick={onNew}><Plus size={17} /> Novo orçamento</button></section>
    <section className="budget-kpi-grid"><Kpi icon={<Clock3 size={18} />} label="Em aberto" value={String(open.length)} /><Kpi icon={<CheckCircle2 size={18} />} label="Total" value={String(data.length)} /><Kpi icon={<WalletCards size={18} />} label="Em negociação" value={formatCurrency(open.reduce((sum, budget) => sum + Number(budget.total_final), 0))} /></section>
    {loading ? <div className="panel loading-state">Carregando orçamentos...</div> : error ? <div className="api-message error">{error}</div> : <BudgetTable
      budgets={data} onNew={onNew} onOpen={onOpen} onView={setPreviewId} onDelete={removeBudget}
      onChangeStatus={budget => {
        setNewStatus(budget.status)
        setStatusBudget(budget)
      }}
      onDuplicate={copyBudget} onGenerateSale={generateSale} generatedSaleBudgetIds={generatedSaleBudgetIds}
      onPrepareServiceOrder={budget => setServiceOrderId(budget.id)}
      onGenerateProduction={budgetProductionEnabled ? budget => setProductionId(budget.id) : undefined}
      productionReason={budgetProductionEnabled ? undefined : budgetProductionDisabledReason}
      onShare={(budget, channel) => setSharing({ budget, channel })} onPrint={printBudget} deletingId={busyId} />}
    {actionError && <div className="api-message error" role="alert">{actionError}</div>}
    {statusBudget && <div className="budget-status-overlay">
      <section className="panel budget-status-dialog"
        role="dialog" aria-modal="true"
        aria-label="Alterar situacao do orcamento">

        <h2>Alterar situação</h2>
        <p>Orçamento #{statusBudget.numero}</p>

        <label className="field">
          <span>Nova situação</span>
          <select value={newStatus}
            disabled={busyId !== null}
            onChange={e => setNewStatus(e.target.value)}>
            <option value="EM_ABERTO">Em aberto</option>
            <option value="APROVADO">Aprovado</option>
            <option value="CANCELADO">Cancelado</option>
          </select>
        </label>

        {actionError && <p role="alert">{actionError}</p>}

        <div className="budget-status-buttons">
          <button type="button" className="secondary-button"
            disabled={busyId !== null}
            onClick={() => setStatusBudget(null)}>
            Voltar
          </button>
          <button type="button" className="primary-button"
            disabled={busyId !== null || newStatus === statusBudget.status}
            onClick={() => void saveBudgetStatus()}>
            Salvar situação
          </button>
        </div>
      </section>
    </div>}
    {sharing && <BudgetShareDialog budget={sharing.budget} channel={sharing.channel} onClose={closeShare} />}
    {serviceOrderId !== null && <BudgetServiceOrderDialog key={serviceOrderId} budgetId={serviceOrderId} onClose={closeServiceOrder} />}
    {productionId !== null && budgetProductionEnabled && <BudgetProductionDialog key={productionId} budgetId={productionId} onClose={closeProduction} />}
    {previewId !== null && <BudgetPreviewDialog key={previewId} id={previewId} onClose={closePreview} />}
  </div>
}

function Kpi({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <article className="budget-kpi dark"><div className="budget-kpi-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>API real</small></div></article>
}
