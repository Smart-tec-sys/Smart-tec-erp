import type { ApiBudget, ApiClient, ApiProduct, BudgetPayload } from '../types/budget'
import type { RomanaResult } from '../types/romana'
import type { RomanaTetoResult } from '../types/romana_teto'
import type { RoloResult } from '../types/rolo'
import type { DoubleVisionResult } from '../types/double_vision'
import type { CommercialProfile } from '../types/budget'
import { getApiAuthHeaders } from './auth'

export const apiConfig = { baseUrl: import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000' } as const

export const simulateRomana = (data: { produto_id: number; largura: number; altura: number; quantidade: number; perfil_comercial: CommercialProfile; desconto: number }) =>
  request<RomanaResult>('/orcamentos/simulacao-romana', { method: 'POST', body: JSON.stringify(data) })

export const simulateRomanaTeto = (data: {
  produto_id: number
  largura_modulo_m: number
  comprimento_avanco_m: number
  quantidade_modulos: number
  acionamento: 'MANUAL_BASTAO' | 'MANUAL_CORRENTE' | 'MOTORIZADA'
  lado_comando?: 'ESQUERDA' | 'DIREITA'
  comprimento_bastao_m?: number
  comprimento_corrente_sem_fim_m?: number
  perfil_comercial: CommercialProfile
  desconto: number
  cor?: string
}) =>
  request<RomanaTetoResult>('/orcamentos/simulacao-romana-teto', { method: 'POST', body: JSON.stringify(data) })

export const simulateRolo = (data: { produto_id: number; largura: number; altura: number; quantidade: number; perfil_comercial: CommercialProfile; desconto: number; cor?: string; acionamento?: 'manual' | 'motorizado'; lado_comando?: string }) =>
  request<RoloResult>('/orcamentos/simulacao-rolo', { method: 'POST', body: JSON.stringify(data) })

export const simulateDoubleVision = (data: { produto_id: number; largura: number; altura: number; quantidade: number; perfil_comercial: CommercialProfile; desconto: number; com_bando?: boolean; tem_validacao_tecido_fornecedor?: boolean }) =>
  request<DoubleVisionResult>('/orcamentos/simulacao-double-vision', { method: 'POST', body: JSON.stringify(data) })


export const simulateCurtain = (data: {
  componentes?: { produto_id: number; quantidade: number }[]
  tecido_produto_id: number
  forro_produto_id?: number
  largura_forro?: number
  trilho_produto_id?: number
  rodizio_produto_id?: number
  gancho_produto_id?: number
  botao_produto_id?: number
  entretela_produto_id?: number
  largura: number
  altura: number
  quantidade: number
  fator: number
  largura_tecido: number
  modelo_prega: string
  possui_forro: boolean
  tipo_forro?: string
  trilho_linha?: 'MINI' | 'MAX' | 'MASTER'
  trilho_modelo?: string
  rodizio_tipo?: 'MINI' | 'MAX' | 'BOTAO'
  cabeca_cm: number
  barra_cm: number
  barra_dupla: boolean
  usa_entretela: boolean
  tipo_entretela: string
  fixacao_cortina: 'RODIZIO' | 'GANCHO'
  trilho_com_cordas: boolean
  sistema_wave: 'PREGA_PRONTA' | 'BOTAO'
  espacamento_botao_cm: 7 | 10
  abertura_cortina:
    | 'LATERAL_ESQUERDA'
    | 'LATERAL_DIREITA'
    | 'CENTRAL'
    | 'DUAS_LATERAIS'
}) =>
  request<any>('/orcamentos/simulacao-cortina', {
    method: 'POST',
    body: JSON.stringify(data),
  })

type AuxOption = { id: number; nome: string; categoria: string; descricao: string | null; situacao: string; ordem: number }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await getApiAuthHeaders()
  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...authHeaders, ...init?.headers }
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`API ${response.status}: ${detail || response.statusText}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function getAllProducts(): Promise<ApiProduct[]> {
  const all: ApiProduct[] = []
  const limit = 500
  for (let page = 0; page < 100; page += 1) {
    const chunk = await request<ApiProduct[]>(`/produtos/?skip=${page * limit}&limit=${limit}`)
    all.push(...chunk)
    if (chunk.length < limit) return all
  }
  throw new Error('Paginação do catálogo excedeu o limite de segurança.')
}

export const getClients = () => request<ApiClient[]>('/clientes/')
export type ProductCommercialUpdate = { nome: string } & Partial<Pick<ApiProduct,
  'grupo_produto' | 'unidade_venda' | 'cor' | 'cor_componente' | 'variacao_cor' |
  'varia_cor' | 'situacao' | 'status_comercial'>> & { valor_custo?: number; valor_venda?: number }

export const updateProductCommercial = (id: number, data: ProductCommercialUpdate) =>
  request<ApiProduct>(`/produtos/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteBudget = (id: number) => request<void>(`/orcamentos/${id}`, { method: 'DELETE' })
