import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { ApiClient } from '../types/budget'
import './budgetClientPicker.css'

type Props = {
  clients: ApiClient[]
  value: number
  onChange: (id: number) => void
  onCreate?: () => void
  disabled?: boolean
}

const normalize = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim()

export function BudgetClientPicker({ clients, value, onChange, onCreate, disabled = false }: Props) {
  const [query, setQuery] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const input = useRef<HTMLInputElement>(null)
  const listId = useId()
  const selected = clients.find(client => client.id === value)
  const display = query ?? (selected?.nome || (value ? `Cliente #${value}` : ''))
  const matches = useMemo(() => {
    const term = normalize(query ?? '')
    if (!term) return clients
    const digits = term.replace(/\D/g, '')
    const documentSearch = /^[\d\s./-]+$/.test(term) && digits.length > 0
    return clients.filter(client => normalize(client.nome).includes(term)
      || normalize(client.documento ?? '').includes(term)
      || (documentSearch && (client.documento ?? '').replace(/\D/g, '').includes(digits)))
  }, [clients, query])
  const optionCount = matches.length + (onCreate ? 1 : 0)
  const expanded = open && !disabled

  useEffect(() => {
    if (value) { setQuery(null); setOpen(false); setActive(-1) }
  }, [value])

  function choose(index: number) {
    const client = matches[index]
    if (client) { setQuery(null); onChange(client.id) }
    else if (index === matches.length && onCreate) onCreate()
    setOpen(false); setActive(-1)
  }

  return <div className="budget-client-picker" onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) { setOpen(false); setActive(-1) }
  }}>
    <div className="budget-client-picker-control">
      <input ref={input} type="text" role="combobox" aria-label="Cliente" aria-autocomplete="list"
        aria-expanded={expanded} aria-controls={listId} aria-activedescendant={expanded && active >= 0 && active < optionCount ? `${listId}-${active}` : undefined}
        autoComplete="off" placeholder="Buscar por nome, CPF ou CNPJ" value={display} disabled={disabled}
        onFocus={() => { setOpen(true); setActive(-1) }}
        onChange={event => {
          setQuery(event.target.value); setOpen(true); setActive(0)
          if (value) onChange(0)
        }}
        onKeyDown={event => {
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault(); setOpen(true)
            if (optionCount) setActive(current => !expanded || current < 0
              ? (event.key === 'ArrowDown' ? 0 : optionCount - 1)
              : (current + (event.key === 'ArrowDown' ? 1 : -1) + optionCount) % optionCount)
          } else if (event.key === 'Enter' && expanded) {
            event.preventDefault()
            if (active >= 0 && active < optionCount) choose(active)
          } else if (event.key === 'Escape' && expanded) {
            event.preventDefault(); event.stopPropagation(); setOpen(false); setActive(-1)
          }
        }} />
      {display && !disabled && <button type="button" className="budget-client-picker-clear" aria-label="Limpar cliente"
        onMouseDown={event => event.preventDefault()} onClick={() => {
          setQuery(null); onChange(0); setOpen(true); setActive(-1); input.current?.focus()
        }}>×</button>}
    </div>
    {expanded && <div id={listId} className="budget-client-options" role="listbox" aria-label="Sugestões de clientes">
      {matches.map((client, index) => <button key={client.id} id={`${listId}-${index}`} type="button" role="option"
        aria-selected={value === client.id} className={active === index ? 'is-active' : undefined} tabIndex={-1}
        onMouseDown={event => event.preventDefault()} onMouseEnter={() => setActive(index)} onClick={() => choose(index)}>
        <strong>{client.nome}</strong>{client.documento && <small>{client.documento}</small>}
      </button>)}
      {!matches.length && <p className="budget-client-empty" role="status">Nenhum cliente encontrado.</p>}
      {onCreate && <button id={`${listId}-${matches.length}`} type="button" role="option" aria-selected={false}
        className={active === matches.length ? 'is-active' : undefined} tabIndex={-1}
        onMouseDown={event => event.preventDefault()} onMouseEnter={() => setActive(matches.length)} onClick={() => choose(matches.length)}>+ Cadastrar novo cliente</button>}
    </div>}
  </div>
}
