import { Columns3, X } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import './columnManager.css'

export type ManagedColumn = { id: string; label: string; defaultVisible: boolean }
type Props = {
  columns: ManagedColumn[]
  storageKey: string
  lockedColumns?: string[]
  children?: ReactNode
  visibleColumns?: string[]
  onChange?: (visible: string[]) => void
}
type Preference = Record<string, boolean>
function readPreference(key: string): Preference {
  try {
    const saved = JSON.parse(localStorage.getItem(key) || 'null')
    if (saved?.version !== 1 || !saved.visibility || typeof saved.visibility !== 'object' || Array.isArray(saved.visibility)) return {}
    return Object.fromEntries(Object.entries(saved.visibility).filter((entry): entry is [string, boolean] => typeof entry[1] === 'boolean'))
  } catch { return {} }
}

export function ColumnManager({ columns, storageKey, lockedColumns = [], children, visibleColumns, onChange }: Props) {
  const [preference, setPreference] = useState(() => ({ key: storageKey, values: readPreference(storageKey) }))
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const popup = useRef<HTMLDivElement>(null)
  const scope = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const values = preference.key === storageKey ? preference.values : readPreference(storageKey)
  const locked = new Set([...lockedColumns, columns[0]?.id].filter((id): id is string => !!id))
  const visible = columns.filter(column => locked.has(column.id) || (visibleColumns ? visibleColumns.includes(column.id) : values[column.id] ?? column.defaultVisible)).map(column => column.id)
  function change(next: Preference, reset = false) {
    const visibleIds = columns.filter(column => locked.has(column.id) || next[column.id] === true || (next[column.id] === undefined && column.defaultVisible)).map(column => column.id)
    setPreference({ key: storageKey, values: next })
    try {
      if (reset) localStorage.removeItem(storageKey)
      else localStorage.setItem(storageKey, JSON.stringify({ version: 1, visibility: next }))
    } catch { /* A lista continua funcionando quando o armazenamento está indisponível. */ }
    onChange?.(visibleIds)
  }
  function toggle(id: string, checked: boolean) {
    const next = Object.fromEntries(columns.map(column => [column.id, visible.includes(column.id)]))
    next[id] = checked
    change(next)
  }
  function close() { setPosition(null); trigger.current?.focus() }
  useEffect(() => {
    if (!position) return
    popup.current?.querySelector<HTMLButtonElement>('button')?.focus()
    function outside(event: PointerEvent) {
      if (!popup.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setPosition(null)
    }
    function key(event: KeyboardEvent) { if (event.key === 'Escape') { setPosition(null); trigger.current?.focus() } }
    function moved(event: Event) { if (!popup.current?.contains(event.target as Node)) setPosition(null) }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', key)
    window.addEventListener('resize', moved)
    window.addEventListener('scroll', moved, true)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('keydown', key)
      window.removeEventListener('resize', moved)
      window.removeEventListener('scroll', moved, true)
    }
  }, [position])
  const hiddenRules = columns.flatMap((column, index) => visible.includes(column.id) ? [] : [
    `[data-columns-scope="${scope}"] > table > thead > tr > :nth-child(${index + 1}), [data-columns-scope="${scope}"] > table > tbody > tr > :nth-child(${index + 1}):not([colspan]) { display: none; }`,
  ]).join('\n')
  return <>
    <div className="column-manager-toolbar"><button ref={trigger} type="button" className="column-manager-trigger" aria-haspopup="dialog" aria-expanded={!!position} onClick={() => {
      const rect = trigger.current!.getBoundingClientRect()
      setPosition(position ? null : { left: Math.max(8, Math.min(rect.right - 280, window.innerWidth - 288)), top: Math.max(8, Math.min(rect.bottom + 4, window.innerHeight - 350)) })
    }}><Columns3 size={16} />Gerenciar colunas</button></div>
    {children && <div data-columns-scope={scope}><style>{hiddenRules}</style>{children}</div>}
    {position && createPortal(<div ref={popup} className="column-manager-popup" role="dialog" aria-label="Gerenciar colunas" style={{ ...position, maxHeight: Math.max(120, window.innerHeight - position.top - 8) }}>
      <header><strong>Gerenciar colunas</strong><button type="button" aria-label="Fechar gerenciador de colunas" onClick={close}><X size={15} /></button></header>
      <div className="column-manager-options">{columns.map(column => <label key={column.id}><input type="checkbox" checked={visible.includes(column.id)} disabled={locked.has(column.id)} onChange={event => toggle(column.id, event.target.checked)} /><span>{column.label}</span>{locked.has(column.id) && <small>Fixa</small>}</label>)}</div>
      <button type="button" className="column-manager-reset" onClick={() => change({}, true)}>Restaurar padrão</button>
    </div>, document.body)}
  </>
}