export const getBudgets = () => request<ApiBudget[]>('/orcamentos/')
export const getBudget = (id: number) => request<ApiBudget>(`/orcamentos/${id}`)
export const createBudget = (payload: BudgetPayload) => request<ApiBudget>('/orcamentos/', { method: 'POST', body: JSON.stringify(payload) })
export const updateBudget = (id: number, payload: BudgetPayload) => request<ApiBudget>(`/orcamentos/${id}`, { method: 'PUT', body: JSON.stringify(payload) })

export type ApiOrderItem = {
  id: number
  tipo_item: string
  produto_id?: number | null
  descricao?: string | null
  codigo_interno?: string | null
  grupo_tecnico?: string | null
  modelo_tecnico?: string | null
  unidade?: string | null
  quantidade: number | string
  largura: number | string
  altura: number | string
  area: number | string
  preco_unitario: number | string
  desconto: number | string
  subtotal: number | string
  observacao_item?: string | null
  material?: string | null
  cor?: string | null
  acionamento?: string | null
  lado_comando?: string | null
  calculo_producao_status?: string | null
  dados_tecnicos?: Record<string, unknown> | null
}

export type ApiOrder = {
  cliente_final_nome?: string | null
  cliente_final_documento?: string | null
  cliente_final_telefone?: string | null
  cliente_final_email?: string | null
  cliente_final_endereco?: string | null

  id: number
  numero?: string | null
  empresa_id?: number | null
  cliente_id?: number | null
  orcamento_id?: number | null
  vendedor_id?: number | null
  parceiro_id?: number | null
  representante_id?: number | null
  orcamento_numero?: string | null
  status?: string | null
  perfil_comercial: string
  data_venda?: string | null
  prazo_entrega?: string | null
  canal_venda?: string | null
  total: number | string
  desconto: number | string
  total_final: number | string
  percentual_parceiro?: number | string | null
  incluir_rt?: boolean | null
  tipo_rt?: string | null
  percentual_rt?: number | string | null
  valor_rt?: number | string | null
  incluir_taxa_bancaria?: boolean | null
  taxa_bancaria_percentual?: number | string | null
  valor_parceiro?: number | string | null
  valor_taxa_bancaria?: number | string | null
  total_cliente_final?: number | string | null
  observacao?: string | null
  observacao_interna?: string | null
  criado_em?: string | null
  atualizado_em?: string | null
  itens: ApiOrderItem[]
}

export type ConvertBudgetToOrderPayload = {
  prazo_entrega?: string | null
  canal_venda?: string | null
}

export const getOrders = () =>
  request<ApiOrder[]>('/pedidos/')

export const getOrder = (id: number) =>
  request<ApiOrder>(`/pedidos/${id}`)

export const convertBudgetToOrder = (
  budgetId: number,
  data: ConvertBudgetToOrderPayload = {},
) =>
  request<ApiOrder>(
    `/pedidos/converter-orcamento/${budgetId}`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  )
export const createClient = (data: { tipo: string; nome: string }) => request<ApiClient>('/clientes/', { method: 'POST', body: JSON.stringify(data) })
export type ProductCommercialCreate = ProductCommercialUpdate & { grupo_produto: string; unidade_venda: string; valor_custo: number }
export const createProduct = (data: ProductCommercialCreate) => request<ApiProduct>('/produtos/', { method: 'POST', body: JSON.stringify(data) })


export type CadastroRecord = {
  id: number
  [key: string]: unknown
}

export type CadastroPayload = Record<
  string,
  string | number | boolean | null | undefined
>

export const getClientesCadastro = () =>
  request<CadastroRecord[]>('/clientes/')

