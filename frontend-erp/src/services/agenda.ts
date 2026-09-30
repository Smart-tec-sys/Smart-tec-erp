import { getApiAuthHeaders } from './auth'

const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
export const AGENDA_LIMIT = 500

// Matches app/schemas/agenda_evento.py. Category and status are intentionally open strings.
export interface AgendaEvento {
  id: number
  empresa_id: number
  external_uid: string
  titulo: string
  descricao: string | null
  categoria: string
  status: string
  inicio: string
  fim: string | null
  dia_inteiro: boolean
  cliente_id: number | null
  cliente_nome: string | null
  responsavel_ref: string | null
  responsavel_nome: string | null
  local: string | null
  endereco: string | null
  observacoes: string | null
  origem: string
  origem_ref: string | null
  origem_updated_at: string | null
  sincronizacao_status: string
  metadados: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type AgendaCampos = Pick<AgendaEvento,
  'titulo' | 'descricao' | 'categoria' | 'status' | 'inicio' | 'fim' |
  'dia_inteiro' | 'cliente_nome' | 'responsavel_nome' | 'local' | 'endereco' | 'observacoes'>

export interface AgendaFiltros {
  inicio_de?: string
  inicio_ate?: string
  categoria?: string
  status?: string
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = await getApiAuthHeaders()
  const response = await fetch(`${API_URL}/agenda/${path}`, {
    ...options,
    headers: { ...headers, ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : ''
    throw new Error(detail || `Não foi possível concluir a operação na Agenda (${response.status}).`)
  }
  return response.json() as Promise<T>
}

const atualizacaoListeners = new Set<() => void>()

// A successful full-page read (including "Atualizar") refreshes the shared daily summary.
export function assinarAtualizacaoAgenda(listener: () => void) {
  atualizacaoListeners.add(listener)
  return () => { atualizacaoListeners.delete(listener) }
}

export function listarAgenda(filters: AgendaFiltros = {}, signal?: AbortSignal, notificar = true) {
  const query = new URLSearchParams({ limit: String(AGENDA_LIMIT) })
  Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value) })
  return request<AgendaEvento[]>(`?${query}`, { signal }).then(data => {
    if (notificar && !signal?.aborted) atualizacaoListeners.forEach(listener => listener())
    return data
  })
}

export function criarAgenda(data: AgendaCampos) {
  return request<AgendaEvento>('', {
    method: 'POST',
    body: JSON.stringify({ ...data, origem: 'ERP', sincronizacao_status: 'LOCAL' }),
  })
}

export function atualizarAgenda(id: number, data: AgendaCampos) {
  // Only editable fields are sent: integrations, IDs and metadata remain untouched.
  return request<AgendaEvento>(String(id), { method: 'PUT', body: JSON.stringify(data) })
}

export function removerAgenda(id: number) {
  return request<{ mensagem: string }>(String(id), { method: 'DELETE' })
}

export function dataLocal(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

export function dataHoraLocal(value: string) {
  const date = new Date(value)
  return `${dataLocal(date)}T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function limiteDia(value: string, end = false) {
  return new Date(`${value}T${end ? '23:59:59.999' : '00:00:00'}`).toISOString()
}