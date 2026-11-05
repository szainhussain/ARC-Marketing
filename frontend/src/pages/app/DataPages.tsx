import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Download, Plus, Trash2, Upload } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { apiRequest } from '../../api/client'
import {
  ConfirmDialog,
  DataTable,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  FilterBar,
  KpiCard,
  PageHeader,
  PageSkeleton,
  StatusPill,
  Tabs,
  useToast,
} from '../../components/ui'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useAction, useResource } from '../../hooks/useResource'
import { INTEGRATION_STATUS_LABEL } from '../../lib/marketing'
import { WordPressCard } from '../../components/WordPressPublish'
import { humanize, money, relativeTime } from '../../lib/labels'

import { API_BASE_URL as API } from '../../lib/apiBase'
const TOOLTIP = { contentStyle: { background: '#16181d', border: '1px solid #33373e', borderRadius: 8, fontSize: 12 } }
const AXIS = { stroke: '#6b6f74', fontSize: 11, tickLine: false, axisLine: false }

/* ---------------- Assets ---------------- */

type Doc = { id: string; original_filename: string; content_type: string; size_bytes: number; created_at: string }

export function AssetsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const { data, error, loading, reload } = useResource<{ documents: Doc[]; limits: { max_mb: number; allowed: string[] } }>(
    orgId ? `/organizations/${orgId}/documents` : null,
  )
  const input = useRef<HTMLInputElement | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<Doc | null>(null)

  async function upload(file: File) {
    setUploading(true)
    setUploadError(null)
    try {
      const csrf = await fetch(`${API}/auth/csrf-token`, { credentials: 'include' }).then((r) => r.json())
      const body = new FormData()
      body.append('file', file)
      const res = await fetch(`${API}/organizations/${orgId}/documents`, {
        method: 'POST', body, credentials: 'include', headers: { 'X-CSRFToken': csrf.csrf_token },
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json?.error?.details?.[0]?.issue || json?.error?.message || 'Upload failed')
      toast({ title: `Uploaded ${file.name}`, tone: 'success' })
      reload()
    } catch (err) {
      setUploadError((err as Error).message)
    } finally {
      setUploading(false)
      if (input.current) input.current.value = ''
    }
  }
  async function remove() {
    if (!deleting) return
    await apiRequest(`/organizations/${orgId}/documents/${deleting.id}`, { method: 'DELETE' })
    setDeleting(null)
    reload()
  }

  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page">
      <PageHeader title="Brand assets" description="Logos, guidelines, product sheets. Files are type- and content-checked, stored privately, and only downloadable by workspace members."
        actions={
          <>
            <label htmlFor="asset-file" className="sr-only">Choose a file</label>
            <input id="asset-file" ref={input} type="file" hidden accept={data?.limits.allowed.map((a) => `.${a}`).join(',')}
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <button disabled={uploading} onClick={() => input.current?.click()}><Upload size={15} aria-hidden="true" /> {uploading ? 'Uploading…' : 'Upload file'}</button>
          </>
        } />
      {error && <ErrorState message={error} onRetry={reload} />}
      {uploadError && <ErrorState message={uploadError} />}
      {data && <p className="muted small">Allowed: {data.limits.allowed.join(', ')} · up to {data.limits.max_mb} MB. Agents don't read uploaded files yet; add key facts to the Knowledge library.</p>}
      <div className="card">
        <DataTable rows={data?.documents || []} rowKey={(r) => r.id} caption="Assets"
          empty={<EmptyState title="No assets yet" body="Upload your logo or brand guidelines." />}
          columns={[
            { key: 'name', header: 'File', render: (r) => <strong className="small">{r.original_filename}</strong> },
            { key: 'type', header: 'Type', render: (r) => <span className="mono small">{r.content_type}</span> },
            { key: 'size', header: 'Size', render: (r) => <span className="small">{(r.size_bytes / 1024).toFixed(1)} KB</span> },
            { key: 'when', header: 'Uploaded', render: (r) => <span className="muted small">{relativeTime(r.created_at)}</span> },
            { key: 'actions', header: '', render: (r) => (
              <span className="head-actions">
                <a className="icon-btn" href={`${API}/organizations/${orgId}/documents/${r.id}/download`} aria-label={`Download ${r.original_filename}`}><Download size={15} /></a>
                <button className="icon-btn" aria-label={`Delete ${r.original_filename}`} onClick={() => setDeleting(r)}><Trash2 size={15} /></button>
              </span>
            ) },
          ]} />
      </div>
      <ConfirmDialog open={!!deleting} title="Delete file?" body={`${deleting?.original_filename} will be removed from storage.`} tone="danger"
        confirmLabel="Delete" onConfirm={remove} onCancel={() => setDeleting(null)} />
    </div>
  )
}

