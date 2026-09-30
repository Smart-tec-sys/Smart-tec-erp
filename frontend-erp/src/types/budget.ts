import type { RomanaState } from './romana'
import type { RomanaTetoState } from './romana_teto'
import type { RoloState } from './rolo'
import type { DoubleVisionState } from './double_vision'
export type CommercialType = 'Decorador' | 'Varejo' | 'Consumidor final'
export type CommercialProfile = 'DECORADOR' | 'VAREJO' | 'CONSUMIDOR_FINAL'
export type ApiProduct = {
  id: number
  nome: string
  codigo?: string | null
  codigo_interno?: string | null
  codigo_barras?: string | null
  grupo_produto?: string | null
  grupo_tecnico?: string | null
  modelo_tecnico?: string | null
  familia_tecnica?: string | null
  produto_base?: string | null
  variacao_cor?: string | null
  variacao_lado?: string | null
  variacao_tamanho?: string | null
  varia_cor?: boolean | null
  cor_componente?: string | null
  cor?: string | null
  unidade?: string | null
  unidade_venda?: string | null
  unidade_compra?: string | null
  unidade_controle?: string | null
  comprimento_compra?: number | string | null
  saldo_metros?: number | string | null
  tipo_produto?: string | null
  movimenta_estoque?: string | null
  habilitar_nota_fiscal?: string | null
  possui_variacoes?: string | null
  possui_composicao?: string | null
  situacao?: string | null
  status_comercial?: string | null
  linha?: string | null
  modelo?: string | null
  tipo_cortina_persiana?: string | null
  material_tecido?: string | null
  largura?: number | string | null
  altura?: number | string | null
  comprimento?: number | string | null
  peso?: number | string | null
  descricao?: string | null
  observacoes?: string | null
  valor_custo?: number | string | null
  despesas_acessorias?: number | string | null
  outras_despesas?: number | string | null
  custo_final?: number | string | null
  margem_lucro?: number | string | null
  valor_venda?: number | string | null
  estoque_minimo?: number | string | null
  estoque_maximo?: number | string | null
  estoque_atual?: number | string | null
  ncm?: string | null
  cest?: string | null
  origem?: string | null
  fornecedores?: string | null
  nome_fornecedor?: string | null
  codigo_fornecedor?: string | null
}
export type ApiClient = {
  id: number
  nome: string
  situacao?: string | null
  tipo?: string | null
  email?: string | null
  telefone_comercial?: string | null
  telefone_celular?: string | null
  documento?: string | null
  site?: string | null
  vendedor_responsavel?: string | null
  cep?: string | null
  logradouro?: string | null
  numero?: string | null
  complemento?: string | null
  bairro?: string | null
  cidade?: string | null
  estado?: string | null
  limite_credito?: number | null
  permitir_exceder?: boolean | null
  observacoes?: string | null
}
export type ApiBudgetItem = { dados_tecnicos?: { cortina?: CurtainState } | null; id?:number; tipo_item:string; produto_id?:number|null; descricao:string; codigo_interno?:string|null; grupo_tecnico?:string|null; modelo_tecnico?:string|null; unidade?:string|null; quantidade:number; largura:number; altura:number; area:number; preco_unitario:number; desconto:number; subtotal:number; observacao_item?:string|null; cor?:string|null }
export type ApiBudget = { id:number; numero:string; cliente_id:number; cliente_nome?:string|null; perfil_comercial?:CommercialProfile; status:string; validade?:string|null; total:number; desconto:number; total_final:number; observacao?:string|null; observacao_interna?:string|null; criado_em?:string|null; atualizado_em?:string|null; itens:ApiBudgetItem[] }
export type BudgetPayload = Omit<ApiBudget, 'id'|'numero'|'cliente_nome'|'criado_em'|'atualizado_em'>
export type CurtainState = {
  tecido: string
  tecidoProdutoId?: number
  tecidoNome?: string
  fornecedorTecido?: string
  colecaoTecido?: string
  cor: string
  larguraTecido: 1.4 | 1.5 | 2.8 | 3
  possuiForro: boolean
  tipoForro?: string
  modeloPrega: string
  fator: number
  trilhoLinha?: 'MINI' | 'MAX' | 'MASTER'
  trilhoModelo?: string
  rodizioTipo?: 'MINI' | 'MAX' | 'BOTAO'
  possuiGancho?: boolean
  cabecaCm: number
  barraCm: 0 | 5 | 10 | 15 | 20 | 25 | 30 | 35 | 40 | 45 | 50
  barraDupla: boolean
  usaEntretela: boolean
  tipoEntretela: 'TNT'
  fixacaoCortina: 'RODIZIO' | 'GANCHO'
  trilhoComCordas: boolean
  sistemaWave: 'PREGA_PRONTA' | 'BOTAO'
  espacamentoBotaoCm: 7 | 10
  aberturaCortina:
    | 'LATERAL_ESQUERDA'
    | 'LATERAL_DIREITA'
    | 'CENTRAL'
    | 'DUAS_LATERAIS'
  observacaoTecnica?: string

  simulationKey?: string
  error?: string
  result?: {
    desenvolvimento_m: number
    custo_cadastrado?: number | null
    preco_unitario?: number
    subtotal?: number
    preco_disponivel?: boolean
    origem_preco?: string
    avisos?: string[]
    quantidade_alturas: number

    tecido: {
      quantidade_alturas: number
      cabeca_cm: number
      barra_cm: number
      barra_dupla: boolean
      tipo_barra: string
      consumo_barra_m: number
      consumo_por_altura_m: number
      consumo_total_ml: number
      status_calculo: string
    }

    entretela: {
      usa: boolean
      tipo: string
      quantidade_ml: number
      status_calculo: string
    }

    mao_de_obra: {
      quantidade_alturas: number
      valor_por_altura: number
      total: number
    }

    trilho: {
      linha?: string | null
      modelo?: string | null
      quantidade_ml: number
    }

    rodizios: {
      tipo?: string | null
      quantidade_cortina_un: number
      quantidade_trilho_un: number
      quantidade_total_un: number
      regra: string
    }

    ganchos: {
      quantidade_cortina_un: number
      regra: string
    }

    wave: {
      aplicavel: boolean
      sistema?: string | null
      abertura?: string | null
      quantidade_folhas: number
      pontos_por_folha: number
      quantidade_pontos_total: number
      espacamento_cm?: number | null
      quantidade_botoes: number
      paridade_por_folha?: string | null
    }
  }
}

