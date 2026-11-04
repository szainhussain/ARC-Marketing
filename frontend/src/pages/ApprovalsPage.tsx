import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldAlert, ShieldCheck } from 'lucide-react'
import { apiRequest } from '../api/client'
import type { Approval } from '../api/types'
import { EmptyState, ErrorState, FilterBar, PageHeader, PageSkeleton, StatusPill, Tabs, useToast } from '../components/ui'
import { useWorkspace } from '../context/WorkspaceContext'
import { useAction, useResource } from '../hooks/useResource'
import { humanize, relativeTime } from '../lib/labels'

export default function ApprovalsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const [view, setView] = useState<'pending' | 'all'>('pending')
  const [risk, setRisk] = useState('')
  const [agent, setAgent] = useState('')
  const [q, setQ] = useState('')
  const [comment, setComment] = useState<Record<string, string>>({})
  const { data, error, loading, reload } = useResource<{ approvals: Approval[] }>(
    orgId ? `/organizations/${orgId}/approvals?decision=${view}` : null,
    { pollMs: 10000 },
  )
  const action = useAction()

  async function decide(a: Approval, decision: 'approved' | 'rejected' | 'changes_requested') {
    const r = await action.run(() =>
      apiRequest(`/organizations/${orgId}/approvals/${a.id}/decision`, { method: 'POST', body: { decision, comment: comment[a.id] || undefined } }),
    )
    if (r) toast({ title: `${humanize(decision)}`, tone: decision === 'approved' ? 'success' : 'info' })
    reload()
  }
  async function revoke(a: Approval) {
    await action.run(() => apiRequest(`/organizations/${orgId}/approvals/${a.id}/revoke`, { method: 'POST' }))
    reload()
  }

  if (loading && !data) return <PageSkeleton />
  const all = data?.approvals || []
  const agents = Array.from(new Set(all.map((a) => a.requesting_agent_id).filter(Boolean))) as string[]
  const rows = all.filter(
    (a) =>
      (!risk || a.risk_level === risk) &&
      (!agent || a.requesting_agent_id === agent) &&
      (!q || `${a.deliverable_type} ${a.campaign_name}`.toLowerCase().includes(q.toLowerCase())),
  )

  return (
    <div className="page">
      <PageHeader
        title="Approval inbox"
        description="Every decision is pinned to one exact version. If the content changes, the approval is invalidated automatically; approvals also expire."
      />
      {(error || action.error) && <ErrorState message={(error || action.error) as string} onRetry={reload} />}
      <Tabs label="Approval view" value={view} onChange={setView}
        tabs={[{ value: 'pending', label: 'Waiting on you', count: view === 'pending' ? all.length : undefined }, { value: 'all', label: 'All decisions' }]} />
      <FilterBar search={q} onSearch={setQ} placeholder="Search by deliverable or campaign">
        <label htmlFor="ap-risk" className="sr-only">Risk</label>
        <select id="ap-risk" className="select-inline" value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option value="">Any risk</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
        </select>
        <label htmlFor="ap-agent" className="sr-only">Requesting agent</label>
        <select id="ap-agent" className="select-inline" value={agent} onChange={(e) => setAgent(e.target.value)}>
          <option value="">Any agent</option>
          {agents.map((x) => <option key={x} value={x}>{humanize(x)}</option>)}
        </select>
      </FilterBar>

      {rows.length === 0 ? (
        <div className="card">
          <EmptyState title={view === 'pending' ? 'Nothing waiting' : 'No approval decisions yet'}
            body={view === 'pending' ? 'Request approval on a deliverable from its campaign page.' : undefined} />
        </div>
      ) : (
        rows.map((a) => (
          <div key={a.id} className="card">
            <div className="card-head">
              <div>
                <div className="approval-title">
                  {humanize(a.deliverable_type || 'deliverable')}
                  {a.campaign_name && <span className="muted"> · {a.campaign_name}</span>}
                </div>
                <div className="muted small">
                  {a.requesting_agent_id ? `From ${humanize(a.requesting_agent_id)}` : 'Requested'} · {relativeTime(a.created_at)}
                  {a.expires_at && a.decision === 'pending' && <> · expires {relativeTime(a.expires_at)}</>}
                  {!a.is_current_version && ' · a newer version exists'}
                </div>
              </div>
              <div className="head-actions">
                {a.risk_level && (
                  <span className={`int-status ${a.risk_level === 'high' ? 'planned' : 'architecture_supported'}`} style={a.risk_level === 'high' ? { color: 'var(--color-danger)', borderColor: 'rgba(255,138,128,.4)' } : undefined}>
                    {humanize(a.risk_level)} risk
                  </span>
                )}
                <StatusPill status={a.decision} />
              </div>
            </div>
            {a.expected_outcome && <p className="small"><strong>If approved:</strong> <span className="muted">{a.expected_outcome}</span></p>}
            {(a.risk_checks || []).length > 0 && (
              <ul className="deliverable-list small" style={{ listStyle: 'none', paddingLeft: 0 }}>
                {a.risk_checks!.map((c, i) => (
                  <li key={i} style={{ display: 'flex', gap: 8 }}>
                    {c.passed ? <ShieldCheck size={15} color="var(--color-success)" aria-hidden="true" /> : <ShieldAlert size={15} color="var(--color-danger)" aria-hidden="true" />}
                    <span>{c.detail || humanize(c.check)}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="muted small mono">version {a.deliverable_version_id.slice(0, 8)} · payload {a.action_payload_hash.slice(0, 12)}</p>
            <div className="head-actions">
              {a.campaign_id && <Link to={`/app/campaigns/${a.campaign_id}/deliverables`} className="btn secondary small-btn">Review or edit content</Link>}
              {a.decision === 'pending' && (
                <>
                  <label htmlFor={`cm-${a.id}`} className="sr-only">Comment</label>
                  <input id={`cm-${a.id}`} className="select-inline" placeholder="Comment (optional)" value={comment[a.id] || ''} onChange={(e) => setComment({ ...comment, [a.id]: e.target.value })} />
                  <button className="small-btn" disabled={action.busy} onClick={() => decide(a, 'approved')}>Approve</button>
                  <button className="secondary small-btn" disabled={action.busy} onClick={() => decide(a, 'changes_requested')}>Request changes</button>
                  <button className="danger small-btn" disabled={action.busy} onClick={() => decide(a, 'rejected')}>Reject</button>
                </>
              )}
              {a.decision === 'approved' && <button className="secondary small-btn" onClick={() => revoke(a)}>Revoke approval</button>}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
