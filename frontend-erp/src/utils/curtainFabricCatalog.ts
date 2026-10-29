import type { ApiProduct, CurtainState } from '../types/budget'
import { normalizeSearch } from '../types/budget'

export const DEFAULT_CURTAIN: CurtainState = {
  tecido: '',
  cor: '',
  larguraTecido: 1.5,
  possuiForro: false,
  tipoForro: '',
  modeloPrega: 'WAVE',
  fator: 2.5,
  trilhoLinha: 'MINI',
  trilhoModelo: 'SIMPLES',
  rodizioTipo: 'MINI',
  possuiGancho: true,
  cabecaCm: 10,
  barraCm: 15,
  barraDupla: true,
  usaEntretela: true,
  tipoEntretela: 'TNT',
  fixacaoCortina: 'RODIZIO',
  trilhoComCordas: false,
  sistemaWave: 'PREGA_PRONTA',
  espacamentoBotaoCm: 10,
  aberturaCortina: 'LATERAL_ESQUERDA',
}

export const canonicalFabricSupplier = (value: string | null | undefined) => {
  const raw = String(value ?? '').trim()
  const normalized = normalizeSearch(raw)

  if (!normalized) return ''

  // Aceita A??O, ACAO e tamb?m o legado quebrado A??O.
  if (
    normalized.includes('DISTRIBUIDORA') &&
    (
      normalized.includes('ACAO') ||
      raw.toUpperCase().startsWith('AÃ‡ÃƒO '.toUpperCase()) ||
      normalized.startsWith('A??O') ||
      normalized.startsWith('A O') ||
      normalized.startsWith('AO ')
    )
  ) {
    return 'AÇÃO DISTRIBUIDORA'
  }

  if (
    normalized.includes('JP PERSIANAS') ||
    normalized === 'JP'
  ) {
    return 'JP PERSIANAS'
  }

  return raw
}

const isAcaoCurtainTableFabric = (fabric: ApiProduct) => {
  const raw = fabric as ApiProduct & { linha?: string | null }
  const line = normalizeSearch(raw.linha ?? '')
  const name = normalizeSearch(fabric.nome ?? '')
    .replace(/^\d+(?:-\d+)*\s*-\s*/, '')

  return line === 'CORTINA' &&
    /^(VOIL\b|LINHO VOIL\b|CAMBURI\b|PARATI\b|TECIDO VELUDO\b)/.test(name)
}

export const getFabricSupplier = (fabric: ApiProduct) => {
  const explicit = String(fabric.nome_fornecedor ?? '').trim() ||
    String(fabric.fornecedores ?? '').trim()

  if (explicit) return canonicalFabricSupplier(explicit)

  if (isAcaoCurtainTableFabric(fabric)) {
    return canonicalFabricSupplier('ACAO DISTRIBUIDORA')
  }

  const raw = fabric as ApiProduct & {
    origem?: string | null
  }

  const origem = normalizeSearch(raw.origem ?? '')
  const nome = normalizeSearch(fabric.nome ?? '')

  if (
    origem.includes('ACAO DISTRIBUIDORA') ||
    origem.includes('TABELA DE CORTINAS') ||
    origem.includes('TABELA CORTINA IMPORTADO')
  ) {
    return 'AÇÃO DISTRIBUIDORA'
  }

  if (
    origem.includes('2 - TECIDO.PDF') ||
    nome.includes(' JP ') ||
    nome.startsWith('JP ') ||
    nome.includes('JP157') ||
    nome.includes('JP159') ||
    nome.includes('RATTAN') ||
    nome.includes('ROLLER') ||
    nome.includes('PANDORA')
  ) {
    return 'JP PERSIANAS'
  }

  return ''
}

