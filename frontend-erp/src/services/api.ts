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
  produto_id: number
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
export const getBudgets = () => request<ApiBudget[]>('/orcamentos/')
export const getBudget = (id: number) => request<ApiBudget>(`/orcamentos/${id}`)
export const createBudget = (payload: BudgetPayload) => request<ApiBudget>('/orcamentos/', { method: 'POST', body: JSON.stringify(payload) })
export const updateBudget = (id: number, payload: BudgetPayload) => request<ApiBudget>(`/orcamentos/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
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
