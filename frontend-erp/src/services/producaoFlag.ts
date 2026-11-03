export const producaoV1Enabled = import.meta.env.VITE_PRODUCAO_V1_ENABLED?.trim().toLowerCase() === 'true'

export function exigirProducaoHabilitada() {
  if (!producaoV1Enabled) throw new Error('Produção V1 desabilitada.')
}
