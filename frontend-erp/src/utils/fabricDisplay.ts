import { normalizeSearch, type ApiProduct } from '../types/budget'

// Agrupamento exclusivamente visual; estoque, preço e identidade do SKU permanecem intactos.
const normalizeField = (value: unknown) => normalizeSearch(String(value ?? ''))
  .replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim()
const supplyMeasure = /^\d+(?:[.,]\d+)?\s*(?:M|ML|METROS?|METROS? LINEARES?)$/i
// Cores inequívocas observadas no cadastro; não interpretar códigos ou larguras como cor.
const displayColor = /^(?:CINZA|BEGE|BRANCO|BRANCA|PRETO|PRETA|CREME|MARROM|LINHO|PALHA|PRATA|AMENDOA|FENDI|GELO|ALPINO|WHITE|BLACK|GREY|GRAY|IVORY|LINEN|NAVY|PEACH|BROWN|MESCLA|NATURAL|OFF WHITE|OFF WHAIT|DK GREY|LT GREY|INK BLACK|AZUL ROYAL|CHOCOLATE|TINTO (?:BEGE|PALHA|PRATA))$/i
const trailingColor = /\b(DK GREY|LT GREY|INK BLACK|AZUL ROYAL|OFF WHAIT|OFF WHITE|TINTO (?:BEGE|PALHA|PRATA)|BRANCO|BRANCA|BEGE|PRETO|PRETA|CINZA|WHITE|BLACK|GREY|GRAY|IVORY|CREME|MARROM|FENDI|GELO|AMENDOA|ALPINO|LINHO|LINEN|NATURAL|PALHA|PRATA|NAVY|PEACH|BROWN|MESCLA|CHOCOLATE)\s*$/i

// Referência da cartela, não uma cor. Apenas inteiros em parênteses.
export function fabricReference(product: ApiProduct): string {
  if (!isFabricProduct(product)) return ''
  const name = product.nome.trim()
  const numeric = name.match(/\((\d{1,3})\)\s*$/)
  if (numeric) return numeric[1]
  const combined = name.match(/\((\d{1,3})\s*\/\s*\d+(?:[.,]\d+)?\)\s*$/)
  if (combined) return combined[1]
  // "TEC HOUSTON BK - BEGE 812 - 2,50M": 812 é referência do SKU, não cor.
  const parts = name.split(/\s+[-–—]\s+/)
  if (parts.length < 3 || !supplyMeasure.test(parts[parts.length - 1])) return ''
  const segment = parts[parts.length - 2]
  const code = segment.match(/^(?:BEGE|BRANCO|CINZA|PRETO|WHITE|BLACK|GREY|FENDI|MARROM|CREME|NATURAL|AMENDOA|ALPINO|LINEN|GELO)\s+(\d{3,4})$/i)
  if (!code) return ''
  const base = parts.slice(0,-2).join(' - ')
  if (/^(?:TECIDO|TEC|TECDO)\s+(?:BK|TR|SC|JP)$/i.test(base)) return ''
  return code[1]
}

