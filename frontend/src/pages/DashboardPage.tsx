import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Info, Sparkles } from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useWorkspace } from '../context/WorkspaceContext'
import { useResource } from '../hooks/useResource'
import { humanize, money, relativeTime } from '../lib/labels'
import { EmptyState, ErrorState, KpiCard, PageHeader, PageSkeleton, StatusPill } from '../components/ui'
import GettingStarted from '../components/GettingStarted'

type Kpi = {
  key: string
  label: string
  value: number | null
  previous: number | null
  change_pct: number | null
  explanation: string
  link: string
  unit: string | null
  basis: string
}
type CampaignCard = {
  id: string
  name: string
  objective: string
  status: string
  run_status: string | null
  progress_pct: number
  agents_done: number
  agents_total: number
  deliverables: number
  pending_decisions: number
  estimated_cost_usd: number
  budget_guidance: string | null
  start_date: string | null
  end_date: string | null
  updated_at: string | null
}
type Dashboard = {
  range: { days: number }
  kpis: Kpi[]
  business_metrics: { key: string; label: string; requires: string; link: string; available?: boolean; value?: number | null; unit?: string | null; status?: string }[]
  series: { date: string; tasks_succeeded: number; tasks_failed: number; cost_usd: number; retries: number }[]
  cost_by_agent: { agent_id: string; agent_name: string; number: number; executions: number; cost_usd: number }[]
  campaigns: CampaignCard[]
  needs_attention: { severity: string; title: string; detail: string; link: string }[]
  upcoming: { id: string; scheduled_date: string; channel: string; title: string; status: string }[]
  recent_deliverables: { id: string; deliverable_type: string; review_status: string; campaign_id: string; campaign_name: string; created_at: string }[]
  recommendations: { title: string; detail: string; link: string; action: string }[]
}

const TOOLTIP = { contentStyle: { background: '#16181d', border: '1px solid #33373e', borderRadius: 8, fontSize: 12 } }
const AXIS = { stroke: '#6b6f74', fontSize: 11, tickLine: false, axisLine: false }

