import { useEffect, useId, useState } from 'react'
import type { ApiProduct, BudgetProduct } from '../types/budget'
import { normalizeSearch } from '../types/budget'
import { listGrades, listGradeValues } from '../services/gradesVariacoes'
import { applyCurtainColor, curtainColorSuggestions } from '../utils/curtainColors'

type Props = { product: BudgetProduct; catalog: ApiProduct[]; onChange: (product: BudgetProduct) => void }
export function CurtainColorField({ product, catalog, onChange }: Props) {
  const [gradeColors, setGradeColors] = useState<string[]>([])
  const listId = useId()
  useEffect(() => {
    let active = true
    async function load() {
      try {
        const grades = await listGrades()
        const grade = grades.find(item => item.ativo && normalizeSearch(item.nome) === 'CORES')
        const values = grade ? await listGradeValues(grade.id) : []
        if (active) setGradeColors(values.filter(item => item.ativo).map(item => item.valor))
      } catch {
        // The optional grade never blocks technical variants or free text.
        if (active) setGradeColors([])
      }
    }
    void load()
    return () => { active = false }
  }, [])
  const suggestions = curtainColorSuggestions(catalog, product, gradeColors)
  const value = product.curtain?.cor ?? product.color
  return <div style={{ position: 'relative', minWidth: 0 }}>
    <input style={{ paddingRight: 44 }} aria-label="Cor do tecido" role="combobox" aria-autocomplete="list" list={listId}
      value={value} onChange={event => onChange(applyCurtainColor(product, catalog, event.target.value))}
      placeholder="Selecione ou digite a cor" autoComplete="off" />
    <datalist id={listId}>{suggestions.map(item => <option key={normalizeSearch(item.value)} value={item.value} label={item.source} />)}</datalist>
    {value && <button type="button" aria-label="Limpar cor" title="Limpar cor"
      style={{ position: 'absolute', right: 22, top: '50%', transform: 'translateY(-50%)', width: 18, height: 22, padding: 0, border: 0, background: 'transparent', color: 'var(--color-text-muted)', fontSize: 18, lineHeight: 1, cursor: 'pointer' }}
      onClick={() => onChange(applyCurtainColor(product, catalog, ''))}>×</button>}
  </div>
}
