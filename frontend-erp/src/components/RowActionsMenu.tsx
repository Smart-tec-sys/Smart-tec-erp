import { Eye, MoreHorizontal, Pencil, Trash2, ChevronRight, ChevronDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import './rowActionsMenu.css'

type Props = {
  module: 'budget' | 'sale' | 'finance'
  label: string
  onView?: () => void
  onToggle?: () => void
  toggleLabel?: string
  onEdit?: () => void
  onDelete?: () => void
  onChangeStatus?: () => void
  onGenerateSale?: () => void
  onViewFinance?: () => void
  onPay?: () => void
  payLabel?: string
  payReason?: string
  onViewPayments?: () => void
  deleteReason?: string
  busy?: boolean
}

export function RowActionsMenu({ module, label, onView, onEdit, onDelete, onChangeStatus, onGenerateSale, onViewFinance, onPay, payLabel, payReason, onViewPayments, deleteReason, onToggle, toggleLabel, busy }: Props) {
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const [submenu, setSubmenu] = useState<string | null>(null)
  const isBudget = module === 'budget'
  const isFinance = module === 'finance'
  const trigger = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!position) return
    menu.current?.querySelector<HTMLButtonElement>('button')?.focus()
    setSubmenu(null)
    function closeOutside(event: PointerEvent) {
      if (!menu.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setPosition(null)
    }
    function keyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') { setPosition(null); trigger.current?.focus() }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        const buttons = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') || [])
        const index = buttons.indexOf(document.activeElement as HTMLButtonElement)
        event.preventDefault()
        buttons[(index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length]?.focus()
      }
    }
    function close(event: Event) { if (!menu.current?.contains(event.target as Node)) setPosition(null) }
    document.addEventListener('pointerdown', closeOutside)
    document.addEventListener('keydown', keyDown)
    window.addEventListener('resize', close)
    window.addEventListener('scroll', close, true)
    return () => {
      document.removeEventListener('pointerdown', closeOutside)
      document.removeEventListener('keydown', keyDown)
      window.removeEventListener('resize', close)
      window.removeEventListener('scroll', close, true)
    }
  }, [position])
  function act(callback: () => void) { setPosition(null); trigger.current?.focus(); callback() }
  function unavailable(title: string, reason = 'Ação ainda não disponível neste módulo.') {
    return <button key={title} type="button" role="menuitem" disabled title={reason}>{title}</button>
  }
  function group(title: string, children: string[]) {
    const expanded = submenu === title
    return <div>
      <button type="button" role="menuitem" aria-haspopup="menu" aria-expanded={expanded} onClick={() => setSubmenu(expanded ? null : title)}>{title}{expanded ? <ChevronDown size={14} className="row-actions-chevron" /> : <ChevronRight size={14} className="row-actions-chevron" />}</button>
      {expanded && <div role="menu" aria-label={title} className="row-actions-submenu">
        {children.map(child => isBudget && child === 'Venda'
          ? <button key={child} type="button" role="menuitem" disabled={!onGenerateSale} title={onGenerateSale ? 'Converter o orçamento aprovado em venda, após confirmação.' : 'Apenas orçamentos aprovados podem ser convertidos em venda.'} onClick={() => onGenerateSale && act(onGenerateSale)}>{child}</button>
          : unavailable(child))}
      </div>}
    </div>
  }
  return <>
    <button ref={trigger} type="button" className="table-action" aria-label={`Ações de ${label}`} aria-haspopup="menu" aria-expanded={!!position} disabled={busy}
      onDoubleClick={event => event.stopPropagation()}
      onClick={event => {
        event.stopPropagation()
        const rect = event.currentTarget.getBoundingClientRect()
        setPosition(position ? null : { left: Math.max(8, Math.min(rect.right - 210, window.innerWidth - 218)), top: rect.bottom + 460 > window.innerHeight ? Math.max(8, rect.top - 460) : rect.bottom + 4 })
      }}><MoreHorizontal size={17} /></button>
    {position && createPortal(<div ref={menu} role="menu" aria-label={`Ações de ${label}`} className="row-actions-menu" style={position} onDoubleClick={event => event.stopPropagation()}>
      {isFinance ? <>
        {onView && <button type="button" role="menuitem" onClick={() => act(onView)}><Eye size={16} />Visualizar</button>}
        <button type="button" role="menuitem" disabled={!onEdit} onClick={() => onEdit && act(onEdit)}><Pencil size={16} />Editar</button>
        {onToggle && <button type="button" role="menuitem" onClick={() => act(onToggle)}>{toggleLabel || 'Alterar situação'}</button>}
        {(onPay || payLabel) && <button type="button" role="menuitem" disabled={!onPay} title={onPay ? undefined : payReason} onClick={() => onPay && act(onPay)}>{payLabel}</button>}
        {onViewPayments && <button type="button" role="menuitem" onClick={() => act(onViewPayments)}>Ver baixas</button>}
        <button type="button" role="menuitem" className="row-actions-delete" disabled={!onDelete} title={onDelete ? undefined : deleteReason} onClick={() => onDelete && act(onDelete)}><Trash2 size={16} />Excluir</button>
      </> : <>
      <button type="button" role="menuitem" disabled={!onView} onClick={() => onView && act(onView)}><Eye size={16} />{isBudget ? 'Visualizar proposta' : 'Visualizar'}</button>
      <button type="button" role="menuitem" disabled={!onEdit} onClick={() => onEdit && act(onEdit)}><Pencil size={16} />Editar</button>
      {!isBudget && unavailable('Link de cobrança')}
      <button type="button" role="menuitem" disabled={!onChangeStatus} title="Abrir o editor existente para alterar e salvar a situação." onClick={() => onChangeStatus && act(onChangeStatus)}>Alterar situação</button>
      {unavailable('Imprimir')}
      {unavailable('Compartilhar')}
      {!isBudget && group('Emitir', ['NF-e', 'NFS-e'])}
      {group('Gerar', isBudget ? ['Cópia', 'Venda', 'Ordem de serviço', 'Produção'] : ['Cópia', 'Ordem de serviço', 'Produção', 'Instalação', 'Devolução'])}
      {!isBudget && (onViewFinance
        ? <button type="button" role="menuitem" onClick={() => act(onViewFinance)}>Ver no financeiro</button>
        : unavailable('Ver no financeiro', 'Abertura do título financeiro indisponível nesta tela.'))}
      <button type="button" role="menuitem" className="row-actions-delete" disabled={!onDelete} onClick={() => onDelete && act(onDelete)}><Trash2 size={16} />Excluir</button>
      </>}
    </div>, document.body)}
  </>
}
