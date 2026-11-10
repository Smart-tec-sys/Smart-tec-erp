import { normalizeSearch, type ApiProduct } from '../types/budget'
import { fabricDisplay } from './fabricDisplay'

const searchTerms = (query: string) => normalizeSearch(query).split(/\s+/).filter(Boolean)

/**
 * Faixas de relevância das sugestões de produto:
 * 0 - produto acabado com todos os termos no nome;
 * 1 - produto acabado com termos no nome e o restante na própria classificação (ex.: "persiana rolô");
 * 2 - demais produtos com todos os termos no nome;
 * 3 - produtos encontrados apenas por classificação técnica, grupo ou família.
 */
export function productSuggestionTier(product: ApiProduct, query: string, finished: boolean) {
  const terms = searchTerms(query)
  if (!terms.length) return 3
  const name = normalizeSearch(`${fabricDisplay(product).name} ${product.nome}`)
  const inName = terms.filter(term => name.includes(term)).length
  if (finished && inName === terms.length) return 0
  if (finished && inName > 0) {
    const classification = normalizeSearch(`${product.grupo_produto || ''} ${product.grupo_tecnico || ''} ${product.modelo_tecnico || ''}`).replace(/_/g, ' ')
    if (terms.every(term => name.includes(term) || classification.includes(term))) return 1
  }
  return inName === terms.length ? 2 : 3
}

// Ordenação estável: dentro de cada faixa preserva a ordem original do catálogo.
export function rankProductSuggestions(products: ApiProduct[], query: string, isFinished: (product: ApiProduct) => boolean) {
  if (!searchTerms(query).length) return products
  return products
    .map((product, index) => ({ product, index, tier: productSuggestionTier(product, query, isFinished(product)) }))
    .sort((a, b) => a.tier - b.tier || a.index - b.index)
    .map(item => item.product)
}
