import { normalizeSearch, type ApiProduct } from '../types/budget'

// Agrupamento exclusivamente visual; estoque, preço e identidade do SKU permanecem intactos.
const normalizeField = (value: unknown) => normalizeSearch(String(value ?? ''))
  .replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim()
const supplyMeasure = /^\d+(?:[.,]\d+)?\s*(?:M|ML|METROS?|METROS? LINEARES?)$/i
// Cores inequívocas observadas no cadastro; não interpretar códigos ou larguras como cor.
const displayColor = /^(?:CINZA|BEGE|BRANCO|BRANCA|PRETO|PRETA|CREME|MARROM|LINHO|PALHA|PRATA|AMENDOA|FENDI|GELO|ALPINO|WHITE|BLACK|GREY|GRAY|IVORY|LINEN|NAVY|PEACH|BROWN|MESCLA|NATURAL|OFF WHITE|OFF WHAIT|TINTO (?:BEGE|PALHA|PRATA))$/i

export function fabricColor(product: ApiProduct): string {
  const structured = product.variacao_cor?.trim() || product.cor?.trim() || product.cor_componente?.trim()
  if (structured) return structured
  if (!isFabricProduct(product)) return ''

  // Exemplos reais sem cor estruturada: "TEC PICASSO BK - AMENDOA - 2,50M".
  // Fallback intencionalmente estrito: nomes genéricos e códigos numéricos não são cores.
  const match = product.nome.trim().match(/\s+[-–—]\s+([^–—]+?)\s+[-–—]\s+(\d+(?:[.,]\d+)?\s*(?:M|ML|METROS?))\s*$/i)
  return match && displayColor.test(match[1].trim()) ? match[1].trim() : ''
}

export function isFabricProduct(product: ApiProduct): boolean {
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
  if (!isFabricProduct(product)) return { name: raw, width: '', fabric: false }
  const color = normalizeField(fabricColor(product))
  // O cadastro legado também usa "TECIDO BK BRISK (WHITE)" e "ROMANA BK BRISK (AMENDOA)".
  // Remover cor só quando corresponder ao campo cor do SKU (ou a uma cor conhecida).
  let label = raw
  const suffix = label.match(/\s*\(([^()]*)\)\s*$/)
  if (suffix && ((color && normalizeField(suffix[1]) === color) || displayColor.test(suffix[1]))) {
    label = label.slice(0, suffix.index).trim()
  }
  const parts = label.split(/\s+[-–—]\s+/)
  let width = ''
  while (parts.length > 1) {
    const last = parts[parts.length - 1].trim()
    if (supplyMeasure.test(last)) { width = last; parts.pop() }
    else if ((color && normalizeField(last) === color) || displayColor.test(last)) parts.pop()
    else break
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
  if (!product.produto_base?.trim()) return null
  return JSON.stringify([
    product.produto_base, product.familia_tecnica, product.modelo_tecnico,
    product.grupo_tecnico, product.tipo_produto, product.unidade_venda ?? product.unidade,
  ].map(value => normalizeField(value)))
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
    const groupable = view.fabric && !!(fabricColor(product) || product.produto_base?.trim())
    const key = groupable ? 'fabric:' + fabricVariantKey(product)
      : 'product:' + String((product as ApiProduct & { empresa_id?: number | null }).empresa_id ?? '') + ':' + product.id
    let collection = collections.get(key)
    if (!collection) {
      collection = { key, name: view.name, width: view.width, representative: product, variants: [], colors: [] }
      collections.set(key, collection)
    }
    collection.variants.push(product)
    const color = fabricColor(product)
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
