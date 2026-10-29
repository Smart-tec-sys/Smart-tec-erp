import type { BudgetProduct } from '../types/budget'

export function technicalSimulationError(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error)
  const match = /^API (\d+):\s*([\s\S]*)$/.exec(message)
  if (!match) return 'Não foi possível conectar ao cálculo técnico. Tente novamente; seus dados foram preservados.'
  const status = Number(match[1])
  if (status >= 500) return 'O cálculo técnico está temporariamente indisponível. Tente novamente.'
  if (status === 404) return 'Produto não encontrado para a empresa atual. Revise a seleção.'
  if (status === 401 || status === 403) return 'Sua sessão não permite acessar este cálculo. Entre novamente.'
  try {
    const detail: unknown = JSON.parse(match[2]).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const labels: Record<string, string> = { largura: 'largura', altura: 'altura', largura_modulo_m: 'largura do módulo', comprimento_avanco_m: 'avanço', quantidade: 'quantidade', quantidade_modulos: 'quantidade de módulos', fator: 'fator', largura_tecido: 'largura do tecido', cor: 'cor', acionamento: 'acionamento' }
      const fields = [...new Set(detail.flatMap(item => {
        const field = Array.isArray(item.loc) ? item.loc.at(-1) : undefined
        return labels[field] ? [labels[field]] : []
      }))]
      return fields.length ? `Revise os campos do cálculo técnico: ${fields.join(', ')}.` : 'Revise as medidas e as opções do modelo selecionado.'
    }
  } catch { /* A resposta não estruturada não deve aparecer como JSON na tela. */ }
  return 'Não foi possível validar o cálculo técnico. Revise as medidas e as opções do modelo.'
}

// Transporta somente as entradas dos componentes existentes; não calcula valores.
export function technicalItemData(product: BudgetProduct) {
  if (product.curtain) return { cortina: { ...product.curtain, result: undefined, error: undefined, simulationKey: undefined } }
  if (product.romanaTetoKind) return { romana_teto: {
    acionamento: product.acao_acionamento || 'MANUAL_BASTAO',
    lado_comando: product.lado_comando || 'ESQUERDA',
    comprimento_bastao_m: Number((product.comprimento_bastao || '1.50').replace(',', '.')),
    comprimento_corrente_sem_fim_m: Number((product.comprimento_corrente_sem_fim || '1.50').replace(',', '.')),
  } }
  return null
}