export type BudgetProduct = { id:number; productId:number|null; product:string; code:string; family:string; groupTechnical:string; modelTechnical:string; unit:string; color:string; details:string; quantity:number; width:string; height:string; price:number; discount:number; romanaKind?: 'MANUAL' | 'MOTORIZADA' | null; romana?: RomanaState; romanaTetoKind?: 'MANUAL_BASTAO' | 'MANUAL_CORRENTE' | 'MOTORIZADA' | null; romanaTeto?: RomanaTetoState; roloKind?: 'MANUAL' | 'MOTORIZADA' | null; rolo?: RoloState; doubleVisionKind?: 'MANUAL' | 'MOTORIZADA' | null; doubleVision?: DoubleVisionState; curtain?: CurtainState; acionamento?: string; acao_acionamento?: string; lado_comando?: string; comprimento_bastao?: string; comprimento_corrente_sem_fim?: string }
export type BudgetService = { id:number; service:string; details:string; quantity:number; value:number; discount:number }
export type BudgetInstallment = { id:number; dueDate:string; description:string; value:number; paymentMethod:string; note:string }
export const formatCurrency = (value:number) => value.toLocaleString('pt-BR', { style:'currency', currency:'BRL' })
export const parseDecimal = (value:string) => Number(value.replace(',', '.')) || 0
export const normalizeSearch = (value:string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim()
export const productColor = (product:ApiProduct) => product.cor_componente || product.cor || product.variacao_cor || ''
export const productCost = (product:ApiProduct) => Number(product.custo_final || product.valor_custo || product.valor_venda || 0)
export const commercialPercent:Record<CommercialType,number> = { Decorador:50, Varejo:100, 'Consumidor final':150 }
export const roundHalfUp = (value:number) => Math.round((value + Number.EPSILON) * 100) / 100
export const commercialPrice = (product:ApiProduct, type:CommercialType) => roundHalfUp(productCost(product) * (1 + commercialPercent[type] / 100))
export const usesArea = (model:string) => ['ROLO','ROLÔ','DOUBLE_VISION','DOUBLE VISION','ROMANA','ROMANA_TETO','ROMANA DE TETO'].some(value=>normalizeSearch(model).startsWith(normalizeSearch(value)))
export const productLineSubtotal = (item:BudgetProduct) => item.romanaKind ? Number(item.romana?.result?.subtotal || 0) : item.romanaTetoKind ? Number(item.romanaTeto?.result?.subtotal || 0) : item.roloKind ? Number(item.rolo?.result?.subtotal || 0) : item.doubleVisionKind ? Number(item.doubleVision?.result?.subtotal || 0) : item.curtain?.result?.preco_disponivel ? Number(item.curtain.result.subtotal || 0) : roundHalfUp(Math.max(0,(usesArea(item.modelTechnical)?parseDecimal(item.width)*parseDecimal(item.height)*item.quantity:item.quantity)*item.price-item.discount))
export const profileLabel:Record<CommercialProfile,CommercialType>={DECORADOR:'Decorador',VAREJO:'Varejo',CONSUMIDOR_FINAL:'Consumidor final'}
export const emptyProduct = (id:number):BudgetProduct => ({ id, productId:null, product:'', code:'', family:'', groupTechnical:'', modelTechnical:'', unit:'', color:'', details:'', quantity:1, width:'0,00', height:'0,00', price:0, discount:0, romanaKind:undefined, romana:undefined, romanaTetoKind:undefined, romanaTeto:undefined, roloKind:undefined, rolo:undefined, doubleVisionKind:undefined, doubleVision:undefined, curtain:undefined, acionamento:undefined, lado_comando:undefined, comprimento_bastao:undefined, comprimento_corrente_sem_fim:undefined })

export type ClientCompleteness = {
  isComplete: boolean
  missingGroups: string[]
  missingFields: string[]
}

export function getClientCompleteness(client: ApiClient): ClientCompleteness {
  const missingFields: string[] = []
  const missingGroups: string[] = []

  // Documento
  if (!client.documento?.trim()) {
    missingFields.push('documento')
  }

  // Email
  if (!client.email?.trim()) {
    missingFields.push('email')
  }

  // Telefone (pelo menos um)
  const hasPhone = client.telefone_comercial?.trim() || client.telefone_celular?.trim()
  if (!hasPhone) {
    missingFields.push('telefone')
  }

  // Endereço - todos os campos obrigatórios
  const addressFields = [
    { key: 'cep', label: 'CEP' },
    { key: 'logradouro', label: 'Logradouro' },
    { key: 'numero', label: 'Número' },
    { key: 'bairro', label: 'Bairro' },
    { key: 'cidade', label: 'Cidade' },
    { key: 'estado', label: 'Estado' }
  ] as const

  let addressMissing = false
  for (const field of addressFields) {
    if (!client[field.key]?.trim()) {
      missingFields.push(field.label.toLowerCase())
      addressMissing = true
    }
  }
  if (addressMissing) {
    missingGroups.push('endereço')
  }

  // Agrupar campos faltantes
  if (missingFields.includes('documento')) {
    missingGroups.push('documento')
  }
  if (missingFields.includes('email')) {
    missingGroups.push('contato')
  }
  if (missingFields.includes('telefone')) {
    if (!missingGroups.includes('contato')) {
      missingGroups.push('contato')
    }
  }

  // Remover duplicatas
  const uniqueGroups = [...new Set(missingGroups)]

  return {
    isComplete: missingFields.length === 0,
    missingGroups: uniqueGroups,
    missingFields
  }
}

export function formatClientCompletenessMessage(client: ApiClient): string {
  const { isComplete, missingGroups } = getClientCompleteness(client)
  if (isComplete) return ''
  return `Cadastro incompleto — faltam ${missingGroups.join(', ')}.`
}

export type ProductCompleteness = {
  isComplete: boolean
  missingGroups: string[]
  missingFields: string[]
}

export function getProductCompleteness(product: ApiProduct): ProductCompleteness {
  const missingFields: string[] = []
  const missingGroups: string[] = []

  // Nome (obrigatório)
  if (!product.nome?.trim()) {
    missingFields.push('nome')
  }

  // Unidade de venda
  if (!product.unidade_venda?.trim()) {
    missingFields.push('unidade de venda')
  }

  // Custo
  const hasCost = (product.custo_final !== null && product.custo_final !== undefined && Number(product.custo_final) > 0) ||
                  (product.valor_custo !== null && product.valor_custo !== undefined && Number(product.valor_custo) > 0) ||
                  (product.valor_venda !== null && product.valor_venda !== undefined && Number(product.valor_venda) > 0)
  if (!hasCost) {
    missingFields.push('custo/valor')
  }

  // Cor / variação (campos que existem no tipo atual)
  if (!product.cor?.trim() && !product.cor_componente?.trim() && !product.variacao_cor?.trim()) {
    missingFields.push('cor/variação')
  }

  // Dados técnicos (campos que existem no tipo atual)
  if (!product.grupo_tecnico?.trim()) {
    missingFields.push('grupo técnico')
  }
  if (!product.modelo_tecnico?.trim()) {
    missingFields.push('modelo técnico')
  }
  if (!product.familia_tecnica?.trim()) {
    missingFields.push('família técnica')
  }

  // Agrupar campos faltantes
  if (missingFields.includes('nome')) {
    missingGroups.push('identificação')
  }
  if (missingFields.includes('unidade de venda')) {
    missingGroups.push('comercial')
  }
  if (missingFields.includes('custo/valor')) {
    missingGroups.push('preço')
  }
  if (missingFields.includes('cor/variação')) {
    missingGroups.push('cor/variação')
  }
  if (missingFields.includes('grupo técnico') || missingFields.includes('modelo técnico') || missingFields.includes('família técnica')) {
    missingGroups.push('dados técnicos')
  }

  const uniqueGroups = [...new Set(missingGroups)]

  return {
    isComplete: missingFields.length === 0,
    missingGroups: uniqueGroups,
    missingFields
  }
}

export function formatProductCompletenessMessage(product: ApiProduct): string {
  const { isComplete, missingGroups } = getProductCompleteness(product)
  if (isComplete) return ''
  return `Cadastro incompleto — faltam ${missingGroups.join(', ')}.`
}