/* ---------------- Analytics ---------------- */

type Analytics = {
  range_days: number
  executions: number
  success_rate_pct: number | null
  retry_rate_pct: number | null
  avg_execution_seconds: number | null
  tokens: number
  estimated_cost_usd: number
  avg_approval_turnaround_hours: number | null
  avg_run_completion_minutes: number | null
  failures_by_reason: Record<string, number>
  series: { date: string; tasks_succeeded: number; tasks_failed: number; retries: number; cost_usd: number }[]
  cost_by_agent: { agent_name: string; number: number; executions: number; tokens: number; cost_usd: number }[]
}

export function AnalyticsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [days, setDays] = useState(30)
  const { data, error, loading, reload } = useResource<Analytics>(orgId ? `/organizations/${orgId}/analytics?days=${days}` : null)
  const dash = useResource<{ business_metrics: { key: string; label: string; requires: string }[] }>(orgId ? `/organizations/${orgId}/dashboard?days=${days}` : null)
  if (loading && !data) return <PageSkeleton />
  const series = (data?.series || []).map((s) => ({ ...s, label: s.date.slice(5) }))
  return (
    <div className="page page-wide">
      <PageHeader title="Analytics" description="Platform metrics are observed from your workspace's records (costs are estimates). Business metrics need a connected source."
        actions={
          <>
            <label htmlFor="an-range" className="sr-only">Date range</label>
            <select id="an-range" className="select-inline" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last year</option>
            </select>
            <a className="btn secondary" href={`${API}/organizations/${orgId}/reports/export.csv?days=${days}`}><Download size={15} aria-hidden="true" /> Export CSV</a>
          </>
        } />
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <div className="kpi-grid">
            <KpiCard label="Agent executions" value={data.executions} />
            <KpiCard label="Success rate" value={data.success_rate_pct} format={(v) => `${v}%`} />
            <KpiCard label="Retry/failure rate" value={data.retry_rate_pct} format={(v) => `${v}%`} />
            <KpiCard label="Avg execution time" value={data.avg_execution_seconds} format={(v) => `${v}s`} />
            <KpiCard label="Avg run completion" value={data.avg_run_completion_minutes} format={(v) => `${v} min`} />
            <KpiCard label="Approval turnaround" value={data.avg_approval_turnaround_hours} format={(v) => `${v} h`} />
            <KpiCard label="Tokens used" value={data.tokens} format={(v) => v.toLocaleString()} />
            <KpiCard label="AI cost" value={data.estimated_cost_usd} basis="estimate" format={money} />
          </div>
          <div className="grid-3">
            <div className="card chart-card">
              <h2>Executions and retries</h2>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={series} margin={{ left: -16, right: 8 }}>
                  <CartesianGrid stroke="#23262c" vertical={false} />
                  <XAxis dataKey="label" {...AXIS} interval="preserveStartEnd" />
                  <YAxis allowDecimals={false} {...AXIS} />
                  <Tooltip {...TOOLTIP} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line name="Succeeded" dataKey="tasks_succeeded" stroke="#6ee7a8" dot={false} strokeWidth={2} />
                  <Line name="Retried (transient)" dataKey="retries" stroke="#f5c76a" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="card chart-card">
              <h2>Estimated cost per day</h2>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={series} margin={{ left: -10, right: 8 }}>
                  <CartesianGrid stroke="#23262c" vertical={false} />
                  <XAxis dataKey="label" {...AXIS} interval="preserveStartEnd" />
                  <YAxis {...AXIS} tickFormatter={(v) => `$${v}`} />
                  <Tooltip {...TOOLTIP} formatter={(v: number) => money(v)} />
                  <Bar name="Est. cost" dataKey="cost_usd" fill="#9fd8ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="grid-3" style={{ marginTop: 18 }}>
            <div className="card">
              <h2>By agent</h2>
              <DataTable rows={data.cost_by_agent} rowKey={(r) => String(r.number)} caption="Cost by agent"
                empty={<EmptyState title="No executions in this period" />}
                columns={[
                  { key: 'a', header: 'Agent', render: (r) => <span className="small">{String(r.number).padStart(2, '0')} {r.agent_name}</span> },
                  { key: 'e', header: 'Runs', render: (r) => r.executions },
                  { key: 't', header: 'Tokens', render: (r) => r.tokens.toLocaleString() },
                  { key: 'c', header: 'Est. cost', render: (r) => money(r.cost_usd) },
                ]} />
            </div>
            <div className="card">
              <h2>Why attempts failed</h2>
              {Object.keys(data.failures_by_reason).length === 0 ? <EmptyState title="No failures" /> : (
                <ul className="deliverable-list">
                  {Object.entries(data.failures_by_reason).map(([k, v]) => <li key={k}>{humanize(k)}: {v}</li>)}
                </ul>
              )}
            </div>
          </div>
          <div className="card" style={{ marginTop: 18 }}>
            <h2>Business metrics</h2>
            <div className="unavailable-grid">
              {dash.data?.business_metrics.map((m) => (
                <div key={m.key}><div className="small" style={{ fontWeight: 600 }}>{m.label}</div><div className="muted small">Not connected · needs {m.requires}</div></div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

/* ---------------- Knowledge ---------------- */

type Knowledge = { id: string; kind: string; title: string; body: string; source_url: string | null; status: string; version: number; created_by: string; updated_at: string }

export function KnowledgePage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [params] = useSearchParams()
  const toast = useToast()
  const [status, setStatus] = useState(params.get('status') || '')
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<Partial<Knowledge> | null>(null)
  const action = useAction()
  const query = [status && `status=${status}`, q && `q=${encodeURIComponent(q)}`].filter(Boolean).join('&')
  const { data, error, reload } = useResource<{ entries: Knowledge[]; kinds: string[] }>(orgId ? `/organizations/${orgId}/knowledge${query ? `?${query}` : ''}` : null)

  async function save() {
    if (!editing) return
    const body = { title: editing.title, body: editing.body, kind: editing.kind || 'note', source_url: editing.source_url || '' }
    const ok = await action.run(() =>
      editing.id
        ? apiRequest(`/organizations/${orgId}/knowledge/${editing.id}`, { method: 'PATCH', body })
        : apiRequest(`/organizations/${orgId}/knowledge`, { method: 'POST', body }),
    )
    if (ok !== undefined) {
      setEditing(null)
      reload()
      toast({ title: 'Knowledge saved', tone: 'success' })
    }
  }
  async function setEntryStatus(entry: Knowledge, next: string) {
    await action.run(() => apiRequest(`/organizations/${orgId}/knowledge/${entry.id}`, { method: 'PATCH', body: { status: next } }))
    reload()
  }

  return (
    <div className="page page-wide">
      <PageHeader title="Knowledge library" description="Approved facts, FAQs and learnings. The CMO and Marketing Manager receive the most recent approved entries as context — always as data, never as instructions."
        actions={<button onClick={() => setEditing({ kind: 'note' })}><Plus size={15} aria-hidden="true" /> Add knowledge</button>} />
      {error && <ErrorState message={error} onRetry={reload} />}
      {action.error && <ErrorState message={action.error} />}
      <FilterBar search={q} onSearch={setQ} placeholder="Search knowledge">
        <Tabs label="Status" value={status} onChange={setStatus}
          tabs={[{ value: '', label: 'Active' }, { value: 'proposed', label: 'Proposed by agents' }, { value: 'approved', label: 'Approved' }, { value: 'archived', label: 'Archived' }]} />
      </FilterBar>
      <div className="card">
        <DataTable rows={data?.entries || []} rowKey={(r) => r.id} caption="Knowledge entries"
          empty={<EmptyState title="No knowledge yet" body="Add product facts and FAQs, or approve learnings the Record Keeper proposes after each run." />}
          columns={[
            { key: 't', header: 'Entry', render: (r) => <><button className="link-btn" onClick={() => setEditing(r)}>{r.title}</button><div className="muted small">{r.body.slice(0, 140)}</div></> },
            { key: 'k', header: 'Kind', render: (r) => <span className="small">{humanize(r.kind)}</span> },
            { key: 's', header: 'Status', render: (r) => <StatusPill status={r.status === 'proposed' ? 'pending' : r.status === 'approved' ? 'approved' : 'cancelled'} label={humanize(r.status)} /> },
            { key: 'p', header: 'Source', render: (r) => <span className="small mono">{r.created_by} · v{r.version}</span> },
            { key: 'a', header: '', render: (r) => (
              <span className="head-actions">
                {r.status === 'proposed' && <button className="small-btn" onClick={() => setEntryStatus(r, 'approved')}>Approve</button>}
                {r.status !== 'archived' && <button className="secondary small-btn" onClick={() => setEntryStatus(r, 'archived')}>Archive</button>}
              </span>
            ) },
          ]} />
      </div>
      <Dialog open={!!editing} onClose={() => setEditing(null)} title={editing?.id ? 'Edit knowledge' : 'Add knowledge'}
        footer={<><button className="secondary" onClick={() => setEditing(null)}>Cancel</button><button disabled={action.busy} onClick={save}>Save</button></>}>
        {editing && (
          <>
            {action.error && <div className="banner error">{action.error}</div>}
            <Field id="kn-title" label="Title"><input id="kn-title" value={editing.title || ''} onChange={(e) => setEditing({ ...editing, title: e.target.value })} /></Field>
            <Field id="kn-kind" label="Kind">
              <select id="kn-kind" value={editing.kind || 'note'} onChange={(e) => setEditing({ ...editing, kind: e.target.value })}>
                {(data?.kinds || ['note']).map((k) => <option key={k} value={k}>{humanize(k)}</option>)}
              </select>
            </Field>
            <Field id="kn-body" label="Content"><textarea id="kn-body" rows={6} value={editing.body || ''} onChange={(e) => setEditing({ ...editing, body: e.target.value })} /></Field>
            <Field id="kn-url" label="Source URL (optional)" hint="Recorded for provenance; ARC does not fetch it."><input id="kn-url" type="url" value={editing.source_url || ''} onChange={(e) => setEditing({ ...editing, source_url: e.target.value })} /></Field>
            {editing.id && <p className="muted small">Saving creates version {(editing.version || 1) + 1}.</p>}
          </>
        )}
      </Dialog>
    </div>
  )
}

/* ---------------- Integrations ---------------- */

type CatalogItem = { key: string; name: string; category: string; status: string; detail: string; prerequisite: string | null; enabled: boolean | null; agents: string[] }
type Webhooks = {
  endpoints: { id: string; url: string; events: string[]; is_active: boolean; description: string }[]
  deliveries: { id: string; event_type: string; status: string; attempts: number; last_response_code: number | null; last_error: string | null; created_at: string }[]
  event_types: string[]
}

export function IntegrationsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const catalog = useResource<{ integrations: CatalogItem[] }>(orgId ? `/organizations/${orgId}/integrations/catalog` : null)
  const hooks = useResource<Webhooks>(orgId ? `/organizations/${orgId}/webhooks` : null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<{ url: string; events: string[]; description: string }>({ url: '', events: ['run.completed'], description: '' })
  const [secret, setSecret] = useState<string | null>(null)
  const [urlPlaceholder, setUrlPlaceholder] = useState('https://example.com/arc-webhook')
  const action = useAction()

  async function toggle(item: CatalogItem) {
    await action.run(() => apiRequest(`/organizations/${orgId}/integrations/${item.key}`, { method: 'PATCH', body: { enabled: !item.enabled } }))
    catalog.reload()
  }
  async function createHook() {
    const r = await action.run(() => apiRequest<{ signing_secret: string }>(`/organizations/${orgId}/webhooks`, { method: 'POST', body: form }))
    if (r) {
      setSecret(r.signing_secret)
      setCreating(false)
      hooks.reload()
    }
  }
  async function removeHook(id: string) {
    await action.run(() => apiRequest(`/organizations/${orgId}/webhooks/${id}`, { method: 'DELETE' }))
    hooks.reload()
    toast({ title: 'Webhook disabled', tone: 'info' })
  }

  return (
    <div className="page page-wide">
      <PageHeader title="Integrations" description="What's connected, what's possible, and what each connector still needs. Nothing here is a claim of partnership." />
      {catalog.error && <ErrorState message={catalog.error} />}
      {action.error && <ErrorState message={action.error} />}
      <div className="cap-grid">
        {catalog.data?.integrations.map((i) => (
          <div key={i.key} className="cap">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <span className="muted small">{i.category}</span>
              <span className={`int-status ${i.status}`}>{INTEGRATION_STATUS_LABEL[i.status]}</span>
            </div>
            <h3>{i.name}</h3>
            <p>{i.detail}</p>
            {i.prerequisite && <p className="small" style={{ marginTop: 8 }}><span className="muted">Needs: </span>{i.prerequisite}</p>}
            {i.enabled != null && (
              <button className={`small-btn ${i.enabled ? 'secondary' : ''}`} style={{ marginTop: 12 }} onClick={() => toggle(i)}>
                {i.enabled ? 'Disable for this workspace' : 'Enable'}
              </button>
            )}
          </div>
        ))}
      </div>

      {orgId && <WordPressCard orgId={orgId} />}

      <div className="card automation-card" style={{ marginTop: 24 }}>
        <h2>Publish approved content with Zapier or Make</h2>
        <p className="muted small" style={{ marginTop: -6 }}>
          Connect once, and every time you export an approved deliverable ARC sends the exact approved content to your
          automation, which can post it to Instagram, LinkedIn, Facebook, email tools, Slack, Google Sheets and thousands
          of other apps. Nothing is sent before approval, and ARC never marks anything published until you confirm it.
        </p>
        <ol className="automation-steps">
          <li>In Zapier, create a Zap starting with <strong>Webhooks by Zapier → Catch Hook</strong> (in Make: a scenario starting with a <strong>Custom webhook</strong>) and copy its URL.</li>
          <li>Click a button below and paste the URL.</li>
          <li>Approve and export a deliverable, then map fields like <code>data.content</code> or <code>data.platform_export</code> to your posting step.</li>
        </ol>
        <div className="head-actions">
          {[
            ['Zapier', 'https://hooks.zapier.com/hooks/catch/…'],
            ['Make', 'https://hook.eu1.make.com/…'],
          ].map(([name, placeholder]) => (
            <button
              key={name}
              onClick={() => {
                setForm({ url: '', events: ['content.approved_for_publishing'], description: `${name}: publish approved content` })
                setUrlPlaceholder(placeholder)
                setCreating(true)
              }}
            >
              <Plus size={14} aria-hidden="true" /> Connect {name}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-head">
          <h2>Outbound webhooks</h2>
          <button className="small-btn" onClick={() => { setForm({ url: '', events: ['run.completed'], description: '' }); setUrlPlaceholder('https://example.com/arc-webhook'); setCreating(true) }}><Plus size={14} aria-hidden="true" /> Add endpoint</button>
        </div>
        <p className="muted small">Signed with <code>ARC-Signature</code> (HMAC-SHA256, 5-minute replay window). HTTPS only; private addresses are refused. Retries 6 times with backoff.</p>
        {hooks.error ? <p className="muted small">{hooks.error}</p> : (
          <>
            <DataTable rows={hooks.data?.endpoints || []} rowKey={(r) => r.id} caption="Webhook endpoints"
              empty={<EmptyState title="No webhook endpoints" />}
              columns={[
                { key: 'u', header: 'URL', render: (r) => <span className="mono small">{r.url}</span> },
                { key: 'e', header: 'Events', render: (r) => <span className="small">{r.events.join(', ')}</span> },
                { key: 's', header: 'Status', render: (r) => <StatusPill status={r.is_active ? 'active' : 'cancelled'} label={r.is_active ? 'Active' : 'Disabled'} /> },
                { key: 'a', header: '', render: (r) => r.is_active && <button className="secondary small-btn" onClick={() => removeHook(r.id)}>Disable</button> },
              ]} />
            {(hooks.data?.deliveries.length || 0) > 0 && (
              <>
                <h3 style={{ marginTop: 18 }}>Recent deliveries</h3>
                <DataTable rows={hooks.data!.deliveries} rowKey={(r) => r.id} caption="Webhook deliveries"
                  columns={[
                    { key: 'e', header: 'Event', render: (r) => <span className="mono small">{r.event_type}</span> },
                    { key: 's', header: 'Status', render: (r) => <StatusPill status={r.status === 'delivered' ? 'succeeded' : r.status === 'failed' ? 'failed' : 'retrying'} label={humanize(r.status)} /> },
                    { key: 'a', header: 'Attempts', render: (r) => r.attempts },
                    { key: 'r', header: 'Result', render: (r) => <span className="small">{r.last_error || (r.last_response_code ? `HTTP ${r.last_response_code}` : '—')}</span> },
                    { key: 'w', header: 'When', render: (r) => <span className="muted small">{relativeTime(r.created_at)}</span> },
                  ]} />
              </>
            )}
          </>
        )}
      </div>
      <p className="muted small">Live publishing connectors require your channel choice and API credentials. See <Link to="/integrations">what each needs</Link>.</p>

      <Dialog open={creating} onClose={() => setCreating(false)} title="Add webhook endpoint"
        footer={<><button className="secondary" onClick={() => setCreating(false)}>Cancel</button><button disabled={action.busy} onClick={createHook}>Create</button></>}>
        {action.error && <div className="banner error">{action.error}</div>}
        <Field id="wh-url" label="HTTPS URL"><input id="wh-url" type="url" placeholder={urlPlaceholder} value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} /></Field>
        <fieldset className="field" style={{ border: 'none', padding: 0 }}>
          <legend className="small" style={{ fontWeight: 600, marginBottom: 6 }}>Events</legend>
          {(hooks.data?.event_types || []).map((ev) => (
            <label key={ev} className="small" style={{ display: 'flex', gap: 8, alignItems: 'center' }} htmlFor={`ev-${ev}`}>
              <input id={`ev-${ev}`} type="checkbox" checked={form.events.includes(ev)}
                onChange={(e) => setForm({ ...form, events: e.target.checked ? [...form.events, ev] : form.events.filter((x) => x !== ev) })} />
              <span className="mono">{ev}</span>
            </label>
          ))}
        </fieldset>
        <Field id="wh-desc" label="Description (optional)"><input id="wh-desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
      </Dialog>
      <Dialog open={!!secret} onClose={() => setSecret(null)} title="Signing secret" footer={<button onClick={() => setSecret(null)}>I've stored it</button>}>
        <p className="muted small">Store this now — it isn't shown again.</p>
        <pre className="content-json">{secret}</pre>
      </Dialog>
    </div>
  )
}
