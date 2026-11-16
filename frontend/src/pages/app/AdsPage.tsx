import { useEffect, useState } from 'react'
import { OctagonX, Plus, ShieldCheck } from 'lucide-react'
import { apiRequest, ApiError } from '../../api/client'
import { DataTable, Dialog, EmptyState, ErrorState, Field, PageHeader, PageSkeleton, StatusPill, useToast } from '../../components/ui'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResource } from '../../hooks/useResource'
import { humanize } from '../../lib/labels'

type Launch = {
  id: string; name: string; channel: string | null; objective: string | null; platform: string; daily_budget: number; currency: string
  end_date: string; status: 'pending_approval' | 'approved' | 'active' | 'paused' | 'stopped' | 'rejected' | 'failed'
  stop_reason: string | null; last_error: string | null; spend_today: number; spend_total: number
}
type Overview = {
  guardrail: { max_daily_budget: number; currency: string; limit: number; committed: number; spend_today: number }
  platforms: { key: string; label: string }[]
  launches: Launch[]
}
type PlanItem = { name: string; channel: string; objective: string; audience: string }
type Plan = { id: string; campaign_name: string | null; current_version?: { content?: { campaign_structure?: PlanItem[] } } }

const PILL: Record<Launch['status'], string> = {
  pending_approval: 'pending', approved: 'running', active: 'succeeded', paused: 'retrying', stopped: 'cancelled', rejected: 'cancelled', failed: 'failed',
}
const money = (n: number, c: string) => new Intl.NumberFormat(undefined, { style: 'currency', currency: c }).format(n)

