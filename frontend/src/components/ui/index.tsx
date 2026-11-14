import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Inbox, Minus, RotateCw, X } from 'lucide-react'
import { statusLabel } from '../../lib/labels'

/* ---------- Layout primitives ---------- */

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  crumbs,
}: {
  eyebrow?: string
  title: string
  description?: ReactNode
  actions?: ReactNode
  crumbs?: { label: string; to?: string }[]
}) {
  return (
    <header className="page-header">
      {crumbs && crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="crumbs">
          {crumbs.map((c, i) => (
            <span key={i}>
              {c.to ? <Link to={c.to}>{c.label}</Link> : <span aria-current="page">{c.label}</span>}
              {i < crumbs.length - 1 && <span className="crumb-sep">/</span>}
            </span>
          ))}
        </nav>
      )}
      <div className="page-header-row">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h1>{title}</h1>
          {description && <p className="muted page-desc">{description}</p>}
        </div>
        {actions && <div className="head-actions">{actions}</div>}
      </div>
    </header>
  )
}

export function StatusPill({ status, label }: { status: string; label?: string }) {
  return <span className={`status-pill ${status}`}>{label || statusLabel(status)}</span>
}

export function Skeleton({ height = 16, width = '100%', count = 1 }: { height?: number; width?: number | string; count?: number }) {
  return (
    <div aria-hidden="true" className="skeleton-group">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height, width }} />
      ))}
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="page" aria-busy="true" aria-label="Loading">
      <Skeleton height={14} width={120} />
      <div style={{ height: 10 }} />
      <Skeleton height={32} width="40%" />
      <div style={{ height: 28 }} />
      <div className="kpi-grid">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="kpi-tile">
            <Skeleton height={12} width="60%" />
            <div style={{ height: 12 }} />
            <Skeleton height={28} width="40%" />
          </div>
        ))}
      </div>
      <div className="card">
        <Skeleton height={14} count={5} />
      </div>
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon?: ReactNode
  title: string
  body?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon" aria-hidden="true">
        {icon || <Inbox size={22} />}
      </div>
      <div className="empty-title">{title}</div>
      {body && <p className="muted small">{body}</p>}
      {action}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <span>{message}</span>
      {onRetry && (
        <button className="secondary small-btn" onClick={onRetry}>
          <RotateCw size={14} aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  )
}

/* ---------- KPI card ---------- */

export function KpiCard({
  label,
  value,
  previous,
  changePct,
  sub,
  to,
  basis,
  unavailable,
  format = (v) => String(v),
}: {
  label: string
  value: number | null | undefined
  previous?: number | null
  changePct?: number | null
  sub?: ReactNode
  to?: string
  basis?: string
  unavailable?: string
  format?: (v: number) => string
}) {
  const reduce = useReducedMotion()
  const trend =
    changePct == null ? null : changePct > 0 ? 'up' : changePct < 0 ? 'down' : 'flat'
  const body = (
    <motion.div
      className={`kpi-tile${unavailable ? ' unavailable' : ''}`}
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="kpi-label">
        {label}
        {basis === 'estimate' && <span className="basis-tag">est.</span>}
      </div>
      <div className="kpi-value">{unavailable ? '-' : value == null ? '-' : format(value)}</div>
      {unavailable ? (
        <div className="kpi-sub">{unavailable}</div>
      ) : (
        <div className="kpi-sub">
          {trend && (
            <span className={`trend ${trend}`}>
              {trend === 'up' ? <ArrowUpRight size={13} /> : trend === 'down' ? <ArrowDownRight size={13} /> : <Minus size={13} />}
              {Math.abs(changePct as number)}%
            </span>
          )}
          {previous != null && trend && <span className="muted"> vs previous period · </span>}
          {sub}
        </div>
      )}
    </motion.div>
  )
  return to ? (
    <Link to={to} className="kpi-link" aria-label={`${label}: open details`}>
      {body}
    </Link>
  ) : (
    body
  )
}