export default function DashboardPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [days, setDays] = useState(30)
  const [campaignId, setCampaignId] = useState('')
  const qs = `days=${days}${campaignId ? `&campaign_id=${campaignId}` : ''}`
  const { data, error, loading, reload } = useResource<Dashboard>(orgId ? `/organizations/${orgId}/dashboard?${qs}` : null, {
    pollMs: 15000,
  })
  const campaigns = useResource<{ campaigns: { id: string; name: string }[] }>(orgId ? `/organizations/${orgId}/campaigns` : null)

  if (!orgId) {
    return (
      <div className="page">
        <EmptyState title="No workspace selected" action={<Link to="/create-workspace" className="btn">Create a workspace</Link>} />
      </div>
    )
  }
  if (loading && !data) return <PageSkeleton />

  const fmtKpi = (k: Kpi) => (v: number) => (k.unit === 'usd' ? money(v) : k.unit === '%' ? `${v}%` : String(v))
  const series = (data?.series || []).map((s) => ({ ...s, label: s.date.slice(5) }))

  return (
    <div className="page page-wide">
      <PageHeader
        title="Business Command Center"
        description="What your marketing team is delivering, what needs you, and what it cost."
        actions={
          <>
            <label htmlFor="dash-range" className="sr-only">Date range</label>
            <select id="dash-range" className="select-inline" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <label htmlFor="dash-campaign" className="sr-only">Campaign</label>
            <select id="dash-campaign" className="select-inline" value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
              <option value="">All campaigns</option>
              {campaigns.data?.campaigns.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </>
        }
      />
      {error && <ErrorState message={error} onRetry={reload} />}
      <GettingStarted orgId={orgId} />
      {data && (
        <>
          <div className="kpi-grid">
            {data.kpis.map((k) => (
              <KpiCard key={k.key} label={k.label} value={k.value} previous={k.previous} changePct={k.change_pct}
                sub={k.explanation} to={k.link} basis={k.basis} format={fmtKpi(k)} />
            ))}
          </div>

          <div className="grid-3">
            <div className="card">
              <h2>Needs your attention</h2>
              {data.needs_attention.length === 0 ? (
                <EmptyState title="All clear" body="Nothing is waiting on you right now." />
              ) : (
                <ul className="attention-list">
                  {data.needs_attention.map((a) => (
                    <li key={a.title}>
                      <Link to={a.link}>
                        {a.severity === 'error' || a.severity === 'warning' ? (
                          <AlertTriangle size={16} color={a.severity === 'error' ? 'var(--color-danger)' : 'var(--color-warning)'} aria-hidden="true" />
                        ) : (
                          <Info size={16} color="var(--color-accent)" aria-hidden="true" />
                        )}
                        <span>
                          <strong className="small">{a.title}</strong>
                          <br />
                          <span className="muted small">{a.detail}</span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="card">
              <h2>Recommended next actions</h2>
              {data.recommendations.length === 0 ? (
                <EmptyState icon={<Sparkles size={20} />} title="You're on track" />
              ) : (
                <ul className="attention-list">
                  {data.recommendations.map((r) => (
                    <li key={r.title}>
                      <Link to={r.link}>
                        <ArrowRight size={16} color="var(--color-accent)" aria-hidden="true" />
                        <span>
                          <strong className="small">{r.title}</strong>
                          <br />
                          <span className="muted small">{r.detail}</span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <h2 className="section-title">Campaigns</h2>
          {data.campaigns.length === 0 ? (
            <div className="card">
              <EmptyState title="No campaigns yet" body="Write a brief and your 12 agents take it from there."
                action={<Link to="/app/campaigns/new" className="btn">Create campaign</Link>} />
            </div>
          ) : (
            <div className="campaign-grid">
              {data.campaigns.map((c) => (
                <Link key={c.id} to={`/app/campaigns/${c.id}`} className="card campaign-card">
                  <div className="card-head" style={{ marginBottom: 0 }}>
                    <strong>{c.name}</strong>
                    <StatusPill status={c.run_status || c.status} />
                  </div>
                  <p className="muted small" style={{ margin: 0 }}>{c.objective}</p>
                  <div className="progress" aria-label={`${c.agents_done} of ${c.agents_total} agents done`}>
                    <span style={{ width: `${c.progress_pct}%` }} />
                  </div>
                  <div className="campaign-meta">
                    <span>{c.agents_total ? `${c.agents_done}/${c.agents_total} agents` : 'Not run yet'}</span>
                    <span>{c.deliverables} deliverables</span>
                    {c.pending_decisions > 0 && <span className="text-warning">{c.pending_decisions} decision(s) pending</span>}
                    <span>{money(c.estimated_cost_usd)} est.</span>
                    {c.budget_guidance && <span>Budget: {c.budget_guidance}</span>}
                    <span>Updated {relativeTime(c.updated_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          <div className="grid-3" style={{ marginTop: 18 }}>
            <div className="card chart-card">
              <h2>Agent task throughput</h2>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={series} margin={{ left: -16, right: 8 }}>
                  <CartesianGrid stroke="#23262c" vertical={false} />
                  <XAxis dataKey="label" {...AXIS} interval="preserveStartEnd" />
                  <YAxis allowDecimals={false} {...AXIS} />
                  <Tooltip {...TOOLTIP} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area name="Succeeded" type="monotone" dataKey="tasks_succeeded" stroke="#6ee7a8" fill="rgba(110,231,168,0.15)" />
                  <Area name="Failed attempts" type="monotone" dataKey="tasks_failed" stroke="#ff8a80" fill="rgba(255,138,128,0.1)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="card chart-card">
              <h2>Estimated cost by agent</h2>
              {data.cost_by_agent.length === 0 ? (
                <EmptyState title="No agent activity in this period" />
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.cost_by_agent} layout="vertical" margin={{ left: 10, right: 12 }}>
                    <CartesianGrid stroke="#23262c" horizontal={false} />
                    <XAxis type="number" {...AXIS} tickFormatter={(v) => `$${v}`} />
                    <YAxis type="category" dataKey="number" {...AXIS} width={24} tickFormatter={(v) => String(v).padStart(2, '0')} />
                    <Tooltip {...TOOLTIP} formatter={(v: number) => money(v)} labelFormatter={(n) => data.cost_by_agent.find((a) => a.number === n)?.agent_name || n} />
                    <Bar name="Est. cost" dataKey="cost_usd" fill="#9fd8ff" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="card" style={{ marginTop: 18 }}>
            <div className="card-head">
              <h2>Business results</h2>
              <Link to="/app/results" className="small">Record results →</Link>
            </div>
            {data.business_metrics.some((m) => m.available) ? (
              <div className="unavailable-grid">
                {data.business_metrics.filter((m) => m.available && m.value != null).map((m) => (
                  <div key={m.key} className="metric-available">
                    <div className="small" style={{ fontWeight: 600 }}>{m.label}</div>
                    <div className="metric-value">
                      {m.unit === 'usd' ? money(m.value!) : m.unit === '%' ? `${m.value!.toFixed(2)}%` : m.unit === 'x' ? `${m.value!.toFixed(2)}x` : m.value!.toLocaleString()}
                    </div>
                    <div className="muted small">Entered manually</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted small" style={{ margin: 0 }}>
                No results recorded for this period. Record spend, leads and revenue to see cost per lead and return on ad spend here.
              </p>
            )}
            {data.business_metrics.some((m) => !m.available && m.link === '/app/integrations') && (
              <p className="muted small" style={{ margin: '12px 0 0' }}>
                Needs a connected source:{' '}
                {data.business_metrics.filter((m) => !m.available && m.link === '/app/integrations').map((m) => m.label.toLowerCase()).join(', ')}.
                ARC never estimates these.
              </p>
            )}
          </div>

          <div className="grid-3" style={{ marginTop: 18 }}>
            <div className="card">
              <div className="card-head"><h2>Recent deliverables</h2><Link to="/app/content" className="small">All content →</Link></div>
              {data.recent_deliverables.length === 0 ? (
                <EmptyState title="No deliverables yet" />
              ) : (
                <ul className="attention-list">
                  {data.recent_deliverables.map((d) => (
                    <li key={d.id}>
                      <Link to={`/app/campaigns/${d.campaign_id}/deliverables`}>
                        <span style={{ flex: 1 }}>
                          <strong className="small">{humanize(d.deliverable_type)}</strong>
                          <br />
                          <span className="muted small">{d.campaign_name} · {relativeTime(d.created_at)}</span>
                        </span>
                        <StatusPill status={d.review_status} />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="card">
              <div className="card-head"><h2>Upcoming schedule</h2><Link to="/app/calendar" className="small">Calendar →</Link></div>
              {data.upcoming.length === 0 ? (
                <EmptyState title="Nothing scheduled in the next 14 days"
                  body="Add a Social Media agent calendar to your content calendar from a campaign's deliverables." />
              ) : (
                <ul className="attention-list">
                  {data.upcoming.map((u) => (
                    <li key={u.id}>
                      <Link to="/app/calendar">
                        <span className="mono small" style={{ width: 80, flexShrink: 0 }}>{u.scheduled_date}</span>
                        <span style={{ flex: 1 }} className="small">{u.title}</span>
                        <span className="muted small">{u.channel}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
