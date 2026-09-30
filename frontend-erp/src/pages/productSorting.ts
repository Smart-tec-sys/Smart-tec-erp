import type { ApiProduct } from '../types/budget'

export const productSortLabels = {
    newest: 'ID — mais recente primeiro', oldest: 'ID — mais antigo primeiro',
    nameAsc: 'Nome — A-Z', nameDesc: 'Nome — Z-A',
    costAsc: 'Custo — menor para maior', costDesc: 'Custo — maior para menor',
    saleAsc: 'Venda — menor para maior', saleDesc: 'Venda — maior para menor',
    active: 'Situação — ativos primeiro', inactive: 'Situação — inativos primeiro',
}
export type ProductSort = keyof typeof productSortLabels
const names = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })
const number = (value: unknown) => Number.isFinite(Number(value)) ? Number(value) : 0
const inactive = (p: ApiProduct) => Number((p.situacao || '').toLowerCase() === 'inativo')
export function sortProducts(products: ApiProduct[], order: ProductSort): ApiProduct[] {
    return [...products].sort((a, b) => {
        let result = 0
        switch (order) {
            case 'oldest': return a.id - b.id
            case 'newest': return b.id - a.id
            case 'nameAsc': result = names.compare(a.nome, b.nome); break
            case 'nameDesc': result = names.compare(b.nome, a.nome); break
            case 'costAsc': result = number(a.valor_custo) - number(b.valor_custo); break
            case 'costDesc': result = number(b.valor_custo) - number(a.valor_custo); break
            case 'saleAsc': result = number(a.valor_venda) - number(b.valor_venda); break
            case 'saleDesc': result = number(b.valor_venda) - number(a.valor_venda); break
            case 'active': result = inactive(a) - inactive(b); break
            case 'inactive': result = inactive(b) - inactive(a); break
        }
        return result || b.id - a.id
    })
}
