import type { ApiProduct, CurtainComponent, CurtainState } from '../types/budget'
import { normalizeSearch, productCost } from '../types/budget'

export function isCurtainComponent(product: ApiProduct) {
  if (normalizeSearch(product.grupo_tecnico ?? '') !== 'COMPONENTES_CORTINAS' || normalizeSearch(product.situacao ?? '') !== 'ATIVO') return false
  const classification = [product.nome, product.grupo_produto, product.modelo_tecnico, product.familia_tecnica, product.tipo_cortina_persiana].filter(Boolean).join(' ')
  return !/PERSIANA|ROLO|ROMANA|DOUBLE[ _-]?VISION|\bDV\b|\bTUBOS?\b|\bCOMANDOS?\b|\bBASES?\b/.test(normalizeSearch(classification))
}

export function searchCurtainComponents(catalog: ApiProduct[], query: string) {
  const terms = normalizeSearch(query).split(/\s+/).filter(Boolean)
  return catalog.filter(isCurtainComponent).filter(product => {
    const text = normalizeSearch([product.nome, product.codigo, product.codigo_interno, product.codigo_fornecedor, product.nome_fornecedor, product.fornecedores].filter(Boolean).join(' '))
    return terms.every(term => text.includes(term))
  })
}

export const curtainComponentUnit = (product: ApiProduct) => product.unidade_venda || product.unidade || product.unidade_controle || product.unidade_compra || '—'
export const curtainComponentSubtotal = (line: CurtainComponent, product?: ApiProduct) => product ? line.quantidade * productCost(product) : 0

export function curtainComponentLines(state: CurtainState, width: number): CurtainComponent[] {
  if (state.componentes) return state.componentes
  // Only previously selected real IDs are carried forward; never infer a product from the model.
  const result = state.result
  const legacy = [
    [state.trilhoProdutoId, width],
    [state.rodizioProdutoId, result?.rodizios?.quantidade_total_un ?? 0],
    [state.ganchoProdutoId, result?.ganchos?.quantidade_cortina_un ?? 0],
    [state.botaoProdutoId, result?.wave?.quantidade_botoes ?? 0],
    [state.entretelaProdutoId, state.usaEntretela ? width * state.fator : 0],
  ]
  return legacy.filter(([id]) => id).map(([id, quantity]) => ({ produto_id: id!, quantidade: quantity ?? 0 }))
}
