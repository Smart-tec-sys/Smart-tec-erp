import { getAccessToken } from './auth'

const API_URL =
  (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000')
    .replace(/\/+$/, '')

export type AdminMe = {
  user: {
    id: number
    nome: string
    email: string
  }
  equipe: {
    id: number
    cargo_exibicao?: string | null
    funcao: {
      id: number
      codigo: string
      nome: string
      nivel: number
    }
    is_owner: boolean
    is_administrator: boolean
  }
  permissions: string[]
}

export type AdminPlan = {
  id: number
  codigo: string
  nome: string
  produto: string
  periodicidade: string
  valor?: number | null
  dias_trial: number
  ativo: boolean
  descricao?: string | null
}

export type AdminModuleCatalogItem = {
  id: number
  codigo: string
  nome: string
  produto: string
  descricao?: string | null
  ativo: boolean
}

export type AdminOverview = {
  empresas_ativas: number
  trials_ativos: number
  trials_encerrando_em_7_dias: number
  renovacoes_em_10_dias: number
  pedidos_modulos_pendentes: number
  chamados_abertos: number
  pagamentos_pendentes: number
  notas_fiscais_pendentes: number
}

export type AdminCompanyListItem = {
  id: number
  nome: string
  nome_fantasia?: string | null
  documento?: string | null
  status: string
  slug: string
  logo_url?: string | null
  criado_em: string
  usuarios_ativos: number
  modulos_ativos: number
  assinatura_status?: string | null
  data_vencimento?: string | null
  data_fim_trial?: string | null
  chamados_abertos: number
}

export type AdminModuleOrder = {
  id: number
  modulo_id: number
  modulo_nome: string
  status: string
  valor?: number | null
  periodicidade?: string | null
  data_pedido: string
  data_aprovacao?: string | null
  data_ativacao?: string | null
  forma_pagamento?: string | null
  observacoes?: string | null
  responsavel_equipe_id?: number | null
  responsavel_nome?: string | null
}

export type AdminPayment = {
  id: number
  assinatura_id?: number | null
  pedido_modulo_id?: number | null
  tipo: string
  status: string
  valor: number
  vencimento?: string | null
  pago_em?: string | null
  forma_pagamento?: string | null
  referencia_externa?: string | null
  observacoes?: string | null
  criado_em: string
  atualizado_em?: string | null
}

export type AdminFiscalNote = {
  id: number
  assinatura_id?: number | null
  pagamento_id?: number | null
  tipo_documento: string
  status: string
  numero?: string | null
  serie?: string | null
  valor_servico?: number | null
  valor_desconto: number
  valor_total?: number | null
  data_emissao?: string | null
  descricao_servico?: string | null
  referencia_externa?: string | null
  protocolo?: string | null
  pdf_url?: string | null
  xml_url?: string | null
  erro_codigo?: string | null
  erro_mensagem?: string | null
  criado_em: string
  atualizado_em?: string | null
}

export type AdminCompanyDetail = {
  empresa: {
    id: number
    nome: string
    nome_fantasia?: string | null
    documento?: string | null
    status: string
    slug: string
    logo_url?: string | null
    configuracoes?: Record<string, unknown>
    criado_em: string
    atualizado_em: string
  }

  resumo: {
    chamados_abertos: number
    pagamentos_pendentes: number
    notas_pendentes: number
    modulos_ativos: number
  }

  usuarios: Array<{
    id: number
    nome: string
    email: string
    status: string
    foto_url?: string | null
    papel: string
    ativo: boolean
  }>

  assinatura?: {
    id: number
    status: string
    periodicidade?: string | null
    data_inicio_trial?: string | null
    data_fim_trial?: string | null
    data_inicio_assinatura?: string | null
    data_vencimento?: string | null
    renovacao_automatica: boolean
    valor?: number | null
    dias_aviso_vencimento: number
    observacoes?: string | null
    plano_codigo?: string | null
    plano_nome?: string | null
    plano_produto?: string | null
  } | null

  modulos: Array<{
    id: number
    codigo: string
    nome: string
    produto: string
    origem: string
    status: string
    data_inicio: string
    data_fim?: string | null
    valor?: number | null
    periodicidade?: string | null
    observacoes?: string | null
  }>

  pedidos_modulos: AdminModuleOrder[]
  pagamentos: AdminPayment[]
  notas_fiscais: AdminFiscalNote[]
  chamados: Array<Record<string, unknown>>
  acompanhamento_comercial: Array<Record<string, unknown>>

  historico: Array<{
    id: number
    acao: string
    recurso?: string | null
    recurso_id?: string | null
    detalhes?: Record<string, unknown>
    request_id?: string | null
    criado_em: string
    usuario_nome?: string | null
  }>
}

async function adminHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken()

  if (!token) {
    throw new Error('Sessão administrativa não encontrada.')
  }

  return {
    Authorization: `Bearer ${token}`,
  }
}

