export type OrigemCampo = 'salvo' | 'manual' | 'cnpj' | 'cep'
export type EstadoAssistido<K extends string> = {
  valores: Record<K, string>
  origens: Partial<Record<K, OrigemCampo>>
  revisoes: Partial<Record<K, number>>
  versao: number
}

export function iniciarPreenchimento<K extends string>(valores: Record<K, string>, existente = false): EstadoAssistido<K> {
  const origens: Partial<Record<K, OrigemCampo>> = {}
  for (const campo of Object.keys(valores) as K[]) {
    if (existente && valores[campo] !== '') origens[campo] = 'salvo'
  }
  return { valores, origens, revisoes: {}, versao: 0 }
}

export function editarCampo<K extends string>(estado: EstadoAssistido<K>, campo: K, valor: string): EstadoAssistido<K> {
  const versao = estado.versao + 1
  return {
    valores: { ...estado.valores, [campo]: valor },
    origens: { ...estado.origens, [campo]: 'manual' },
    revisoes: { ...estado.revisoes, [campo]: versao },
    versao,
  }
}

export function aplicarConsulta<K extends string>(
  estado: EstadoAssistido<K>,
  dados: Partial<Record<K, string>>,
  origem: 'cnpj' | 'cep',
  versaoInicio: number,
): { estado: EstadoAssistido<K>; sugestoes: Partial<Record<K, string>> } {
  const next = { ...estado, valores: { ...estado.valores }, origens: { ...estado.origens }, revisoes: { ...estado.revisoes } }
  const sugestoes: Partial<Record<K, string>> = {}
  for (const campo of Object.keys(dados) as K[]) {
    const valor = dados[campo]
    if (valor == null || valor.trim() === '' || estado.valores[campo] === valor) continue
    if ((estado.revisoes[campo] ?? 0) > versaoInicio) continue
    const protegido = estado.origens[campo] === 'manual' || estado.origens[campo] === 'salvo'
      || (estado.valores[campo] !== '' && estado.origens[campo] == null)
    if (protegido) {
      sugestoes[campo] = valor
    } else {
      next.versao += 1
      next.valores[campo] = valor
      next.origens[campo] = origem
      next.revisoes[campo] = next.versao
    }
  }
  return { estado: next, sugestoes }
}
