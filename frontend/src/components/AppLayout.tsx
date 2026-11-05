import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Bell, LogOut, Menu, Plus, Search } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import { useResource } from '../hooks/useResource'
import { ADMIN_GROUP, ALL_NAV, NAV_GROUPS } from '../lib/nav'
import { Dialog, PageSkeleton } from './ui'
import Logo from './Logo'

type Workspace = { name: string; automation_paused: boolean; kill_switch_enabled: boolean; your_role_label: string }

export default function AppLayout() {
  const { user, memberships, logout } = useAuth()
  const { activeOrganizationId: orgId, setActiveOrganizationId } = useWorkspace()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  const workspace = useResource<{ workspace: Workspace }>(orgId ? `/organizations/${orgId}` : null, { pollMs: 30000 })
  const notifications = useResource<{ unread_count: number }>(
    orgId ? `/organizations/${orgId}/notifications?limit=1` : null,
    { pollMs: 20000 },
  )
  const approvals = useResource<{ approvals: unknown[] }>(orgId ? `/organizations/${orgId}/approvals` : null, {
    pollMs: 30000,
  })

  useEffect(() => setSidebarOpen(false), [location.pathname])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // No workspace yet: send people to create one.
  useEffect(() => {
    if (user && memberships.length === 0) navigate('/create-workspace', { replace: true })
  }, [user, memberships.length, navigate])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const ws = workspace.data?.workspace
  const unread = notifications.data?.unread_count || 0
  const pendingApprovals = approvals.data?.approvals.length || 0

  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      {sidebarOpen && <div className="sidebar-scrim" onClick={() => setSidebarOpen(false)} aria-hidden="true" />}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`} aria-label="Main navigation">
        <Link to="/app/dashboard" className="brand">
          <Logo size={24} />
          ARC
        </Link>
        {(user?.is_platform_admin ? [...NAV_GROUPS, ADMIN_GROUP] : NAV_GROUPS).map((group) => (
          <div key={group.label} className="sidebar-group">
            <div className="sidebar-group-label">{group.label}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/app/settings'}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <item.icon size={16} aria-hidden="true" />
                {item.label}
                {item.to === '/app/approvals' && pendingApprovals > 0 && (
                  <span className="nav-badge">{pendingApprovals}</span>
                )}
                {item.to === '/app/notifications' && unread > 0 && <span className="nav-badge">{unread}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </aside>

      <div className="main-col">
        <header className="topbar">
          <button className="icon-btn mobile-only" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}>
            <Menu size={18} />
          </button>
          {memberships.length > 1 ? (
            <>
              <label htmlFor="workspace-switcher" className="sr-only">
                Workspace
              </label>
              <select
                id="workspace-switcher"
                value={orgId || ''}
                onChange={(e) => setActiveOrganizationId(e.target.value)}
              >
                {memberships.map((m) => (
                  <option key={m.organization_id} value={m.organization_id}>
                    {m.organization_name}
                  </option>
                ))}
              </select>
            </>
          ) : (
            <strong className="small">{ws?.name || memberships[0]?.organization_name}</strong>
          )}
          {ws && (
            <Link
              to="/app/operations"
              className={`automation-chip${ws.automation_paused ? ' paused' : ''}`}
              title="Automation state"
            >
              <span className="dot" aria-hidden="true" />
              {ws.automation_paused ? 'Agents paused' : 'Agents active'}
              {ws.kill_switch_enabled && ' · kill switch on'}
            </Link>
          )}
          <span className="spacer" />
          <button className="cmdk-trigger" onClick={() => setPaletteOpen(true)} aria-label="Search pages (Ctrl+K)">
            <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
              <Search size={14} aria-hidden="true" />
              <span className="cmdk-label">Jump to…</span>
            </span>
            <kbd className="cmdk-label">Ctrl K</kbd>
          </button>
          <Link to="/app/campaigns/new" className="btn small-btn" style={{ padding: '7px 12px' }}>
            <Plus size={14} aria-hidden="true" /> <span className="cmdk-label">Create campaign</span>
          </Link>
          <Link to="/app/notifications" className="icon-btn bell" aria-label={`Notifications, ${unread} unread`}>
            <Bell size={18} />
            {unread > 0 && <span className="bell-dot">{unread > 9 ? '9+' : unread}</span>}
          </Link>
          <span className="muted small cmdk-label" title={ws?.your_role_label}>
            {user?.full_name}
          </span>
          <button className="icon-btn" aria-label="Sign out" onClick={handleLogout}>
            <LogOut size={16} />
          </button>
        </header>
        <main id="main" tabIndex={-1}>
          <Suspense fallback={<PageSkeleton />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState('')
  const [index, setIndex] = useState(0)
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement | null>(null)
  const results = useMemo(() => {
    const term = q.trim().toLowerCase()
    const actions = [{ to: '/app/campaigns/new', label: 'Create campaign', keywords: 'new brief' }]
    return [...actions, ...ALL_NAV].filter(
      (i) => !term || i.label.toLowerCase().includes(term) || (i.keywords || '').includes(term),
    )
  }, [q])

  useEffect(() => {
    if (open) {
      setQ('')
      setIndex(0)
    }
  }, [open])

  function go(to: string) {
    onClose()
    navigate(to)
  }

  return (
    <Dialog open={open} onClose={onClose} title="Jump to">
      <div className="cmdk" style={{ margin: 0, maxWidth: 'none', border: 'none', boxShadow: 'none' }}>
        <label htmlFor="cmdk-input" className="sr-only">
          Search pages
        </label>
        <input
          id="cmdk-input"
          ref={inputRef}
          autoFocus
          placeholder="Type a page or action…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setIndex(0)
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') setIndex((i) => Math.min(i + 1, results.length - 1))
            if (e.key === 'ArrowUp') setIndex((i) => Math.max(i - 1, 0))
            if (e.key === 'Enter' && results[index]) go(results[index].to)
          }}
          role="combobox"
          aria-expanded="true"
          aria-controls="cmdk-list"
        />
        <ul id="cmdk-list" role="listbox">
          {results.map((r, i) => (
            <li key={r.to + r.label} role="option" aria-selected={i === index} onMouseEnter={() => setIndex(i)} onClick={() => go(r.to)}>
              <span>{r.label}</span>
              <span className="muted mono">{r.to}</span>
            </li>
          ))}
          {results.length === 0 && <li className="muted">No matches</li>}
        </ul>
      </div>
    </Dialog>
  )
}