export default function AdsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const [pollMs, setPollMs] = useState<number | undefined>(undefined)
  const { data, error, loading, reload } = useResource<Overview>(orgId ? `/organizations/${orgId}/ads` : null, { pollMs })
  const live = !!data?.launches.some((l) => ['approved', 'active'].includes(l.status))
  useEffect(() => {
    setPollMs(live ? 5000 : undefined)
  }, [live])
  const [dialog, setDialog] = useState<null | 'cap' | 'launch'>(null)
  const [approving, setApproving] = useState<Launch | null>(null)

  async function post(path: string, body: unknown, done: string) {
    try {
      await apiRequest(`/organizations/${orgId}/ads${path}`, { method: 'POST', body })
      toast({ tone: 'success', title: done })
      reload()
      return true
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Something went wrong' })
      return false
    }
  }

  if (!orgId) return null
  if (loading && !data) return <PageSkeleton />
  const g = data?.guardrail
  const cur = g?.currency || 'USD'

  return (
    <div className="page page-wide">
      <PageHeader
        title="Ads"
        description="Launch ads from an approved paid media plan. Agents never spend: a person approves every launch, and ARC pauses everything if you hit your daily cap or turn on the kill switch."
        actions={<button className="danger" disabled={!live} onClick={() => post('/stop-all', {}, 'Stopping all ads')}><OctagonX size={15} aria-hidden="true" /> Stop all ads</button>}
      />
      {error && <ErrorState message={error} />}
      <div className="banner info" style={{ marginBottom: 16 }}>
        Ads run on ARC's <strong>test platform</strong> for now: no real money is spent. Meta and Google Ads connect here once API access is approved.
      </div>

      <div className="card">
        <div className="card-head">
          <h2><ShieldCheck size={18} aria-hidden="true" /> Daily spend cap</h2>
          <button className="secondary small-btn" onClick={() => setDialog('cap')}>{g?.max_daily_budget ? 'Change cap' : 'Set a cap'}</button>
        </div>
        {g && (g.max_daily_budget > 0 ? (
          <div className="kpi-row">
            <div><div className="muted small">Cap per day</div><strong>{money(g.max_daily_budget, cur)}</strong></div>
            <div><div className="muted small">Approved daily budgets</div><strong>{money(g.committed, cur)}</strong></div>
            <div><div className="muted small">Spent today</div><strong>{money(g.spend_today, cur)}</strong></div>
          </div>
        ) : (
          <p className="small">Launching is off until an owner or admin sets the most this workspace may spend per day across all ads.</p>
        ))}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-head">
          <h2>Launches</h2>
          <button className="small-btn" disabled={!g?.max_daily_budget} onClick={() => setDialog('launch')}><Plus size={14} aria-hidden="true" /> Launch an ad</button>
        </div>
        <DataTable rows={data?.launches || []} rowKey={(r) => r.id} caption="Ad launches"
          empty={<EmptyState title="No ads launched yet" body="Approve a paid media plan, then launch one of its ads with a daily budget and an end date." />}
          columns={[
            { key: 'n', header: 'Ad', render: (r) => <><strong>{r.name}</strong><div className="muted small">{[r.channel, r.objective].filter(Boolean).join(' · ')} · ends {r.end_date}</div>{(r.stop_reason || r.last_error) && <div className="small" style={{ color: 'var(--color-warning)' }}>{r.last_error || r.stop_reason}</div>}</> },
            { key: 's', header: 'Status', render: (r) => <StatusPill status={PILL[r.status]} label={r.status === 'approved' ? 'Launching…' : humanize(r.status)} /> },
            { key: 'b', header: 'Budget', render: (r) => <span className="small">{money(r.daily_budget, r.currency)} / day</span> },
            { key: 'x', header: 'Spent', render: (r) => <span className="small">{money(r.spend_today, r.currency)} today<div className="muted">{money(r.spend_total, r.currency)} total</div></span> },
            {
              key: 'a', header: '', render: (r) => (
                <span className="head-actions" style={{ margin: 0 }}>
                  {r.status === 'pending_approval' && <>
                    <button className="small-btn" onClick={() => setApproving(r)}>Review & approve</button>
                    <button className="secondary small-btn" onClick={() => post(`/launches/${r.id}/decision`, { decision: 'reject' }, 'Launch rejected')}>Reject</button>
                  </>}
                  {r.status === 'active' && <button className="secondary small-btn" onClick={() => post(`/launches/${r.id}/pause`, {}, 'Pausing')}>Pause</button>}
                  {r.status === 'paused' && <button className="small-btn" onClick={() => post(`/launches/${r.id}/resume`, {}, 'Resuming')}>Resume</button>}
                  {['approved', 'active', 'paused'].includes(r.status) && <button className="secondary small-btn" onClick={() => post(`/launches/${r.id}/stop`, {}, 'Stopping')}>Stop</button>}
                </span>
              ),
            },
          ]} />
      </div>

      {dialog === 'cap' && g && <CapDialog orgId={orgId} g={g} onClose={() => setDialog(null)} onDone={() => { setDialog(null); reload() }} />}
      {dialog === 'launch' && g && <LaunchDialog orgId={orgId} g={g} onClose={() => setDialog(null)} onDone={() => { setDialog(null); reload() }} />}
      {approving && <ApproveDialog launch={approving} onClose={() => setApproving(null)} onApprove={async (typed) => {
        if (await post(`/launches/${approving.id}/decision`, { decision: 'approve', confirm_daily_budget: typed }, 'Approved. Launching now…')) setApproving(null)
      }} />}
    </div>
  )
}

function CapDialog({ orgId, g, onClose, onDone }: { orgId: string; g: Overview['guardrail']; onClose: () => void; onDone: () => void }) {
  const [cap, setCap] = useState(String(g.max_daily_budget || ''))
  const [err, setErr] = useState<string | null>(null)
  async function save() {
    try {
      await apiRequest(`/organizations/${orgId}/ads/guardrail`, { method: 'POST', body: { max_daily_budget: Number(cap), currency: 'USD' } })
      onDone()
    } catch (e) {
      setErr(e instanceof ApiError ? e.details?.[0]?.issue || e.message : 'Could not save')
    }
  }
  return (
    <Dialog open onClose={onClose} title="Daily ad spend cap" footer={<><button className="secondary" onClick={onClose}>Cancel</button><button onClick={save}>Save cap</button></>}>
      <p className="small muted" style={{ marginTop: 0 }}>The most this workspace can spend per day across every ad. ARC refuses launches above it and pauses all ads if spend goes over it. Set 0 to turn launching off.</p>
      <Field id="cap-amount" label="Cap per day (USD)" error={err || undefined} hint={`Up to ${g.limit} a day.`}>
        <input id="cap-amount" type="number" min={0} step="1" value={cap} onChange={(e) => setCap(e.target.value)} />
      </Field>
    </Dialog>
  )
}