function inferredColor(name: string): string {
  // Ex.: "AQUARELA (GREY / 2,50)".
  const coloredWidth = name.match(/\(([^()/]+?)\s*\/\s*(\d+(?:[.,]\d+)?)\)\s*$/)
  if (coloredWidth && displayColor.test(coloredWidth[1].trim())) {
    const stem = name.slice(0, coloredWidth.index)
    const otherColor = stem.match(trailingColor)
    if (!otherColor || normalizeField(otherColor[1]) === normalizeField(coloredWidth[1])) return coloredWidth[1].trim()
  }
  // Ex.: "TECIDO BK - PINPOINT BEGE - 1,83M".
  const last = name.match(/\s+[-–—]\s+([^–—]+?)\s+[-–—]\s+(\d+(?:[.,]\d+)?\s*(?:M|ML|METROS?))\s*$/i)?.[1]?.trim()
  if (!last) {
    // "TECIDO BK - PINPOINT CINZA 3,00M": largura sem segundo hífen.
    const trailingWidth = name.match(/^(.*?)\s+(\d+(?:[.,]\d+)?)\s*M\s*$/i)
    const stem = trailingWidth?.[1]?.trim() || ''
    const suffix = stem.match(trailingColor)
    return suffix && stem.slice(0, suffix.index).trim() ? suffix[1] : ''
  }
  const colorCode = last.match(/^(BEGE|BRANCO|CINZA|PRETO|WHITE|BLACK|GREY|FENDI|MARROM|CREME|NATURAL|AMENDOA|ALPINO|LINEN|GELO)\s+(\d{3,4})$/i)
  if (colorCode) {
    const base = name.slice(0, name.lastIndexOf(last)).replace(/\s+[-–—]\s*$/, '').trim()
    if (!/^(?:TECIDO|TEC|TECDO)\s+(?:BK|TR|SC|JP)$/i.test(base)) return colorCode[1]
  }
  if (displayColor.test(last)) return last
  const qualified = last.match(/\b(DK GREY|LT GREY|INK BLACK|AZUL ROYAL|OFF WHAIT|OFF WHITE|BRANCO|BRANCA|BEGE|PRETO|PRETA|CINZA|WHITE|BLACK|GREY|GRAY|IVORY|CREME|MARROM|FENDI|GELO|AMENDOA|ALPINO|LINHO|LINEN|NATURAL|PALHA|PRATA|NAVY|PEACH|BROWN|MESCLA)\s+(STANDARD|PREMIUM)\s*$/i)
  if (qualified) return qualified[1]
  const trailing = last.match(trailingColor)
  // Não apagar códigos (ex.: 5101, 812) nem medidas antes da cor.
  if (trailing && last.slice(0, trailing.index).trim() && !/\d$/.test(last.slice(0, trailing.index).trim())) return trailing[1]
  return ''
}

export function fabricColor(product: ApiProduct): string {
  const structured = product.variacao_cor?.trim() || product.cor?.trim() || product.cor_componente?.trim()
  if (structured) return structured
  if (!isFabricProduct(product)) return ''
  return inferredColor(product.nome.trim())
}

// O catálogo legado contém persianas acabadas dentro de grupos técnicos chamados TECIDOS.
// Somente um tipo FABRICADO explícito + nome de produto acabado prevalece sobre o grupo.
export function isClearlyFinishedProduct(product: ApiProduct): boolean {
  const type = normalizeField(product.tipo_produto)
  const name = normalizeField(product.nome)
  return /^(?:PRODUTO FABRICADO|PRODUTO ACABADO|PERSIANA ACABADA)$/.test(type)
    && /^(?:ROMANA|ROLO|PERSIANA|DOUBLE VISION|CORTINA|TOLDO)(?: |$)/.test(name)
}

// Prefixos que identificam componentes mesmo quando o grupo legado diz "TECIDOS".
export function isClearlyAccessory(product: ApiProduct): boolean {
  const name = normalizeField(product.nome)
  return /^(?:EIXO|FITA|BANDO|PRESILHA|CABECEIRA|BRACO|TUBO|SUPORTE|MOTOR|RODIZIO|TRILHO|PERFIL|CORRENTE|BUCHA|PONTEIRA|ROLDANA|CARRETEL|PARAFUSO)(?: |$)/.test(name)
}

export function isFabricProduct(product: ApiProduct): boolean {
  if (isClearlyFinishedProduct(product) || isClearlyAccessory(product)) return false

  const technical = [product.grupo_tecnico, product.familia_tecnica, product.grupo_produto]
    .map(normalizeField)
  if (technical.some(value => /(?:^| )TECIDOS?(?: |$)/.test(value))) return true
  const type = normalizeField(product.tipo_produto)
  if (/(?:^| )(?:PRODUTO ACABADO|PERSIANA ACABADA)(?: |$)/.test(type)) return false
  if (technical.some(value => /(?:^| )(?:PERSIANAS?|CORTINAS? PRONTAS?)(?: |$)/.test(value))) return false
  const name = normalizeField(product.nome)
  if (/^(?:PERSIANA|CORTINA PRONTA) /.test(name)) return false
  if (/(?:^| )TECIDOS?(?: |$)/.test(name)) return true
  const model = normalizeField(product.modelo_tecnico)
  if (/^(?:ROLO|ROMANA|ROMANA TETO|DOUBLE VISION)(?: |$)/.test(model)) return false
  return /(?:^| )(?:SCREEN|BLACKOUT)(?: |$)/.test(name)
}

