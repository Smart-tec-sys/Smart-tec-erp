import { useEffect, useState } from 'react'
import {
    AlertCircle,
    ArrowDownRight,
    ArrowUpRight,

    CalendarDays,
    ChevronLeft,
    ChevronRight,
    CircleDollarSign,
    ClipboardList,
    Clock3,
    FileBarChart,
    FileText,
    Gauge,
    Home,
    Inbox,
    Layers3,
    LayoutGrid,
    Menu,
    Package,
    Plus,
    Search,
    Settings,
    ShoppingCart,
    SlidersHorizontal,
    Sparkles,
    Truck,
    Users,
    WalletCards,
    Wrench,
    X,
} from 'lucide-react'
import type { Metric, RecentQuote } from './types/dashboard'
import { BudgetsPage } from './pages/BudgetsPage'
import { NewBudgetPage } from './pages/NewBudgetPage'
import { ProductsPage } from './pages/ProductsPage'
import { CadastrosPage, type CadastroEntity } from './pages/CadastrosPage'
import { MyProfilePage } from './pages/MyProfilePage'
import { SettingsPage } from './pages/SettingsPage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'
import { getAdminMe } from './services/admin'
import { useAuthSession } from './components/AuthGate'
import { clearAuthSession } from './services/auth'
import { HeaderAgenda } from "./components/HeaderAgenda"
import { HeaderNotifications } from "./components/HeaderNotifications"
import { AgendaPage } from './pages/AgendaPage'
import { useAgendaHoje } from './hooks/useAgendaHoje'
import { useBudgetNotifications } from './hooks/useBudgetNotifications'
import { useStockNotifications } from './hooks/useStockNotifications'


const formatUserRole = (role?: string | null) => {
  switch (role) {
    case 'OWNER':
      return 'Proprietário'
    case 'ADMIN':
      return 'Administrador'
    case 'USUARIO':
      return 'Usuário'
    default:
      return role || 'Usuário'
  }
}
const metrics: Metric[] = [
    { label: 'A receber', value: 'R$ 84.720', delta: '+12,8%', trend: 'up', tone: 'red' },
    { label: 'A pagar', value: 'R$ 31.480', delta: '-4,2%', trend: 'down', tone: 'dark' },
    { label: 'Vendas do mês', value: 'R$ 128.940', delta: '+18,4%', trend: 'up', tone: 'green' },
    { label: 'Orçamentos em aberto', value: '28', delta: '+6 hoje', trend: 'up', tone: 'gold' },
]

const recentQuotes: RecentQuote[] = [
    { id: '#1048', client: 'Marina Azevedo', detail: 'Rolô BK Denver · 3 itens', value: 'R$ 8.460', status: 'Em aberto', date: 'Hoje, 09:42' },
    { id: '#1047', client: 'Ateliê Linha Clara', detail: 'Romana Nápoles · 5 itens', value: 'R$ 14.280', status: 'Aprovado', date: 'Ontem, 16:18' },
    { id: '#1046', client: 'Ponto Norte Arquitetura', detail: 'Double Vision México', value: 'R$ 6.930', status: 'Em análise', date: 'Ontem, 11:05' },
    { id: '#1045', client: 'Casa Jardim', detail: 'Motorização · 2 itens', value: 'R$ 3.740', status: 'Aprovado', date: '02 set, 14:26' },
]

const navGroups = [
    { title: 'Visão geral', items: [{ label: 'Início', icon: 'home' }] },
    {
        title: 'Operação',
        items: [
            { label: 'Cadastros', icon: 'users' },
            { label: 'Produtos', icon: 'package' },
            { label: 'Orçamentos', icon: 'file' },
            { label: 'Vendas', icon: 'cart' },
            { label: 'Ordens de serviço', icon: 'wrench' },
        ],
    },
    {
        title: 'Controle',
        items: [
            { label: 'Estoque', icon: 'layers' },
            { label: 'Financeiro', icon: 'wallet' },
            { label: 'Fiscal', icon: 'bar' },
            { label: 'Relatórios', icon: 'chart' },
        ],
    },
]

const iconMap = {
    home: Home,
    users: Users,
    package: Package,
    file: FileText,
    cart: ShoppingCart,
    wrench: Wrench,
    layers: Layers3,
    wallet: WalletCards,
    bar: FileBarChart,
    chart: Gauge,
} as const


