import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { apiRequest } from '../../api/client'
import { DataTable, EmptyState, ErrorState, KpiCard, PageHeader, PageSkeleton, StatusPill, useToast } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useResource } from '../../hooks/useResource'

type Enquiry = { id: string; name: string; email: string; company: string | null; topic: string; message: string; status: string; created_at: string }
type Overview = {
  users: { total: number; last_7_days: number; last_30_days: number }
  workspaces: { total: number; last_30_days: number }
  runs_last_30_days: number
  new_enquiries: number
}
const STATUSES = ['new', 'contacted', 'closed'] as const

type Margin = { organization_id: string; name: string; plan: string | null; status: string; revenue_usd: number; ai_cost_usd: number; gross_margin_usd: number; gross_margin_pct: number | null }

export default function AdminPage() {
  const { user } = useAuth()
  const toast = useToast()
  const [filter, setFilter] = useState<string>('')
  const overview = useResource<Overview>(user?.is_platform_admin ? '/admin/overview' : null)
  const margins = useResource<{ workspaces: Margin[]; basis: string }>(user?.is_platform_admin ? '/admin/unit-economics' : null)
  const list = useResource<{ enquiries: Enquiry[]; counts: Record<string, number> }>(
    user?.is_platform_admin ? `/admin/enquiries${filter ? `?status=${filter}` : ''}` : null,
  )
  if (user && !user.is_platform_admin) return <Navigate to="/app/dashboard" replace />
  if (!overview.data && !overview.error) return <PageSkeleton />

  async function setStatus(e: Enquiry, status: string) {
    try {
      await apiRequest(`/admin/enquiries/${e.id}`, { method: 'PATCH', body: { status } })
      list.reload()
      overview.reload()
    } catch {
      toast({ tone: 'error', title: 'Could not update the enquiry.' })
    }
  }

  const o = overview.data
  const money = (v: number | null) => (v == null ? '-' : `$${v.toFixed(2)}`)
  return (
    <div className="page page-wide">
      <PageHeader title="Admin" description="Sign-ups, usage across ARC, and every demo request and contact message from the website." />
      {overview.error && <ErrorState message={overview.error} onRetry={overview.reload} />}
      {o && (
        <div className="kpi-grid">
          <KpiCard label="Users" value={o.users.total} sub={`${o.users.last_7_days} in the last 7 days`} />
          <KpiCard label="New users (30 days)" value={o.users.last_30_days} />
          <KpiCard label="Workspaces" value={o.workspaces.total} sub={`${o.workspaces.last_30_days} new in 30 days`} />
          <KpiCard label="Campaign runs (30 days)" value={o.runs_last_30_days} />
          <KpiCard label="New enquiries" value={o.new_enquiries} />
        </div>
      )}
      {margins.data && (
        <div className="card">
          <h2>Revenue and AI cost per workspace · this month</h2>
          <p className="muted small" style={{ marginTop: -8 }}>{margins.data.basis}</p>
          <div className="table-wrap">
            <table className="compare-table">
              <caption className="sr-only">Revenue, AI cost and gross margin per workspace</caption>
              <thead>
                <tr>
                  <th scope="col">Workspace</th>
                  <th scope="col">Plan</th>
                  <th scope="col">Status</th>
                  <th scope="col">Revenue</th>
                  <th scope="col">AI cost (est.)</th>
                  <th scope="col">Gross margin</th>
                </tr>
              </thead>
              <tbody>
                {margins.data.workspaces.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">No workspaces yet.</td>
                  </tr>
                )}
                {margins.data.workspaces.map((w) => (
                  <tr key={w.organization_id}>
                    <th scope="row">{w.name}</th>
                    <td>{w.plan || '-'}</td>
                    <td>{w.status}</td>
                    <td>{money(w.revenue_usd)}</td>
                    <td>{money(w.ai_cost_usd)}</td>
                    <td>
                      {money(w.gross_margin_usd)}
                      {w.gross_margin_pct != null ? ` (${w.gross_margin_pct}%)` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className="card">
        <div className="card-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0 }}>Demo requests and messages</h2>
          <div className="seg" role="group" aria-label="Filter by status">
            {['', ...STATUSES].map((s) => (
              <button key={s || 'all'} type="button" aria-pressed={filter === s} onClick={() => setFilter(s)}>
                {s ? `${s[0].toUpperCase()}${s.slice(1)} (${list.data?.counts?.[s] ?? 0})` : 'All'}
              </button>
            ))}
          </div>
        </div>
        {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
        <DataTable
          rows={list.data?.enquiries || []}
          rowKey={(r) => r.id}
          caption="Enquiries"
          empty={<EmptyState title="No enquiries yet" body="Demo requests and contact form messages will appear here." />}
          columns={[
            { key: 'when', header: 'Received', render: (r) => <span className="mono small nowrap">{new Date(r.created_at.endsWith('Z') || r.created_at.includes('+') ? r.created_at : `${r.created_at}Z`).toLocaleString()}</span> },
            {
              key: 'who',
              header: 'From',
              render: (r) => (
                <>
                  <strong className="small">{r.name}</strong>
                  <div className="small">
                    <a href={`mailto:${r.email}`}>{r.email}</a>
                  </div>
                  {r.company && <div className="muted small">{r.company}</div>}
                </>
              ),
            },
            { key: 'topic', header: 'Topic', render: (r) => <StatusPill status={r.topic === 'demo' ? 'running' : 'queued'} label={r.topic} /> },
            { key: 'msg', header: 'Message', render: (r) => <span className="small" style={{ whiteSpace: 'pre-line' }}>{r.message}</span> },
            {
              key: 'status',
              header: 'Status',
              render: (r) => (
                <>
                  <label htmlFor={`enq-${r.id}`} className="sr-only">
                    Status for {r.name}
                  </label>
                  <select id={`enq-${r.id}`} className="select-inline" value={r.status} onChange={(e) => setStatus(r, e.target.value)}>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </>
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}
