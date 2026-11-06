import { useEffect, useMemo, useState } from 'react'
import { listFinanceRecords, type FinanceRecord } from '../services/api'
import { formatCurrency, type BudgetPaymentInstallment, type PaymentMode } from '../types/budget'

export type BudgetPaymentState = {
  mode: PaymentMode | ''
  count: number
  intervalDays: number
  firstDueDate: string
  defaultPaymentMethodId: number
  installments: BudgetPaymentInstallment[]
}

const addDays = (date: string, days: number) => {
  const value = new Date(`${date}T12:00:00`)
  value.setDate(value.getDate() + days)
  return value.toISOString().slice(0, 10)
}

const cents = (value: number) => Math.round(value * 100)

export function BudgetPaymentSection({ total, value, onChange }: {
  total: number
  value: BudgetPaymentState
  onChange: (value: BudgetPaymentState) => void
}) {
  const [methods, setMethods] = useState<FinanceRecord[]>([])
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    void listFinanceRecords('formas-pagamento')
      .then(rows => setMethods(rows.filter(row => row.ativo && ['RECEBER', 'AMBOS'].includes(row.disponivel_para || 'AMBOS'))))
      .catch(error => setLoadError(error instanceof Error ? error.message : String(error)))
  }, [])

  const totalCents = cents(total)
  const installmentsCents = value.installments.reduce((sum, installment) => sum + cents(installment.valor), 0)
  const difference = (totalCents - installmentsCents) / 100
  const consistent = value.mode === '' || (value.installments.length > 0 && cents(difference) === 0)
  const expectedCount = value.mode === 'AVISTA' ? 1 : value.mode === 'ENTRADA_SALDO' ? 2 : Math.max(2, value.count)

  const generate = () => {
    if (!value.mode || !value.firstDueDate || !value.defaultPaymentMethodId || totalCents <= 0) return
    const count = expectedCount
    const base = Math.floor(totalCents / count)
    const generated = Array.from({ length: count }, (_, index): BudgetPaymentInstallment => ({
      numero: index + 1,
      tipo: value.mode === 'ENTRADA_SALDO' ? (index === 0 ? 'ENTRADA' : 'SALDO') : 'PARCELA',
      valor: (index === count - 1 ? totalCents - base * (count - 1) : base) / 100,
      vencimento: addDays(value.firstDueDate, index * value.intervalDays),
      forma_pagamento_id: value.defaultPaymentMethodId,
    }))
    onChange({ ...value, count, installments: generated })
  }

  const methodOptions = useMemo(() => methods.map(method => <option key={method.id} value={method.id}>{method.nome}</option>), [methods])

  return <div className="payment-plan">
    <div className="form-grid relationship-grid">
      <label className="field"><span>Condição</span><select value={value.mode} onChange={event => onChange({ ...value, mode: event.target.value as PaymentMode | '', installments: [] })}>
        <option value="">Não definida</option><option value="AVISTA">À vista</option><option value="PARCELADO">Parcelado</option><option value="ENTRADA_SALDO">Entrada + saldo</option>
      </select></label>
      <label className="field"><span>Forma padrão</span><select value={value.defaultPaymentMethodId || ''} onChange={event => onChange({ ...value, defaultPaymentMethodId: Number(event.target.value), installments: [] })} disabled={!value.mode}>
        <option value="">Selecione</option>{methodOptions}
      </select></label>
      {value.mode === 'PARCELADO' && <label className="field"><span>Número de parcelas</span><input type="number" min="2" max="24" value={value.count} onChange={event => onChange({ ...value, count: Math.max(2, Math.min(24, Number(event.target.value) || 2)), installments: [] })}/></label>}
      <label className="field"><span>Primeiro vencimento</span><input type="date" value={value.firstDueDate} onChange={event => onChange({ ...value, firstDueDate: event.target.value, installments: [] })} disabled={!value.mode}/></label>
      <label className="field"><span>Intervalo em dias</span><input type="number" min="0" max="365" value={value.intervalDays} onChange={event => onChange({ ...value, intervalDays: Math.max(0, Math.min(365, Number(event.target.value) || 0)), installments: [] })} disabled={!value.mode || value.mode === 'AVISTA'}/></label>
    </div>
    <p className="payment-plan-help">Base das parcelas: <strong>{formatCurrency(total)}</strong>. Desconto e taxa bancária são aplicados pelos controles comerciais existentes antes da geração.</p>
    {loadError && <div className="api-message error">Não foi possível carregar as formas de pagamento: {loadError}</div>}
    <button type="button" className="secondary-button" onClick={generate} disabled={!value.mode || !value.firstDueDate || !value.defaultPaymentMethodId || totalCents <= 0}>Gerar parcelas</button>
    {value.installments.length > 0 && <div className="payment-installments">
      {value.installments.map((installment, index) => <div className="payment-installment" key={installment.numero}>
        <strong>{installment.tipo === 'ENTRADA' ? 'Entrada' : installment.tipo === 'SALDO' ? 'Saldo' : `Parcela ${installment.numero}/${value.installments.length}`}</strong>
        <label className="field"><span>Valor</span><input type="number" min="0.01" step="0.01" value={installment.valor} onChange={event => onChange({ ...value, installments: value.installments.map((item, itemIndex) => itemIndex === index ? { ...item, valor: Number(event.target.value) || 0 } : item) })}/></label>
        <label className="field"><span>Vencimento</span><input type="date" value={installment.vencimento} onChange={event => onChange({ ...value, installments: value.installments.map((item, itemIndex) => itemIndex === index ? { ...item, vencimento: event.target.value } : item) })}/></label>
        <label className="field"><span>Forma</span><select value={installment.forma_pagamento_id} onChange={event => onChange({ ...value, installments: value.installments.map((item, itemIndex) => itemIndex === index ? { ...item, forma_pagamento_id: Number(event.target.value) } : item) })}>{methodOptions}</select></label>
      </div>)}
      <div className={`api-message${consistent ? '' : ' error'}`}>Soma: <strong>{formatCurrency(installmentsCents / 100)}</strong> · Diferença: <strong>{formatCurrency(difference)}</strong></div>
    </div>}
  </div>
}

export const paymentPlanIsConsistent = (total: number, state: BudgetPaymentState) => state.mode === '' || (
  state.installments.length === (state.mode === 'AVISTA' ? 1 : state.mode === 'ENTRADA_SALDO' ? 2 : state.count) &&
  state.installments.every(installment => installment.valor > 0 && installment.vencimento && installment.forma_pagamento_id > 0) &&
  state.installments.reduce((sum, installment) => sum + cents(installment.valor), 0) === cents(total)
)
