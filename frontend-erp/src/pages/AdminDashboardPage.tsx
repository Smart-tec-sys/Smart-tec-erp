import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  Building2,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  FileText,
  Headphones,
  Package,
  PackagePlus,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-react'
import {
  activateAdminModule,
  activateAdminSubscription,
  cancelAdminModule,
  createAdminModuleOrder,
  getAdminCompanies,
  getAdminCompany,
  getAdminMe,
  getAdminModulesCatalog,
  getAdminOverview,
  getAdminPlans,
  startAdminTrial,
  updateAdminModuleOrderStatus,
  type AdminCompanyDetail,
  type AdminCompanyListItem,
  type AdminMe,
  type AdminModuleCatalogItem,
  type AdminOverview,
  type AdminPlan,
} from '../services/admin'

type Props = {
  onBack: () => void
}

type AdminSection = 'dashboard' | 'empresas'

type CompanyTab =
  | 'resumo'
  | 'assinatura'
  | 'modulos'
  | 'pedidos'
  | 'financeiro'
  | 'fiscal'
  | 'suporte'
  | 'comercial'
  | 'historico'


function money(value?: number | null) {
  if (value == null) return '—'

  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

function date(value?: string | null) {
  if (!value) return '—'

  return new Intl.DateTimeFormat('pt-BR').format(
    new Date(`${value}T12:00:00`),
  )
}

function StatusBadge({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        minHeight: 26,
        padding: '4px 9px',
        borderRadius: 999,
        background: '#f1f3f5',
        fontSize: 11,
        fontWeight: 700,
        color: '#555d67',
      }}
    >
      {children}
    </span>
  )
}