export const getFabricCollection = (name: string | null | undefined, supplier = '') => {
  // Ação: family comes from the real reference prefix; category CORTINA is not a collection.
  // Fabric reference and variant continue to be extracted independently below.
  if (normalizeSearch(canonicalFabricSupplier(supplier)) === 'ACAO DISTRIBUIDORA') {
    const reference = normalizeSearch(name ?? '')
      .replace(/^\d+(?:-\d+)*\s*[-–—]\s*/, '')
      .replace(/^(?:CORTINA\s+)?(?:TECIDO\s+)?/, '').trim()
    if (['CORTINA', 'TECIDOS PARA CORTINA'].includes(reference)) return ''
    return reference.match(/^[A-Z]+/)?.[0] ?? ''
  }

  let value = String(name ?? '').trim()

  // Remove c?digo inicial
  value = value.replace(/^\d+(?:-\d+)*\s*-\s*/, '')

  // Cadastros no formato FORNECEDOR - COLEÇÃO - VARIAÇÃO (ex.: Wiler).
  const supplierParts = value.split(/\s+[-–—]\s+/)
  if (supplierParts.length >= 3 && supplier &&
    normalizeSearch(supplierParts[0]) === normalizeSearch(supplier)) {
    return supplierParts[1].trim()
  }

  // Remove largura final
  value = value.replace(/\s*-\s*\d+[.,]\d+\s*M\s*$/i, '')

  if (/^TECIDO VELUDO\s*-/i.test(value)) {
    return 'VELUDO'
  }

  // Remove cor/c?digo final
  value = value.replace(/\s*-\s*\(\d+\)\s*[^-]+$/i, '')

  const parts = value
    .split(/\s+-\s+/)
    .map((part) => part.trim())
    .filter(Boolean)

  if (parts.length > 1) {
    const first = parts[0]

    if (
      /^(RATTAN|ROLLER|PANDORA)$/i.test(first)
    ) {
      return first
    }

    if (
      /^(VOIL LISO|VOIL TELA|VOIL XADREZ|VOIL RUSTICO|VOIL R?STICO|LINHO VOIL I|LINHO VOIL II|LINHO VOIL III|LINHO VOIL IV)$/i.test(first)
    ) {
      return first
    }
  }

  return value
    .replace(/^TECIDO\s+/i, '')
    .replace(/^CORTINA\s+TECIDO\s+/i, '')
    .trim()
}

const getLegacyFabricColorLabel = (fabric: ApiProduct) => {
  const rawFabric = fabric as ApiProduct & {
    cor?: string | null
  }

  const explicit = String(rawFabric.cor ?? '').trim()

  if (explicit) return explicit

  let value = String(fabric.nome ?? '').trim()
  value = value.replace(/^\d+(?:-\d+)*\s*-\s*/, '')

  const parts = value.split(/\s+[-–—]\s+/)
  const supplier = getFabricSupplier(fabric)
  if (parts.length >= 3 && supplier &&
    normalizeSearch(parts[0]) === normalizeSearch(supplier)) {
    // Preserva códigos/faixas reais; não inventa cores individuais.
    return parts.slice(2).join(' - ').trim()
  }

  return String(parts[1] ?? '')
    .replace(/^COR\s*/i, '')
    .replace(/[()]/g, '')
    .trim() || 'Sem cor identificada'
}

// Ação's fabric name is read independently, never copied from the collection helper.
// Historical rows with no separate model keep their real base name (e.g. CAMBURI).
const getAcaoFabricBaseName = (fabric: ApiProduct) => {
 const clean = (value: string) => value.trim()
  .replace(/^\d+(?:-\d+)*\s*-\s*/, '')
  .replace(/\s*[-–—]\s*\d+[.,]\d+\s*M\s*$/i, '')
  .replace(/\s*[-–—]\s*\(\d+\)\s*[^–—]+$/i, '')
  .replace(/^TECIDO\s+(?=VELUDO\b)/i, '').trim()
 const source = String(fabric.modelo || fabric.material_tecido || fabric.nome || '')
 let name = clean(source)
 const color = String(fabric.cor ?? getLegacyFabricColorLabel(fabric)).trim()
 if (color) {
  const parts = name.split(/\s+[-–—]\s+/)
  if (parts.length > 1 && normalizeSearch(parts[parts.length-1]).replace(/^\d+\s+/, '') === normalizeSearch(color).replace(/^\d+\s+/, '')) {
   name = parts.slice(0,-1).join(' - ')
  }
 }
 return name
}

