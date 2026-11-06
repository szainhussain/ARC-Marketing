import { useEffect, useRef, useState } from 'react'
import { Check, Monitor, Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import type { ThemePref } from '../lib/theme'

const OPTIONS: { value: ThemePref; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'Match my device', icon: Monitor },
]

/** Header button: Light / Dark / Match my device. */
export default function ThemeToggle() {
  const { themePref, theme, setThemePref } = useTheme()
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        button.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const Icon = themePref === 'system' ? Monitor : theme === 'light' ? Sun : Moon
  const current = OPTIONS.find((o) => o.value === themePref)!.label
  return (
    <div className="theme-toggle" ref={wrap}>
      <button
        ref={button}
        type="button"
        className="icon-btn"
        aria-label={`Theme: ${current}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon size={17} aria-hidden="true" />
      </button>
      {open && (
        <div className="theme-menu" role="menu" aria-label="Theme">
          {OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              role="menuitemradio"
              aria-checked={themePref === o.value}
              onClick={() => {
                setThemePref(o.value)
                setOpen(false)
                button.current?.focus()
              }}
            >
              <o.icon size={15} aria-hidden="true" />
              <span>{o.label}</span>
              {themePref === o.value && <Check size={15} aria-hidden="true" className="theme-menu-check" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