export function fabricDisplay(product: ApiProduct) {
  const raw = product.nome.trim()
  if (!isFabricProduct(product)) {
    // Ex.: ROMANA BK BRISK (AMENDOA) é produto acabado, com cor escolhida por SKU.
    const color = normalizeField(product.variacao_cor || product.cor || product.cor_componente)
    const suffix = raw.match(/\s*\(([^()]*)\)\s*$/)
    const label = isClearlyFinishedProduct(product) && suffix && color && normalizeField(suffix[1]) === color
      ? raw.slice(0, suffix.index).trim() : raw
    return { name: label, width: '', fabric: false }
  }
  const color = normalizeField(fabricColor(product))
  let label = raw
  let width = ''
  const refWidth = label.match(/\s*\((\d{1,3})\s*\/\s*(\d+(?:[.,]\d+)?)\)\s*$/)
  if (refWidth && fabricReference(product) === refWidth[1]) {
    label = label.slice(0, refWidth.index).trim()
    width = refWidth[2] + ' M'
  }
  const trailingWidth = label.match(/^(.*?)\s+(\d+(?:[.,]\d+)?)\s*M\s*$/i)
  if (trailingWidth && color && trailingWidth[1].trim()) {
    const colored = trailingWidth[1].match(trailingColor)
    if (colored && normalizeField(colored[1]) === color && trailingWidth[1].slice(0, colored.index).trim()) {
      label = trailingWidth[1].slice(0, colored.index).trim()
      width = trailingWidth[2] + ' M'
    }
  }
  const slashWidth = label.match(/\s*\(([^()/]+?)\s*\/\s*(\d+(?:[.,]\d+)?)\)\s*$/)
  if (slashWidth && color && normalizeField(slashWidth[1]) === color) {
    label = label.slice(0, slashWidth.index).trim()
    width = slashWidth[2] + ' M'
  }
  const suffix = label.match(/\s*\(([^()]*)\)\s*$/)
  const reference = fabricReference(product)
  if (suffix && ((color && normalizeField(suffix[1]) === color) ||
      displayColor.test(suffix[1].trim()) || (reference && suffix[1].trim() === reference))) {
    label = label.slice(0, suffix.index).trim()
  }
  const parts = label.split(/\s+[-–—]\s+/)
  while (parts.length > 1) {
    const last = parts[parts.length - 1].trim()
    const reference = fabricReference(product)
    if (color && reference && normalizeField(last) === normalizeField(color + ' ' + reference)) {
      parts.pop()
      break
    }
    if (supplyMeasure.test(last)) { width = last; parts.pop(); continue }
    if (color && (normalizeField(last) === color || displayColor.test(last))) {
      parts.pop()
      continue
    }
    // Preservar nome da coleção e eventuais qualificadores (STANDARD/PREMIUM).
    const escaped = color.replace(/[.*+?^$()|[\]\\]/g, '\\$&')
    const qualifier = color && last.match(new RegExp('^(.*?)\\s+' + escaped + '\\s+(STANDARD|PREMIUM)$', 'i'))
    if (qualifier) {
      parts[parts.length - 1] = (qualifier[1] + ' ' + qualifier[2]).trim()
      break
    }
    const trailing = color && last.match(new RegExp('^(.*?)\\s+' + escaped + '$', 'i'))
    if (trailing && trailing[1].trim()) {
      parts[parts.length - 1] = trailing[1].trim()
    }
    break
  }
  let name = parts.join(' - ').trim()
  if (color && normalizeField(name).endsWith(' ' + color)) {
    const words = name.split(/\s+/)
    const colorWords = color.split(/\s+/).length
    if (words.length > colorWords) name = words.slice(0, -colorWords).join(' ')
  }
  // Existem tecidos com a largura dentro do nome (ex.: "TECIDO BK BRISK 1,80M"),
  // enquanto outros guardam essa informação só no campo largura. Priorizar a
  // largura explícita na descrição para não separar cores do mesmo tecido.
  const namedWidth = name.match(/(?:^|\s)(\d+(?:[.,]\d+)?\s*(?:M|ML|METROS?))\s*$/i)
  return {
    name,
    width: width || (namedWidth ? namedWidth[1] : '') ||
      (Number(product.largura) > 0 ? String(product.largura) + ' m' : ''),
    fabric: true,
  }
}