// Somente separa sufixos de cor inequívocos; faixas continuam um único cadastro.
export const getFabricVariant = (fabric: ApiProduct) => {
  const supplier = getFabricSupplier(fabric)
  const parts = String(fabric.nome ?? '').trim().split(/\s+[-–—]\s+/)
  if (parts.length >= 3 && supplier &&
    normalizeSearch(parts[0]) === normalizeSearch(supplier)) {
    const value = parts.slice(2).join(' - ').trim()
    const numeric = normalizeSearch(supplier) === 'WILER'
      ? value.match(/^(\d+\.\d+)-(\d+)(?:\s+AO\s+(\d+\.\d+)-(\d+))?(?:\s*\([^)]*\))?$/i)
      : null
    if (numeric && (!numeric[3] || numeric[3] === numeric[1])) {
      return { name: numeric[1], color: numeric[4] ? numeric[2] + ' AO ' + numeric[4] : numeric[2] }
    }
    const match = value.match(/^(.*?)(?:\s*\((\d+(?:\s+(?:AO|E)\s+\d+)*)\)|(?:\s*-\s*(?:COR\s*)?|\s+)(\d+(?:\s+(?:AO|E)\s+\d+)*))$/i)
    return {
      name: match?.[1]?.trim() || value,
      color: String(fabric.cor ?? '').trim() || match?.[2] || match?.[3] || 'Sem cor identificada',
    }
  }
  return {
    name: normalizeSearch(supplier) === 'ACAO DISTRIBUIDORA'
      ? getAcaoFabricBaseName(fabric)
      : getFabricCollection(fabric.nome, supplier),
    color: getLegacyFabricColorLabel(fabric),
  }
}

// Only the visible label changes: full references remain the option values and technical state.
export const getFabricDisplayName = (fabric: ApiProduct) => {
  const reference = getFabricVariant(fabric).name
  const supplier = getFabricSupplier(fabric)
  if (normalizeSearch(supplier) !== 'ACAO DISTRIBUIDORA') return reference
  const family = getFabricCollection(fabric.nome, supplier)
  const label = reference.replace(/^TECIDO\s+/i, '').trim()
  const normalized = normalizeSearch(label)
  if (normalized === family) return '—' // No additional reference is registered; do not invent one.
  return family && normalized.startsWith(family + ' ') ? label.slice(family.length).trim() : reference
}

// Shared selection mapping; full product identity remains in tecido and tecidoProdutoId.
export const normalizeCurtainFabric = (fabric: ApiProduct) => ({
  supplier: getFabricSupplier(fabric),
  collection: getFabricCollection(fabric.nome, getFabricSupplier(fabric)),
  fabricName: getFabricVariant(fabric).name,
  displayFabricName: getFabricDisplayName(fabric),
  color: getFabricVariant(fabric).color,
})

export const getFabricColorLabel = (fabric: ApiProduct) => getFabricVariant(fabric).color

