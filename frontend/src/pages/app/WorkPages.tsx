import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import { apiRequest } from '../../api/client'
import type { AgentInfo, Deliverable } from '../../api/types'
import DeliverableContent from '../../components/DeliverableContent'
import {
  DataTable,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  FilterBar,
  PageHeader,
  PageSkeleton,
  StatusPill,
  Tabs,
  useToast,
} from '../../components/ui'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useAction, useResource } from '../../hooks/useResource'
import { AGENT_META } from '../../lib/agentMeta'
import { humanize, money, relativeTime } from '../../lib/labels'

type CampaignRow = { id: string; name: string; objective: string; status: string; channels: string | null; start_date: string | null; end_date: string | null; updated_at: string }
type ContentRow = Deliverable & { campaign_name: string; created_at: string }

export function CampaignListPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<'all' | 'draft' | 'active' | 'archived'>('all')
  const { data, error, loading, reload } = useResource<{ campaigns: CampaignRow[] }>(orgId ? `/organizations/${orgId}/campaigns` : null)
  if (loading && !data) return <PageSkeleton />
  const rows = (data?.campaigns || []).filter(
    (c) => (status === 'all' || c.status === status) && (!q || `${c.name} ${c.objective}`.toLowerCase().includes(q.toLowerCase())),
  )
  return (
    <div className="page page-wide">
      <PageHeader title="Campaigns" description="Every brief your team is working on."
        actions={<Link to="/app/campaigns/new" className="btn"><Plus size={15} aria-hidden="true" /> New campaign</Link>} />
      {error && <ErrorState message={error} onRetry={reload} />}
      <FilterBar search={q} onSearch={setQ} placeholder="Search campaigns">
        <Tabs label="Campaign status" value={status} onChange={setStatus}
          tabs={[{ value: 'all', label: 'All' }, { value: 'draft', label: 'Draft' }, { value: 'active', label: 'Active' }, { value: 'archived', label: 'Archived' }]} />
      </FilterBar>
      <div className="card">
        <DataTable
          caption="Campaigns"
          rows={rows}
          rowKey={(r) => r.id}
          empty={<EmptyState title={q ? 'No matches' : 'No campaigns yet'} body="Write a brief to put your agents to work."
            action={<Link to="/app/campaigns/new" className="btn">Create campaign</Link>} />}
          columns={[
            { key: 'name', header: 'Campaign', render: (r) => <><Link to={`/app/campaigns/${r.id}`}><strong>{r.name}</strong></Link><div className="muted small">{r.objective}</div></> },
            { key: 'status', header: 'Status', render: (r) => <StatusPill status={r.status} /> },
            { key: 'channels', header: 'Channels', render: (r) => <span className="small">{r.channels || '-'}</span> },
            { key: 'dates', header: 'Dates', render: (r) => <span className="small mono">{r.start_date || '-'} → {r.end_date || '-'}</span> },
            { key: 'updated', header: 'Updated', render: (r) => <span className="muted small">{relativeTime(r.updated_at)}</span> },
          ]}
        />
      </div>
    </div>
  )
}