function AdminRecordList({
  items,
  emptyText,
}: {
  items: Array<Record<string, unknown>>
  emptyText: string
}) {
  if (!items.length) {
    return (
      <p style={{ color: '#777f89' }}>
        {emptyText}
      </p>
    )
  }

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {items.map((item, index) => (
        <div
          key={index}
          style={{
            padding: 14,
            border: '1px solid #e7e9ed',
            borderRadius: 10,
            background: '#fff',
          }}
        >
          {Object.entries(item).map(([key, value]) => (
            <div
              key={key}
              style={{
                display: 'grid',
                gridTemplateColumns: '160px 1fr',
                gap: 10,
                fontSize: 12,
                padding: '3px 0',
              }}
            >
              <strong>{key}</strong>
              <span>{String(value ?? '—')}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}


function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string
  value: number | string
  detail: string
  icon: React.ReactNode
}) {
  return (
    <article
      style={{
        background: '#fff',
        border: '1px solid #e7e9ed',
        borderRadius: 14,
        padding: 18,
        minHeight: 138,
        boxShadow: '0 2px 8px rgba(15,23,42,.04)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <span
          style={{
            fontSize: 13,
            color: '#68707d',
            fontWeight: 600,
          }}
        >
          {label}
        </span>

        <span
          style={{
            width: 36,
            height: 36,
            display: 'grid',
            placeItems: 'center',
            borderRadius: 10,
            background: '#f3f4f6',
          }}
        >
          {icon}
        </span>
      </div>

      <strong
        style={{
          display: 'block',
          fontSize: 30,
          marginTop: 14,
        }}
      >
        {value}
      </strong>

      <span
        style={{
          display: 'block',
          marginTop: 6,
          fontSize: 12,
          color: '#8a9099',
        }}
      >
        {detail}
      </span>
    </article>
  )
}

export function AdminDashboardPage({ onBack }: Props) {
  const [section, setSection] =
    useState<AdminSection>(() => {
      const saved =
        window.localStorage.getItem(
          'smarttec:admin-section',
        )

      return saved === 'empresas'
        ? 'empresas'
        : 'dashboard'
    })

  const [me, setMe] = useState<AdminMe | null>(null)
  const [overview, setOverview] =
    useState<AdminOverview | null>(null)

  const [companies, setCompanies] =
    useState<AdminCompanyListItem[]>([])

  const [company, setCompany] =
    useState<AdminCompanyDetail | null>(null)

  const [companyTab, setCompanyTab] =
    useState<CompanyTab>(() => {
      const saved =
        window.localStorage.getItem(
          'smarttec:admin-company-tab',
        )

      if (saved === 'assinatura') return 'assinatura'
      if (saved === 'modulos') return 'modulos'
      if (saved === 'pedidos') return 'pedidos'
      if (saved === 'financeiro') return 'financeiro'
      if (saved === 'fiscal') return 'fiscal'
      if (saved === 'suporte') return 'suporte'
      if (saved === 'comercial') return 'comercial'
      if (saved === 'historico') return 'historico'

      return 'resumo'
    })


  const [plans, setPlans] =
    useState<AdminPlan[]>([])

  const [moduleCatalog, setModuleCatalog] =
    useState<AdminModuleCatalogItem[]>([])

  const [selectedPlanId, setSelectedPlanId] =
    useState('')

  const [
    subscriptionPeriod,
    setSubscriptionPeriod,
  ] = useState<'MENSAL' | 'ANUAL'>('MENSAL')

  const [
    subscriptionValue,
    setSubscriptionValue,
  ] = useState('')

  const [autoRenew, setAutoRenew] =
    useState(false)

  const [
    selectedModuleId,
    setSelectedModuleId,
  ] = useState('')

  const [
    moduleOrigin,
    setModuleOrigin,
  ] = useState<
    'AVULSO' | 'CORTESIA' | 'TRIAL'
  >('AVULSO')

  const [
    modulePeriod,
    setModulePeriod,
  ] = useState<
    'MENSAL' | 'ANUAL' | 'UNICO' | 'CORTESIA'
  >('MENSAL')

  const [
    moduleValue,
    setModuleValue,
  ] = useState('')

  const [
    orderModuleId,
    setOrderModuleId,
  ] = useState('')

  const [
    orderPeriod,
    setOrderPeriod,
  ] = useState<
    'MENSAL' | 'ANUAL' | 'UNICO'
  >('MENSAL')

  const [
    orderValue,
    setOrderValue,
  ] = useState('')

  const [
    orderPaymentMethod,
    setOrderPaymentMethod,
  ] = useState('')

  const [
    orderNotes,
    setOrderNotes,
  ] = useState('')

  const [actionBusy, setActionBusy] =
    useState(false)

  const [actionMessage, setActionMessage] =
    useState('')

  const [actionError, setActionError] =
    useState('')

  const [query, setQuery] = useState('')

  const [loading, setLoading] = useState(true)
  const [companyLoading, setCompanyLoading] =
    useState(false)

  const [error, setError] = useState('')

  const companyRestoreAttempted =
    useRef(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')

      try {
        const [
          adminMe,
          adminOverview,
          adminCompanies,
          adminPlans,
          adminModules,
        ] = await Promise.all([
          getAdminMe(),
          getAdminOverview(),
          getAdminCompanies(),
          getAdminPlans(),
          getAdminModulesCatalog(),
        ])

        if (cancelled) return

        setMe(adminMe)
        setOverview(adminOverview)
        setCompanies(adminCompanies.items)
        setPlans(adminPlans.items)
        setModuleCatalog(adminModules.items)
      } catch (err) {
        if (cancelled) return

        setError(
          err instanceof Error
            ? err.message
            : String(err),
        )
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem(
      'smarttec:admin-section',
      section,
    )
  }, [section])

  useEffect(() => {
    window.localStorage.setItem(
      'smarttec:admin-company-tab',
      companyTab,
    )
  }, [companyTab])

  useEffect(() => {
    if (loading) return

    if (companyRestoreAttempted.current) {
      return
    }

    companyRestoreAttempted.current = true

    if (section !== 'empresas') {
      return
    }

    const saved =
      window.localStorage.getItem(
        'smarttec:admin-company-id',
      )

    if (!saved) {
      return
    }

    const empresaId = Number(saved)

    if (
      !Number.isInteger(empresaId) ||
      empresaId <= 0
    ) {
      window.localStorage.removeItem(
        'smarttec:admin-company-id',
      )
      return
    }

    let cancelled = false

    setCompanyLoading(true)
    setError('')

    void getAdminCompany(empresaId)
      .then(data => {
        if (cancelled) return

        setCompany(data)
        setSection('empresas')
      })
      .catch(err => {
        if (cancelled) return

        window.localStorage.removeItem(
          'smarttec:admin-company-id',
        )

        setCompany(null)
        setCompanyTab('resumo')

        setError(
          err instanceof Error
            ? err.message
            : String(err),
        )
      })
      .finally(() => {
        if (!cancelled) {
          setCompanyLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [loading, section])

  const filteredCompanies = useMemo(() => {
    const term = query.trim().toLowerCase()

    if (!term) return companies

    return companies.filter(item =>
      [
        item.nome,
        item.nome_fantasia,
        item.documento,
        item.slug,
      ]
        .filter(Boolean)
        .some(value =>
          String(value).toLowerCase().includes(term),
        ),
    )
  }, [companies, query])

  async function openCompany(id: number) {
    setCompanyLoading(true)
    setError('')

    try {
      setCompany(await getAdminCompany(id))

      window.localStorage.setItem(
        'smarttec:admin-company-id',
        String(id),
      )

      setCompanyTab('resumo')
      setSection('empresas')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setCompanyLoading(false)
    }
  }

  async function createModuleOrder() {
    if (!company) return

    const moduloId = Number(orderModuleId)

    if (
      !Number.isInteger(moduloId) ||
      moduloId <= 0
    ) {
      setActionError(
        'Selecione o módulo do pedido.',
      )
      return
    }

    const valorTexto =
      orderValue.trim().replace(',', '.')

    const valor = Number(valorTexto)

    if (
      !Number.isFinite(valor) ||
      valor < 0
    ) {
      setActionError(
        'Informe um valor válido.',
      )
      return
    }

    setActionBusy(true)
    setActionError('')
    setActionMessage('')

    try {
      await createAdminModuleOrder(
        company.empresa.id,
        {
          modulo_id: moduloId,
          valor,
          periodicidade: orderPeriod,
          forma_pagamento:
            orderPaymentMethod.trim() || null,
          observacoes:
            orderNotes.trim() || null,
        },
      )

      setCompany(
        await getAdminCompany(
          company.empresa.id,
        ),
      )

      setOrderModuleId('')
      setOrderValue('')
      setOrderPaymentMethod('')
      setOrderNotes('')

      setActionMessage(
        'Pedido de módulo registrado.',
      )
    } catch (err) {
      setActionError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setActionBusy(false)
    }
  }

  async function changeModuleOrderStatus(
    pedidoId: number,
    nextStatus:
      | 'EM_ANALISE'
      | 'AGUARDANDO_PAGAMENTO'
      | 'PAGO'
      | 'ATIVADO'
      | 'CANCELADO',
  ) {
    if (!company) return

    setActionBusy(true)
    setActionError('')
    setActionMessage('')

    try {
      await updateAdminModuleOrderStatus(
        company.empresa.id,
        pedidoId,
        nextStatus,
      )

      setCompany(
        await getAdminCompany(
          company.empresa.id,
        ),
      )

      setActionMessage(
        nextStatus === 'ATIVADO'
          ? 'Pedido concluído e módulo ativado.'
          : 'Status do pedido atualizado.',
      )
    } catch (err) {
      setActionError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setActionBusy(false)
    }
  }

  function closeCompany() {
    window.localStorage.removeItem(
      'smarttec:admin-company-id',
    )

    setCompany(null)
    setCompanyTab('resumo')
  }


  async function refreshCompany() {
    if (!company) return

    const [
      freshCompany,
      freshOverview,
      freshCompanies,
    ] = await Promise.all([
      getAdminCompany(company.empresa.id),
      getAdminOverview(),
      getAdminCompanies(),
    ])

    setCompany(freshCompany)
    setOverview(freshOverview)
    setCompanies(freshCompanies.items)
  }

  async function runAdminAction(
    action: () => Promise<unknown>,
    successMessage: string,
  ) {
    setActionBusy(true)
    setActionError('')
    setActionMessage('')

    try {
      await action()
      await refreshCompany()
      setActionMessage(successMessage)
    } catch (err) {
      setActionError(
        err instanceof Error
          ? err.message
          : String(err),
      )
    } finally {
      setActionBusy(false)
    }
  }

  async function handleStartTrial() {
    if (!company) return

    await runAdminAction(
      () =>
        startAdminTrial(
          company.empresa.id,
          {
            plano_id:
              selectedPlanId
                ? Number(selectedPlanId)
                : null,
            dias: 7,
          },
        ),
      'Teste gratuito de 7 dias iniciado.',
    )
  }

  async function handleActivateSubscription() {
    if (!company) return

    if (!selectedPlanId) {
      setActionError(
        'Selecione um plano para ativar a assinatura.',
      )
      return
    }

    const parsed =
      subscriptionValue.trim()
        ? Number(
            subscriptionValue.replace(',', '.'),
          )
        : undefined

    await runAdminAction(
      () =>
        activateAdminSubscription(
          company.empresa.id,
          {
            plano_id: Number(selectedPlanId),
            periodicidade: subscriptionPeriod,
            valor:
              parsed !== undefined &&
              Number.isFinite(parsed)
                ? parsed
                : undefined,
            renovacao_automatica: autoRenew,
          },
        ),
      'Assinatura ativada com sucesso.',
    )
  }

  async function handleActivateModule() {
    if (!company) return

    if (!selectedModuleId) {
      setActionError(
        'Selecione um módulo.',
      )
      return
    }

    const parsed =
      moduleValue.trim()
        ? Number(
            moduleValue.replace(',', '.'),
          )
        : undefined

    const periodicidade =
      moduleOrigin === 'CORTESIA' ||
      moduleOrigin === 'TRIAL'
        ? 'CORTESIA'
        : modulePeriod

    await runAdminAction(
      () =>
        activateAdminModule(
          company.empresa.id,
          Number(selectedModuleId),
          {
            origem: moduleOrigin,
            periodicidade,
            valor:
              parsed !== undefined &&
              Number.isFinite(parsed)
                ? parsed
                : undefined,
          },
        ),
      'Módulo ativado com sucesso.',
    )
  }

  async function handleCancelModule(
    moduleCode: string,
  ) {
    if (!company) return

    const catalogModule =
      moduleCatalog.find(
        item => item.codigo === moduleCode,
      )

    if (!catalogModule) {
      setActionError(
        'Módulo não localizado no catálogo.',
      )
      return
    }

    await runAdminAction(
      () =>
        cancelAdminModule(
          company.empresa.id,
          catalogModule.id,
        ),
      'Módulo cancelado.',
    )
  }

  return (
    <section>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
          marginBottom: 18,
        }}
      >
        <div>
          <button
            type="button"
            onClick={onBack}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              border: 0,
              background: 'transparent',
              padding: 0,
              marginBottom: 12,
              color: '#6a7079',
              cursor: 'pointer',
            }}
          >
            <ChevronLeft size={16} />
            Voltar ao ERP
          </button>

          <p
            style={{
              margin: 0,
              fontSize: 12,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '.08em',
              color: '#d7282f',
            }}
          >
            Smart-tec Sistemas
          </p>

          <h1
            style={{
              margin: '5px 0 6px',
              fontSize: 'clamp(26px,3vw,38px)',
            }}
          >
            Administração da plataforma
          </h1>

          <p style={{ margin: 0, color: '#6f7680' }}>
            Controle central da operação Smart-tec.
          </p>
        </div>

        {me && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              background: '#111214',
              color: '#fff',
              borderRadius: 12,
              padding: '10px 14px',
            }}
          >
            <ShieldCheck size={18} />

            <div>
              <strong
                style={{
                  display: 'block',
                  fontSize: 13,
                }}
              >
                {me.user.nome}
              </strong>

              <span
                style={{
                  fontSize: 11,
                  opacity: .72,
                }}
              >
                {me.equipe.cargo_exibicao ||
                  me.equipe.funcao.nome}
              </span>
            </div>
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 8,
          marginBottom: 20,
        }}
      >
        <button
          type="button"
          onClick={() => {
            window.localStorage.removeItem(
              'smarttec:admin-company-id',
            )

            setSection('dashboard')
            setCompany(null)
          }}
          className={
            section === 'dashboard'
              ? 'primary-button'
              : 'secondary-button'
          }
        >
          Visão geral
        </button>

        <button
          type="button"
          onClick={() => {
            window.localStorage.removeItem(
              'smarttec:admin-company-id',
            )

            setSection('empresas')
            setCompany(null)
          }}
          className={
            section === 'empresas'
              ? 'primary-button'
              : 'secondary-button'
          }
        >
          Empresas
        </button>
      </div>

      {loading && (
        <div className="panel" style={{ padding: 22 }}>
          Carregando administração...
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            padding: 18,
            borderRadius: 12,
            background: '#fff1f1',
            color: '#9f1c22',
            border: '1px solid #f1c6c8',
            marginBottom: 18,
          }}
        >
          {error}
        </div>
      )}

      {!loading &&
        !error &&
        section === 'dashboard' &&
        overview && (
          <>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  'repeat(auto-fit,minmax(210px,1fr))',
                gap: 14,
              }}
            >
              <Metric
                label="Empresas ativas"
                value={overview.empresas_ativas}
                detail="Empresas atualmente ativas"
                icon={<Building2 size={18} />}
              />

              <Metric
                label="Testes gratuitos"
                value={overview.trials_ativos}
                detail="Trials de 7 dias ativos"
                icon={<Sparkles size={18} />}
              />

              <Metric
                label="Trials encerrando"
                value={
                  overview.trials_encerrando_em_7_dias
                }
                detail="Nos próximos 7 dias"
                icon={<CalendarClock size={18} />}
              />

              <Metric
                label="Renovações"
                value={overview.renovacoes_em_10_dias}
                detail="Nos próximos 10 dias"
                icon={<CalendarClock size={18} />}
              />

              <Metric
                label="Pedidos de módulos"
                value={
                  overview.pedidos_modulos_pendentes
                }
                detail="Pedidos em andamento"
                icon={<PackagePlus size={18} />}
              />

              <Metric
                label="Chamados"
                value={overview.chamados_abertos}
                detail="Suportes não encerrados"
                icon={<Headphones size={18} />}
              />

              <Metric
                label="Pagamentos"
                value={overview.pagamentos_pendentes}
                detail="Pendentes ou atrasados"
                icon={<CircleDollarSign size={18} />}
              />

              <Metric
                label="Notas fiscais"
                value={
                  overview.notas_fiscais_pendentes
                }
                detail="Pendentes ou com erro"
                icon={<FileText size={18} />}
              />
            </div>

            <div
              style={{
                marginTop: 18,
                display: 'grid',
                gridTemplateColumns:
                  'repeat(auto-fit,minmax(280px,1fr))',
                gap: 14,
              }}
            >
              <button
                type="button"
                onClick={() => setSection('empresas')}
                style={{
                  textAlign: 'left',
                  padding: 20,
                  border: 0,
                  background: '#111214',
                  color: '#fff',
                  borderRadius: 14,
                  cursor: 'pointer',
                }}
              >
                <Building2 size={20} />

                <h2
                  style={{
                    margin: '14px 0 6px',
                    fontSize: 18,
                  }}
                >
                  Empresas
                </h2>

                <p
                  style={{
                    margin: 0,
                    opacity: .7,
                    fontSize: 13,
                  }}
                >
                  Abra a ficha central de cada cliente.
                </p>
              </button>

              <article
                style={{
                  padding: 20,
                  background: '#fff',
                  border:
                    '1px solid #e7e9ed',
                  borderRadius: 14,
                }}
              >
                <Users size={20} />
                <h2
                  style={{
                    margin: '14px 0 6px',
                    fontSize: 18,
                  }}
                >
                  Equipe Smart-tec
                </h2>
                <p
                  style={{
                    margin: 0,
                    color: '#6f7680',
                    fontSize: 13,
                  }}
                >
                  Funcionários, funções e permissões.
                </p>
              </article>
            </div>
          </>
        )}

      {!loading &&
        section === 'empresas' &&
        !company && (
          <>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                marginBottom: 14,
              }}
            >
              <div>
                <h2 style={{ margin: 0 }}>
                  Empresas
                </h2>
                <p
                  style={{
                    margin: '4px 0 0',
                    color: '#747b85',
                    fontSize: 13,
                  }}
                >
                  {companies.length} empresa(s)
                  cadastrada(s)
                </p>
              </div>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '9px 12px',
                  background: '#fff',
                  border: '1px solid #dfe3e8',
                  borderRadius: 10,
                  minWidth: 260,
                }}
              >
                <Search size={16} />
                <input
                  value={query}
                  onChange={e =>
                    setQuery(e.target.value)
                  }
                  placeholder="Buscar empresa"
                  style={{
                    border: 0,
                    outline: 0,
                    width: '100%',
                    background: 'transparent',
                  }}
                />
              </label>
            </div>

            <div
              style={{
                background: '#fff',
                border: '1px solid #e7e9ed',
                borderRadius: 14,
                overflow: 'hidden',
              }}
            >
              {filteredCompanies.map(item => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() =>
                    void openCompany(item.id)
                  }
                  onMouseEnter={event => {
                    event.currentTarget.style.background =
                      '#f7f8fa'
                  }}
                  onMouseLeave={event => {
                    event.currentTarget.style.background =
                      '#fff'
                  }}
                  style={{
                    width: '100%',
                    border: 0,
                    borderBottom:
                      '1px solid #eef0f2',
                    background: '#fff',
                    padding: 16,
                    cursor: 'pointer',
                    textAlign: 'left',
                    display: 'grid',
                    gridTemplateColumns:
                      'minmax(220px,2fr) repeat(4,minmax(90px,1fr)) auto',
                    gap: 16,
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <strong
                      style={{
                        display: 'block',
                        marginBottom: 3,
                      }}
                    >
                      {item.nome_fantasia ||
                        item.nome}
                    </strong>

                    <span
                      style={{
                        color: '#7b828c',
                        fontSize: 12,
                      }}
                    >
                      {item.documento ||
                        `Empresa #${item.id}`}
                    </span>
                  </div>

                  <div>
                    <small>Status</small>
                    <br />
                    <StatusBadge>
                      {item.status}
                    </StatusBadge>
                  </div>

                  <div>
                    <small>Plano</small>
                    <br />
                    <strong>
                      {item.assinatura_status ||
                        'Sem assinatura'}
                    </strong>
                  </div>

                  <div>
                    <small>Módulos</small>
                    <br />
                    <strong>
                      {item.modulos_ativos}
                    </strong>
                  </div>

                  <div>
                    <small>Suporte</small>
                    <br />
                    <strong>
                      {item.chamados_abertos}
                    </strong>
                  </div>
                
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'flex-end',
                      gap: 6,
                      color: '#d7282f',
                      fontSize: 12,
                      fontWeight: 700,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    Abrir ficha
                    <ChevronRight size={16} />
                  </span>
</button>
              ))}

              {!filteredCompanies.length && (
                <div
                  style={{
                    padding: 24,
                    color: '#777f89',
                  }}
                >
                  Nenhuma empresa encontrada.
                </div>
              )}
            </div>
          </>
        )}

      {actionMessage && (
        <div
          style={{
            marginBottom: 14,
            padding: '12px 14px',
            borderRadius: 10,
            background: '#edf8f0',
            border: '1px solid #cce8d2',
            color: '#276738',
          }}
        >
          {actionMessage}
        </div>
      )}

      {actionError && (
        <div
          role="alert"
          style={{
            marginBottom: 14,
            padding: '12px 14px',
            borderRadius: 10,
            background: '#fff1f1',
            border: '1px solid #efc8ca',
            color: '#9f1c22',
          }}
        >
          {actionError}
        </div>
      )}

      {companyLoading && (
        <div className="panel" style={{ padding: 22 }}>
          Carregando empresa...
        </div>
      )}

      {!companyLoading && company && (
        <>
          <button
            type="button"
            onClick={closeCompany}
            style={{
              border: 0,
              background: 'transparent',
              padding: 0,
              marginBottom: 14,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              cursor: 'pointer',
              color: '#626a74',
            }}
          >
            <ChevronLeft size={16} />
            Voltar para empresas
          </button>

          <div
            style={{
              background: '#fff',
              border: '1px solid #e7e9ed',
              borderRadius: 14,
              padding: 20,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 20,
              }}
            >
              <div>
                <p
                  style={{
                    margin: 0,
                    color: '#d7282f',
                    fontSize: 11,
                    fontWeight: 800,
                    textTransform: 'uppercase',
                  }}
                >
                  Empresa #{company.empresa.id}
                </p>

                <h2
                  style={{
                    margin: '5px 0 4px',
                    fontSize: 26,
                  }}
                >
                  {company.empresa.nome_fantasia ||
                    company.empresa.nome}
                </h2>

                <p
                  style={{
                    margin: 0,
                    color: '#747b85',
                  }}
                >
                  {company.empresa.documento ||
                    'Documento não informado'}
                </p>
              </div>

              <StatusBadge>
                {company.empresa.status}
              </StatusBadge>
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns:
                'repeat(auto-fit,minmax(180px,1fr))',
              gap: 12,
              marginBottom: 16,
            }}
          >
            <Metric
              label="Módulos ativos"
              value={company.resumo.modulos_ativos}
              detail="Acessos comerciais ativos"
              icon={<Package size={18} />}
            />

            <Metric
              label="Chamados"
              value={company.resumo.chamados_abertos}
              detail="Ainda em atendimento"
              icon={<Headphones size={18} />}
            />

            <Metric
              label="Pagamentos"
              value={
                company.resumo.pagamentos_pendentes
              }
              detail="Pendências financeiras"
              icon={<CircleDollarSign size={18} />}
            />

            <Metric
              label="Notas fiscais"
              value={company.resumo.notas_pendentes}
              detail="Pendentes ou com erro"
              icon={<FileText size={18} />}
            />
          </div>

                    <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
              marginBottom: 14,
            }}
          >
            {[
              ['resumo', 'Resumo'],
              ['assinatura', 'Assinatura'],
              ['modulos', 'Módulos'],
              ['pedidos', 'Pedidos'],
              ['financeiro', 'Financeiro'],
              ['fiscal', 'Notas fiscais'],
              ['suporte', 'Suporte'],
              ['comercial', 'Comercial'],
              ['historico', 'Histórico'],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() =>
                  setCompanyTab(id as CompanyTab)
                }
                className={
                  companyTab === id
                    ? 'primary-button'
                    : 'secondary-button'
                }
              >
                {label}
              </button>
            ))}
          </div>

          {companyTab === 'resumo' && (
<div
            style={{
              display: 'grid',
              gridTemplateColumns:
                'repeat(auto-fit,minmax(300px,1fr))',
              gap: 14,
            }}
          >
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Assinatura
              </h3>

              {company.assinatura ? (
                <div
                  style={{
                    display: 'grid',
                    gap: 9,
                    fontSize: 13,
                  }}
                >
                  <div>
                    <span>Plano</span>
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {company.assinatura.plano_nome ||
                        company.assinatura.plano_codigo ||
                        'Plano não informado'}
                    </strong>
                  </div>

                  <div>
                    <span>Status</span>
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {company.assinatura.status}
                    </strong>
                  </div>

                  <div>
                    <span>Periodicidade</span>
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {company.assinatura
                        .periodicidade || '—'}
                    </strong>
                  </div>

                  <div>
                    <span>Valor</span>
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {money(
                        company.assinatura.valor,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>Fim do trial</span>
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {date(
                        company.assinatura
                          .data_fim_trial,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>Vencimento</span>
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {date(
                        company.assinatura
                          .data_vencimento,
                      )}
                    </strong>
                  </div>
                </div>
              ) : (
                <p
                  style={{
                    color: '#777f89',
                    marginBottom: 0,
                  }}
                >
                  Nenhuma assinatura cadastrada.
                </p>
              )}
            </article>

            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Usuários
              </h3>

              {company.usuarios.length ? (
                company.usuarios.map(user => (
                  <div
                    key={user.id}
                    style={{
                      padding: '10px 0',
                      borderBottom:
                        '1px solid #eceff2',
                    }}
                  >
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {user.nome}
                    </strong>

                    <span
                      style={{
                        display: 'block',
                        fontSize: 12,
                        color: '#777f89',
                      }}
                    >
                      {user.email}
                    </span>

                    <small>
                      {user.papel} ·{' '}
                      {user.ativo
                        ? 'Ativo'
                        : 'Inativo'}
                    </small>
                  </div>
                ))
              ) : (
                <p>Nenhum usuário vinculado.</p>
              )}
            </article>

            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Módulos
              </h3>

              {company.modulos.length ? (
                company.modulos.map(modulo => (
                  <div
                    key={modulo.id}
                    style={{
                      padding: '10px 0',
                      borderBottom:
                        '1px solid #eceff2',
                    }}
                  >
                    <strong
                      style={{
                        display: 'block',
                      }}
                    >
                      {modulo.nome}
                    </strong>

                    <small>
                      {modulo.origem} ·{' '}
                      {modulo.status}
                    </small>
                  </div>
                ))
              ) : (
                <p
                  style={{
                    color: '#777f89',
                  }}
                >
                  Nenhum módulo SaaS ativo.
                </p>
              )}
            </article>
          </div>
          )}


          

          {companyTab === 'assinatura' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Assinatura e trial
              </h3>


              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    'repeat(auto-fit,minmax(190px,1fr))',
                  gap: 12,
                  padding: 14,
                  marginBottom: 18,
                  background: '#f7f8f9',
                  borderRadius: 12,
                  border: '1px solid #e7e9ed',
                }}
              >
                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Plano
                  </span>

                  <select
                    value={selectedPlanId}
                    onChange={event => {
                      const value =
                        event.target.value

                      setSelectedPlanId(value)

                      const plan =
                        plans.find(
                          item =>
                            item.id ===
                            Number(value),
                        )

                      if (
                        plan?.periodicidade ===
                        'MENSAL'
                      ) {
                        setSubscriptionPeriod(
                          'MENSAL',
                        )
                      }

                      if (
                        plan?.periodicidade ===
                        'ANUAL'
                      ) {
                        setSubscriptionPeriod(
                          'ANUAL',
                        )
                      }

                      if (plan?.valor != null) {
                        setSubscriptionValue(
                          String(plan.valor),
                        )
                      }
                    }}
                    style={{
                      width: '100%',
                      minHeight: 40,
                    }}
                  >
                    <option value="">
                      Sem plano definido
                    </option>

                    {plans
                      .filter(
                        item => item.ativo,
                      )
                      .map(plan => (
                        <option
                          key={plan.id}
                          value={plan.id}
                        >
                          {plan.nome}
                          {' · '}
                          {plan.periodicidade}
                        </option>
                      ))}
                  </select>
                </label>

                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Periodicidade
                  </span>

                  <select
                    value={
                      subscriptionPeriod
                    }
                    onChange={event =>
                      setSubscriptionPeriod(
                        event.target.value as
                          | 'MENSAL'
                          | 'ANUAL',
                      )
                    }
                    style={{
                      width: '100%',
                      minHeight: 40,
                    }}
                  >
                    <option value="MENSAL">
                      Mensal
                    </option>

                    <option value="ANUAL">
                      Anual
                    </option>
                  </select>
                </label>

                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Valor
                  </span>

                  <input
                    value={subscriptionValue}
                    onChange={event =>
                      setSubscriptionValue(
                        event.target.value,
                      )
                    }
                    placeholder="0,00"
                    inputMode="decimal"
                    style={{
                      width: '100%',
                      minHeight: 40,
                      boxSizing: 'border-box',
                    }}
                  />
                </label>

                <label
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    minHeight: 40,
                    alignSelf: 'end',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={autoRenew}
                    onChange={event =>
                      setAutoRenew(
                        event.target.checked,
                      )
                    }
                  />

                  Renovação automática
                </label>

                <div
                  style={{
                    gridColumn: '1 / -1',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 8,
                  }}
                >
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={
                      actionBusy ||
                      company.assinatura
                        ?.status === 'TRIAL' ||
                      company.assinatura
                        ?.status === 'ATIVA' ||
                      company.assinatura
                        ?.status ===
                          'PROXIMA_VENCIMENTO'
                    }
                    onClick={() =>
                      void handleStartTrial()
                    }
                  >
                    Iniciar teste grátis — 7 dias
                  </button>

                  <button
                    type="button"
                    className="primary-button"
                    disabled={
                      actionBusy ||
                      !selectedPlanId ||
                      company.assinatura
                        ?.status === 'ATIVA' ||
                      company.assinatura
                        ?.status ===
                          'PROXIMA_VENCIMENTO'
                    }
                    onClick={() =>
                      void handleActivateSubscription()
                    }
                  >
                    Ativar assinatura
                  </button>
                </div>

                {!plans.length && (
                  <div
                    style={{
                      gridColumn: '1 / -1',
                      fontSize: 12,
                      color: '#747b85',
                    }}
                  >
                    Nenhum plano comercial
                    cadastrado ainda. O trial
                    de 7 dias pode ser iniciado
                    sem plano.
                  </div>
                )}
              </div>

              {company.assinatura ? (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns:
                      'repeat(auto-fit,minmax(190px,1fr))',
                    gap: 18,
                  }}
                >
                  {[
                    [
                      'Plano',
                      company.assinatura.plano_nome ||
                        company.assinatura.plano_codigo ||
                        'Não informado',
                    ],
                    ['Status', company.assinatura.status],
                    [
                      'Periodicidade',
                      company.assinatura.periodicidade || '—',
                    ],
                    [
                      'Valor',
                      money(company.assinatura.valor),
                    ],
                    [
                      'Início do trial',
                      date(
                        company.assinatura.data_inicio_trial,
                      ),
                    ],
                    [
                      'Fim do trial',
                      date(
                        company.assinatura.data_fim_trial,
                      ),
                    ],
                    [
                      'Início da assinatura',
                      date(
                        company.assinatura
                          .data_inicio_assinatura,
                      ),
                    ],
                    [
                      'Vencimento',
                      date(
                        company.assinatura.data_vencimento,
                      ),
                    ],
                    [
                      'Aviso de renovação',
                      `${company.assinatura
                        .dias_aviso_vencimento} dias`,
                    ],
                    [
                      'Renovação automática',
                      company.assinatura.renovacao_automatica
                        ? 'Sim'
                        : 'Não',
                    ],
                  ].map(([label, value]) => (
                    <div key={String(label)}>
                      <span>{label}</span>
                      <strong
                        style={{
                          display: 'block',
                          marginTop: 3,
                        }}
                      >
                        {value}
                      </strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: '#777f89' }}>
                  Nenhuma assinatura ou trial cadastrado.
                </p>
              )}
            </article>
          )}

          {companyTab === 'modulos' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Módulos
              </h3>


              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    'minmax(210px,2fr) repeat(3,minmax(140px,1fr)) auto',
                  gap: 10,
                  alignItems: 'end',
                  padding: 14,
                  marginBottom: 18,
                  background: '#f7f8f9',
                  borderRadius: 12,
                  border: '1px solid #e7e9ed',
                }}
              >
                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Módulo
                  </span>

                  <select
                    value={selectedModuleId}
                    onChange={event =>
                      setSelectedModuleId(
                        event.target.value,
                      )
                    }
                    style={{
                      width: '100%',
                      minHeight: 40,
                    }}
                  >
                    <option value="">
                      Selecione
                    </option>

                    {moduleCatalog
                      .filter(
                        item => item.ativo,
                      )
                      .map(modulo => (
                        <option
                          key={modulo.id}
                          value={modulo.id}
                        >
                          {modulo.nome}
                        </option>
                      ))}
                  </select>
                </label>

                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Origem
                  </span>

                  <select
                    value={moduleOrigin}
                    onChange={event =>
                      setModuleOrigin(
                        event.target.value as
                          | 'AVULSO'
                          | 'CORTESIA'
                          | 'TRIAL',
                      )
                    }
                    style={{
                      width: '100%',
                      minHeight: 40,
                    }}
                  >
                    <option value="AVULSO">
                      Avulso
                    </option>

                    <option value="CORTESIA">
                      Cortesia
                    </option>

                    <option value="TRIAL">
                      Trial
                    </option>
                  </select>
                </label>

                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Periodicidade
                  </span>

                  <select
                    value={
                      moduleOrigin ===
                        'CORTESIA' ||
                      moduleOrigin ===
                        'TRIAL'
                        ? 'CORTESIA'
                        : modulePeriod
                    }
                    disabled={
                      moduleOrigin ===
                        'CORTESIA' ||
                      moduleOrigin ===
                        'TRIAL'
                    }
                    onChange={event =>
                      setModulePeriod(
                        event.target.value as
                          | 'MENSAL'
                          | 'ANUAL'
                          | 'UNICO'
                          | 'CORTESIA',
                      )
                    }
                    style={{
                      width: '100%',
                      minHeight: 40,
                    }}
                  >
                    <option value="MENSAL">
                      Mensal
                    </option>

                    <option value="ANUAL">
                      Anual
                    </option>

                    <option value="UNICO">
                      Único
                    </option>

                    <option value="CORTESIA">
                      Cortesia
                    </option>
                  </select>
                </label>

                <label>
                  <span
                    style={{
                      display: 'block',
                      fontSize: 12,
                      marginBottom: 5,
                    }}
                  >
                    Valor
                  </span>

                  <input
                    value={moduleValue}
                    disabled={
                      moduleOrigin ===
                        'CORTESIA' ||
                      moduleOrigin ===
                        'TRIAL'
                    }
                    onChange={event =>
                      setModuleValue(
                        event.target.value,
                      )
                    }
                    placeholder="0,00"
                    inputMode="decimal"
                    style={{
                      width: '100%',
                      minHeight: 40,
                      boxSizing: 'border-box',
                    }}
                  />
                </label>

                <button
                  type="button"
                  className="primary-button"
                  disabled={
                    actionBusy ||
                    !selectedModuleId
                  }
                  onClick={() =>
                    void handleActivateModule()
                  }
                >
                  Ativar módulo
                </button>
              </div>

              {company.modulos.length ? (
                <div>
                  {company.modulos.map(modulo => (
                    <div
                      key={modulo.id}
                      style={{
                        display: 'grid',
                        gridTemplateColumns:
                          'minmax(190px,2fr) repeat(4,minmax(90px,1fr)) auto',
                        gap: 14,
                        padding: '12px 0',
                        borderBottom:
                          '1px solid #eceff2',
                      }}
                    >
                      <strong>{modulo.nome}</strong>
                      <span>
                        {modulo.origem}
                        {modulo.data_fim
                          ? ` · até ${date(modulo.data_fim)}`
                          : ''}
                      </span>
                      <span>{modulo.status}</span>
                      <span>
                        {modulo.periodicidade || '—'}
                      </span>
                      <span>{money(modulo.valor)}</span>

                      <button
                        type="button"
                        className="secondary-button"
                        disabled={
                          actionBusy ||
                          modulo.status !== 'ATIVO'
                        }
                        onClick={() =>
                          void handleCancelModule(
                            modulo.codigo,
                          )
                        }
                      >
                        Cancelar
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: '#777f89' }}>
                  Nenhum módulo cadastrado.
                </p>
              )}
            </article>
          )}

          {companyTab === 'pedidos' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Pedidos de módulos
              </h3>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    'minmax(180px, 1.5fr) repeat(2, minmax(120px, 0.8fr)) minmax(150px, 1fr)',
                  gap: 10,
                  alignItems: 'end',
                  padding: 14,
                  marginBottom: 16,
                  border: '1px solid #e3e6e9',
                  borderRadius: 14,
                  background: '#fafbfc',
                }}
              >
                <label>
                  <span style={{ fontSize: 12 }}>
                    Módulo
                  </span>

                  <select
                    value={orderModuleId}
                    onChange={event =>
                      setOrderModuleId(
                        event.target.value,
                      )
                    }
                    style={{
                      width: '100%',
                      minHeight: 40,
                      marginTop: 5,
                    }}
                  >
                    <option value="">
                      Selecione
                    </option>

                    {moduleCatalog
                      .filter(item => item.ativo)
                      .map(item => (
                        <option
                          key={item.id}
                          value={item.id}
                        >
                          {item.nome}
                        </option>
                      ))}
                  </select>
                </label>

                <label>
                  <span style={{ fontSize: 12 }}>
                    Periodicidade
                  </span>

                  <select
                    value={orderPeriod}
                    onChange={event =>
                      setOrderPeriod(
                        event.target.value as
                          | 'MENSAL'
                          | 'ANUAL'
                          | 'UNICO',
                      )
                    }
                    style={{
                      width: '100%',
                      minHeight: 40,
                      marginTop: 5,
                    }}
                  >
                    <option value="MENSAL">
                      Mensal
                    </option>
                    <option value="ANUAL">
                      Anual
                    </option>
                    <option value="UNICO">
                      Pagamento único
                    </option>
                  </select>
                </label>

                <label>
                  <span style={{ fontSize: 12 }}>
                    Valor
                  </span>

                  <input
                    value={orderValue}
                    onChange={event =>
                      setOrderValue(
                        event.target.value,
                      )
                    }
                    placeholder="0,00"
                    inputMode="decimal"
                    style={{
                      width: '100%',
                      minHeight: 40,
                      marginTop: 5,
                    }}
                  />
                </label>

                <label>
                  <span style={{ fontSize: 12 }}>
                    Forma de pagamento
                  </span>

                  <input
                    value={orderPaymentMethod}
                    onChange={event =>
                      setOrderPaymentMethod(
                        event.target.value,
                      )
                    }
                    placeholder="Ex.: Banco Inter"
                    style={{
                      width: '100%',
                      minHeight: 40,
                      marginTop: 5,
                    }}
                  />
                </label>

                <label
                  style={{
                    gridColumn: '1 / -2',
                  }}
                >
                  <span style={{ fontSize: 12 }}>
                    Observações
                  </span>

                  <input
                    value={orderNotes}
                    onChange={event =>
                      setOrderNotes(
                        event.target.value,
                      )
                    }
                    placeholder="Observação comercial opcional"
                    style={{
                      width: '100%',
                      minHeight: 40,
                      marginTop: 5,
                    }}
                  />
                </label>

                <button
                  type="button"
                  disabled={actionBusy}
                  onClick={() =>
                    void createModuleOrder()
                  }
                  style={{
                    minHeight: 40,
                  }}
                >
                  Registrar pedido
                </button>
              </div>

              {company.pedidos_modulos.length ? (
                <div
                  style={{
                    display: 'grid',
                    gap: 10,
                  }}
                >
                  {company.pedidos_modulos.map(
                    pedido => (
                      <div
                        key={pedido.id}
                        style={{
                          padding: 14,
                          border:
                            '1px solid #e3e6e9',
                          borderRadius: 14,
                          display: 'grid',
                          gap: 10,
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent:
                              'space-between',
                            gap: 12,
                            flexWrap: 'wrap',
                          }}
                        >
                          <div>
                            <strong>
                              {pedido.modulo_nome}
                            </strong>

                            <div
                              style={{
                                marginTop: 4,
                                fontSize: 12,
                                color: '#777f89',
                              }}
                            >
                              Pedido #{pedido.id}
                              {' · '}
                              {pedido.periodicidade ??
                                '—'}
                              {' · '}
                              {money(
                                pedido.valor,
                              )}
                            </div>
                          </div>

                          <StatusBadge>
                            {pedido.status
                              .replaceAll('_', ' ')}
                          </StatusBadge>
                        </div>

                        <div
                          style={{
                            display: 'flex',
                            gap: 16,
                            flexWrap: 'wrap',
                            fontSize: 12,
                            color: '#626a73',
                          }}
                        >
                          <span>
                            Pagamento:{' '}
                            {pedido.forma_pagamento ||
                              'não informado'}
                          </span>

                          <span>
                            Responsável:{' '}
                            {pedido.responsavel_nome?.trim() ||
                              'não informado'}
                          </span>

                          <span>
                            Pedido:{' '}
                            {date(
                              pedido.data_pedido.slice(
                                0,
                                10,
                              ),
                            )}
                          </span>
                        </div>

                        {pedido.observacoes && (
                          <div
                            style={{
                              fontSize: 12,
                              color: '#626a73',
                            }}
                          >
                            {pedido.observacoes}
                          </div>
                        )}

                        <div
                          style={{
                            display: 'flex',
                            gap: 8,
                            flexWrap: 'wrap',
                          }}
                        >
                          {pedido.status ===
                            'SOLICITADO' && (
                            <button
                              type="button"
                              disabled={actionBusy}
                              onClick={() =>
                                void changeModuleOrderStatus(
                                  pedido.id,
                                  'EM_ANALISE',
                                )
                              }
                            >
                              Iniciar análise
                            </button>
                          )}

                          {pedido.status ===
                            'EM_ANALISE' && (
                            <button
                              type="button"
                              disabled={actionBusy}
                              onClick={() =>
                                void changeModuleOrderStatus(
                                  pedido.id,
                                  'AGUARDANDO_PAGAMENTO',
                                )
                              }
                            >
                              Aprovar
                            </button>
                          )}

                          {pedido.status ===
                            'AGUARDANDO_PAGAMENTO' && (
                            <button
                              type="button"
                              disabled={actionBusy}
                              onClick={() =>
                                void changeModuleOrderStatus(
                                  pedido.id,
                                  'PAGO',
                                )
                              }
                            >
                              Confirmar pagamento
                            </button>
                          )}

                          {pedido.status ===
                            'PAGO' && (
                            <button
                              type="button"
                              disabled={actionBusy}
                              onClick={() =>
                                void changeModuleOrderStatus(
                                  pedido.id,
                                  'ATIVADO',
                                )
                              }
                            >
                              Ativar módulo
                            </button>
                          )}

                          {[
                            'SOLICITADO',
                            'EM_ANALISE',
                            'AGUARDANDO_PAGAMENTO',
                          ].includes(
                            pedido.status,
                          ) && (
                            <button
                              type="button"
                              disabled={actionBusy}
                              onClick={() =>
                                void changeModuleOrderStatus(
                                  pedido.id,
                                  'CANCELADO',
                                )
                              }
                            >
                              Cancelar
                            </button>
                          )}
                        </div>
                      </div>
                    ),
                  )}
                </div>
              ) : (
                <p style={{ color: '#777f89' }}>
                  Nenhum pedido de módulo registrado.
                </p>
              )}
            </article>
          )}

          {companyTab === 'financeiro' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Financeiro
              </h3>

              {company.pagamentos.length ? (
                <div
                  style={{
                    display: 'grid',
                    gap: 10,
                  }}
                >
                  {company.pagamentos.map(
                    pagamento => (
                      <div
                        key={pagamento.id}
                        style={{
                          padding: 14,
                          border:
                            '1px solid #e3e6e9',
                          borderRadius: 14,
                          display: 'grid',
                          gap: 10,
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent:
                              'space-between',
                            alignItems: 'center',
                            gap: 12,
                            flexWrap: 'wrap',
                          }}
                        >
                          <div>
                            <strong>
                              Pagamento #{pagamento.id}
                            </strong>

                            {pagamento.pedido_modulo_id && (
                              <div
                                style={{
                                  marginTop: 4,
                                  fontSize: 12,
                                  color: '#777f89',
                                }}
                              >
                                Pedido de módulo #
                                {pagamento.pedido_modulo_id}
                              </div>
                            )}
                          </div>

                          <StatusBadge>
                            {pagamento.status.replaceAll(
                              '_',
                              ' ',
                            )}
                          </StatusBadge>
                        </div>

                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns:
                              'repeat(auto-fit, minmax(140px, 1fr))',
                            gap: 12,
                          }}
                        >
                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Tipo
                            </div>
                            <strong>
                              {pagamento.tipo.replaceAll(
                                '_',
                                ' ',
                              )}
                            </strong>
                          </div>

                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Valor
                            </div>
                            <strong>
                              {money(pagamento.valor)}
                            </strong>
                          </div>

                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Forma de pagamento
                            </div>
                            <strong>
                              {pagamento.forma_pagamento ||
                                'Não informada'}
                            </strong>
                          </div>

                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Pago em
                            </div>
                            <strong>
                              {pagamento.pago_em
                                ? date(
                                    pagamento.pago_em.slice(
                                      0,
                                      10,
                                    ),
                                  )
                                : '—'}
                            </strong>
                          </div>
                        </div>

                        {pagamento.observacoes && (
                          <div
                            style={{
                              fontSize: 12,
                              color: '#626a73',
                            }}
                          >
                            {pagamento.observacoes}
                          </div>
                        )}
                      </div>
                    ),
                  )}
                </div>
              ) : (
                <p style={{ color: '#777f89' }}>
                  Nenhum pagamento registrado.
                </p>
              )}
            </article>
          )}

          {companyTab === 'fiscal' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Notas fiscais
              </h3>

              <p
                style={{
                  marginTop: -4,
                  marginBottom: 16,
                  color: '#777f89',
                  fontSize: 12,
                }}
              >
                Registros pendentes ainda não representam
                emissão na prefeitura.
              </p>

              {company.notas_fiscais.length ? (
                <div
                  style={{
                    display: 'grid',
                    gap: 10,
                  }}
                >
                  {company.notas_fiscais.map(
                    nota => (
                      <div
                        key={nota.id}
                        style={{
                          padding: 14,
                          border:
                            '1px solid #e3e6e9',
                          borderRadius: 14,
                          display: 'grid',
                          gap: 10,
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent:
                              'space-between',
                            alignItems: 'center',
                            gap: 12,
                            flexWrap: 'wrap',
                          }}
                        >
                          <div>
                            <strong>
                              {nota.tipo_documento}{' '}
                              #{nota.id}
                            </strong>

                            {nota.pagamento_id && (
                              <div
                                style={{
                                  marginTop: 4,
                                  fontSize: 12,
                                  color: '#777f89',
                                }}
                              >
                                Pagamento #
                                {nota.pagamento_id}
                              </div>
                            )}
                          </div>

                          <StatusBadge>
                            {nota.status.replaceAll(
                              '_',
                              ' ',
                            )}
                          </StatusBadge>
                        </div>

                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns:
                              'repeat(auto-fit, minmax(140px, 1fr))',
                            gap: 12,
                          }}
                        >
                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Valor do serviço
                            </div>
                            <strong>
                              {money(
                                nota.valor_servico,
                              )}
                            </strong>
                          </div>

                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Desconto
                            </div>
                            <strong>
                              {money(
                                nota.valor_desconto,
                              )}
                            </strong>
                          </div>

                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Total
                            </div>
                            <strong>
                              {money(nota.valor_total)}
                            </strong>
                          </div>

                          <div>
                            <div
                              style={{
                                fontSize: 11,
                                color: '#777f89',
                              }}
                            >
                              Emissão
                            </div>
                            <strong>
                              {nota.data_emissao
                                ? date(
                                    nota.data_emissao.slice(
                                      0,
                                      10,
                                    ),
                                  )
                                : 'Pendente'}
                            </strong>
                          </div>
                        </div>

                        {nota.descricao_servico && (
                          <div
                            style={{
                              fontSize: 12,
                              color: '#626a73',
                            }}
                          >
                            {nota.descricao_servico}
                          </div>
                        )}

                        {nota.numero && (
                          <div
                            style={{
                              fontSize: 12,
                              color: '#626a73',
                            }}
                          >
                            Número: {nota.numero}
                            {nota.serie
                              ? ` · Série ${nota.serie}`
                              : ''}
                          </div>
                        )}

                        {nota.erro_mensagem && (
                          <div
                            style={{
                              fontSize: 12,
                              color: '#b42318',
                            }}
                          >
                            {nota.erro_mensagem}
                          </div>
                        )}
                      </div>
                    ),
                  )}
                </div>
              ) : (
                <p style={{ color: '#777f89' }}>
                  Nenhuma nota fiscal registrada.
                </p>
              )}
            </article>
          )}

          {companyTab === 'suporte' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Suporte
              </h3>
              <AdminRecordList
                items={company.chamados}
                emptyText="Nenhum chamado registrado."
              />
            </article>
          )}

          {companyTab === 'comercial' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Acompanhamento comercial
              </h3>
              <AdminRecordList
                items={company.acompanhamento_comercial}
                emptyText="Nenhum acompanhamento comercial registrado."
              />
            </article>
          )}

          {companyTab === 'historico' && (
            <article className="panel" style={{ padding: 20 }}>
              <h3 style={{ marginTop: 0 }}>
                Histórico e auditoria
              </h3>

              {company.historico.length ? (
                company.historico.map(item => (
                  <div
                    key={item.id}
                    style={{
                      padding: '12px 0',
                      borderBottom:
                        '1px solid #eceff2',
                    }}
                  >
                    <strong
                      style={{ display: 'block' }}
                    >
                      {item.acao}
                    </strong>

                    <span
                      style={{
                        display: 'block',
                        marginTop: 3,
                        color: '#727983',
                        fontSize: 12,
                      }}
                    >
                      {item.usuario_nome || 'Sistema'}
                      {' · '}
                      {new Intl.DateTimeFormat(
                        'pt-BR',
                        {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        },
                      ).format(
                        new Date(item.criado_em),
                      )}
                    </span>

                    {item.recurso && (
                      <small>
                        {item.recurso}
                        {item.recurso_id
                          ? ` #${item.recurso_id}`
                          : ''}
                      </small>
                    )}
                  </div>
                ))
              ) : (
                <p style={{ color: '#777f89' }}>
                  Nenhum evento de auditoria vinculado
                  a esta empresa.
                </p>
              )}
            </article>
          )}

        </>
      )}
    </section>
  )
}