export const curtainFabricCatalog = (catalog: ApiProduct[]) => catalog.filter((fabric) => {
  const raw = fabric as ApiProduct & {
    modelo_tecnico?: string | null
    grupo_tecnico?: string | null
    grupo_produto?: string | null
    linha?: string | null
    tipo_produto?: string | null
  }

  if (normalizeSearch(fabric.situacao ?? '') === 'INATIVO' ||
    (fabric as ApiProduct & { ativo?: boolean }).ativo === false) return false

  // Curtain scope: only the confirmed suppliers, still subject to fabric classification below.
  // This filter is local to curtains and never removes JP from the general product catalog.
  const supplier = normalizeSearch(getFabricSupplier(fabric))
  if (!['ACAO DISTRIBUIDORA', 'WILER'].includes(supplier)) return false

  const group = normalizeSearch(raw.grupo_tecnico ?? '')
  const productGroup = normalizeSearch(raw.grupo_produto ?? '')
  const name = normalizeSearch(fabric.nome ?? '')

  const isVerticalFabric = [
    name,
    group,
    productGroup,
    normalizeSearch(raw.modelo_tecnico ?? ''),
    normalizeSearch(raw.linha ?? ''),
    normalizeSearch(raw.tipo_produto ?? ''),
  ].some((value) => /(^|[^A-Z])VERTICA(?:L|IS)([^A-Z]|$)/i.test(value))

  if (isVerticalFabric) {
    return false
  }

  if ([name, group, productGroup, normalizeSearch(raw.linha ?? '')]
    .some((value) => value.includes('HOSPITALAR'))) {
    return false
  }

  const isCurtainFabricGroup =
    isAcaoCurtainTableFabric(fabric) ||
    group === 'TECIDOS_CORTINA' ||
    group === 'TECIDOS_CORTINAS' ||
    // Compatibilidade histórica: o tipo sozinho não torna componentes em tecidos.
    (productGroup === 'TECIDOS' &&
      normalizeSearch(fabric.tipo_cortina_persiana ?? '') === 'TECIDO PARA CORTINA') ||
    // Classificação existente em grupo_produto, mesmo sem grupo_tecnico.
    /^TECIDOS? CORTINAS?$/.test(productGroup.replace(/_/g, ' ')) ||
    productGroup.includes('TECIDO CORTINA') ||
    productGroup.includes('TECIDO PARA CORTINA')

  if (!isCurtainFabricGroup) {
    return false
  }

  const isExcluded =
    /FITA|TRILHO|VARAO|RODIZIO|MOTOR|MOTC|PONTEIRA|SUPORTE|CURVA|CORREIA|CORRENTE|COMANDO|PERFIL|TAMPA|CLIP|FIO CONTINUO|MANIVELA|HOSPITALAR|CORTINA WAVE|CORTINA MOTORIZADA|APMOTV/.test(
      name
    )

  if (isExcluded) {
    return false
  }

  return true
})


export const fabricState = (current: CurtainState, fabric: ApiProduct, normalized = normalizeCurtainFabric(fabric)): CurtainState => {
    const rawWidth = Number(
      String(fabric.largura ?? '')
        .replace(',', '.')
    )

    let detectedWidth =
      Number.isFinite(rawWidth) && rawWidth > 0
        ? rawWidth
        : undefined

    if (!detectedWidth) {
      const name = normalizeSearch(fabric.nome ?? '')
      const match = name.match(/(?:^|\s)(1[,.]40|1[,.]50|2[,.]80|3[,.]00)(?:M|\s|$)/)

      if (match) {
        detectedWidth = Number(match[1].replace(',', '.'))
      }
    }

    return {
      ...current,
      tecido: fabric.nome ?? '',
      tecidoNome: normalized.fabricName,
      tecidoProdutoId: fabric.id,
      fornecedorTecido: normalized.supplier,
      colecaoTecido: normalized.collection,
      cor: normalized.color,
      larguraTecido:
        detectedWidth === 1.4 ||
        detectedWidth === 1.5 ||
        detectedWidth === 2.8 ||
        detectedWidth === 3
          ? detectedWidth
          : current.larguraTecido,
      simulationKey: undefined,
      result: undefined,
      error: undefined,
    }
}

export const fabricVariants = (catalog: ApiProduct[], state?: CurtainState) => {
 if (!state) return []
 const selected = catalog.find(p => p.id === state.tecidoProdutoId)
 const supplier = canonicalFabricSupplier(state.fornecedorTecido) || (selected ? getFabricSupplier(selected) : '')
 const collection = state.colecaoTecido || (selected ? getFabricCollection(selected.nome, supplier) : '')
 const name = selected ? getFabricVariant(selected).name : state.tecidoNome
 return curtainFabricCatalog(catalog).filter(p => getFabricSupplier(p) === supplier &&
  getFabricCollection(p.nome, supplier) === collection && getFabricVariant(p).name === name)
}