export function AgentsDirectoryPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const { data, error, loading, reload } = useResource<{ agents: AgentInfo[] }>(orgId ? `/organizations/${orgId}/agents` : null, { pollMs: 8000 })
  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page page-wide">
      <PageHeader title="Your marketing team" description="Specialists with distinct jobs, permissions and budgets. Open one to see its history, configuration and controls."
        actions={<Link to="/app/operations" className="btn secondary">Operations Center</Link>} />
      {error && <ErrorState message={error} onRetry={reload} />}
      <div className="agent-grid">
        {data?.agents.map((a) => {
          const Icon = AGENT_META[a.agent_id]?.icon
          return (
            <Link key={a.agent_id} to={`/app/agents/${a.agent_id}`} className={`card agent-card ${a.status}`} style={{ color: 'inherit', textDecoration: 'none' }}>
              <div className="agent-card-head">
                <span className="agent-glyph">{Icon && <Icon size={17} aria-hidden="true" />}</span>
                <StatusPill status={a.status} />
              </div>
              <span className="agent-name">{String(a.number).padStart(2, '0')} · {a.name}</span>
              <p className="muted small agent-role">{a.role}</p>
              <div className="agent-stats small">
                <span>{a.stats_30d.succeeded} done</span>
                <span>{a.stats_30d.failed} failed</span>
                <span>{money(a.stats_30d.estimated_cost_usd)}</span>
                <span className="mono">v{a.version}</span>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

type CalEntry = { id: string; scheduled_date: string; channel: string; title: string; body: string | null; status: string; campaign_id: string | null; campaign_name: string | null }

function monthGrid(year: number, month: number) {
  const first = new Date(Date.UTC(year, month, 1))
  const start = new Date(first)
  start.setUTCDate(1 - ((first.getUTCDay() + 6) % 7))
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start)
    d.setUTCDate(start.getUTCDate() + i)
    return d
  })
}

export function CalendarPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const now = new Date()
  const [cursor, setCursor] = useState({ y: now.getUTCFullYear(), m: now.getUTCMonth() })
  const days = useMemo(() => monthGrid(cursor.y, cursor.m), [cursor])
  const from = days[0].toISOString().slice(0, 10)
  const to = days[41].toISOString().slice(0, 10)
  const { data, error, reload } = useResource<{ entries: CalEntry[] }>(orgId ? `/organizations/${orgId}/calendar?from=${from}&to=${to}` : null)
  const [selected, setSelected] = useState<CalEntry | null>(null)
  const [creating, setCreating] = useState<string | null>(null)
  const [form, setForm] = useState({ title: '', channel: 'instagram', body: '' })
  const action = useAction()
  const today = now.toISOString().slice(0, 10)
  const byDay = new Map<string, CalEntry[]>()
  data?.entries.forEach((e) => byDay.set(e.scheduled_date, [...(byDay.get(e.scheduled_date) || []), e]))

  async function setStatus(entry: CalEntry, status: string) {
    await action.run(() => apiRequest(`/organizations/${orgId}/calendar/${entry.id}`, { method: 'PATCH', body: { status } }))
    setSelected(null)
    reload()
    if (status === 'published_confirmed') toast({ title: 'Marked as published by you', tone: 'success' })
  }
  async function create() {
    if (!form.title.trim()) return action.setError('Title is required')
    const ok = await action.run(() => apiRequest(`/organizations/${orgId}/calendar`, { method: 'POST', body: { ...form, scheduled_date: creating } }))
    if (ok !== undefined) {
      setCreating(null)
      setForm({ title: '', channel: 'instagram', body: '' })
      reload()
    }
  }
  async function remove(entry: CalEntry) {
    await action.run(() => apiRequest(`/organizations/${orgId}/calendar/${entry.id}`, { method: 'DELETE' }))
    setSelected(null)
    reload()
  }

  const label = new Date(Date.UTC(cursor.y, cursor.m, 1)).toLocaleString(undefined, { month: 'long', year: 'numeric', timeZone: 'UTC' })
  return (
    <div className="page page-wide">
      <PageHeader title="Content calendar" description="Planned posts and their status. ARC never publishes; mark items published once you've posted them."
        actions={
          <>
            <button className="icon-btn" aria-label="Previous month" onClick={() => setCursor((c) => (c.m === 0 ? { y: c.y - 1, m: 11 } : { y: c.y, m: c.m - 1 }))}><ChevronLeft size={18} /></button>
            <strong style={{ minWidth: 150, textAlign: 'center' }}>{label}</strong>
            <button className="icon-btn" aria-label="Next month" onClick={() => setCursor((c) => (c.m === 11 ? { y: c.y + 1, m: 0 } : { y: c.y, m: c.m + 1 }))}><ChevronRight size={18} /></button>
            <button onClick={() => setCreating(today)}><Plus size={15} aria-hidden="true" /> Add entry</button>
          </>
        } />
      {error && <ErrorState message={error} onRetry={reload} />}
      <div className="calendar-grid" role="grid" aria-label={label}>
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div key={d} className="dow">{d}</div>)}
        {days.map((d) => {
          const iso = d.toISOString().slice(0, 10)
          const items = byDay.get(iso) || []
          const out = d.getUTCMonth() !== cursor.m
          return (
            <div key={iso} role="gridcell" className={`calendar-day${out ? ' out' : ''}${iso === today ? ' today' : ''}${items.length ? '' : ' empty-day'}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="d">{d.getUTCDate()}</span>
                <button className="icon-btn" style={{ padding: 2 }} aria-label={`Add entry on ${iso}`} onClick={() => setCreating(iso)}><Plus size={12} /></button>
              </div>
              {items.map((e) => (
                <button key={e.id} className={`cal-item ${e.status}`} onClick={() => setSelected(e)} title={e.title}>
                  {e.channel}: {e.title}
                </button>
              ))}
            </div>
          )
        })}
      </div>
      {data && data.entries.length === 0 && (
        <p className="muted small" style={{ marginTop: 14 }}>
          Nothing scheduled this month. Add posts from a campaign's Social calendar deliverable, or add entries manually.
        </p>
      )}

      <Dialog open={!!selected} onClose={() => setSelected(null)} title={selected?.title || ''}
        footer={selected && (
          <>
            <button className="danger" onClick={() => remove(selected)}>Delete</button>
            {selected.status !== 'ready' && <button className="secondary" onClick={() => setStatus(selected, 'ready')}>Mark ready</button>}
            {selected.status !== 'published_confirmed' && <button onClick={() => setStatus(selected, 'published_confirmed')}>I posted this</button>}
          </>
        )}>
        {selected && (
          <>
            <p className="small"><StatusPill status={selected.status} label={humanize(selected.status)} /> <span className="mono">{selected.scheduled_date}</span> · {selected.channel}
              {selected.campaign_id && <> · <Link to={`/app/campaigns/${selected.campaign_id}`}>{selected.campaign_name}</Link></>}</p>
            <pre className="content-json" style={{ whiteSpace: 'pre-wrap' }}>{selected.body}</pre>
            <button className="secondary small-btn" onClick={() => navigator.clipboard?.writeText(selected.body || selected.title)}>Copy post text</button>
            {action.error && <div className="banner error">{action.error}</div>}
          </>
        )}
      </Dialog>
      <Dialog open={!!creating} onClose={() => setCreating(null)} title={`New entry · ${creating}`}
        footer={<><button className="secondary" onClick={() => setCreating(null)}>Cancel</button><button disabled={action.busy} onClick={create}>Add</button></>}>
        {action.error && <div className="banner error">{action.error}</div>}
        <Field id="cal-date" label="Date"><input id="cal-date" type="date" value={creating || ''} onChange={(e) => setCreating(e.target.value)} /></Field>
        <Field id="cal-title" label="Title"><input id="cal-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
        <Field id="cal-channel" label="Channel"><input id="cal-channel" value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })} /></Field>
        <Field id="cal-body" label="Copy"><textarea id="cal-body" rows={4} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></Field>
      </Dialog>
    </div>
  )
}

const CONTENT_TYPES = ['content_pack', 'social_calendar', 'paid_media_plan', 'outreach_plan', 'site_optimization_plan', 'campaign_plan', 'strategy', 'account_plan', 'campaign_record', 'qa_report']

export function ContentPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [type, setType] = useState('')
  const [review, setReview] = useState('')
  const qs = [type && `type=${type}`, review && `review_status=${review}`].filter(Boolean).join('&')
  const { data, error, loading, reload } = useResource<{ deliverables: ContentRow[]; page: { total: number } }>(
    orgId ? `/organizations/${orgId}/deliverables?limit=100${qs ? `&${qs}` : ''}` : null,
  )
  return (
    <div className="page page-wide">
      <PageHeader title="Content" description="Every deliverable your agents have produced, across campaigns. Each is versioned; edits create a new version." />
      {error && <ErrorState message={error} onRetry={reload} />}
      <FilterBar>
        <label htmlFor="ct-type" className="sr-only">Type</label>
        <select id="ct-type" className="select-inline" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option>
          {CONTENT_TYPES.map((t) => <option key={t} value={t}>{humanize(t)}</option>)}
        </select>
        <label htmlFor="ct-review" className="sr-only">Review status</label>
        <select id="ct-review" className="select-inline" value={review} onChange={(e) => setReview(e.target.value)}>
          <option value="">Any review status</option>
          <option value="draft">Draft</option>
          <option value="approved">Approved</option>
          <option value="changes_requested">Changes requested</option>
        </select>
        {data && <span className="muted small">{data.page.total} items</span>}
      </FilterBar>
      <div className="card">
        {loading && !data ? <PageSkeleton /> : (
          <DataTable
            caption="Deliverables"
            rows={data?.deliverables || []}
            rowKey={(r) => r.id}
            empty={<EmptyState title="No content yet" body="Run the department on a campaign to generate deliverables." />}
            columns={[
              { key: 'type', header: 'Deliverable', render: (r) => <Link to={`/app/campaigns/${r.campaign_id}/deliverables`}><strong>{humanize(r.deliverable_type)}</strong></Link> },
              { key: 'campaign', header: 'Campaign', render: (r) => <span className="small">{r.campaign_name}</span> },
              { key: 'version', header: 'Version', render: (r) => <span className="mono small">v{r.current_version?.version_number}</span> },
              { key: 'review', header: 'Review', render: (r) => <StatusPill status={r.review_status} /> },
              { key: 'created', header: 'Created', render: (r) => <span className="muted small">{relativeTime(r.created_at)}</span> },
            ]}
          />
        )}
      </div>
    </div>
  )
}

export function ResearchPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const { data, error, loading } = useResource<{ deliverables: ContentRow[] }>(
    orgId ? `/organizations/${orgId}/deliverables?type=research_notes,customer_insights&limit=20` : null,
  )
  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page">
      <PageHeader title="Research & insights" description="Market research and voice-of-customer analysis from agents 07 and 08. No external research source is connected yet, so these are built from your brand profile and labelled as such." />
      {error && <ErrorState message={error} />}
      {(data?.deliverables || []).length === 0 && <div className="card"><EmptyState title="No research yet" body="Research notes appear after a campaign run." /></div>}
      {data?.deliverables.map((d) => (
        <div key={d.id} className="card">
          <div className="card-head">
            <h2>{humanize(d.deliverable_type)} <span className="muted small">· {d.campaign_name}</span></h2>
            <span className="muted small">{relativeTime(d.created_at)}</span>
          </div>
          <DeliverableContent deliverableType={d.deliverable_type} content={d.current_version?.content} />
        </div>
      ))}
    </div>
  )
}
