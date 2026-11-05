import RetentionCard from '../../components/RetentionCard'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Download, Plus } from 'lucide-react'
import { apiRequest } from '../../api/client'
import type { ActivityEvent, AgentInfo } from '../../api/types'
import {
  ConfirmDialog,
  DataTable,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  FilterBar,
  PageHeader,
  PageSkeleton,
  StatusPill,
  useToast,
} from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useAction, useResource } from '../../hooks/useResource'
import { humanize, money, relativeTime } from '../../lib/labels'

import { API_BASE_URL as API } from '../../lib/apiBase'

type Workspace = {
  id: string; name: string; timezone: string; max_concurrent_tasks: number; default_run_budget_usd: number | null
  platform_default_run_budget_usd: number; automation_paused: boolean; kill_switch_enabled: boolean; your_role: string; your_role_label: string
}

function useWorkspaceInfo() {
  const { activeOrganizationId: orgId } = useWorkspace()
  return useResource<{ workspace: Workspace }>(orgId ? `/organizations/${orgId}` : null)
}

/* ---------------- Team ---------------- */

type Members = {
  members: { membership_id: string; user_id: string; full_name: string; email: string; role: string; role_label: string; joined_at: string }[]
  invitations: { id: string; email: string; role: string; expires_at: string }[]
  roles: { role: string; label: string }[]
}

