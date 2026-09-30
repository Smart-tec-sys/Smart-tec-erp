import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  Bell,
  CalendarClock,
  ChevronRight,
  Clock,
  FileText,
  PackageSearch,
} from 'lucide-react'

import type { AgendaHoje } from '../hooks/useAgendaHoje'
import type { BudgetNotificationsState } from '../hooks/useBudgetNotifications'
import type { StockNotificationsState } from '../hooks/useStockNotifications'
import { derivarNotificacoesAgenda } from '../services/agendaNotifications'
import { derivarNotificacoesOrcamentos } from '../services/budgetNotifications'
import { derivarNotificacoesEstoque } from '../services/stockNotifications'

import './headerNotifications.css'

type HeaderNotificationsProps = {
  agenda: AgendaHoje
  budgets: BudgetNotificationsState
  stock: StockNotificationsState
  onOpenAgenda: () => void
  onOpenBudgets: () => void
  onOpenProducts: () => void
}

export function HeaderNotifications({
  agenda,
  budgets,
  stock,
  onOpenAgenda,
  onOpenBudgets,
  onOpenProducts,
}: HeaderNotificationsProps) {
  const [open, setOpen] = useState(false)
  const [now, setNow] = useState(() => new Date())

  const wrapperRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  const agendaNotifications =
    derivarNotificacoesAgenda(agenda.events, now)

  const budgetNotifications =
    derivarNotificacoesOrcamentos(budgets.budgets, now)

  const stockNotifications =
    derivarNotificacoesEstoque(stock.products)

  const total =
    agendaNotifications.length +
    budgetNotifications.length +
    stockNotifications.length

  const loading = agenda.loading || budgets.loading || stock.loading
  const hasError = Boolean(agenda.error || budgets.error || stock.error)

  useEffect(() => {
    const updateClock = () => setNow(new Date())

    const timer = window.setInterval(
      updateClock,
      15_000,
    )

    window.addEventListener('focus', updateClock)

    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', updateClock)
    }
  }, [])

  useEffect(() => {
    setNow(new Date())
  }, [agenda.events, budgets.budgets, stock.products])

  useEffect(() => {
    if (!open) return

    function outside(event: MouseEvent) {
      if (
        !wrapperRef.current?.contains(
          event.target as Node,
        )
      ) {
        setOpen(false)
      }
    }

    function keyboard(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', outside)
    document.addEventListener('keydown', keyboard)

    return () => {
      document.removeEventListener(
        'mousedown',
        outside,
      )
      document.removeEventListener(
        'keydown',
        keyboard,
      )
    }
  }, [open])

  function openAgenda() {
    setOpen(false)
    onOpenAgenda()
  }

  function openBudgets() {
    setOpen(false)
    onOpenBudgets()
  }

  function openProducts() {
    setOpen(false)
    onOpenProducts()
  }

  function refreshAll() {
    agenda.refresh()
    budgets.refresh()
    stock.refresh()
    setNow(new Date())
  }

  return (
    <div
      className="header-agenda header-notifications"
      ref={wrapperRef}
    >
      <button
        ref={buttonRef}
        type="button"
        className={`icon-button notification-button agenda-header-button${
          open ? ' active' : ''
        }`}
        aria-label="Notificações"
        aria-expanded={open}
        aria-controls="header-notifications-panel"
        onClick={() => {
          setOpen((value) => !value)
          setNow(new Date())

          if (!open) {
            refreshAll()
          }
        }}
      >
        <Bell size={18} />

        {!loading && !hasError && total > 0 && (
          <span
            className="agenda-header-badge"
            aria-label={`${total} alertas ativos`}
          >
            {total > 9 ? '9+' : total}
          </span>
        )}
      </button>

      {open && (
        <section
          className="agenda-header-panel notifications-panel"
          id="header-notifications-panel"
          aria-label="Notificações"
        >
          <div className="agenda-header-panel-head">
            <div>
              <strong>Notificações</strong>
              <span>Alertas do sistema</span>
            </div>
          </div>

          <div
            className="agenda-header-content"
            aria-busy={loading}
          >
            {loading && (
              <div
                className="agenda-header-state"
                role="status"
              >
                Carregando notificações...
              </div>
            )}

            {!loading && hasError && (
              <div
                className="agenda-header-state agenda-header-error"
                role="alert"
              >
                Não foi poss?vel carregar todas as notificações.
              </div>
            )}

            {!loading &&
              !hasError &&
              total === 0 && (
                <div className="agenda-header-empty">
                  <Bell size={28} />
                  <strong>
                    Nenhuma notifica??o no momento.
                  </strong>
                </div>
              )}

            {!loading &&
              !hasError &&
              agendaNotifications.map(
                (notification) => (
                  <button
                    type="button"
                    key={`agenda-${notification.id}`}
                    className="notification-item"
                    onClick={openAgenda}
                  >
                    {notification.tipo ===
                    'ATRASADO' ? (
                      <AlertCircle size={17} />
                    ) : (
                      <Clock size={17} />
                    )}

                    <span className="notification-copy">
                      <span className="notification-type">
                        {notification.mensagem}
                      </span>

                      <strong
                        title={notification.titulo}
                      >
                        {notification.titulo}
                      </strong>

                      <time
                        dateTime={
                          notification.inicio
                        }
                      >
                        {new Intl.DateTimeFormat(
                          'pt-BR',
                          {
                            hour: '2-digit',
                            minute: '2-digit',
                          },
                        ).format(
                          new Date(
                            notification.inicio,
                          ),
                        )}
                      </time>
                    </span>

                    <ChevronRight size={14} />
                  </button>
                ),
              )}

            {!loading &&
              !hasError &&
              budgetNotifications.map(
                (notification) => (
                  <button
                    type="button"
                    key={notification.id}
                    className="notification-item notification-budget"
                    onClick={openBudgets}
                  >
                    {notification.tipo ===
                    'ORCAMENTO_VENCIDO' ? (
                      <AlertCircle size={17} />
                    ) : notification.tipo ===
                      'ORCAMENTO_VENCE_HOJE' ? (
                      <CalendarClock size={17} />
                    ) : (
                      <FileText size={17} />
                    )}

                    <span className="notification-copy">
                      <span className="notification-type">
                        {notification.mensagem}
                      </span>

                      <strong>
                        {notification.titulo}
                      </strong>

                      <span className="notification-detail">
                        {notification.detalhe}
                      </span>
                    </span>

                    <ChevronRight size={14} />
                  </button>
                ),
              )}

            {!loading &&
              !hasError &&
              stockNotifications.map(
                (notification) => (
                  <button
                    type="button"
                    key={notification.id}
                    className="notification-item notification-stock"
                    onClick={openProducts}
                  >
                    <PackageSearch size={17} />

                    <span className="notification-copy">
                      <span className="notification-type">
                        {notification.mensagem}
                      </span>

                      <strong title={notification.titulo}>
                        {notification.titulo}
                      </strong>

                      <span className="notification-detail">
                        {notification.detalhe}
                      </span>
                    </span>

                    <ChevronRight size={14} />
                  </button>
                ),
              )}

            {!loading &&
              !hasError &&
              agenda.limited && (
                <p className="notification-limit">
                  Limite da consulta da Agenda atingido.
                  Pode haver outros alertas.
                </p>
              )}
          </div>

          {hasError ? (
            <button
              type="button"
              className="agenda-header-footer"
              onClick={refreshAll}
            >
              Tentar novamente
            </button>
          ) : (
            <div className="notification-footer-actions">
              <button
                type="button"
                className="agenda-header-footer"
                onClick={openAgenda}
              >
                <span>Agenda</span>
                <ChevronRight size={16} />
              </button>

              <button
                type="button"
                className="agenda-header-footer"
                onClick={openBudgets}
              >
                <span>Orçamentos</span>
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
