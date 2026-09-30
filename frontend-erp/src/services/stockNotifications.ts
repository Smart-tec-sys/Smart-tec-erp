import type { ApiProduct } from '../types/budget'

export type StockNotificationType =
  | 'ESTOQUE_ZERADO'
  | 'ESTOQUE_BAIXO'

export interface StockNotification {
  id: string
  productId: number
  tipo: StockNotificationType
  mensagem: string
  titulo: string
  detalhe: string
  prioridade: number
}

function asNumber(value: number | string | null | undefined) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function controlsStock(value: string | null | undefined) {
  const normalized = String(value || '')
    .trim()
    .toUpperCase()

  return (
    normalized === 'SIM' ||
    normalized === 'S' ||
    normalized === 'TRUE' ||
    normalized === '1'
  )
}

export function derivarNotificacoesEstoque(
  products: ApiProduct[],
): StockNotification[] {
  return products
    .flatMap<StockNotification>((product) => {
      if (!controlsStock(product.movimenta_estoque)) {
        return []
      }

      const situacao = String(product.situacao || '')
        .trim()
        .toUpperCase()

      if (
        situacao &&
        situacao !== 'ATIVO' &&
        situacao !== 'ATIVA'
      ) {
        return []
      }

      const atual = asNumber(product.estoque_atual)
      const minimo = asNumber(product.estoque_minimo)

      // Sem estoque minimo configurado, nao existe parametro
      // suficiente para afirmar que o produto precisa de reposicao.
      if (minimo <= 0) {
        return []
      }

      const titulo =
        product.nome?.trim() ||
        product.descricao?.trim() ||
        `Produto ${product.id}`

      if (atual <= 0) {
        return [{
          id: `stock-zero-${product.id}`,
          productId: product.id,
          tipo: 'ESTOQUE_ZERADO',
          mensagem: 'Estoque zerado',
          titulo,
          detalhe: `Saldo atual: ${atual}`,
          prioridade: 1,
        }]
      }

      if (minimo > 0 && atual <= minimo) {
        return [{
          id: `stock-low-${product.id}`,
          productId: product.id,
          tipo: 'ESTOQUE_BAIXO',
          mensagem: 'Estoque baixo',
          titulo,
          detalhe: `Atual: ${atual} ? M?nimo: ${minimo}`,
          prioridade: 2,
        }]
      }

      return []
    })
    .sort((a, b) =>
      a.prioridade - b.prioridade ||
      a.titulo.localeCompare(b.titulo, 'pt-BR')
    )
}
