/** Apresentação comercial; nunca use este retorno para persistir dados. */
export function commercialDisplayText(value: string, preservedValues: readonly string[] = []): string {
  // Observações e descrições extensas mantêm a legibilidade e a grafia original.
  if (value.length > 255 || /[\r\n]/.test(value)) return value
  const escaped = preservedValues.filter(Boolean).sort((a, b) => b.length - a.length)
    .map(part => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  // Códigos mistos também podem vir embutidos no nome sem um campo separado.
  const codeToken = '(?=[A-Za-z0-9._/-]*[0-9])(?=[A-Za-z0-9._/-]*[A-Za-z])[A-Za-z0-9][A-Za-z0-9._/-]*'
  const explicit = escaped.length ? [`(?<![\\p{L}\\p{N}])(?:${escaped.join('|')})(?![\\p{L}\\p{N}])`] : []
  const protectedParts = new RegExp([
    ...explicit, 'https?://[^\\s<>]+', '[^\\s<>@]+@[^\\s<>@]+\\.[^\\s<>@]+', `\\b${codeToken}\\b`,
  ].join('|'), 'gu')
  let result = '', cursor = 0
  for (const match of value.matchAll(protectedParts)) {
    result += value.slice(cursor, match.index).toLocaleUpperCase('pt-BR') + match[0]
    cursor = match.index + match[0].length
  }
  return result + value.slice(cursor).toLocaleUpperCase('pt-BR')
}
