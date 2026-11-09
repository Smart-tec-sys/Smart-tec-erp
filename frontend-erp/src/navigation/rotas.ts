// Rotas internas por hash (#/...): funcionam no site estático do Render sem regra de reescrita.

export type AppView =
    | 'dashboard'
    | 'budgets'
    | 'sales'
    | 'sale-detail'
    | 'new-sale'
    | 'accounting'
    | 'finance'
    | 'new-budget'
    | 'products'
    | 'cadastro'
    | 'profile'
    | 'settings'
    | 'agenda'
    | 'admin'

export type CadastroRota =
    | 'clientes'
    | 'revendas'
    | 'servicos'
    | 'representantes'
    | 'fornecedores'
    | 'transportadoras'
    | 'funcionarios'

export type EstadoNavegacao = {
    view: AppView
    activePage: string
    cadastro: CadastroRota | null
}

export const ESTADO_INICIAL: EstadoNavegacao = { view: 'dashboard', activePage: 'Início', cadastro: null }

const ROTAS: Record<string, { view: AppView; activePage: string }> = {
    'inicio': { view: 'dashboard', activePage: 'Início' },
    'orcamentos': { view: 'budgets', activePage: 'Orçamentos' },
    'orcamentos/novo': { view: 'new-budget', activePage: 'Novo orçamento' },
    'vendas': { view: 'sales', activePage: 'Vendas' },
    'vendas/nova': { view: 'new-sale', activePage: 'Vendas' },
    'financeiro': { view: 'finance', activePage: 'Financeiro' },
    'contabilidade': { view: 'accounting', activePage: 'Contabilidade' },
    'produtos': { view: 'products', activePage: 'Produtos' },
    'agenda': { view: 'agenda', activePage: 'Agenda' },
    'perfil': { view: 'profile', activePage: 'Meus dados' },
    'configuracoes': { view: 'settings', activePage: 'Configurações' },
    'admin': { view: 'admin', activePage: 'Administração Smart-tec' },
}

export const ROTULOS_CADASTRO: Record<CadastroRota, string> = {
    clientes: 'Clientes',
    revendas: 'Revendas',
    servicos: 'Serviços',
    representantes: 'Representantes',
    fornecedores: 'Fornecedores',
    transportadoras: 'Transportadoras',
    funcionarios: 'Funcionários',
}

function ehCadastro(valor: string): valor is CadastroRota {
    return Object.prototype.hasOwnProperty.call(ROTULOS_CADASTRO, valor)
}

/** Converte o hash da URL em tela; vazio, desconhecido ou callback do Supabase abre a Dashboard. */
export function navegacaoDoHash(hash: string): EstadoNavegacao {
    if (typeof hash !== 'string' || !hash.startsWith('#/')) return ESTADO_INICIAL
    const caminho = hash.slice(2).split(/[?#]/)[0].replace(/\/+$/, '').toLowerCase()
    const rota = Object.prototype.hasOwnProperty.call(ROTAS, caminho) ? ROTAS[caminho] : undefined
    if (rota) return { ...rota, cadastro: null }
    const cadastro = caminho.startsWith('cadastros/') ? caminho.slice('cadastros/'.length) : ''
    if (ehCadastro(cadastro)) {
        return { view: 'cadastro', activePage: ROTULOS_CADASTRO[cadastro], cadastro }
    }
    return ESTADO_INICIAL
}

/** Hash correspondente à tela atual; a Dashboard usa a URL principal, sem hash. */
export function hashDaNavegacao(
    view: AppView,
    cadastro: CadastroRota | null,
    opcoes: { orcamentoExistente?: boolean } = {},
): string {
    switch (view) {
        case 'dashboard': return ''
        case 'budgets': return '#/orcamentos'
        // Edição de orçamento existente não tem id na URL: recarregar volta à lista, nunca a um orçamento vazio.
        case 'new-budget': return opcoes.orcamentoExistente ? '#/orcamentos' : '#/orcamentos/novo'
        case 'sales':
        case 'sale-detail': return '#/vendas'
        case 'new-sale': return '#/vendas/nova'
        case 'finance': return '#/financeiro'
        case 'accounting': return '#/contabilidade'
        case 'products': return '#/produtos'
        case 'agenda': return '#/agenda'
        case 'profile': return '#/perfil'
        case 'settings': return '#/configuracoes'
        case 'admin': return '#/admin'
        case 'cadastro': return cadastro ? `#/cadastros/${cadastro}` : '#/cadastros/clientes'
    }
}

/** URL sem hash, preservando caminho e query, para a Dashboard e o logout. */
export function urlSemHash(pathname: string, search: string): string {
    return `${pathname || '/'}${search || ''}`
}
