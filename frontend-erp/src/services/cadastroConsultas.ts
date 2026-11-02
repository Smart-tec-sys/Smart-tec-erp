import { request } from './api'

export type EnderecoPrincipal = {
  cep?: string | null
  logradouro?: string | null
  numero?: string | null
  complemento?: string | null
  bairro?: string | null
  cidade?: string | null
  estado?: string | null
}

export type DadosConsultaCnpj = EnderecoPrincipal & {
  razao_social?: string | null
  nome_fantasia?: string | null
  situacao_cadastral?: string | null
  email?: string | null
  telefone_comercial?: string | null
  inscricao_estadual?: string | null
}

export type ResultadoConsulta<T> = {
  dados: T
  fonte: string
  consultado_em: string
}

export const consultarCnpj = (documento: string) =>
  request<ResultadoConsulta<DadosConsultaCnpj>>('/consultas/cnpj', {
    method: 'POST', body: JSON.stringify({ documento }),
  })

export const consultarCep = (cep: string) =>
  request<ResultadoConsulta<Pick<EnderecoPrincipal, 'cep' | 'logradouro' | 'bairro' | 'cidade' | 'estado'>>>('/consultas/cep', {
    method: 'POST', body: JSON.stringify({ cep }),
  })

export function normalizarCnpj(value: string): string {
  return value.replace(/[.\-/\s]/g, '').toUpperCase()
}

export function cnpjValido(value: string): boolean {
  const normalized = normalizarCnpj(value)
  if (!/^[A-Z0-9]{12}\d{2}$/.test(normalized) || /^(\d)\1{13}$/.test(normalized)) return false
  const calculate = (base: string) => {
    let weight = base.length - 7
    let sum = 0
    for (const character of base) {
      sum += (character.charCodeAt(0) - 48) * weight
      weight = weight === 2 ? 9 : weight - 1
    }
    const remainder = sum % 11
    return String(remainder < 2 ? 0 : 11 - remainder)
  }
  const first = calculate(normalized.slice(0, 12))
  return normalized.slice(12) === first + calculate(normalized.slice(0, 12) + first)
}

export function normalizarCep(value: string): string {
  return value.replace(/[-\s]/g, '')
}

export const cepValido = (value: string) => /^\d{8}$/.test(normalizarCep(value))
export const ufsBrasil = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']

export function consultaAindaAtual(
  origem: 'cnpj' | 'cep', chave: string, requestId: number,
  atual: { requestId: number; documento: string; cep: string; tipo_pessoa: string },
): boolean {
  return requestId === atual.requestId && (origem === 'cnpj'
    ? atual.tipo_pessoa === 'JURIDICA' && normalizarCnpj(atual.documento) === chave
    : normalizarCep(atual.cep) === chave)
}
