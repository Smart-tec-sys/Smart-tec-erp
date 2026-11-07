import { apiConfig } from './api'
import { getApiAuthHeaders } from './auth'

export type ImportSourceConfig = {
  codigo_cliente: number | null
  mapeamento: Record<string, number>
  linha_cabecalho: number
  aba: string | null
  separador: 'auto' | ';' | ',' | '\t' | '|'
  encoding: 'auto' | 'utf-8-sig' | 'cp1252'
}
export type ImportRelatedFiles = { enderecos?: File | null; contatos?: File | null }

export type ImportConfig = {
  codigo_cliente?: number | null
  enderecos?: ImportSourceConfig | null
  contatos?: ImportSourceConfig | null
  complementar_vazios?: boolean
  ignorar_inconsistencias?: boolean
  mapeamento: Record<string, number>
  linha_cabecalho: number
  aba: string | null
  separador: 'auto' | ';' | ',' | '\t' | '|'
  encoding: 'auto' | 'utf-8-sig' | 'cp1252'
  tipo_padrao: 'Física' | 'Jurídica'
}

export type ImportTable = {
  colunas: string[]
  abas: string[]
  aba: string | null
  separador: string | null
  total: number
  amostra: string[][]
  vinculados?: number
  sem_vinculo?: number
}

export type ImportRow = {
  linha: number
  dados: Record<string, string | null>
  dados_originais?: Record<string, string | null>
  campos_disponiveis?: Record<string, string | null>
  status: 'inserir' | 'complementar' | 'complementado' | 'revisar' | 'ignorado' | 'erro' | 'inserido' | 'nao_importado'
  codigo_cliente?: string | null
  cliente_existente_id?: number | null
  campos_complementar?: Record<string, string | null>
  conflitos?: string[]
  motivos: string[]
  avisos: string[]
}

export type ImportPreview = ImportTable & {
  previa_hash: string
  inserir: number
  complementar: number
  inconsistencias: number
  fontes?: Record<string, ImportTable>
  ocorrencias?: string[]
  ignorados: number
  erros: number
  linhas: ImportRow[]
}

export type ImportReport = {
  concluido: boolean
  mensagem: string
  total: number
  inseridos: number
  complementados: number
  inconsistencias: number
  ignorados: number
  erros: number
  nao_importados: number
  linhas: ImportRow[]
  fontes?: Record<string, ImportTable>
  ocorrencias?: string[]
}

async function upload<T>(action: string, file: File, config: ImportConfig, previewHash?: string, related?: ImportRelatedFiles): Promise<T> {
  const body = new FormData()
  body.set('file', file)
  body.set('configuracao', JSON.stringify(config))
  if (related?.enderecos) body.set('enderecos_file', related.enderecos)
  if (related?.contatos) body.set('contatos_file', related.contatos)
  if (previewHash) {
    body.set('previa_hash', previewHash)
    body.set('confirmado', 'true')
  }
  const headers = await getApiAuthHeaders()
  const response = await fetch(`${apiConfig.baseUrl}/clientes/importacao/${action}`, { method: 'POST', headers, body })
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : null
    throw new Error(typeof detail === 'string' ? detail : `Não foi possível processar a importação (HTTP ${response.status}).`)
  }
  return payload as T
}

export const inspectClientImport = (file: File, config: ImportConfig) => upload<ImportTable>('inspecionar', file, config)
export const previewClientImport = (file: File, config: ImportConfig, related?: ImportRelatedFiles) => upload<ImportPreview>('previa', file, config, undefined, related)
export const confirmClientImport = (file: File, config: ImportConfig, previewHash: string, related?: ImportRelatedFiles) =>
  upload<ImportReport>('confirmar', file, config, previewHash, related)