export function TeamPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const { user } = useAuth()
  const ws = useWorkspaceInfo()
  const { data, error, loading, reload } = useResource<Members>(orgId ? `/organizations/${orgId}/members` : null)
  const [inviting, setInviting] = useState(false)
  const [form, setForm] = useState({ email: '', role: 'contributor' })
  const [link, setLink] = useState<string | null>(null)
  const [removing, setRemoving] = useState<Members['members'][number] | null>(null)
  const action = useAction()
  const isAdmin = ['owner', 'admin'].includes(ws.data?.workspace.your_role || '')

  async function invite() {
    const r = await action.run(() => apiRequest<{ invite_link: string }>(`/organizations/${orgId}/invitations`, { method: 'POST', body: form }))
    if (r) {
      setLink(r.invite_link)
      setInviting(false)
      setForm({ email: '', role: 'contributor' })
      reload()
    }
  }
  async function changeRole(membershipId: string, role: string) {
    await action.run(() => apiRequest(`/organizations/${orgId}/members/${membershipId}`, { method: 'PATCH', body: { role } }))
    reload()
  }
  async function remove() {
    if (!removing) return
    await action.run(() => apiRequest(`/organizations/${orgId}/members/${removing.membership_id}`, { method: 'DELETE' }))
    setRemoving(null)
    reload()
  }
  async function revoke(id: string) {
    await action.run(() => apiRequest(`/organizations/${orgId}/invitations/${id}`, { method: 'DELETE' }))
    reload()
  }

  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page">
      <PageHeader title="Team" description="Roles decide who can run agents, approve work, manage billing and change policies."
        actions={isAdmin && <button onClick={() => setInviting(true)}><Plus size={15} aria-hidden="true" /> Invite</button>} />
      {(error || action.error) && <ErrorState message={(error || action.error) as string} />}
      <div className="card">
        <DataTable rows={data?.members || []} rowKey={(r) => r.membership_id} caption="Members"
          columns={[
            { key: 'n', header: 'Member', render: (r) => <><strong className="small">{r.full_name}</strong><div className="muted small">{r.email}</div></> },
            { key: 'r', header: 'Role', render: (r) => isAdmin && r.user_id !== user?.id ? (
              <>
                <label htmlFor={`role-${r.membership_id}`} className="sr-only">Role for {r.full_name}</label>
                <select id={`role-${r.membership_id}`} className="select-inline" value={r.role} onChange={(e) => changeRole(r.membership_id, e.target.value)}>
                  {data?.roles.map((x) => <option key={x.role} value={x.role}>{x.label}</option>)}
                </select>
              </>
            ) : <span className="small">{r.role_label}</span> },
            { key: 'j', header: 'Joined', render: (r) => <span className="muted small">{relativeTime(r.joined_at)}</span> },
            { key: 'a', header: '', render: (r) => isAdmin && r.user_id !== user?.id && <button className="secondary small-btn" onClick={() => setRemoving(r)}>Remove</button> },
          ]} />
      </div>
      {isAdmin && (data?.invitations.length || 0) > 0 && (
        <div className="card">
          <h2>Pending invitations</h2>
          <DataTable rows={data!.invitations} rowKey={(r) => r.id} caption="Invitations"
            columns={[
              { key: 'e', header: 'Email', render: (r) => r.email },
              { key: 'r', header: 'Role', render: (r) => humanize(r.role) },
              { key: 'x', header: 'Expires', render: (r) => <span className="muted small">{relativeTime(r.expires_at)}</span> },
              { key: 'a', header: '', render: (r) => <button className="secondary small-btn" onClick={() => revoke(r.id)}>Revoke</button> },
            ]} />
        </div>
      )}
      <div className="card">
        <h2>What each role can do</h2>
        <ul className="deliverable-list small">
          <li><strong>Workspace Owner</strong> — everything, including billing, ownership and deletion.</li>
          <li><strong>Administrator</strong> — team, policies, budgets, integrations, kill switch.</li>
          <li><strong>Marketing Manager</strong> — run, pause and retry agents; approve work.</li>
          <li><strong>Approver</strong> — approve or reject deliverables and run starts.</li>
          <li><strong>Contributor</strong> — start runs, edit knowledge and calendar.</li>
          <li><strong>Analyst / Viewer</strong> — read-only.</li>
        </ul>
      </div>
      <Dialog open={inviting} onClose={() => setInviting(false)} title="Invite a teammate"
        footer={<><button className="secondary" onClick={() => setInviting(false)}>Cancel</button><button disabled={action.busy} onClick={invite}>Create invite</button></>}>
        {action.error && <div className="banner error">{action.error}</div>}
        <Field id="inv-email" label="Email"><input id="inv-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field id="inv-role" label="Role">
          <select id="inv-role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {data?.roles.filter((r) => r.role !== 'owner').map((r) => <option key={r.role} value={r.role}>{r.label}</option>)}
          </select>
        </Field>
      </Dialog>
      <Dialog open={!!link} onClose={() => setLink(null)} title="Share this invitation link" footer={<button onClick={() => setLink(null)}>Done</button>}>
        <p className="muted small">Email delivery isn't configured yet, so share this link yourself. It works once, for that email, and expires in 7 days.</p>
        <pre className="content-json" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{link}</pre>
        <button className="secondary small-btn" onClick={() => link && navigator.clipboard?.writeText(link)}>Copy link</button>
      </Dialog>
      <ConfirmDialog open={!!removing} title="Remove member?" body={`${removing?.full_name} will lose access to this workspace immediately.`} tone="danger"
        confirmLabel="Remove" onConfirm={remove} onCancel={() => setRemoving(null)} />
    </div>
  )
}

/* ---------------- Billing ---------------- */

type PlanT = { code: string; name: string; tagline: string; monthly_price_usd: number | null; entitlements: Record<string, number | null>; features: string[] }
type Billing = {
  subscription: { status: string; plan: PlanT; billing_connected: boolean; current_period_end: string | null }
  usage: Record<string, { used: number; limit: number | null }>
  plans: PlanT[]
  payments: { connected: boolean; note: string }
}

export function UsageBars({ usage }: { usage: Billing['usage'] }) {
  return (
    <div className="stack" style={{ gap: 12 }}>
      {Object.entries(usage).filter(([k]) => k !== 'agents').map(([k, v]) => {
        const pct = v.limit ? Math.min(100, (v.used / v.limit) * 100) : 0
        const label = k === 'monthly_ai_budget_usd' ? `${money(v.used)} of ${v.limit == null ? 'unlimited' : money(v.limit)}` : `${v.used} of ${v.limit == null ? 'unlimited' : v.limit}`
        return (
          <div key={k}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }} className="small">
              <span>{humanize(k.replace('monthly_', 'monthly '))}</span>
              <span className={pct >= 100 ? 'text-danger' : pct >= 80 ? 'text-warning' : 'muted'}>{label}</span>
            </div>
            <div className="progress" style={{ marginTop: 6 }}><span style={{ width: `${pct}%`, background: pct >= 100 ? 'var(--color-danger)' : undefined }} /></div>
          </div>
        )
      })}
    </div>
  )
}

