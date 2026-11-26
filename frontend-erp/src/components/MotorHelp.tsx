import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

type Props = { message: string; label: string }

export function MotorHelp({ message, label }: Props) {
  const [open, setOpen] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const button = useRef<HTMLButtonElement>(null)
  const popup = useRef<HTMLDivElement>(null)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const id = useId()

  const cancelClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current)
    closeTimer.current = null
  }
  const closeAfterHover = () => {
    if (pinned || button.current?.matches(':focus-visible')) return
    cancelClose()
    closeTimer.current = setTimeout(() => setOpen(false), 200)
  }
  useEffect(() => () => cancelClose(), [])

  useEffect(() => {
    if (!open) return
    const updatePosition = () => {
      const rect = button.current?.getBoundingClientRect()
      if (!rect) return
      const width = Math.min(320, window.innerWidth - 24)
      const height = popup.current?.getBoundingClientRect().height ?? 0
      const top = rect.bottom + 8 + height <= window.innerHeight - 12
        ? rect.bottom + 8 : Math.max(12, rect.top - height - 8)
      setPosition({ left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)), top })
    }
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !button.current?.contains(event.target) && !popup.current?.contains(event.target)) {
        setOpen(false)
        setPinned(false)
      }
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        setPinned(false)
      }
    }
    updatePosition()
    window.addEventListener('scroll', updatePosition, true)
    window.addEventListener('resize', updatePosition)
    document.addEventListener('pointerdown', dismiss)
    document.addEventListener('keydown', escape)
    return () => {
      window.removeEventListener('scroll', updatePosition, true)
      window.removeEventListener('resize', updatePosition)
      document.removeEventListener('pointerdown', dismiss)
      document.removeEventListener('keydown', escape)
    }
  }, [open])

  return <>
    <button ref={button} type="button" className="motor-help-button" aria-label={label}
      aria-describedby={open ? id : undefined} aria-expanded={open}
      onMouseEnter={() => { cancelClose(); setOpen(true) }} onMouseLeave={closeAfterHover}
      onFocus={event => { cancelClose(); if (event.currentTarget.matches(':focus-visible')) setOpen(true) }}
      onBlur={() => { if (!pinned) setOpen(false) }}
      onClick={() => { cancelClose(); if (pinned) { setPinned(false); setOpen(false) } else { setPinned(true); setOpen(true) } }}>?</button>
    {open && createPortal(<div ref={popup} id={id} role="tooltip" className="motor-help-popup"
      onMouseEnter={cancelClose} onMouseLeave={closeAfterHover}
      style={{ top: position.top, left: position.left }}>{message}</div>, document.body)}
  </>
}
