export type NavItem = {
    label: string
    icon: string
    section?: string
}

export type Metric = {
    label: string
    value: string
    delta: string
    trend: 'up' | 'down'
    tone: 'red' | 'green' | 'gold' | 'dark'
}

export type RecentQuote = {
    id: string
    client: string
    detail: string
    value: string
    status: 'Em aberto' | 'Aprovado' | 'Em análise'
    date: string
}