/* ---------- Tabs (roving focus) ---------- */

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
}: {
  tabs: { value: T; label: ReactNode; count?: number }[]
  value: T
  onChange: (v: T) => void
  label: string
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  function onKey(e: KeyboardEvent, index: number) {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    const next = (index + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
    refs.current[next]?.focus()
    onChange(tabs[next].value)
  }
  return (
    <div className="filter-row" role="tablist" aria-label={label}>
      {tabs.map((t, i) => (
        <button
          key={t.value}
          ref={(el) => {
            refs.current[i] = el
          }}
          role="tab"
          aria-selected={value === t.value}
          tabIndex={value === t.value ? 0 : -1}
          className={value === t.value ? 'chip active' : 'chip'}
          onClick={() => onChange(t.value)}
          onKeyDown={(e) => onKey(e, i)}
        >
          {t.label}
          {t.count != null && <span className="chip-count">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}

/* ---------- Dialog / Drawer ---------- */

function useEscape(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return
    const handler = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])
}

function useFocusOnOpen(open: boolean) {
  const ref = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!open) return
    const previous = document.activeElement as HTMLElement | null
    const node = ref.current
    const first = node?.querySelector<HTMLElement>('input, textarea, select, button:not(.dialog-close), [href]')
    ;(first || node)?.focus()
    return () => previous?.focus()
  }, [open])
  return ref
}

export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  wide,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}) {
  const reduce = useReducedMotion()
  const titleId = useId()
  useEscape(open, onClose)
  const ref = useFocusOnOpen(open)
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="overlay"
          onMouseDown={(e) => e.target === e.currentTarget && onClose()}
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            ref={ref}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className={`dialog${wide ? ' wide' : ''}`}
            initial={reduce ? false : { opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="dialog-head">
              <h2 id={titleId}>{title}</h2>
              <button className="icon-btn dialog-close" aria-label="Close" onClick={onClose}>
                <X size={18} />
              </button>
            </div>
            <div className="dialog-body">{children}</div>
            {footer && <div className="dialog-foot">{footer}</div>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = 'Confirm',
  tone = 'default',
  busy,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  body: ReactNode
  confirmLabel?: string
  tone?: 'default' | 'danger'
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <Dialog
      open={open}
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button className="secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className={tone === 'danger' ? 'danger' : ''} disabled={busy} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </>
      }
    >
      <div className="muted">{body}</div>
    </Dialog>
  )
}

export function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  const reduce = useReducedMotion()
  const titleId = useId()
  useEscape(open, onClose)
  const ref = useFocusOnOpen(open)
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="overlay"
          onMouseDown={(e) => e.target === e.currentTarget && onClose()}
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.aside
            ref={ref}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            className="drawer"
            initial={reduce ? false : { x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 40, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="dialog-head">
              <h2 id={titleId}>{title}</h2>
              <button className="icon-btn dialog-close" aria-label="Close" onClick={onClose}>
                <X size={18} />
              </button>
            </div>
            <div className="drawer-body">{children}</div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/* ---------- Toasts ---------- */

type Toast = { id: number; title: string; tone: 'success' | 'error' | 'info' }
const ToastContext = createContext<(t: Omit<Toast, 'id'>) => void>(() => undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { ...t, id }])
    window.setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 4200)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              className={`toast ${t.tone}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
            >
              {t.title}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}

/* ---------- Filter bar ---------- */

export function FilterBar({
  search,
  onSearch,
  placeholder = 'Search',
  children,
}: {
  search?: string
  onSearch?: (v: string) => void
  placeholder?: string
  children?: ReactNode
}) {
  const id = useId()
  return (
    <div className="filter-bar">
      {onSearch && (
        <div className="search-field">
          <label htmlFor={id} className="sr-only">
            {placeholder}
          </label>
          <input id={id} type="search" placeholder={placeholder} value={search} onChange={(e) => onSearch(e.target.value)} />
        </div>
      )}
      {children}
    </div>
  )
}

/* ---------- Responsive table: rows become cards on narrow screens ---------- */

export type Column<T> = { key: string; header: string; render: (row: T) => ReactNode; className?: string }

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty,
  caption,
}: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  empty?: ReactNode
  caption?: string
}) {
  if (rows.length === 0) return <>{empty || <EmptyState title="Nothing here yet" />}</>
  return (
    <div className="table-wrap">
      <table className="simple responsive">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)}>
              {columns.map((c) => (
                <td key={c.key} data-label={c.header} className={c.className}>
                  {c.render(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ---------- Timeline / activity feed ---------- */

export function Timeline({
  items,
}: {
  items: { id: string; title: ReactNode; meta?: ReactNode; tone?: string }[]
}) {
  if (items.length === 0) return <EmptyState title="No activity yet" />
  return (
    <ol className="timeline">
      {items.map((i) => (
        <li key={i.id} className={i.tone || ''}>
          <span className="timeline-dot" aria-hidden="true" />
          <div>
            <div>{i.title}</div>
            {i.meta && <div className="muted small mono">{i.meta}</div>}
          </div>
        </li>
      ))}
    </ol>
  )
}

export function Field({
  label,
  hint,
  error,
  children,
  id,
}: {
  label: string
  hint?: ReactNode
  error?: string
  children: ReactNode
  id: string
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && !error && <span className="muted small">{hint}</span>}
      {error && (
        <span className="error" role="alert">
          {error}
        </span>
      )}
    </div>
  )
}
