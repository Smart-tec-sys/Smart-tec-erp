import type { ApiProduct, BudgetProduct } from '../types/budget'
import { normalizeSearch } from '../types/budget'
import { DEFAULT_CURTAIN, fabricVariants, fabricState, getFabricColorLabel } from './curtainFabricCatalog'

export function curtainColorSuggestions(catalog: ApiProduct[], product: BudgetProduct, gradeColors: string[]) {
  const unique = new Map<string, { value: string; source: string }>()
  for (const fabric of fabricVariants(catalog, product.curtain)) {
    const value = getFabricColorLabel(fabric).trim()
    // Aggregated supplier ranges are metadata, not individual color choices.
    const range = /^[0-9]+(?:[.,][0-9]+)?[ ]*(?:AO|A|ATE|[-–—])[ ]*[0-9]+(?:[.,][0-9]+)?$/.test(normalizeSearch(value))
    if (value && !range) unique.set(normalizeSearch(value), { value, source: 'Variante do fornecedor' })
  }
  for (const color of gradeColors) {
    const value = color.trim()
    if (value && !unique.has(normalizeSearch(value))) unique.set(normalizeSearch(value), { value, source: 'Grade CORES' })
  }
  return [...unique.values()]
}

export function applyCurtainColor(product: BudgetProduct, catalog: ApiProduct[], color: string): BudgetProduct {
  const current = product.curtain ?? DEFAULT_CURTAIN
  const matches = color.trim() ? fabricVariants(catalog, current)
    .filter(fabric => normalizeSearch(getFabricColorLabel(fabric)) === normalizeSearch(color)) : []
  const fabric = matches.find(item => item.id === current.tecidoProdutoId) ?? (matches.length === 1 ? matches[0] : undefined)
  // Free text keeps the existing technical identity; no fabric ID is fabricated.
  const curtain = fabric && fabric.id !== current.tecidoProdutoId
    ? { ...fabricState(current, fabric), cor: color }
    : { ...current, cor: color }
  return { ...product, color, curtain }
}
