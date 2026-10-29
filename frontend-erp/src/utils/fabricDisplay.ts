import { normalizeSearch, productColor, type ApiProduct } from '../types/budget'

const supplyMeasure = /^\d+(?:[.,]\d+)?\s*(?:M|METROS?)$/i
// Reconhecimento apenas para apresentação; não cria uma relação de cores no cadastro.
const displayColor = /^(?:CINZA|BEGE|BRANCO|BRANCA|PRETO|PRETA|CREME|MARROM|LINHO|PALHA|PRATA|TINTO (?:BEGE|PALHA|PRATA))$/i
export function fabricDisplay(product: ApiProduct) {
  const raw = product.nome.trim()
  const fabric = /\b(?:SCREEN|TECIDOS?|BLACKOUT)\b/.test(normalizeSearch([raw, product.grupo_tecnico, product.grupo_produto, product.familia_tecnica].join(' ')))
  if (!fabric) return { name: raw, width: '', fabric: false }
  const parts = raw.split(/\s+[-–—]\s+/)
  const color = normalizeSearch(productColor(product))
  let width = ''
  while (parts.length > 1) {
    const last = parts[parts.length - 1].trim()
    if (supplyMeasure.test(last)) { width = last; parts.pop() }
    else if ((color && normalizeSearch(last) === color) || displayColor.test(last)) parts.pop()
    else break
  }
  const name = parts.join(' - ').trim()
  return { name, width: width || (Number(product.largura) > 0 ? String(product.largura) + ' m' : ''), fabric: true }
}
export function fabricVariantKey(product: ApiProduct) {
  const view = fabricDisplay(product)
  return JSON.stringify([normalizeSearch(view.name), product.familia_tecnica ?? '', product.modelo_tecnico ?? '', product.grupo_tecnico ?? '', product.tipo_produto ?? '', product.unidade_venda ?? product.unidade ?? '', normalizeSearch(view.width).replace(',', '.')])
}
export function groupFabricSuggestions(products: ApiProduct[]) {
  const groups = new Map<string, ApiProduct[]>()
  for (const product of products) {
    const view = fabricDisplay(product)
    // Sem cor estruturada, preservar cada registro e o comportamento já existente.
    const key = view.fabric && productColor(product) ? fabricVariantKey(product) : `id:${product.id}`
    groups.set(key, [...(groups.get(key) ?? []), product])
  }
  const result: ApiProduct[] = []
  for (const rows of groups.values()) {
    const colors = rows.map(row => normalizeSearch(productColor(row)))
    // Duplicidades da mesma cor podem ser cadastros distintos: não ocultá-las.
    if (new Set(colors).size < rows.length) result.push(...rows)
    else result.push(rows[0])
  }
  return result
}