function normalizedWidth(value: string) {
  const match = value.match(/^(\d+(?:[.,]\d+)?)\s*(?:M|ML|METROS?|METROS? LINEARES?)$/i)
  return match ? String(Number(match[1].replace(',', '.'))) + ' M' : normalizeField(value)
}

export function fabricVariantKey(product: ApiProduct) {
  const view = fabricDisplay(product)
  return JSON.stringify([
    normalizeField(view.name), normalizeField(product.produto_base),
    normalizeField(product.nome_fornecedor || product.fornecedores || ''),
    normalizeField(product.grupo_tecnico), normalizeField(product.familia_tecnica),
    normalizeField(product.modelo_tecnico), normalizeField(product.tipo_produto),
    normalizeField(product.unidade_venda || product.unidade), normalizedWidth(view.width),
    (product as ApiProduct & { empresa_id?: number | null }).empresa_id ?? null,
  ])
}

// Identidade própria para produtos acabados, independente da identificação dos tecidos.
export function commercialVariantKey(product: ApiProduct) {
  if (!isClearlyFinishedProduct(product)) return null
  const view = fabricDisplay(product)
  const base = normalizeField(view.name)
  // Sem cor estruturada ou nome-base confiável, não agrupar SKUs acabados.
  const raw = normalizeField(product.nome)
  if (!base || base === raw || !fabricColor(product)) return null
  return JSON.stringify([
    base, product.produto_base, product.familia_tecnica, product.modelo_tecnico,
    product.grupo_tecnico, product.tipo_produto, product.unidade_venda ?? product.unidade,
    (product as ApiProduct & { empresa_id?: number | null }).empresa_id ?? null,
  ].map(normalizeField))
}

export type FabricCollection = {
  key: string
  name: string
  width: string
  representative: ApiProduct
  variants: ApiProduct[]
  colors: Array<{ color: string; variants: ApiProduct[] }>
}

// Uma coleção por entrada na busca, com as cores e SKUs preservados.
export function groupFabricCollections(products: ApiProduct[]): FabricCollection[] {
  const collections = new Map<string, FabricCollection>()
  for (const product of products) {
    const view = fabricDisplay(product)
    const groupableFabric = view.fabric && !!(fabricColor(product) || fabricReference(product) || product.produto_base?.trim())
    const finishedKey = !view.fabric ? commercialVariantKey(product) : null
    const key = groupableFabric ? 'fabric:' + fabricVariantKey(product)
      : finishedKey ? 'finished:' + finishedKey
      : 'product:' + String((product as ApiProduct & { empresa_id?: number | null }).empresa_id ?? '') + ':' + product.id
    let collection = collections.get(key)
    if (!collection) {
      collection = { key, name: view.name, width: view.width, representative: product, variants: [], colors: [] }
      collections.set(key, collection)
    }
    collection.variants.push(product)
    const color = fabricColor(product) || (fabricReference(product) ? 'Ref. ' + fabricReference(product) : '')
    const colorKey = normalizeField(color)
    const matching = collection.colors.find(c => normalizeField(c.color) === colorKey)
    if (matching) matching.variants.push(product)
    else collection.colors.push({ color, variants: [product] })
  }
  return [...collections.values()]
}

// Não perde SKUs nas telas que ainda usam a interface antiga.
export function groupFabricSuggestions(products: ApiProduct[]): ApiProduct[] {
  return groupFabricCollections(products).flatMap(group => group.variants)
}
