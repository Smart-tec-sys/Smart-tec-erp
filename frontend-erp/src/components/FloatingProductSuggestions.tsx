import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

type Position = { left: number; top: number; width: number; maxHeight: number }
type AnchorRect = { left: number; right: number; top: number; bottom: number; width: number }

export function productSuggestionsPosition(rect: AnchorRect, viewport: { width: number; height: number }, contentHeight = 300): Position {
  const margin = 8, gap = 4
  const width = Math.max(0, Math.min(420, Math.max(320, rect.width), viewport.width - margin * 2))
  const left = Math.max(margin, Math.min(rect.left, viewport.width - margin - width))
  const below = Math.max(0, viewport.height - margin - rect.bottom - gap)
  const above = Math.max(0, rect.top - margin - gap)
  const desired = Math.min(300, contentHeight)
  const upwards = below < desired && above > below
  const maxHeight = Math.min(300, upwards ? above : below)
  const top = upwards ? rect.top - gap - Math.min(desired, maxHeight) : rect.bottom + gap
  return { left, top: Math.max(margin, top), width, maxHeight }
}

export function FloatingProductSuggestions({ children, onClose, enabled = true }: { children: ReactNode; onClose: () => void; enabled?: boolean }) {
  const anchor = useRef<HTMLSpanElement>(null)
  const layer = useRef<HTMLDivElement>(null)
  const close = useRef(onClose)
  close.current = onClose
  const [position, setPosition] = useState<Position | null>(null)
  const positioned = position !== null

  useLayoutEffect(() => {
    if (!enabled) return
    function update() {
      const field = anchor.current?.parentElement?.querySelector('input')
      if (!field) return
      const rect = field.getBoundingClientRect()
      const scroller = anchor.current?.closest('.product-fields')?.getBoundingClientRect()
      if (rect.bottom <= 0 || rect.top >= window.innerHeight || rect.right <= 0 || rect.left >= window.innerWidth
        || (scroller && (rect.right <= scroller.left || rect.left >= scroller.right))) {
        close.current(); return
      }
      const height = layer.current?.firstElementChild?.scrollHeight || 300
      const next = productSuggestionsPosition(rect, { width: window.innerWidth, height: window.innerHeight }, height)
      setPosition(current => current && Object.keys(next).every(key => current[key as keyof Position] === next[key as keyof Position]) ? current : next)
    }
    function outside(event: PointerEvent) {
      const target = event.target as Node | null
      if (!layer.current?.contains(target) && !anchor.current?.parentElement?.contains(target)) close.current()
    }
    function escape(event: KeyboardEvent) {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close.current() }
    }
    update()
    window.addEventListener('scroll', update, true)
    window.addEventListener('resize', update)
    document.addEventListener('pointerdown', outside, true)
    document.addEventListener('keydown', escape)
    return () => {
      window.removeEventListener('scroll', update, true)
      window.removeEventListener('resize', update)
      document.removeEventListener('pointerdown', outside, true)
      document.removeEventListener('keydown', escape)
    }
  }, [children, positioned, enabled])

  if (!enabled) return <>{children}</>
  return <>
    <span ref={anchor} hidden aria-hidden="true" style={{ display: 'none' }} />
    {position && createPortal(<div ref={layer} className="budget-product-suggestions-layer" style={position}>{children}</div>, document.body)}
  </>
}