function LaunchDialog({ orgId, g, onClose, onDone }: { orgId: string; g: Overview['guardrail']; onClose: () => void; onDone: () => void }) {
  const plans = useResource<{ deliverables: Plan[] }>(`/organizations/${orgId}/deliverables?type=paid_media_plan`)
  const items = (plans.data?.deliverables || []).flatMap((d) => (d.current_version?.content?.campaign_structure || []).map((it, i) => ({ d, it, i })))
  const remaining = Math.max(0, g.max_daily_budget - g.committed)
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10)
  const inAWeek = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)
  const [pick, setPick] = useState(0)
  const [budget, setBudget] = useState(String(Math.min(10, remaining)))
  const [end, setEnd] = useState(inAWeek)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  async function save() {
    const sel = items[pick]
    if (!sel) return
    setErrors({}); setFormError(null)
    try {
      await apiRequest(`/organizations/${orgId}/ads/launches`, { method: 'POST', body: { deliverable_id: sel.d.id, item_index: sel.i, daily_budget: Number(budget), end_date: end, platform: 'sandbox' } })
      onDone()
    } catch (e) {
      if (e instanceof ApiError && e.details?.length) setErrors(Object.fromEntries(e.details.map((d) => [d.field, d.issue])))
      else setFormError(e instanceof ApiError ? e.message : 'Could not request the launch')
    }
  }
  return (
    <Dialog open onClose={onClose} title="Launch an ad" footer={<><button className="secondary" onClick={onClose}>Cancel</button><button disabled={!items.length} onClick={save}>Request approval</button></>}>
      {formError && <div className="banner error">{formError}</div>}
      {items.length === 0 ? (
        <p className="small">No paid media plans yet. Run a campaign, then approve its paid media plan.</p>
      ) : (
        <>
          <Field id="ad-item" label="Ad from your paid media plan" error={errors.item_index}>
            <select id="ad-item" value={pick} onChange={(e) => setPick(Number(e.target.value))}>
              {items.map((x, k) => <option key={k} value={k}>{x.d.campaign_name || 'Campaign'} · {x.it.name} ({x.it.channel})</option>)}
            </select>
          </Field>
          <Field id="ad-budget" label={`Daily budget (${g.currency})`} error={errors.daily_budget} hint={`${remaining.toFixed(2)} ${g.currency} a day left under your cap.`}>
            <input id="ad-budget" type="number" min={1} step="1" value={budget} onChange={(e) => setBudget(e.target.value)} />
          </Field>
          <Field id="ad-end" label="End date" error={errors.end_date} hint="Ads stop automatically on this date (90 days at most).">
            <input id="ad-end" type="date" min={tomorrow} value={end} onChange={(e) => setEnd(e.target.value)} />
          </Field>
          <p className="small muted">The plan must be approved in its current version. An approver then confirms the budget before anything launches.</p>
        </>
      )}
    </Dialog>
  )
}

function ApproveDialog({ launch, onClose, onApprove }: { launch: Launch; onClose: () => void; onApprove: (typed: string) => void }) {
  const [typed, setTyped] = useState('')
  return (
    <Dialog open onClose={onClose} title="Approve ad spend" footer={<><button className="secondary" onClick={onClose}>Cancel</button><button disabled={Number(typed) !== launch.daily_budget} onClick={() => onApprove(typed)}>Approve and launch</button></>}>
      <p style={{ marginTop: 0 }}><strong>{launch.name}</strong></p>
      <p className="small">{money(launch.daily_budget, launch.currency)} a day until {launch.end_date}, on {launch.platform === 'sandbox' ? "ARC's test platform (no real money)" : humanize(launch.platform)}.</p>
      <Field id="ad-confirm" label={`Type the daily budget (${launch.daily_budget}) to confirm`}>
        <input id="ad-confirm" inputMode="decimal" value={typed} onChange={(e) => setTyped(e.target.value)} />
      </Field>
    </Dialog>
  )
}
