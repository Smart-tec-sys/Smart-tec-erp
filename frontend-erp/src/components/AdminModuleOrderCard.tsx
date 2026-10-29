import type { AdminModuleOrder, AdminPayment } from '../services/admin'
import { orderPresentation, type OrderDestination } from '../utils/adminOrders'
import './adminOrders.css'

type Props = {
  order: AdminModuleOrder
  payments: AdminPayment[]
  busy: boolean
  onChange: (id: number, destination: OrderDestination) => void
}
const money = (value?: number | null) => value == null ? '—' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
export function AdminModuleOrderCard({ order, payments, busy, onChange }: Props) {
  const action = orderPresentation(order.status)
  const pending = payments.filter(payment => payment.pedido_modulo_id === order.id && payment.status === 'PENDENTE')
  const date = order.data_pedido?.slice(0,10).split('-').reverse().join('/') || '—'
  return <article className="admin-order-card">
    <header className="admin-order-header">
      <div><h4>{order.modulo_nome}</h4><p>Pedido #{order.id} · {order.periodicidade ?? '—'} · {money(order.valor)}</p></div>
      <span className={`admin-order-badge admin-order-badge--${action.tone}`}>{order.status.replaceAll('_',' ')}</span>
    </header>
    <dl className="admin-order-data">
      <div><dt>Pagamento</dt><dd>{order.forma_pagamento_nome || order.forma_pagamento || 'não informado'}</dd></div>
      <div><dt>Responsável</dt><dd>{order.responsavel_nome?.trim() || 'não informado'}</dd></div>
      <div><dt>Pedido</dt><dd>{date}</dd></div>
    </dl>
    {order.status === 'AGUARDANDO_PAGAMENTO' && <p className="admin-order-payment">
      {money(order.valor)} · {order.forma_pagamento_nome || order.forma_pagamento || 'Forma não informada'}<br />
      {pending.length ? `Pagamento pendente vinculado: ${pending.map(payment => `#${payment.id}`).join(', ')}` : 'Nenhum pagamento pendente vinculado retornado pela API.'}
    </p>}
    {order.status === 'PAGO' && <p className="admin-order-payment">Pagamento confirmado · {money(order.valor)}</p>}
    {order.observacoes && <p className="admin-order-notes">{order.observacoes}</p>}
    {(action.primary || action.cancel) && <footer className="admin-order-actions">
      {action.primary && <button type="button" className="admin-order-primary" disabled={busy} onClick={() => onChange(order.id, action.primary!.destination)}>{action.primary.label}</button>}
      {action.cancel && <button type="button" className="admin-order-cancel" disabled={busy} onClick={() => onChange(order.id,'CANCELADO')}>Cancelar</button>}
    </footer>}
  </article>
}