export function BillingPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const ws = useWorkspaceInfo()
  const { data, error, loading, reload } = useResource<Billing>(orgId ? `/organizations/${orgId}/billing` : null)
  const history = useResource<{ events: { id: string; event_type: string; amount_usd: number | null; is_test: boolean; outcome: string; created_at: string }[] }>(
    orgId ? `/organizations/${orgId}/billing/history` : null,
  )
  const action = useAction()
  const isOwner = ws.data?.workspace.your_role === 'owner'

  async function choose(plan: PlanT) {
    if (plan.monthly_price_usd == null) return navigate('/contact')
    const r = await action.run(() => apiRequest<{ checkout: { url: string; mode: string } }>(`/organizations/${orgId}/billing/checkout`, { method: 'POST', body: { plan_code: plan.code } }))
    if (!r) return
    if (r.checkout.url.startsWith('/')) navigate(r.checkout.url)
    else window.location.assign(r.checkout.url)
  }

  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page page-wide">
      <PageHeader title="Billing" description="Your plan, usage against its limits, and billing history." />
      {params.get('checkout') === 'success' && <div className="banner success">Checkout complete. Your plan updates as soon as the payment provider confirms it.</div>}
      {(error || action.error) && <ErrorState message={(error || action.error) as string} onRetry={reload} />}
      {data && (
        <>
          <div className="notice">{data.payments.note} Prices are provisional.</div>
          <div className="grid-3">
            <div className="card">
              <h2>Current plan</h2>
              <p style={{ fontSize: '1.6rem', fontWeight: 800, margin: '0 0 4px' }}>{data.subscription.plan.name}</p>
              <p className="small"><StatusPill status={data.subscription.status === 'active' ? 'active' : data.subscription.status === 'past_due' ? 'failed' : 'pending'} label={humanize(data.subscription.status)} />
                {data.subscription.status === 'trialing' && data.subscription.current_period_end && <span className="muted"> · trial ends {new Date(data.subscription.current_period_end).toLocaleDateString()}</span>}
              </p>
              <p className="muted small">{data.subscription.plan.tagline}</p>
            </div>
            <div className="card">
              <h2>Usage this month</h2>
              <UsageBars usage={data.usage} />
            </div>
          </div>
          <h2 className="section-title">Change plan</h2>
          <div className="pricing-grid">
            {data.plans.map((p) => (
              <div key={p.code} className={`plan${p.code === data.subscription.plan.code ? ' featured' : ''}`}>
                <strong>{p.name}</strong>
                <div className="price">{p.monthly_price_usd == null ? 'Custom' : `$${p.monthly_price_usd}`}{p.monthly_price_usd != null && <small> /mo</small>}</div>
                <p className="muted small" style={{ margin: 0 }}>{p.tagline}</p>
                <ul>
                  <li>{p.entitlements.monthly_workflow_runs ?? 'Unlimited'} runs / month</li>
                  <li>{p.entitlements.seats ?? 'Unlimited'} seats</li>
                  <li>{p.entitlements.monthly_ai_budget_usd == null ? 'Custom' : money(p.entitlements.monthly_ai_budget_usd)} AI budget</li>
                </ul>
                {p.code === data.subscription.plan.code ? <span className="muted small">Current plan</span> : (
                  <button disabled={!isOwner || action.busy} onClick={() => choose(p)} title={isOwner ? undefined : 'Only the owner can change plans'}>
                    {p.monthly_price_usd == null ? 'Contact sales' : `Switch to ${p.name}`}
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="card" style={{ marginTop: 18 }}>
            <h2>Billing history</h2>
            <DataTable rows={history.data?.events || []} rowKey={(r) => r.id} caption="Billing history"
              empty={<EmptyState title="No billing events yet" body="Events appear here once the payment provider confirms them." />}
              columns={[
                { key: 't', header: 'Event', render: (r) => <span className="mono small">{r.event_type}</span> },
                { key: 'o', header: 'Outcome', render: (r) => humanize(r.outcome) },
                { key: 'a', header: 'Amount', render: (r) => (r.amount_usd != null ? money(r.amount_usd) : '—') },
                { key: 'm', header: 'Mode', render: (r) => (r.is_test ? <span className="sample-tag">TEST</span> : 'Live') },
                { key: 'w', header: 'When', render: (r) => <span className="muted small">{relativeTime(r.created_at)}</span> },
              ]} />
          </div>
          {isOwner && orgId && (
            <RetentionCard orgId={orgId} workspaceName={ws.data?.workspace.name || ''} planName={data.subscription.plan.name} />
          )}
        </>
      )}
    </div>
  )
}

export function TestCheckoutPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const action = useAction()
  const plan = params.get('plan') || ''
  async function complete() {
    const r = await action.run(() => apiRequest(`/organizations/${orgId}/billing/test-complete`, { method: 'POST', body: { plan_code: plan, session_id: params.get('session') } }))
    if (r) navigate('/app/billing?checkout=success')
  }
  return (
    <div className="page" style={{ maxWidth: 560 }}>
      <PageHeader title="Test checkout" />
      <div className="card">
        <p><span className="sample-tag">TEST MODE — NO REAL PAYMENT</span></p>
        <p className="muted">This simulates the payment provider confirming a subscription to <strong>{humanize(plan)}</strong>. It sends a signed webhook through the same verification path real payments use.</p>
        {action.error && <div className="banner error">{action.error}</div>}
        <div className="head-actions">
          <button disabled={action.busy} onClick={complete}>Complete test payment</button>
          <Link to="/app/billing" className="btn secondary">Cancel</Link>
        </div>
      </div>
    </div>
  )
}

/* ---------------- Notifications ---------------- */

type Notif = { id: string; kind: string; severity: string; title: string; body: string | null; link: string | null; read: boolean; created_at: string }

export function NotificationsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [unreadOnly, setUnreadOnly] = useState(false)
  const { data, error, reload } = useResource<{ notifications: Notif[]; unread_count: number }>(
    orgId ? `/organizations/${orgId}/notifications?limit=100${unreadOnly ? '&unread=1' : ''}` : null, { pollMs: 20000 },
  )
  async function markAll() {
    await apiRequest(`/organizations/${orgId}/notifications/read`, { method: 'POST', body: {} })
    reload()
  }
  async function markOne(id: string) {
    await apiRequest(`/organizations/${orgId}/notifications/read`, { method: 'POST', body: { ids: [id] } })
    reload()
  }
  return (
    <div className="page">
      <PageHeader title="Notifications" description="Run results, approvals waiting, budget alerts and learnings to review."
        actions={<>
          <label className="small" htmlFor="unread-only" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input id="unread-only" type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only
          </label>
          <button className="secondary" onClick={markAll} disabled={!data?.unread_count}>Mark all read</button>
        </>} />
      {error && <ErrorState message={error} onRetry={reload} />}
      <div className="card">
        {(data?.notifications.length || 0) === 0 ? <EmptyState title="You're all caught up" /> : (
          <ul className="notif-list">
            {data!.notifications.map((n) => (
              <li key={n.id} className={n.read ? '' : 'unread'}>
                <span className={`notif-sev ${n.severity}`} aria-hidden="true" />
                <div style={{ flex: 1 }}>
                  <div className="notif-title">{n.link ? <Link to={n.link} onClick={() => markOne(n.id)}>{n.title}</Link> : n.title}</div>
                  {n.body && <div className="muted small">{n.body}</div>}
                  <div className="muted small mono">{relativeTime(n.created_at)}</div>
                </div>
                {!n.read && <button className="link-btn small" onClick={() => markOne(n.id)}>Mark read</button>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

/* ---------------- Settings ---------------- */

export function SettingsPage() {
  const ws = useWorkspaceInfo()
  const toast = useToast()
  const action = useAction()
  const [form, setForm] = useState({ name: '', timezone: 'UTC' })
  useEffect(() => {
    if (ws.data) setForm({ name: ws.data.workspace.name, timezone: ws.data.workspace.timezone })
  }, [ws.data])
  if (!ws.data) return <PageSkeleton />
  const w = ws.data.workspace
  const canEdit = ['owner', 'admin'].includes(w.your_role)
  async function save() {
    const r = await action.run(() => apiRequest(`/organizations/${w.id}`, { method: 'PATCH', body: form }))
    if (r) {
      toast({ title: 'Workspace updated', tone: 'success' })
      ws.reload()
    }
  }
  return (
    <div className="page">
      <PageHeader title="Workspace settings" description={`You are ${w.your_role_label} in this workspace.`} />
      {action.error && <ErrorState message={action.error} />}
      <div className="card">
        <div className="form-grid">
          <Field id="ws-name" label="Workspace name"><input id="ws-name" disabled={!canEdit} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field id="ws-tz" label="Time zone" hint="IANA name, e.g. Europe/London"><input id="ws-tz" disabled={!canEdit} value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })} /></Field>
        </div>
        {canEdit && <button disabled={action.busy} onClick={save}>Save</button>}
      </div>
      <div className="grid-3">
        {[
          ['Automation', 'Policies, budgets, concurrency and emergency controls.', '/app/settings/automation'],
          ['Usage', 'Plan limits, AI cost and execution quotas.', '/app/settings/usage'],
          ['Security', 'Password, sessions, data export and deletion.', '/app/settings/security'],
          ['Team', 'Members, roles and invitations.', '/app/team'],
        ].map(([t, b, to]) => (
          <Link key={t} to={to} className="card" style={{ color: 'inherit', textDecoration: 'none' }}><h3>{t}</h3><p className="muted small" style={{ margin: 0 }}>{b}</p></Link>
        ))}
      </div>
    </div>
  )
}

export function SecuritySettingsPage() {
  const { user, refresh, logout } = useAuth()
  const ws = useWorkspaceInfo()
  const navigate = useNavigate()
  const toast = useToast()
  const action = useAction()
  const [pw, setPw] = useState({ current_password: '', new_password: '' })
  const [confirmName, setConfirmName] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const w = ws.data?.workspace

  async function changePassword() {
    const r = await action.run(() => apiRequest('/auth/change-password', { method: 'POST', body: pw }))
    if (r) {
      setPw({ current_password: '', new_password: '' })
      toast({ title: 'Password changed. Other sessions were signed out.', tone: 'success' })
    }
  }
  async function signOutEverywhere() {
    await action.run(() => apiRequest('/auth/sign-out-everywhere', { method: 'POST' }))
    await logout().catch(() => undefined)
    navigate('/login')
  }
  async function verifyEmail() {
    const r = await action.run(() => apiRequest<{ message: string }>('/auth/verify-email/request', { method: 'POST' }))
    if (r) toast({ title: r.message, tone: 'info' })
    refresh()
  }
  async function scheduleDeletion() {
    const r = await action.run(() => apiRequest(`/organizations/${w?.id}/deletion`, { method: 'POST', body: { confirm_name: confirmName } }))
    setConfirmDelete(false)
    if (r) {
      toast({ title: 'Deletion scheduled in 30 days. Agents paused.', tone: 'info' })
      ws.reload()
    }
  }

  return (
    <div className="page">
      <PageHeader title="Security" description="Your account and this workspace's data." />
      {action.error && <ErrorState message={action.error} />}
      <div className="grid-3">
        <div className="card">
          <h2>Password</h2>
          <Field id="sec-current" label="Current password"><input id="sec-current" type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
          <Field id="sec-new" label="New password" hint="At least 8 characters."><input id="sec-new" type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
          <button disabled={action.busy} onClick={changePassword}>Change password</button>
        </div>
        <div className="card">
          <h2>Sessions & verification</h2>
          <p className="small">Email: {user?.email} — {user?.email_verified ? <span className="text-success">verified</span> : <span className="text-warning">not verified</span>}</p>
          {!user?.email_verified && <button className="secondary small-btn" onClick={verifyEmail}>Send verification link</button>}
          <p className="muted small" style={{ marginTop: 14 }}>Signs out this and every other device.</p>
          <button className="secondary" onClick={signOutEverywhere}>Sign out everywhere</button>
          <p className="muted small" style={{ marginTop: 14 }}>Multi-factor authentication is designed but not available yet.</p>
        </div>
      </div>
      {w && ['owner', 'admin'].includes(w.your_role) && (
        <div className="card">
          <h2>Export workspace data</h2>
          <p className="muted small">Download everything in this workspace as JSON: campaigns, runs, tasks, executions, deliverables and versions, approvals, knowledge, calendar and audit log. Secrets are never included.</p>
          <a className="btn secondary" href={`${API}/organizations/${w.id}/export`}><Download size={15} aria-hidden="true" /> Download export</a>
        </div>
      )}
      {w && w.your_role === 'owner' && (
        <div className="card" style={{ borderColor: 'rgba(255,138,128,0.35)' }}>
          <h2>Delete workspace</h2>
          <p className="muted small">Pauses all agents and blocks exports immediately; data is permanently purged after 30 days. You can cancel during that time.</p>
          <Field id="del-confirm" label={`Type “${w.name}” to confirm`}><input id="del-confirm" value={confirmName} onChange={(e) => setConfirmName(e.target.value)} /></Field>
          <button className="danger" disabled={confirmName !== w.name} onClick={() => setConfirmDelete(true)}>Schedule deletion</button>
          <button className="secondary" style={{ marginLeft: 8 }} onClick={async () => { await action.run(() => apiRequest(`/organizations/${w.id}/deletion`, { method: 'DELETE' })); ws.reload() }}>Cancel scheduled deletion</button>
        </div>
      )}
      <ConfirmDialog open={confirmDelete} title="Schedule deletion?" body="This workspace and all its data will be permanently deleted in 30 days." tone="danger"
        confirmLabel="Schedule deletion" onConfirm={scheduleDeletion} onCancel={() => setConfirmDelete(false)} />
    </div>
  )
}

type Policy = { action_type: string; label: string; mode: string; locked: boolean; enforced_by: string }

export function AutomationSettingsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const ws = useWorkspaceInfo()
  const toast = useToast()
  const policies = useResource<{ policies: Policy[] }>(orgId ? `/organizations/${orgId}/policies` : null)
  const agents = useResource<{ agents: AgentInfo[] }>(orgId ? `/organizations/${orgId}/agents` : null)
  const action = useAction()
  const [limits, setLimits] = useState({ max_concurrent_tasks: 2, default_run_budget_usd: '' })
  const [budgets, setBudgets] = useState<Record<string, string>>({})
  useEffect(() => {
    if (ws.data) setLimits({ max_concurrent_tasks: ws.data.workspace.max_concurrent_tasks, default_run_budget_usd: ws.data.workspace.default_run_budget_usd?.toString() || '' })
  }, [ws.data])
  useEffect(() => {
    if (agents.data) setBudgets(Object.fromEntries(agents.data.agents.map((a) => [a.agent_id, a.settings.monthly_budget_usd?.toString() || ''])))
  }, [agents.data])
  if (!ws.data || !policies.data) return <PageSkeleton />
  const w = ws.data.workspace
  const admin = ['owner', 'admin'].includes(w.your_role)

  async function control(field: string, value: boolean) {
    await action.run(() => apiRequest(`/organizations/${orgId}/operations/controls`, { method: 'PATCH', body: { [field]: value } }))
    ws.reload()
  }
  async function setMode(p: Policy, mode: string) {
    await action.run(() => apiRequest(`/organizations/${orgId}/policies/${p.action_type}`, { method: 'PATCH', body: { mode } }))
    policies.reload()
  }
  async function saveLimits() {
    const r = await action.run(() => apiRequest(`/organizations/${orgId}`, { method: 'PATCH', body: { max_concurrent_tasks: Number(limits.max_concurrent_tasks), default_run_budget_usd: limits.default_run_budget_usd || null } }))
    if (r) toast({ title: 'Limits saved', tone: 'success' })
  }
  async function saveBudget(agentId: string) {
    const r = await action.run(() => apiRequest(`/organizations/${orgId}/agents/${agentId}/settings`, { method: 'PATCH', body: { monthly_budget_usd: budgets[agentId] || null } }))
    if (r) toast({ title: 'Agent budget saved', tone: 'success' })
  }

  return (
    <div className="page page-wide">
      <PageHeader title="Automation" description="What agents may do on their own, how much they may spend, and how to stop them. All of this is enforced by the backend." />
      {action.error && <ErrorState message={action.error} />}
      <div className="card controls-bar">
        <div className="control">
          <div><div className="control-title">Pause all agents</div><div className="muted small">{w.automation_paused ? 'Paused — no new agent work starts.' : 'Running.'}</div></div>
          <button disabled={!admin} className={w.automation_paused ? '' : 'secondary'} onClick={() => control('automation_paused', !w.automation_paused)}>{w.automation_paused ? 'Resume' : 'Pause all'}</button>
        </div>
        <div className="control">
          <div><div className="control-title">Kill switch (external actions)</div><div className="muted small">{w.kill_switch_enabled ? 'On — exports blocked.' : 'Off.'}</div></div>
          <button disabled={!admin} className={w.kill_switch_enabled ? '' : 'danger'} onClick={() => control('kill_switch_enabled', !w.kill_switch_enabled)}>{w.kill_switch_enabled ? 'Turn off' : 'Engage'}</button>
        </div>
      </div>
      <div className="card">
        <h2>Action policies</h2>
        <DataTable rows={policies.data.policies} rowKey={(r) => r.action_type} caption="Action policies"
          columns={[
            { key: 'l', header: 'Action', render: (r) => <><strong className="small">{r.label}</strong><div className="muted small">{r.enforced_by}</div></> },
            { key: 'm', header: 'Mode', render: (r) => r.locked ? <span className="small">{humanize(r.mode)} <span className="muted">(platform locked)</span></span> : (
              <>
                <label htmlFor={`pol-${r.action_type}`} className="sr-only">Mode for {r.label}</label>
                <select id={`pol-${r.action_type}`} className="select-inline" disabled={!admin} value={r.mode} onChange={(e) => setMode(r, e.target.value)}>
                  <option value="auto">Automatic</option>
                  <option value="require_approval">Require approval</option>
                </select>
              </>
            ) },
          ]} />
      </div>
      <div className="card">
        <h2>Budgets & concurrency</h2>
        <div className="form-grid">
          <Field id="lim-conc" label="Max agents working at once" hint="1–12. Lower values are gentler on provider rate limits.">
            <input id="lim-conc" type="number" min={1} max={12} disabled={!admin} value={limits.max_concurrent_tasks} onChange={(e) => setLimits({ ...limits, max_concurrent_tasks: Number(e.target.value) })} />
          </Field>
          <Field id="lim-budget" label="Budget per campaign run (USD, estimated)" hint={`Blank = platform default ($${w.platform_default_run_budget_usd}). Capped by your plan.`}>
            <input id="lim-budget" type="number" step="0.05" min={0.05} disabled={!admin} value={limits.default_run_budget_usd} onChange={(e) => setLimits({ ...limits, default_run_budget_usd: e.target.value })} />
          </Field>
        </div>
        {admin && <button disabled={action.busy} onClick={saveLimits}>Save limits</button>}
      </div>
      <div className="card">
        <h2>Per-agent monthly budgets</h2>
        <DataTable rows={agents.data?.agents || []} rowKey={(r) => r.agent_id} caption="Agent budgets"
          columns={[
            { key: 'a', header: 'Agent', render: (r) => <span className="small">{String(r.number).padStart(2, '0')} {r.name}</span> },
            { key: 's', header: 'Spent (30d, est.)', render: (r) => money(r.stats_30d.estimated_cost_usd) },
            { key: 'b', header: 'Monthly cap (USD)', render: (r) => (
              <>
                <label htmlFor={`bud-${r.agent_id}`} className="sr-only">Monthly budget for {r.name}</label>
                <input id={`bud-${r.agent_id}`} className="select-inline" style={{ width: 110 }} type="number" step="0.1" min={0} placeholder="No cap" disabled={!admin}
                  value={budgets[r.agent_id] ?? ''} onChange={(e) => setBudgets({ ...budgets, [r.agent_id]: e.target.value })} />
              </>
            ) },
            { key: 'x', header: '', render: (r) => admin && <button className="secondary small-btn" onClick={() => saveBudget(r.agent_id)}>Save</button> },
          ]} />
      </div>
    </div>
  )
}

export function UsagePage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const billing = useResource<Billing>(orgId ? `/organizations/${orgId}/billing` : null)
  const usage = useResource<{ usage: { id: string; provider: string; model: string; input_tokens: number; output_tokens: number; estimated_cost_usd: number; created_at: string }[] }>(
    orgId ? `/organizations/${orgId}/usage` : null,
  )
  if (!billing.data) return <PageSkeleton />
  return (
    <div className="page page-wide">
      <PageHeader title="Usage" description="Limits come from your plan and are enforced before any agent runs. Costs are estimates from token counts, not invoices."
        actions={<Link to="/app/billing" className="btn secondary">Change plan</Link>} />
      <div className="card"><h2>{billing.data.subscription.plan.name} plan · this month</h2><UsageBars usage={billing.data.usage} /></div>
      <div className="card">
        <h2>AI calls</h2>
        <DataTable rows={(usage.data?.usage || []).slice(0, 100)} rowKey={(r) => r.id} caption="AI usage records"
          empty={<EmptyState title="No AI calls yet" />}
          columns={[
            { key: 'w', header: 'When', render: (r) => <span className="muted small">{relativeTime(r.created_at)}</span> },
            { key: 'p', header: 'Provider', render: (r) => <span className="mono small">{r.provider} · {r.model}</span> },
            { key: 't', header: 'Tokens', render: (r) => (r.input_tokens + r.output_tokens).toLocaleString() },
            { key: 'c', header: 'Est. cost', render: (r) => money(r.estimated_cost_usd) },
          ]} />
      </div>
    </div>
  )
}

export function AuditLogPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [q, setQ] = useState('')
  const { data, error, loading } = useResource<{ audit_events: ActivityEvent[] }>(orgId ? `/organizations/${orgId}/audit-events` : null)
  if (loading && !data) return <PageSkeleton />
  const rows = (data?.audit_events || []).filter((e) => !q || `${e.action} ${e.target_type}`.toLowerCase().includes(q.toLowerCase()))
  return (
    <div className="page page-wide">
      <PageHeader title="Audit log" description="Append-only record of who did what. The most recent 200 events; the full log is in the workspace export." />
      {error && <ErrorState message={error} />}
      <FilterBar search={q} onSearch={setQ} placeholder="Filter by action, e.g. approval" />
      <div className="card">
        <DataTable rows={rows} rowKey={(r) => r.id} caption="Audit events" empty={<EmptyState title="No events" />}
          columns={[
            { key: 'w', header: 'When', render: (r) => <span className="mono small">{new Date(r.created_at.endsWith('Z') || r.created_at.includes('+') ? r.created_at : `${r.created_at}Z`).toLocaleString()}</span> },
            { key: 'a', header: 'Action', render: (r) => <span className="mono small">{r.action}</span> },
            { key: 't', header: 'Target', render: (r) => <span className="small">{r.target_type ? humanize(r.target_type) : '—'}</span> },
            { key: 'u', header: 'Actor', render: (r) => <span className="small">{r.actor_user_id ? 'Person' : 'System / agent'}</span> },
            { key: 'o', header: 'Outcome', render: (r) => <StatusPill status={r.outcome === 'success' ? 'succeeded' : 'failed'} label={r.outcome} /> },
          ]} />
      </div>
    </div>
  )
}
