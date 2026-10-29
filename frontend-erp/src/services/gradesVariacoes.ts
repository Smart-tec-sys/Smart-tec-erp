import { apiConfig } from './api'
import { getApiAuthHeaders } from './auth'

export type Grade = { id: number; empresa_id: number; nome: string; descricao: string | null; ativo: boolean; ordem: number; quantidade_valores: number }
export type GradeValue = { id: number; grade_id: number; valor: string; ativo: boolean; ordem: number }
export type GradePayload = { nome: string; descricao: string | null; ativo: boolean; ordem: number }
export type ValuePayload = { valor: string; ativo: boolean; ordem: number }

async function request<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const headers = await getApiAuthHeaders()
  const response = await fetch(apiConfig.baseUrl + '/grades-variacoes' + path, {
    method, headers: { ...headers, 'Content-Type': 'application/json' },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Não foi possível concluir a operação. Confira os campos informados.')
  }
  return response.status === 204 ? undefined as T : response.json()
}
export const listGrades = () => request<Grade[]>('/')
export const createGrade = (data: GradePayload) => request<Grade>('/', 'POST', data)
export const updateGrade = (id: number, data: Partial<GradePayload>) => request<Grade>(`/${id}`, 'PATCH', data)
export const deleteGrade = (id: number) => request<void>(`/${id}`, 'DELETE')
export const listGradeValues = (id: number) => request<GradeValue[]>(`/${id}/valores`)
export const createGradeValue = (id: number, data: ValuePayload) => request<GradeValue>(`/${id}/valores`, 'POST', data)
export const updateGradeValue = (gradeId: number, id: number, data: Partial<ValuePayload>) => request<GradeValue>(`/${gradeId}/valores/${id}`, 'PATCH', data)
export const deleteGradeValue = (gradeId: number, id: number) => request<void>(`/${gradeId}/valores/${id}`, 'DELETE')
