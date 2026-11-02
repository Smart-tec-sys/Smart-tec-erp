import { request } from './api'
import type { DadosConsultaCnpj, EnderecoPrincipal } from './cadastroConsultas'
import { cepValido, normalizarCep, ufsBrasil } from './cadastroConsultas'

export type Revenda = EnderecoPrincipal & {
  id: number
  nome: string
  tipo_pessoa?: 'FISICA' | 'JURIDICA' | null
  ativo: boolean
  nome_fantasia?: string | null
  razao_social?: string | null
  documento?: string | null
  email?: string | null
  situacao_cadastral?: string | null
  inscricao_estadual?: string | null
  inscricao_municipal?: string | null
  tipo_contribuinte?: 'CONTRIBUINTE' | 'ISENTO' | 'NAO_CONTRIBUINTE' | null
  isento_ie?: boolean
  telefone?: string | null
  telefone_celular?: string | null
  responsavel?: string | null
  site?: string | null
  percentual_padrao: number | string
  vendedor_responsavel_id?: number | null
  observacao?: string | null
  limite_credito?: number | string | null
  permitir_exceder_limite?: boolean
}

export const revendaInicial = {
  nome: '', tipo_pessoa: '', ativo: 'true', nome_fantasia: '', razao_social: '',
  documento: '', email: '', situacao_cadastral: '', inscricao_estadual: '',
  inscricao_municipal: '', tipo_contribuinte: '', isento_ie: 'false',
  telefone: '', telefone_celular: '', responsavel: '', site: '',
  cep: '', logradouro: '', numero: '', complemento: '', bairro: '', cidade: '', estado: '',
  percentual_padrao: '0', vendedor_responsavel_id: '', observacao: '', limite_credito: '',
  permitir_exceder_limite: 'false',
}
export type CampoRevenda = keyof typeof revendaInicial
export type FormularioRevenda = Record<CampoRevenda, string>
export type RevendaPayload = Omit<Revenda, 'id'>

export const listarRevendas = () => request<Revenda[]>('/representantes/parceiros')
export const obterRevenda = (id: number) => request<Revenda>(`/representantes/parceiros/${id}`)
export const criarRevenda = (payload: RevendaPayload) =>
  request<Revenda>('/representantes/parceiros', { method: 'POST', body: JSON.stringify(payload) })
export const atualizarRevenda = (id: number, payload: Partial<RevendaPayload>) =>
  request<Revenda>(`/representantes/parceiros/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })

export function formularioDaRevenda(revenda?: Revenda): FormularioRevenda {
  const form = { ...revendaInicial }
  if (revenda) {
    for (const campo of Object.keys(form) as CampoRevenda[]) {
      const valor = revenda[campo]
      if (valor != null) form[campo] = String(valor)
    }
  }
  return form
}

export function validarFormularioRevenda(form: FormularioRevenda): string | null {
  if (!form.nome.trim()) return 'Informe o nome de exibição da revenda.'
  const percentual = Number(form.percentual_padrao)
  if (!form.percentual_padrao.trim() || !Number.isFinite(percentual) || percentual < 0 || percentual > 100) return 'O percentual padrão deve ficar entre 0 e 100.'
  const credito = Number(form.limite_credito)
  if (form.limite_credito.trim() && (!Number.isFinite(credito) || credito < 0 || credito > 999999999999.99)) return 'Informe um limite de crédito não negativo dentro do valor permitido.'
  if (form.cep.trim() && !cepValido(form.cep)) return 'Informe um CEP com oito dígitos ou deixe o campo vazio.'
  if (form.estado.trim() && !ufsBrasil.includes(form.estado.trim().toUpperCase())) return 'Informe uma UF brasileira válida ou deixe o campo vazio.'
  if (form.vendedor_responsavel_id && (!Number.isInteger(Number(form.vendedor_responsavel_id)) || Number(form.vendedor_responsavel_id) <= 0)) return 'Selecione um vendedor responsável válido ou deixe o vínculo vazio.'
  if (form.isento_ie === 'true' && form.inscricao_estadual.trim()) return 'Revise a inscrição estadual: isenção e inscrição preenchida são incompatíveis.'
  if (form.isento_ie === 'true' && form.tipo_contribuinte && form.tipo_contribuinte !== 'ISENTO') return 'Revise o tipo de contribuinte e a isenção de IE.'
  if (form.tipo_contribuinte === 'ISENTO' && form.isento_ie !== 'true') return 'Marque a isenção de IE para o tipo de contribuinte Isento.'
  return null
}

export function payloadDaRevenda(form: FormularioRevenda): RevendaPayload {
  const optional = (campo: CampoRevenda) => form[campo].trim() || null
  return {
    nome: form.nome.trim(), tipo_pessoa: form.tipo_pessoa === 'FISICA' || form.tipo_pessoa === 'JURIDICA' ? form.tipo_pessoa : null,
    ativo: form.ativo === 'true', nome_fantasia: optional('nome_fantasia'), razao_social: optional('razao_social'),
    documento: optional('documento'), email: optional('email'), situacao_cadastral: optional('situacao_cadastral'),
    inscricao_estadual: optional('inscricao_estadual'), inscricao_municipal: optional('inscricao_municipal'),
    tipo_contribuinte: form.tipo_contribuinte === 'CONTRIBUINTE' || form.tipo_contribuinte === 'ISENTO' || form.tipo_contribuinte === 'NAO_CONTRIBUINTE' ? form.tipo_contribuinte : null,
    isento_ie: form.isento_ie === 'true', telefone: optional('telefone'), telefone_celular: optional('telefone_celular'),
    responsavel: optional('responsavel'), site: optional('site'), cep: form.cep.trim() ? normalizarCep(form.cep) : null,
    logradouro: optional('logradouro'), numero: optional('numero'), complemento: optional('complemento'),
    bairro: optional('bairro'), cidade: optional('cidade'), estado: form.estado.trim().toUpperCase() || null,
    percentual_padrao: form.percentual_padrao,
    vendedor_responsavel_id: form.vendedor_responsavel_id ? Number(form.vendedor_responsavel_id) : null,
    observacao: optional('observacao'), limite_credito: form.limite_credito.trim() || null,
    permitir_exceder_limite: form.permitir_exceder_limite === 'true',
  }
}

export function camposConsultaCnpj(dados: DadosConsultaCnpj): Partial<FormularioRevenda> {
  const campos: Partial<FormularioRevenda> = {}
  const permitidos = ['razao_social', 'nome_fantasia', 'situacao_cadastral', 'email', 'inscricao_estadual',
    'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'] as const
  for (const campo of permitidos) {
    const valor = dados[campo]
    if (typeof valor === 'string' && valor.trim()) campos[campo] = valor.trim()
  }
  if (dados.telefone_comercial?.trim()) campos.telefone = dados.telefone_comercial.trim()
  return campos
}

export function camposConsultaCep(dados: EnderecoPrincipal): Partial<FormularioRevenda> {
  const campos: Partial<FormularioRevenda> = {}
  for (const campo of ['cep', 'logradouro', 'bairro', 'cidade', 'estado'] as const) {
    const valor = dados[campo]
    if (typeof valor === 'string' && valor.trim()) campos[campo] = valor.trim()
  }
  return campos
}
