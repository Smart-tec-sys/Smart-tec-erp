import type { FocusEvent } from 'react'

/** Só seleciona zero em campos numéricos; não altera o valor nem o foco. */
export function selectZeroOnFocus(event: FocusEvent<HTMLElement>) {
  const input = event.target
  if (!(input instanceof HTMLInputElement) || input.readOnly || input.disabled) return
  const label = input.closest('label')?.querySelector('span')?.textContent?.trim() ?? ''
  const numeric = input.type === 'number' || input.inputMode === 'decimal' || input.inputMode === 'numeric' || input.closest('.stepper') !== null || /^(Largura|Altura|Comprimento|Área|Quantidade|Quant\.|Valor|Preço|Percentual|Desconto|Taxa|Fator|Barra|Cabeça|Espaçamento)($|\s)/.test(label)
  if (numeric && /^[+-]?0+(?:[.,]0+)?$/.test(input.value.trim())) input.select()
}
