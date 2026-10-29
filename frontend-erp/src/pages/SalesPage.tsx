import './salesPage.css'
import { ColumnManager } from '../components/ColumnManager'
import {
  CheckCircle2,
  Clock3,
  FileText,
  ShoppingCart,
  WalletCards,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { SaleEditDialog } from '../components/SaleEditDialog'
import { RowActionsMenu } from '../components/RowActionsMenu'
import {
  deleteOrder,
  getClients,
  getOrders,
  getCommercialPartners,
  getRepresentatives,
  type ApiCommercialPartner,
  type ApiRepresentative,
  createOrderReceivable,
  type ApiOrder,
} from '../services/api'
import type { ApiClient } from '../types/budget'
import { formatCurrency } from '../types/budget'

function formatDate(value?: string | null) {
  if (!value) return '-'

  const date = new Date(`${value.slice(0, 10)}T12:00:00`)

  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('pt-BR').format(date)
}

function statusLabel(status?: string | null) {
  const value = (status || 'ABERTO').toUpperCase()

  if (value === 'ABERTO') return 'Em aberto'
  if (value === 'CONCLUIDO') return 'Concluído'
  if (value === 'CANCELADO') return 'Cancelado'
  if (value === 'FATURADO') return 'Faturado'

  return value.replaceAll('_', ' ')
}

function commercialName(
  records: { id: number; nome?: unknown }[],
  id: number | null | undefined,
  fallback: string,
) {
  if (id == null) return '—'

  const name = records.find((record) => record.id === id)?.nome
  return typeof name === 'string' && name.trim()
    ? name.trim()
    : `${fallback} #${id}`
}

export function SalesPage({ onOpenSale, onNewSale, onViewFinance }: { onOpenSale: (id: number) => void; onNewSale: () => void; onViewFinance?: (id: number) => void }) {
  const [editingOrder, setEditingOrder] = useState<ApiOrder | null>(null)
  const [actionError, setActionError] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)
  async function removeOrder(order: ApiOrder) {
    if (deletingId !== null || !window.confirm(`Excluir a venda ${order.numero || order.id}? Esta ação não pode ser desfeita.`)) return
    setDeletingId(order.id); setActionError('')
    try { await deleteOrder(order.id); setOrders(current => current.filter(item => item.id !== order.id)) }
    catch (err) { setActionError(err instanceof Error ? err.message : String(err)) }
    finally { setDeletingId(null) }
  }
  const [orders, setOrders] = useState<ApiOrder[]>([])
  const [clients, setClients] = useState<ApiClient[]>([])
  const [partners, setPartners] = useState<ApiCommercialPartner[]>([])
  const [representatives, setRepresentatives] = useState<ApiRepresentative[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [receivableOrderId, setReceivableOrderId] = useState<number | null>(null)
  const [receivableDueDate, setReceivableDueDate] = useState('')
  const [receivableError, setReceivableError] = useState('')
  const [receivableSaving, setReceivableSaving] = useState(false)
  const [receivableDone, setReceivableDone] = useState<number[]>([])

  useEffect(() => {
    let cancelled = false

    void Promise.all([
      getOrders(),
      getClients(),
      Promise.allSettled([
        getCommercialPartners(),
        getRepresentatives(),
      ]),
    ])
      .then(([ordersData, clientsData, commercialData]) => {
        if (cancelled) return

        setOrders(ordersData)
        setClients(clientsData)

        const [partnersResult, representativesResult] = commercialData
        if (partnersResult.status === 'fulfilled') setPartners(partnersResult.value)
        if (representativesResult.status === 'fulfilled') {
          setRepresentatives(representativesResult.value)
        }
        commercialData.forEach((result) => {
          if (result.status === 'rejected') {
            console.warn('Falha ao carregar nomes da origem comercial', result.reason)
          }
        })
      })
      .catch((err) => {
        if (cancelled) return

        setError(
          err instanceof Error
            ? err.message
            : String(err),
        )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function handleCreateReceivable(order: ApiOrder) {
    if (!receivableDueDate) {
      setReceivableError('Informe o vencimento.')
      return
    }

    setReceivableSaving(true)
    setReceivableError('')

    try {
      await createOrderReceivable(
        order.id,
        {
          vencimento: receivableDueDate,
          categoria: 'VENDAS',
        },
      )

      setReceivableDone((current) => [
        ...current,
        order.id,
      ])

      setReceivableOrderId(null)
      setReceivableDueDate('')
    } catch (err) {
      setReceivableError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setReceivableSaving(false)
    }
  }
  const clientMap = useMemo(
    () =>
      new Map(
        clients.map((client) => [
          client.id,
          client.nome,
        ]),
      ),
    [clients],
  )

  const openOrders = orders.filter(
    (order) =>
      (order.status || 'ABERTO').toUpperCase() === 'ABERTO',
  )

  const totalOpen = openOrders.reduce(
    (sum, order) =>
      sum + Number(order.total_final || 0),
    0,
  )

  const totalSales = orders.reduce(
    (sum, order) =>
      sum + Number(order.total_final || 0),
    0,
  )

  return (
    <div className="budget-page">
      <section className="budget-page-heading page-heading">
        <div>
          <p className="eyebrow">
            OPERAÇÃO COMERCIAL
          </p>

          <h1>Vendas</h1>

          <p className="heading-subtitle">
            Pedidos comerciais gerados a partir dos
            orçamentos aprovados.
          </p>
        </div>
        <button type="button" className="primary-button" onClick={onNewSale}>+ Nova venda</button>
      </section>

      <section className="budget-kpi-grid">
        <article className="budget-kpi dark">
          <div className="budget-kpi-icon">
            <ShoppingCart size={18} />
          </div>

          <div>
            <span>Total de vendas</span>
            <strong>{orders.length}</strong>
            <small>API real</small>
          </div>
        </article>

        <article className="budget-kpi dark">
          <div className="budget-kpi-icon">
            <Clock3 size={18} />
          </div>

          <div>
            <span>Em aberto</span>
            <strong>{openOrders.length}</strong>
            <small>Pedidos comerciais</small>
          </div>
        </article>

        <article className="budget-kpi dark">
          <div className="budget-kpi-icon">
            <WalletCards size={18} />
          </div>

          <div>
            <span>Valor em aberto</span>
            <strong>{formatCurrency(totalOpen)}</strong>
            <small>Vendas abertas</small>
          </div>
        </article>

        <article className="budget-kpi dark">
          <div className="budget-kpi-icon">
            <CheckCircle2 size={18} />
          </div>

          <div>
            <span>Valor total</span>
            <strong>{formatCurrency(totalSales)}</strong>
            <small>Pedidos cadastrados</small>
          </div>
        </article>
      </section>

      {actionError && <div className="api-message error" role="alert">{actionError}</div>}
      {editingOrder && <SaleEditDialog order={editingOrder} onClose={() => setEditingOrder(null)} onSaved={updated => { setOrders(current => current.map(item => item.id === updated.id ? updated : item)); setEditingOrder(null) }} />}
      {loading ? (
        <div className="panel loading-state">
          Carregando vendas...
        </div>
      ) : error ? (
        <div className="api-message error">
          {error}
        </div>
      ) : orders.length === 0 ? (
        <section className="panel loading-state">
          <ShoppingCart size={24} />

          <strong>
            Nenhuma venda registrada.
          </strong>

          <p>
            Abra um orçamento aprovado e use
            “Converter em venda”.
          </p>
        </section>
      ) : (
        <section className="panel">
          <div className="table-wrap">
            <ColumnManager storageKey="smarttec:columns:sales" lockedColumns={['number', 'actions']} columns={[{ id: 'number', label: 'Venda', defaultVisible: true }, { id: 'client', label: 'Cliente', defaultVisible: true }, { id: 'commercialLinks', label: 'Revenda / Representante', defaultVisible: true }, { id: 'budget', label: 'Orçamento', defaultVisible: true }, { id: 'date', label: 'Data', defaultVisible: true }, { id: 'deadline', label: 'Prazo', defaultVisible: true }, { id: 'status', label: 'Status', defaultVisible: true }, { id: 'items', label: 'Itens', defaultVisible: true }, { id: 'financial', label: 'Financeiro', defaultVisible: true }, { id: 'total', label: 'Total', defaultVisible: true }, { id: 'actions', label: 'Ações', defaultVisible: true }]}><table className="sales-table">
              <thead>
                <tr>
                  <th>Venda</th>
                  <th>Cliente</th>
                  <th>Revenda / Representante</th>
                  <th>Orçamento</th>
                  <th>Data</th>
                  <th>Prazo</th>
                  <th>Status</th>
                  <th>Itens</th>
                  <th>Financeiro</th>
                  <th style={{ textAlign: 'right' }}>
                    Total
                  </th>
                  <th className="sales-actions-cell">Ações</th>
                </tr>
              </thead>

              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <button
                        type="button"
                        className="quote-id"
                        onClick={() => onOpenSale(order.id)}
                        aria-label={`Abrir venda ${order.numero || `#${order.id}`}`}
                        title="Abrir venda"
                        style={{ border: 0, background: 'transparent', padding: 0, cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: 3, font: 'inherit', fontWeight: 700 }}
                      >
                        {order.numero || `#${order.id}`}
                      </button>
                    </td>

                    <td>
                      <strong>
                        {order.parceiro_id != null
                          ? order.cliente_final_nome?.trim() || '—'
                          : order.cliente_id != null
                            ? clientMap.get(order.cliente_id)?.trim() || `Cliente #${order.cliente_id}`
                            : '—'}
                      </strong>
                    </td>

                    <td>
                      {[
                        order.parceiro_id != null ? commercialName(partners, order.parceiro_id, 'Revenda') : null,
                        order.representante_id != null ? commercialName(representatives, order.representante_id, 'Representante') : null,
                      ].filter(Boolean).join(' • ') || '—'}
                    </td>

                    <td>
                      {order.orcamento_numero
                        ? `#${order.orcamento_numero}`
                        : order.orcamento_id
                          ? `#${order.orcamento_id}`
                          : '-'}
                    </td>

                    <td>
                      {formatDate(order.data_venda)}
                    </td>

                    <td>
                      {formatDate(order.prazo_entrega)}
                    </td>

                    <td>
                      <span className="draft-badge">
                        {statusLabel(order.status)}
                      </span>
                    </td>

                    <td>
                      <FileText
                        size={14}
                        style={{
                          verticalAlign: 'middle',
                          marginRight: 5,
                        }}
                      />

                      {order.itens?.length || 0}
                    </td>

                    <td>
                      {receivableDone.includes(order.id) ? (
                        <span className="draft-badge">
                          Conta criada
                        </span>
                      ) : receivableOrderId === order.id ? (
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                          <input
                            type="date"
                            value={receivableDueDate}
                            onChange={(e) => setReceivableDueDate(e.target.value)}
                            style={{ maxWidth: 160 }}
                          />
                          <button
                            type="button"
                            className="primary-button"
                            onClick={() => void handleCreateReceivable(order)}
                            disabled={receivableSaving}
                          >
                            {receivableSaving ? 'Gerando...' : 'Confirmar'}
                          </button>
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => {
                              setReceivableOrderId(null)
                              setReceivableDueDate('')
                              setReceivableError('')
                            }}
                            disabled={receivableSaving}
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => {
                            setReceivableOrderId(order.id)
                            setReceivableDueDate('')
                            setReceivableError('')
                          }}
                        >
                          Gerar conta a receber
                        </button>
                      )}

                      {receivableOrderId === order.id && receivableError && (
                        <div className="api-message error" style={{ marginTop: 8 }}>
                          {receivableError}
                        </div>
                      )}
                    </td>

                    <td style={{ textAlign: 'right' }}>
                      <strong>
                        {formatCurrency(
                          Number(order.total_final || 0),
                        )}
                      </strong>
                    </td>
                    <td className="sales-actions-cell"><RowActionsMenu module="sale" label={`venda ${order.numero || `#${order.id}`}`} onView={() => onOpenSale(order.id)} onEdit={() => setEditingOrder(order)} onChangeStatus={() => setEditingOrder(order)} onViewFinance={onViewFinance ? () => onViewFinance(order.id) : undefined} onDelete={() => void removeOrder(order)} busy={deletingId !== null} /></td>
                  </tr>
                ))}
              </tbody>
            </table></ColumnManager>
          </div>
        </section>
      )}
    </div>
  )
}