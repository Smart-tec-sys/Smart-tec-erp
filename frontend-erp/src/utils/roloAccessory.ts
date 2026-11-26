import type { RoloAccessory } from '../services/api'
import { commercialPrice, emptyProduct, type ApiProduct, type BudgetProduct, type CommercialType } from '../types/budget'

export function createRoloAccessoryProduct(item: RoloAccessory, catalog: ApiProduct[], profile: CommercialType, id: number, ambiente: string): BudgetProduct {
  const product = catalog.find(entry => entry.id === item.produto_id)
  if (!product) throw new Error('Acessório compatível não encontrado no catálogo carregado.')
  const price = commercialPrice(product, profile)
  return { ...emptyProduct(id), productId: product.id, product: product.nome,
    code: product.codigo_interno || product.codigo || '', unit: 'UN', environment: ambiente,
    price, suggestedPrice: price, acessorioRolo: true }
}
