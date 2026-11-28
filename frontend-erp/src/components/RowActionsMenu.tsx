import { Eye, MoreHorizontal, Pencil, Printer, Trash2, ChevronRight, ChevronDown } from 'lucide-react'
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
  generateSaleReason?: string
  onDuplicateBudget?: () => void
  onPrepareServiceOrder?: () => void
  onGenerateProduction?: () => void
  onPrepareFiscal?: (type: 'NFE' | 'NFSE' | 'NFCE') => void
  productionReason?: string
  onShareBudget?: (channel: 'whatsapp' | 'email') => void
  onPrintSale?: () => void
  onPrintBudget?: (mode: 'direct' | 'reseller_commercial' | 'reseller_internal' | 'reseller_client') => void
  hasReseller?: boolean
  onViewFinance?: () => void
  onPay?: () => void
  payLabel?: string
  payReason?: string
  onViewPayments?: () => void
  deleteReason?: string
  busy?: boolean
}

export function RowActionsMenu({ module, label, onView, onEdit, onDelete, onChangeStatus, onGenerateSale, generateSaleReason, onDuplicateBudget, onPrepareServiceOrder, onGenerateProduction, onPrepareFiscal, productionReason, onShareBudget, onPrintSale, onPrintBudget, hasReseller, onViewFinance, onPay, payLabel, payReason, onViewPayments, deleteReason, onToggle, toggleLabel, busy }: Props) {
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
        {children.map(child => {
          if (module === 'sale' && title === 'Emitir') {
            const type = child === 'NF-e' ? 'NFE' : child === 'NFS-e' ? 'NFSE' : 'NFCE'
            return <button key={child} type="button" role="menuitem" disabled={!onPrepareFiscal}
              title="Preparar e analisar pendências; não transmite nem autoriza notas."
              onClick={() => onPrepareFiscal && act(() => onPrepareFiscal(type))}>Preparar {child}</button>
          }
          if (!isBudget && child !== 'Produção') return unavailable(child)
          const actions: Record<string, { callback?: () => void; reason?: string }> = {
            'Cópia': { callback: onDuplicateBudget },
            'Venda': { callback: onGenerateSale, reason: generateSaleReason || 'Apenas orçamentos aprovados podem ser convertidos em venda.' },
            'Ordem de serviço': { callback: onPrepareServiceOrder, reason: 'Preparar os dados para a OS; criação depende do backend de Ordens de Serviço.' },
            'Produção': { callback: onGenerateProduction, reason: productionReason },
          }
          const action = actions[child]
          return <button key={child} type="button" role="menuitem" disabled={!action?.callback} title={action?.reason}
            onClick={() => action?.callback && act(action.callback)}>{child}</button>
        })}
      </div>}
    </div>
  }
  function printMenu() {
    const expanded = submenu === 'Imprimir'
    const options = hasReseller
      ? ([['PDF Revenda', 'reseller_commercial'], ['PDF Cliente Final', 'reseller_client'], ['PDF Interno Smart-tec', 'reseller_internal']] as const)
      : ([['PDF do Cliente', 'direct']] as const)
    return <div>
      <button type="button" role="menuitem" aria-haspopup="menu" aria-expanded={expanded} disabled={!onPrintBudget}
        onClick={() => setSubmenu(expanded ? null : 'Imprimir')}><Printer size={16} />Imprimir
        {expanded ? <ChevronDown size={14} className="row-actions-chevron" /> : <ChevronRight size={14} className="row-actions-chevron" />}</button>
      {expanded && <div role="menu" aria-label="Imprimir orçamento" className="row-actions-submenu">
        {options.map(([text, mode]) => <button key={mode} type="button" role="menuitem"
          onClick={() => onPrintBudget && act(() => onPrintBudget(mode))}>{text}</button>)}
      </div>}
    </div>
  }
  function shareMenu() {
    const expanded = submenu === 'Compartilhar'
    return <div>
      <button type="button" role="menuitem" aria-haspopup="menu" aria-expanded={expanded} disabled={!onShareBudget}
        onClick={() => setSubmenu(expanded ? null : 'Compartilhar')}>Compartilhar
        {expanded ? <ChevronDown size={14} className="row-actions-chevron" /> : <ChevronRight size={14} className="row-actions-chevron" />}</button>
      {expanded && <div role="menu" aria-label="Compartilhar orçamento" className="row-actions-submenu">
        <button type="button" role="menuitem" onClick={() => onShareBudget && act(() => onShareBudget('whatsapp'))}>WhatsApp</button>
        <button type="button" role="menuitem" onClick={() => onShareBudget && act(() => onShareBudget('email'))}>E-mail</button>
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
      {isBudget ? printMenu() :
        <button type="button" role="menuitem"
          disabled={!onPrintSale}
          title={!onPrintSale ? 'PDF comercial especifico indisponivel.' : undefined}
          onClick={() => onPrintSale && act(onPrintSale)}>
          <Printer size={16}/>Imprimir
        </button>}
      {shareMenu()}
      {!isBudget && group('Emitir', ['NF-e', 'NFS-e', 'NFC-e'])}
      {group('Gerar', isBudget ? ['Cópia', 'Venda', 'Ordem de serviço'] : ['Cópia', 'Ordem de serviço', 'Produção', 'Instalação', 'Devolução'])}
      {!isBudget && (onViewFinance
        ? <button type="button" role="menuitem" onClick={() => act(onViewFinance)}>Ver no financeiro</button>
        : unavailable('Ver no financeiro', 'Abertura do título financeiro indisponível nesta tela.'))}
      <button type="button" role="menuitem" className="row-actions-delete" disabled={!onDelete} onClick={() => onDelete && act(onDelete)}><Trash2 size={16} />Excluir</button>
      </>}
    </div>, document.body)}
  </>
}