async function adminFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: await adminHeaders(),
  })

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('Acesso administrativo não autorizado.')
    }

    if (response.status === 404) {
      throw new Error('Registro administrativo não encontrado.')
    }

    throw new Error(
      `Falha na consulta administrativa (${response.status}).`,
    )
  }

  return response.json() as Promise<T>
}

export function getAdminMe() {
  return adminFetch<AdminMe>('/admin/me')
}

export function getAdminOverview() {
  return adminFetch<AdminOverview>('/admin/overview')
}

export async function getAdminCompanies() {
  const data = await adminFetch<{
    items: AdminCompanyListItem[]
    total: number
  }>('/admin/empresas')

  return data
}

export function getAdminCompany(id: number) {
  return adminFetch<AdminCompanyDetail>(
    `/admin/empresas/${id}`,
  )
}


export async function getAdminPlans() {
  return adminFetch<{
    items: AdminPlan[]
    total: number
  }>('/admin/catalogo/planos')
}

export async function getAdminModulesCatalog() {
  return adminFetch<{
    items: AdminModuleCatalogItem[]
    total: number
  }>('/admin/catalogo/modulos')
}

async function adminMutation<T>(
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      method: 'POST',
      headers: {
        ...(await adminHeaders()),
        'Content-Type': 'application/json',
      },
      body:
        body === undefined
          ? undefined
          : JSON.stringify(body),
    },
  )

  const data = await response
    .json()
    .catch(() => ({}))

  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : `Falha na operação (${response.status}).`

    throw new Error(detail)
  }

  return data as T
}

export function startAdminTrial(
  empresaId: number,
  input: {
    plano_id?: number | null
    dias?: number
    observacoes?: string | null
  } = {},
) {
  return adminMutation(
    `/admin/empresas/${empresaId}/trial`,
    {
      dias: 7,
      ...input,
    },
  )
}

export function activateAdminSubscription(
  empresaId: number,
  input: {
    plano_id: number
    periodicidade?: 'MENSAL' | 'ANUAL'
    valor?: number | null
    renovacao_automatica?: boolean
    observacoes?: string | null
  },
) {
  return adminMutation(
    `/admin/empresas/${empresaId}/assinatura/ativar`,
    input,
  )
}

export function activateAdminModule(
  empresaId: number,
  moduloId: number,
  input: {
    origem:
      | 'AVULSO'
      | 'CORTESIA'
      | 'TRIAL'
    valor?: number | null
    periodicidade?:
      | 'MENSAL'
      | 'ANUAL'
      | 'UNICO'
      | 'CORTESIA'
    data_fim?: string | null
    observacoes?: string | null
  },
) {
  return adminMutation(
    `/admin/empresas/${empresaId}/modulos/${moduloId}/ativar`,
    input,
  )
}

export function cancelAdminModule(
  empresaId: number,
  moduloId: number,
) {
  return adminMutation(
    `/admin/empresas/${empresaId}/modulos/${moduloId}/cancelar`,
  )
}


export function createAdminModuleOrder(
  empresaId: number,
  input: {
    modulo_id: number
    valor: number
    periodicidade:
      | 'MENSAL'
      | 'ANUAL'
      | 'UNICO'
    forma_pagamento?: string | null
    observacoes?: string | null
  },
) {
  return adminMutation<{
    ok: boolean
    pedido_id: number
    status: string
    modulo_id: number
    modulo: string
  }>(
    `/admin/empresas/${empresaId}/pedidos-modulos`,
    input,
  )
}

export function updateAdminModuleOrderStatus(
  empresaId: number,
  pedidoId: number,
  status:
    | 'EM_ANALISE'
    | 'AGUARDANDO_PAGAMENTO'
    | 'PAGO'
    | 'ATIVADO'
    | 'CANCELADO',
) {
  return adminMutation<{
    ok: boolean
    pedido_id: number
    status_anterior: string
    status: string
    modulo_registro_id?: number | null
    pagamento_id?: number | null
    nota_fiscal_id?: number | null
  }>(
    `/admin/empresas/${empresaId}/pedidos-modulos/${pedidoId}/status`,
    { status },
  )
}