function formatDashboardDate() {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
    .format(new Date())
    .replace(/^\p{L}/u, (char) => char.toUpperCase())
}

function App() {
    const authSession = useAuthSession()
    const [adminAvailable, setAdminAvailable] = useState(false)

    useEffect(() => {
        let cancelled = false

        if (!authSession?.user?.id) {
            setAdminAvailable(false)
            return
        }

        void getAdminMe()
            .then(() => {
                if (!cancelled) setAdminAvailable(true)
            })
            .catch(() => {
                if (!cancelled) setAdminAvailable(false)
            })

        return () => {
            cancelled = true
        }
    }, [authSession?.user?.id])
    const [collapsed, setCollapsed] = useState(false)
    const [mobileOpen, setMobileOpen] = useState(false)
    const [cadastrosOpen, setCadastrosOpen] = useState(true)
const [activePage, setActivePage] = useState(() => {
        const saved = window.localStorage.getItem(
            'smarttec:last-active-page',
        )

        return saved || 'Início'
    })
    const [view, setView] = useState<
        'dashboard' |
        'budgets' |
        'new-budget' |
        'products' |
        'cadastro' |
        'profile' |
        'settings' |
        'agenda' |
        'admin'
    >(() => {
        const saved = window.localStorage.getItem(
            'smarttec:last-view',
        )

        if (saved === 'budgets') return 'budgets'
        if (saved === 'new-budget') return 'new-budget'
        if (saved === 'products') return 'products'
        if (saved === 'cadastro') return 'cadastro'
        if (saved === 'profile') return 'profile'
        if (saved === 'settings') return 'settings'
        if (saved === 'agenda') return 'agenda'
        if (saved === 'admin') return 'admin'

        return 'dashboard'
    })
    const [searchOpen, setSearchOpen] = useState(false)
    const [userMenuOpen, setUserMenuOpen] = useState(false)
    const [budgetId, setBudgetId] = useState<number | null>(null)
    const [budgetRefresh, setBudgetRefresh] = useState(0)
    const [budgetSavedToast, setBudgetSavedToast] = useState<{ message: string } | null>(null)
    useEffect(() => {
        if (!budgetSavedToast) return
        const timer = window.setTimeout(() => setBudgetSavedToast(null), 3500)
        return () => window.clearTimeout(timer)
    }, [budgetSavedToast])
    const [agendaRefresh, setAgendaRefresh] = useState(0)
    const [agendaNewRequest, setAgendaNewRequest] = useState(0)
    const agendaHoje = useAgendaHoje(view, agendaRefresh, authSession?.empresa.id)
    const budgetNotifications = useBudgetNotifications(view, budgetRefresh)
    const stockNotifications = useStockNotifications(view, budgetRefresh)
    const agendaDate = new Date(agendaHoje.today + 'T12:00:00')

    const openAgenda = (create = false) => {
        setAgendaNewRequest(value => create ? value + 1 : 0)
        setActivePage('Agenda')
        setView('agenda')
        setMobileOpen(false)
    }
    const [cadastroEntity, setCadastroEntity] =
        useState<CadastroEntity>(() => {
            const saved =
                window.localStorage.getItem(
                    'smarttec:last-cadastro',
                )

            if (saved === 'fornecedores') {
                return 'fornecedores'
            }

            if (saved === 'transportadoras') {
                return 'transportadoras'
            }

            if (saved === 'funcionarios') {
                return 'funcionarios'
            }

            return 'clientes'
        })


    useEffect(() => {
        window.localStorage.setItem(
            'smarttec:last-view',
            view,
        )
    }, [view])

    useEffect(() => {
        window.localStorage.setItem(
            'smarttec:last-active-page',
            activePage,
        )
    }, [activePage])

    useEffect(() => {
        window.localStorage.setItem(
            'smarttec:last-cadastro',
            cadastroEntity,
        )
    }, [cadastroEntity])


    const userName =
        authSession?.user.nome?.trim() ||
        authSession?.user.email ||
        'Usuário'

  const apiUrl = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

  const userPhotoUrl = authSession?.user.foto_url
    ? `${apiUrl}${authSession.user.foto_url}`
    : null
    const userInitials = userName
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join('')

    const userRole = authSession?.empresa.papel || 'Usuário'

    const companyLogoPath = authSession?.empresa.logo_url || null
    const companyLogoUrl = companyLogoPath
        ? companyLogoPath.startsWith('http')
            ? companyLogoPath
            : `${apiUrl}${companyLogoPath}`
        : null

    const handleLogout = () => {
        clearAuthSession()

        window.localStorage.removeItem(
            'smarttec:last-view',
        )
        window.localStorage.removeItem(
            'smarttec:last-active-page',
        )
        window.localStorage.removeItem(
            'smarttec:last-cadastro',
        )

        window.location.reload()
    }

    const navigate = (label: string) => {
        if (label === 'Cadastros') {
            setCadastrosOpen((value) => !value)
            return
        }

        const cadastroMap: Record<string, CadastroEntity> = {
            'Clientes': 'clientes',
            'Fornecedores': 'fornecedores',
            'Transportadoras': 'transportadoras',
            'Funcionários': 'funcionarios',
        }

        if (cadastroMap[label]) {
            setCadastroEntity(cadastroMap[label])
            setActivePage(label)
            setView('cadastro')
            setMobileOpen(false)
            return
        }

        if (label !== 'Início' && label !== 'Orçamentos' && label !== 'Produtos' && label !== 'Configurações') return

        setActivePage(label)

        if (label === 'Orçamentos') setView('budgets')
        else if (label === 'Produtos') setView('products')
        else if (label === 'Configurações') setView('settings')
        else setView('dashboard')

        setMobileOpen(false)
    }

    const openNewBudget = () => {
        setBudgetId(null)
        setActivePage('Novo orçamento')
        setView('new-budget')
        setMobileOpen(false)
    }

    return (
        <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
            <div role="status" aria-live="polite" aria-atomic="true">
                {budgetSavedToast && <div className="budget-global-save-toast">{budgetSavedToast.message}</div>}
            </div>
            <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
                <div className="brand-lockup">
  {!collapsed && (
    <div className="brand-wordmark" aria-label="Smart-tec Sistemas">
      <strong className="brand-name">
        <span className="brand-smart">Smart-</span>
        <span className="brand-tec">tec</span>
      </strong>
      <span className="brand-sistemas">SISTEMAS</span>
    </div>
  )}
                    <button className="icon-button sidebar-close" aria-label="Fechar menu" onClick={() => setMobileOpen(false)}><X size={18} /></button>
                </div>

                <div className="company-switcher">
                    <div className="company-avatar">
    {companyLogoUrl ? (
        <img src={companyLogoUrl} alt="Logo da empresa" />
    ) : (
        'ST'
    )}
</div>
                    
                    
                </div>

                <nav className="main-nav" aria-label="Navegação principal">
                    {navGroups.map((group) => (
                        <div className="nav-group" key={group.title}>
                            {!collapsed && <div className="nav-label">{group.title}</div>}
                            {group.items.map((item) => {
                                const Icon = iconMap[item.icon as keyof typeof iconMap]
                                const isActive = activePage === item.label
                                return (
                                    <div key={item.label}>
                                        <button
                                            className={`nav-item ${isActive ? 'active' : ''}`}
                                            onClick={() => navigate(item.label)}
                                            title={collapsed ? item.label : undefined}
                                        >
                                            <Icon size={18} strokeWidth={1.8} />
                                            {!collapsed && <span>{item.label}</span>}
                                            {item.label === 'Orçamentos' && !collapsed && <span className="nav-badge">8</span>}

                                            {item.label === 'Cadastros' && !collapsed && (
                                                <ChevronRight
                                                    size={14}
                                                    style={{
                                                        marginLeft: 'auto',
                                                        transform: cadastrosOpen ? 'rotate(90deg)' : 'none',
                                                    }}
                                                />
                                            )}
                                        </button>

                                        {item.label === 'Cadastros' && cadastrosOpen && !collapsed && (
                                            <div className="nav-submenu">
                                                {[
                                                    'Clientes',
                                                    'Fornecedores',
                                                    'Transportadoras',
                                                    'Funcionários',
                                                ].map((label) => (
                                                    <button
                                                        key={label}
                                                        className={`nav-subitem ${activePage === label ? 'active' : ''}`}
                                                        onClick={() => navigate(label)}
                                                    >
                                                        {label}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    ))}
                </nav>

                <div className="sidebar-foot">
                    <button
  className="nav-item"
  onClick={() => {
    setActivePage('Configurações')
    setView('settings')
    setMobileOpen(false)
  }}
  title={collapsed ? 'Configurações' : undefined}
>
  <Settings size={18} strokeWidth={1.8} />
  {!collapsed && <span>Configurações</span>}
</button>
                    {!collapsed && <div className="sidebar-status"><span className="status-dot" /> Ambiente de demonstração</div>}
                </div>
            </aside>

            {mobileOpen && <button className="mobile-scrim" aria-label="Fechar menu" onClick={() => setMobileOpen(false)} />}

            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left">
                        <button className="icon-button mobile-menu" aria-label="Abrir menu" onClick={() => setMobileOpen(true)}><Menu size={20} /></button>
                        <button className="icon-button desktop-collapse" aria-label="Recolher menu" onClick={() => setCollapsed((value) => !value)}>{collapsed ? <ChevronRight size={19} /> : <ChevronLeft size={19} />}</button>
                        <div className="breadcrumb"><span>Visão geral</span><ChevronRight size={14} /><strong>{activePage}</strong></div>
                    </div>
                    <div className="topbar-actions">
                        {searchOpen && <div className="global-search"><Search size={16} /><input autoFocus placeholder="Buscar no sistema" /><kbd>⌘ K</kbd></div>}
                        <button className="icon-button" aria-label="Pesquisar" onClick={() => setSearchOpen((value) => !value)}><Search size={18} /></button>
                        <HeaderAgenda onOpen={() => openAgenda()} onNew={() => openAgenda(true)} agenda={agendaHoje} />
                            <HeaderNotifications
                                agenda={agendaHoje}
                                budgets={budgetNotifications}
                                stock={stockNotifications}
                                onOpenAgenda={() => openAgenda()}
                                onOpenBudgets={() => navigate('Or\u00e7amentos')}
                                onOpenProducts={() => setView('products')}
                            />
                        <div className="user-menu">
    <button
        type="button"
        className="user-menu-trigger"
        aria-label="Menu do usuário"
        aria-expanded={userMenuOpen}
        onClick={() => setUserMenuOpen((value) => !value)}
    >
        <div className="user-avatar">
                  {userPhotoUrl ? (
                    <img src={userPhotoUrl} alt={userName} />
                  ) : (
                    userInitials || '?'
                  )}
                </div>
        <div className="user-copy">
            <strong>{userName}</strong>
            <span>{formatUserRole(userRole)}</span>
        </div>
        <ChevronRight size={15} />
    </button>

    {userMenuOpen && (
        <div className="user-dropdown">
            <div className="user-dropdown-copy">
                <strong>{userName}</strong>
                {authSession?.user.email && <span>{authSession.user.email}</span>}
            </div>

            <button

                type="button"

                onClick={() => {

                    setUserMenuOpen(false)

                    setActivePage('Meus dados')

                    setView('profile')

                }}

            >

                Meus dados

            </button>


            {adminAvailable && (
                <button
                    type="button"
                    onClick={() => {
                        setUserMenuOpen(false)
                        setActivePage('Administração Smart-tec')
                        setView('admin')
                    }}
                >
                    Administração Smart-tec
                </button>
            )}

            <button type="button" onClick={handleLogout}>
                Sair
            </button>
        </div>
    )}
</div>
                    </div>
                </header>

<div className="page-wrap">
                    {view === 'agenda' && <AgendaPage newRequest={agendaNewRequest} onChanged={() => setAgendaRefresh(value => value + 1)} onBack={() => { setActivePage('Início'); setView('dashboard') }} />}
                    {view === 'budgets' && <BudgetsPage onNew={openNewBudget} refreshKey={budgetRefresh} onOpen={(id) => { setBudgetId(id); setActivePage('Orçamento'); setView('new-budget') }} />}
                    {view === 'new-budget' && <NewBudgetPage budgetId={budgetId} onBack={() => navigate('Orçamentos')} onSaved={(id, mode) => { setBudgetId(id); setBudgetRefresh((value) => value + 1); navigate('Orçamentos'); setBudgetSavedToast({ message: mode === 'created' ? 'Orçamento salvo com sucesso.' : 'Orçamento atualizado com sucesso.' }) }} />}
                    {view === 'products' && <ProductsPage />}
                    {view === 'cadastro' && <CadastrosPage entity={cadastroEntity} />}
                    {view === 'profile' && <MyProfilePage />}
            {view === 'settings' && <SettingsPage />}
            {view === 'admin' && (
                <AdminDashboardPage
                    onBack={() => {
                        setActivePage('Início')
                        setView('dashboard')
                    }}
                />
            )}
                    {view === 'dashboard' && <>
                    <section className="page-heading">
                        <div><p className="eyebrow">{formatDashboardDate()}</p><h1>Bom dia, Valmir <span>👋</span></h1><p className="heading-subtitle">Aqui está o panorama da sua operação hoje.</p></div>
                        <button className="primary-button" onClick={openNewBudget}><Plus size={18} /> Novo orçamento</button>
                    </section>

                    <section className="metric-grid" aria-label="Indicadores financeiros">
                        {metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
                    </section>

                    <section className="dashboard-grid">
                        <article className="panel cashflow-panel">
                            <PanelHeader title="Fluxo de caixa" subtitle="Entradas e saídas nos últimos 30 dias" action="Ver financeiro" />
                            <div className="cashflow-summary"><div><span className="legend-dot red" /> Entradas <strong>R$ 142.840</strong></div><div><span className="legend-dot gray" /> Saídas <strong>R$ 68.210</strong></div></div>
                            <CashflowChart />
                            <div className="chart-axis"><span>05 ago</span><span>12 ago</span><span>19 ago</span><span>26 ago</span><span>04 set</span></div>
                        </article>

                        <article className="panel agenda-panel">
                            <PanelHeader title="Agenda" subtitle="Compromissos de hoje" action="Ver agenda" onAction={() => openAgenda()} />
                            <div className="agenda-date">
                                <span>{new Intl.DateTimeFormat('pt-BR', { day: '2-digit' }).format(agendaDate)}</span>
                                <div>
                                    <strong>{new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(agendaDate)}, {new Intl.DateTimeFormat('pt-BR', { weekday: 'long' }).format(agendaDate)}</strong>
                                    <small>{agendaHoje.loading ? 'Carregando compromissos...' : agendaHoje.error ? 'Agenda indisponível' : `${agendaHoje.limited ? 'Pelo menos ' : ''}${agendaHoje.events.length} compromisso${agendaHoje.events.length === 1 ? '' : 's'} para hoje`}</small>
                                </div>
                                <button type="button" className="icon-button" aria-label="Abrir agenda completa" onClick={() => openAgenda()}><CalendarDays size={19} /></button>
                            </div>
                            <div className="agenda-list" aria-busy={agendaHoje.loading}>
                                {agendaHoje.loading ? <p className="heading-subtitle" role="status">Carregando agenda...</p> :
                                    agendaHoje.error ? <div role="alert"><p className="heading-subtitle">Não foi possível carregar os compromissos.</p><button className="panel-action" onClick={agendaHoje.refresh}>Tentar novamente</button></div> :
                                    agendaHoje.events.length === 0 ? <p className="heading-subtitle">Nenhum compromisso para hoje</p> :
                                    agendaHoje.events.slice(0, 4).map(event => <AgendaItem key={event.id}
                                        time={event.dia_inteiro ? 'Dia inteiro' : new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date(event.inicio))}
                                        title={event.titulo} type={event.cliente_nome || event.categoria.replaceAll('_', ' ')} tone="red" />)}
                                {!agendaHoje.loading && !agendaHoje.error && agendaHoje.events.length > 4 && <button className="panel-action" onClick={() => openAgenda()}>{agendaHoje.limited ? 'Pelo menos mais ' : 'Mais '}{agendaHoje.events.length - 4} compromisso(s) na agenda <ArrowUpRight size={14} /></button>}
                                {!agendaHoje.loading && !agendaHoje.error && agendaHoje.limited && <p className="heading-subtitle">Limite da consulta atingido. Consulte a Agenda completa.</p>}
                            </div>
                        </article>
                    </section>

                    <section className="lower-grid">
                        <article className="panel quotes-panel"><PanelHeader title="Orçamentos recentes" subtitle="Acompanhe as últimas movimentações" action="Ver todos" /><div className="table-wrap"><table><thead><tr><th>Orçamento</th><th>Cliente</th><th>Valor</th><th>Status</th><th>Data</th></tr></thead><tbody>{recentQuotes.map((quote) => <tr key={quote.id}><td><strong className="quote-id">{quote.id}</strong></td><td><strong>{quote.client}</strong><small>{quote.detail}</small></td><td><strong>{quote.value}</strong></td><td><StatusPill status={quote.status} /></td><td className="muted-cell">{quote.date}</td></tr>)}</tbody></table></div></article>
                        <article className="panel operations-panel"><PanelHeader title="Visão operacional" subtitle="Pontos que merecem atenção" /><OperationRow icon={<Truck size={18} />} tone="red" title="Instalações próximas" value="6" detail="nos próximos 7 dias" /><OperationRow icon={<ClipboardList size={18} />} tone="green" title="Pedidos aprovados" value="12" detail="+3 nesta semana" /><OperationRow icon={<Package size={18} />} tone="gold" title="Itens com estoque baixo" value="8" detail="ver lista de reposição" /><button className="text-button">Abrir central de tarefas <ArrowUpRight size={15} /></button></article>
                    </section>

                    <footer className="page-footer"><span>Smart-tec Sistemas · Ambiente de demonstração</span><span>Última atualização há 2 min <span className="status-dot inline" /></span></footer>
                    </>}
                </div>
            </main>
        </div>
    )
}

function MetricCard({ metric }: { metric: Metric }) {
    return <article className={`metric-card tone-${metric.tone}`}><div className="metric-top"><span>{metric.label}</span><div className="metric-icon">{metric.tone === 'red' ? <CircleDollarSign size={18} /> : metric.tone === 'gold' ? <ClipboardList size={18} /> : metric.tone === 'green' ? <ArrowUpRight size={18} /> : <WalletCards size={18} />}</div></div><strong>{metric.value}</strong><div className={`metric-delta ${metric.trend}`}>{metric.trend === 'up' ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{metric.delta}<span>vs. mês anterior</span></div></article>
}

function PanelHeader({ title, subtitle, action, onAction }: { title: string; subtitle?: string; action?: string; onAction?: () => void }) { return <div className="panel-header"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action && <button className="panel-action" onClick={onAction}>{action}<ArrowUpRight size={14} /></button>}<button className="icon-button panel-menu" aria-label={`Mais opções de ${title}`}><SlidersHorizontal size={16} /></button></div> }
function StatusPill({ status }: { status: RecentQuote['status'] }) { return <span className={`status-pill ${status.toLowerCase().replace(' ', '-')}`}><span />{status}</span> }
function AgendaItem({ time, title, type, tone }: { time: string; title: string; type: string; tone: string }) { return <div className="agenda-item"><time style={{ flexShrink: 0 }}>{time}</time><span className={`agenda-line ${tone}`} style={{ flexShrink: 0 }} /><div><strong title={title}>{title}</strong><small title={type}>{type}</small></div></div> }
function OperationRow({ icon, tone, title, value, detail }: { icon: React.ReactNode; tone: string; title: string; value: string; detail: string }) { return <div className="operation-row"><div className={`operation-icon ${tone}`}>{icon}</div><div className="operation-copy"><strong>{title}</strong><span>{detail}</span></div><b>{value}</b></div> }
function CashflowChart() { return <div className="chart" aria-label="Gráfico de fluxo de caixa ilustrativo"><div className="chart-grid"><span>150k</span><span>100k</span><span>50k</span><span>0</span></div><svg viewBox="0 0 800 210" preserveAspectRatio="none" role="img" aria-label="Entradas e saídas"><defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--color-primary)" stopOpacity=".22" /><stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" /></linearGradient></defs><path d="M0 166 C46 152 66 158 105 130 S164 145 205 110 S264 128 307 83 S370 110 407 92 S464 82 510 58 S562 94 605 68 S670 76 720 42 S765 55 800 26 L800 210 L0 210 Z" fill="url(#area)" /><path d="M0 166 C46 152 66 158 105 130 S164 145 205 110 S264 128 307 83 S370 110 407 92 S464 82 510 58 S562 94 605 68 S670 76 720 42 S765 55 800 26" fill="none" stroke="var(--color-primary)" strokeWidth="3" strokeLinecap="round" /><path d="M0 186 C55 175 75 181 114 166 S176 180 215 152 S274 168 314 142 S371 156 415 130 S477 150 515 118 S570 135 610 111 S674 130 718 98 S762 115 800 94" fill="none" stroke="#aeb5bf" strokeWidth="2" strokeDasharray="5 7" strokeLinecap="round" /></svg></div> }

export default App