export const createClienteCadastro = (data: CadastroPayload) =>
  request<CadastroRecord>('/clientes/', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateClienteCadastro = (id: number, data: CadastroPayload) =>
  request<CadastroRecord>(`/clientes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteClienteCadastro = (id: number) =>
  request<{ message: string }>(`/clientes/${id}`, { method: 'DELETE' })

export const getFornecedoresCadastro = () =>
  request<CadastroRecord[]>('/fornecedores/')

export const createFornecedorCadastro = (data: CadastroPayload) =>
  request<CadastroRecord>('/fornecedores/', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateFornecedorCadastro = (id: number, data: CadastroPayload) =>
  request<CadastroRecord>(`/fornecedores/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteFornecedorCadastro = (id: number) =>
  request<{ message: string }>(`/fornecedores/${id}`, { method: 'DELETE' })

export const getTransportadorasCadastro = () =>
  request<CadastroRecord[]>('/transportadoras/')

export const createTransportadoraCadastro = (data: CadastroPayload) =>
  request<CadastroRecord>('/transportadoras/', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateTransportadoraCadastro = (id: number, data: CadastroPayload) =>
  request<CadastroRecord>(`/transportadoras/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteTransportadoraCadastro = (id: number) =>
  request<{ message: string }>(`/transportadoras/${id}`, { method: 'DELETE' })

export const getFuncionariosCadastro = () =>
  request<CadastroRecord[]>('/funcionarios/')

export const createFuncionarioCadastro = (data: CadastroPayload) =>
  request<CadastroRecord>('/funcionarios/', {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateFuncionarioCadastro = (id: number, data: CadastroPayload) =>
  request<CadastroRecord>(`/funcionarios/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })

export const deleteFuncionarioCadastro = (id: number) =>
  request<{ message: string }>(`/funcionarios/${id}`, { method: 'DELETE' })


function adaptOptions(items: AuxOption[]): string[] {
  return items
    .filter(item => item.situacao !== 'inativo' && item.situacao !== 'INATIVO' && item.situacao !== 'Inativo')
    .map(item => item.nome.trim())
    .filter(name => name.length > 0)
    .filter((name, index, arr) => arr.indexOf(name) === index)
    .sort((a, b) => a.localeCompare(b, 'pt-BR'))
}

export const getProductGroups = async (): Promise<string[]> => {
  const items = await request<AuxOption[]>('/opcoes-auxiliares/categoria/grupo_produto')
  return adaptOptions(items)
}

export const getProductUnits = async (): Promise<string[]> => {
  const items = await request<AuxOption[]>('/opcoes-auxiliares/categoria/unidade_venda')
  return adaptOptions(items)
}


export type ApiReceivable = {
  id: number
  pedido_id: number
  cliente_id?: number | null
  descricao: string
  valor: number | string
  vencimento: string
  status: string
  categoria?: string | null
  observacao?: string | null
}

export const createOrderReceivable = (
  orderId: number,
  data: {
    vencimento: string
    categoria?: string
    observacao?: string | null
  },
) =>
  request<ApiReceivable>(
    `/pedidos/${orderId}/conta-receber`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  )

export type AccountingSummary = {
  competencia: string
  nf_produtos: number | string
  nf_servicos: number | string
  faturamento_fiscal: number | string
  qtd_nf_produtos: number
  qtd_nf_servicos: number
  total_obrigacoes: number | string
  total_pendente: number | string
  total_pago: number | string
  honorarios_contabeis: number | string
  fechamento: {
    id?: number
    status: string
    observacao?: string | null
    fechado_em?: string | null
  }
}

export type AccountingDocument = {
  id: number
  empresa_id: number
  competencia: string
  tipo_documento: string
  numero?: string | null
  chave_acesso?: string | null
  data_emissao: string
  valor: number | string
  pedido_id?: number | null
  compra_id?: number | null
  observacao?: string | null
  criado_em?: string | null
}

export type AccountingObligation = {
  id: number
  empresa_id: number
  competencia: string
  tipo_obrigacao: string
  descricao: string
  valor: number | string
  vencimento: string
  status: string
  fornecedor_id?: number | null
  financeiro_id?: number | null
  observacao?: string | null
  criado_em?: string | null
}

export const getAccountingSummary = (
  competencia: string,
) =>
  request<AccountingSummary>(
    `/contabilidade/resumo?competencia=${encodeURIComponent(competencia)}`,
  )

export const getAccountingDocuments = (
  competencia: string,
) =>
  request<AccountingDocument[]>(
    `/contabilidade/documentos?competencia=${encodeURIComponent(competencia)}`,
  )

export const createAccountingDocument = (
  data: {
    competencia: string
    tipo_documento: string
    numero?: string | null
    chave_acesso?: string | null
    data_emissao: string
    valor: number
    pedido_id?: number | null
    compra_id?: number | null
    observacao?: string | null
  },
) =>
  request<AccountingDocument>(
    '/contabilidade/documentos',
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  )

export const getAccountingObligations = (
  competencia: string,
) =>
  request<AccountingObligation[]>(
    `/contabilidade/obrigacoes?competencia=${encodeURIComponent(competencia)}`,
  )

export const createAccountingObligation = (
  data: {
    competencia: string
    tipo_obrigacao: string
    descricao: string
    valor: number
    vencimento: string
    fornecedor_id?: number | null
    observacao?: string | null
  },
) =>
  request<AccountingObligation>(
    '/contabilidade/obrigacoes',
    {
      method: 'POST',
      body: JSON.stringify(data),
    },
  )

export const createAccountingPayable = (
  obligationId: number,
) =>
  request<{
    obrigacao: AccountingObligation
    financeiro: Record<string, unknown>
  }>(
    `/contabilidade/obrigacoes/${obligationId}/gerar-conta-pagar`,
    {
      method: 'POST',
      body: JSON.stringify({}),
    },
  )

export const markAccountingObligationPaid = (
  obligationId: number,
  pagamento: string,
) =>
  request<AccountingObligation>(
    `/contabilidade/obrigacoes/${obligationId}/marcar-paga`,
    {
      method: 'POST',
      body: JSON.stringify({ pagamento }),
    },
  )

export const closeAccountingPeriod = (
  competencia: string,
  observacao?: string | null,
) =>
  request<Record<string, unknown>>(
    `/contabilidade/fechamentos/${encodeURIComponent(competencia)}/fechar`,
    {
      method: 'POST',
      body: JSON.stringify({
        observacao: observacao || null,
      }),
    },
  )

export type ApiCommercialPartner = {
  id: number
  nome: string
  documento?: string | null
  percentual_padrao?: number
  ativo?: boolean
}

export type ApiRepresentative = {
  id: number
  nome: string
  parceiro_id?: number | null
  parceiro_nome?: string | null
  tipo_rt_padrao?: 'PERCENTUAL' | 'VALOR_FIXO'
  percentual_rt_padrao?: number
  valor_rt_padrao?: number
  ativo?: boolean
}

// Cadastros incluem também registros inativos; selects comerciais mantêm o filtro atual.
export const getCommercialPartnersCadastro = () => request<CadastroRecord[]>('/representantes/parceiros')
export const getRepresentativesCadastro = () => request<CadastroRecord[]>('/representantes/')
export const createCommercialPartner = (payload: CadastroPayload) => request<CadastroRecord>('/representantes/parceiros', { method: 'POST', body: JSON.stringify(payload) })
export const createRepresentative = (payload: CadastroPayload) => request<CadastroRecord>('/representantes/', { method: 'POST', body: JSON.stringify(payload) })

export const getCommercialPartners = () =>
  request<ApiCommercialPartner[]>(
    '/representantes/parceiros?ativos=true'
  )

export const getRepresentatives = () =>
  request<ApiRepresentative[]>(
    '/representantes/?ativos=true'
  )

export type OrderUpdate = Partial<Pick<ApiOrder, 'cliente_id' | 'vendedor_id' | 'parceiro_id' | 'representante_id' | 'status' | 'perfil_comercial' | 'data_venda' | 'prazo_entrega' | 'canal_venda' | 'observacao' | 'observacao_interna' | 'cliente_final_nome' | 'cliente_final_documento' | 'cliente_final_telefone' | 'cliente_final_email' | 'cliente_final_endereco' | 'percentual_parceiro' | 'incluir_rt' | 'tipo_rt' | 'percentual_rt' | 'valor_rt' | 'incluir_taxa_bancaria' | 'taxa_bancaria_percentual' | 'valor_parceiro' | 'valor_taxa_bancaria' | 'total_cliente_final'>>
export const updateOrder = (id: number, payload: OrderUpdate) => request<ApiOrder>(`/pedidos/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
export const deleteOrder = (id: number) => request<void>(`/pedidos/${id}`, { method: 'DELETE' })


export type OrderItemCreate = Omit<ApiOrderItem, 'id' | 'pedido_id'>
export type OrderCreate = Pick<ApiOrder, 'cliente_id' | 'parceiro_id' | 'representante_id' | 'vendedor_id' | 'cliente_final_nome' | 'cliente_final_documento' | 'cliente_final_telefone' | 'cliente_final_email' | 'cliente_final_endereco' | 'perfil_comercial' | 'data_venda' | 'prazo_entrega' | 'canal_venda' | 'observacao' | 'observacao_interna'> & {
  status: 'ABERTO'
  desconto: number
  percentual_parceiro: number
  incluir_rt: boolean
  tipo_rt: 'PERCENTUAL' | 'VALOR_FIXO' | null
  percentual_rt: number
  valor_rt: number
  incluir_taxa_bancaria: boolean
  taxa_bancaria_percentual: number
  itens: OrderItemCreate[]
}
export const createOrder = (payload: OrderCreate) => request<ApiOrder>('/pedidos/', { method: 'POST', body: JSON.stringify(payload) })

export type FinanceResource = 'contas-financeiras' | 'formas-pagamento' | 'plano-contas' | 'situacoes' | 'centros-custo'
export type FinanceRecord = {
  id: number
  empresa_id: number
  ativo: boolean
  nome: string
  tipo?: string
  codigo?: string
  pai_id?: number | null
  banco?: string | null
  agencia?: string | null
  numero_conta?: string | null
  saldo_inicial?: number | string
  observacao?: string | null
  conta_financeira_id?: number | null
  disponivel_para?: string
  quitado?: boolean
  padrao?: boolean
}
export type FinancePayload = Partial<Omit<FinanceRecord, 'id' | 'empresa_id'>>
export const listFinanceRecords = (resource: FinanceResource) => request<FinanceRecord[]>(`/financeiro/${resource}`)
export const createFinanceRecord = (resource: FinanceResource, payload: FinancePayload) =>
  request<FinanceRecord>(`/financeiro/${resource}`, { method: 'POST', body: JSON.stringify(payload) })
export const updateFinanceRecord = (resource: FinanceResource, id: number, payload: FinancePayload) =>
  request<FinanceRecord>(`/financeiro/${resource}/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
export const deleteFinanceRecord = (resource: FinanceResource, id: number) =>
  request<void>(`/financeiro/${resource}/${id}`, { method: 'DELETE' })
export type FinanceTipo = 'R' | 'P'
export type FinanceOrigem = 'VENDA' | 'CONTABILIDADE' | 'RT' | 'MANUAL'
export type FinanceTitle = {
  id: number
  empresa_id: number
  tipo: FinanceTipo
  descricao: string
  competencia?: string | null
  valor_original?: number | string | null
  desconto?: number | string | null
  juros?: number | string | null
  valor: number | string
  valor_pago: number | string
  saldo: number | string
  vencimento?: string | null
  data_baixa?: string | null
  status: string
  cliente_id?: number | null
  fornecedor_id?: number | null
  pedido_id?: number | null
  conta_financeira_id?: number | null
  forma_pagamento_id?: number | null
  plano_conta_id?: number | null
  centro_custo_id?: number | null
  situacao_financeira_id?: number | null
  categoria?: string | null
  observacao?: string | null
  origem: FinanceOrigem
  cliente_nome?: string | null
  fornecedor_nome?: string | null
  pedido_numero?: string | null
  qtd_baixas: number
  qtd_baixas_total: number
  pode_excluir: boolean
  pode_baixar: boolean
  vinculado: boolean
}
export type FinanceTitleFilters = {
  tipo?: FinanceTipo
  status?: string
  vencimento_inicial?: string
  vencimento_final?: string
  cliente_id?: number
  fornecedor_id?: number
  pedido_id?: number
  conta_financeira_id?: number
  forma_pagamento_id?: number
  plano_conta_id?: number
  centro_custo_id?: number
  situacao_financeira_id?: number
  vencimento_status?: string
  q?: string
}
export type FinanceTitlePayload = Partial<Pick<FinanceTitle, 'tipo' | 'descricao' | 'competencia' | 'vencimento' | 'cliente_id' | 'fornecedor_id' | 'conta_financeira_id' | 'forma_pagamento_id' | 'plano_conta_id' | 'centro_custo_id' | 'situacao_financeira_id' | 'categoria' | 'observacao'>> & {
  valor_original?: number
  desconto?: number
  juros?: number
}
export type FinanceCard = { quantidade: number; total: number | string }
export type FinanceIndicators = {
  total_periodo: FinanceCard
  vencidos: FinanceCard
  vencem_hoje: FinanceCard
  a_vencer: FinanceCard
  quitados: FinanceCard
}
export type FinanceBaixa = {
  id: number
  financeiro_id: number
  data_baixa: string
  valor: number | string
  juros: number | string
  desconto: number | string
  conta_financeira_id?: number | null
  forma_pagamento_id?: number | null
  observacao?: string | null
  estornada_em?: string | null
  ativa: boolean
}
export type FinanceBaixaPayload = {
  data_baixa: string
  valor: number
  juros: number
  desconto: number
  conta_financeira_id?: number | null
  forma_pagamento_id?: number | null
  observacao?: string | null
}
export type FinanceBaixaResult = { baixa: FinanceBaixa; titulo: FinanceTitle }

const financeQuery = (filters: object) => {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  })
  const text = params.toString()
  return text ? `?${text}` : ''
}
export const listFinanceTitles = (filters: FinanceTitleFilters) =>
  request<FinanceTitle[]>(`/financeiro/titulos${financeQuery({ limit: 500, ...filters })}`)
export const getFinanceIndicators = (filters: FinanceTitleFilters) =>
  request<FinanceIndicators>(`/financeiro/titulos/indicadores${financeQuery(filters)}`)
export const createFinanceTitle = (payload: FinanceTitlePayload) =>
  request<FinanceTitle>('/financeiro/titulos', { method: 'POST', body: JSON.stringify(payload) })
export const updateFinanceTitle = (id: number, payload: FinanceTitlePayload) =>
  request<FinanceTitle>(`/financeiro/titulos/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
export const deleteFinanceTitle = (id: number) =>
  request<void>(`/financeiro/titulos/${id}`, { method: 'DELETE' })
export const listFinanceBaixas = (id: number) => request<FinanceBaixa[]>(`/financeiro/titulos/${id}/baixas`)
export const payFinanceTitle = (id: number, payload: FinanceBaixaPayload) =>
  request<FinanceBaixaResult>(`/financeiro/titulos/${id}/baixar`, { method: 'POST', body: JSON.stringify(payload) })
export const reverseFinanceBaixa = (baixaId: number) =>
  request<FinanceBaixaResult>(`/financeiro/baixas/${baixaId}/estornar`, { method: 'POST' })
export type CashFlowFilters = {
  data_inicial?: string
  data_final?: string
  conta_financeira_id?: number
  centro_custo_id?: number
  plano_conta_id?: number
  origem?: string
  modo?: 'realizado' | 'previsto' | 'ambos'
}
export type CashFlowSummary = {
  data_inicial: string
  data_final: string
  modo: string
  saldo_inicial: number | string
  recebimentos: number | string
  pagamentos: number | string
  saldo_realizado: number | string
  recebimentos_previstos: number | string
  pagamentos_previstos: number | string
  saldo_previsto: number | string
  saldo_inicial_contas_incluido: boolean
  atrasados_receber: number | string
  atrasados_pagar: number | string
}
export type CashFlowDay = {
  data: string
  saldo_inicial: number | string
  recebimentos: number | string
  pagamentos: number | string
  saldo_dia: number | string
  recebimentos_previstos: number | string
  pagamentos_previstos: number | string
  saldo_previsto: number | string
}
export type CashFlowMovement = {
  data: string
  descricao: string
  tipo: FinanceTipo
  natureza: 'REALIZADO' | 'PREVISTO'
  situacao: string
  origem: FinanceOrigem
  conta_financeira_id?: number | null
  conta: string
  valor: number | string
  titulo_id: number
  baixa_id?: number | null
  pedido_id?: number | null
  legado: boolean
}
export const getCashFlowSummary = (filters: CashFlowFilters) =>
  request<CashFlowSummary>(`/financeiro/fluxo-caixa/resumo${financeQuery(filters)}`)
export const getCashFlowDaily = (filters: CashFlowFilters) =>
  request<CashFlowDay[]>(`/financeiro/fluxo-caixa/diario${financeQuery(filters)}`)
export const getCashFlowMovements = (filters: CashFlowFilters) =>
  request<{ total: number; itens: CashFlowMovement[] }>(`/financeiro/fluxo-caixa/movimentos${financeQuery({ limit: 1000, ...filters })}`)