import { useState, type InputHTMLAttributes } from 'react'

/** O zero continua no estado de cálculo; somente a apresentação fica vazia. */
export function zeroInputValue(value: number | string) {
  return /^[+-]?0+(?:[.,]0+)?$/.test(String(value).trim()) ? '' : value
}
type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type'> & {
  value: number | string; onValueChange?: (value: number) => void
}
export function ZeroNumberInput({ value, onValueChange, readOnly, disabled, placeholder = '0', onFocus, onBlur, ...props }: Props) {
  const [draft, setDraft] = useState('')
  const [focused, setFocused] = useState(false)
  const protectedValue = readOnly || disabled
  return <input {...props} type="text" inputMode="decimal" readOnly={readOnly} disabled={disabled} placeholder={placeholder}
    value={protectedValue ? value : focused ? draft : zeroInputValue(value)}
    onFocus={event => { setDraft(String(zeroInputValue(value))); setFocused(true); onFocus?.(event) }}
    onChange={event => {
      const text = event.target.value
      if (!/^[+-]?\d*(?:[.,]\d*)?$/.test(text)) return
      setDraft(text)
      const number = Number(text.replace(',', '.'))
      if (Number.isFinite(number)) onValueChange?.(number)
    }}
    onBlur={event => { setFocused(false); onBlur?.(event) }} />
}