// These are virtual choices: the row always keeps the canonical curtain product ID.
export type CurtainSuggestion = { key: string; label: string; fabric?: ApiProduct; lining?: ApiProduct; normalized?: ReturnType<typeof normalizeCurtainFabric> }
const terms = (s: string) => normalizeSearch(s).split(/\s+/).filter(Boolean)
const matches = (p: ApiProduct, tokens: string[]) => {
 const hay = normalizeSearch([p.nome, p.descricao, getFabricSupplier(p), getFabricCollection(p.nome, getFabricSupplier(p)), getFabricColorLabel(p)].join(' '))
 return tokens.every(t => hay.includes(t))
}
// Hide aggregate Wiler ranges only in suggestion labels; technical data remains intact.
const suggestionColor = (fabric: ApiProduct) => {
 const color = getFabricColorLabel(fabric)
 const range = /^[0-9]+(?:[.,][0-9]+)?[ ]*(?:AO|A|ATE|[-–—])[ ]*[0-9]+(?:[.,][0-9]+)?$/.test(normalizeSearch(color))
 return normalizeSearch(getFabricSupplier(fabric)) === 'WILER' && range ? '' : color
}
export const curtainSuggestions = (catalog: ApiProduct[], query: string): CurtainSuggestion[] => {
 const tokens = terms(query)
 if (!tokens.length) return []
 const fabrics = curtainFabricCatalog(catalog).filter(p => normalizeSearch(p.nome) !== 'CORTINA DE TECIDO')
 // Terms after FORRO belong exclusively to the lining; no catalog combination is invented.
 const forro = tokens.indexOf('FORRO')
 const ignore = ['CORTINA', 'DE', 'TECIDO']
 const main = (forro < 0 ? tokens : tokens.slice(0, forro)).filter(t => !ignore.includes(t))
 const liningTerms = forro < 0 ? [] : tokens.slice(forro + 1).filter(t => !ignore.includes(t))
 const mains = main.length ? fabrics.filter(p => matches(p, main)) : []
 const linings = forro < 0 || !liningTerms.length ? [] : fabrics.filter(p => matches(p, liningTerms))
 if (forro >= 0) {
  if (!linings.length) return []
  return (main.length ? mains : [undefined]).flatMap(fabric => linings.map(lining => ({
   key: `curtain-${fabric?.id ?? 'keep'}-lining-${lining.id}`,
   label: `Cortina de tecido${fabric ? ' · ' + fabric.nome : ''} · Forro: ${lining.nome}`, fabric, lining, normalized: fabric ? normalizeCurtainFabric(fabric) : undefined,
  }))).slice(0, 12)
 }
 const result: CurtainSuggestion[] = main.length ? [] : [{ key: 'curtain-base', label: 'Cortina de tecido' }]
 return [...result, ...(main.length ? mains : fabrics).map(fabric => ({ key: `curtain-${fabric.id}`, label: ['Cortina de tecido', ...new Set([getFabricSupplier(fabric), getFabricCollection(fabric.nome, getFabricSupplier(fabric)), getFabricVariant(fabric).name, suggestionColor(fabric)].filter(Boolean))].join(' · '), fabric, normalized: normalizeCurtainFabric(fabric) }))].slice(0,12)
}
export const applyCurtainSuggestion = (current: CurtainState, suggestion: CurtainSuggestion): CurtainState => ({
 ...(suggestion.fabric ? fabricState(current, suggestion.fabric, suggestion.normalized) : current),
 ...(suggestion.lining ? { possuiForro: true, tipoForro: suggestion.lining.nome } : {}),
 simulationKey: undefined, result: undefined, error: undefined,
})

export const isCurtainBaseProduct = (p: ApiProduct) =>
 normalizeSearch(p.nome ?? '').replace(/\s+/g, ' ').trim() === 'CORTINA DE TECIDO' &&
 !['INATIVO', 'INATIVA'].includes(normalizeSearch(p.status_comercial || p.situacao || 'ATIVO')) &&
 (p as ApiProduct & { ativo?: boolean }).ativo !== false &&
 (!p.modelo_tecnico || normalizeSearch(p.modelo_tecnico) === 'CORTINA')

export const resolveCurtainBase = (catalog: ApiProduct[]) => catalog.filter(isCurtainBaseProduct)
 .sort((a,b) => Number(normalizeSearch(b.tipo_produto ?? '') === 'PRODUTO FABRICADO') -
  Number(normalizeSearch(a.tipo_produto ?? '') === 'PRODUTO FABRICADO') || a.id-b.id)[0]
