import type { ApiProduct } from '../types/budget'

// Isolado do orçamento: todos os termos podem ocorrer em campos diferentes.
export const normalizeProductSearch = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim().replace(/\s+/g, ' ')
export const productFilterLabels = { group: 'Grupo comercial', family: 'Família técnica', unit: 'Unidade de venda', color: 'Cor/variação', supplier: 'Fornecedor' }
export type ProductFilterKey = keyof typeof productFilterLabels
export const productFilterKeys = Object.keys(productFilterLabels) as ProductFilterKey[]
export const emptyProductFilters = { group: '', family: '', unit: '', color: '', supplier: '' }
export const productFilterValues = (p: ApiProduct): Record<ProductFilterKey, string[]> => ({
    group: [p.grupo_produto ?? ''], family: [p.familia_tecnica ?? ''],
    unit: [p.unidade_venda?.trim() || p.unidade?.trim() || ''],
    color: [p.cor ?? '', p.cor_componente ?? '', p.variacao_cor ?? ''],
    supplier: [p.nome_fornecedor ?? '', p.fornecedores ?? ''],
})
export function indexProduct(p: ApiProduct) {
    const values = productFilterValues(p)
    return {
        product: p,
        text: normalizeProductSearch([p.nome, p.codigo_interno, p.codigo, p.codigo_barras, p.grupo_tecnico, p.modelo_tecnico, ...Object.values(values).flat()].filter(Boolean).join(' ')),
        values: Object.fromEntries(productFilterKeys.map(key => [key, values[key].map(normalizeProductSearch)])) as Record<ProductFilterKey, string[]>,
    }
}
export function productFilterOptions(products: ApiProduct[]) {
    const maps = Object.fromEntries(productFilterKeys.map(key => [key, new Map<string, string>()])) as Record<ProductFilterKey, Map<string, string>>
    products.forEach(p => {
        const values = productFilterValues(p)
        productFilterKeys.forEach(key => values[key].forEach(value => {
            const normalized = normalizeProductSearch(value)
            if (normalized && !maps[key].has(normalized)) maps[key].set(normalized, value.trim())
        }))
    })
    return Object.fromEntries(productFilterKeys.map(key => [key, [...maps[key]].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'))])) as Record<ProductFilterKey, { value: string; label: string }[]>
}
