import { useMemo, useState } from 'react'
import { AXIS, CHART, TOOLTIP } from '../../lib/chartTheme'
import { Link, useSearchParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FileText, Plus, Printer } from 'lucide-react'
import { apiRequest, ApiError } from '../../api/client'
import { ConfirmDialog, DataTable, Dialog, EmptyState, ErrorState, Field, PageHeader, PageSkeleton, useToast } from '../../components/ui'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResource } from '../../hooks/useResource'
import { humanize } from '../../lib/labels'
import { API_BASE_URL } from '../../lib/apiBase'

type Metrics = {
  spend: number | null
  impressions: number | null
  clicks: number | null
  leads: number | null
  conversions: number | null
  revenue: number | null
  ctr_pct: number | null
  conversion_rate_pct: number | null
  cost_per_lead: number | null
  cost_per_acquisition: number | null
  roas: number | null
}
type ResultRow = Metrics & { id: string; campaign_id: string; campaign_name: string | null; channel: string; period_start: string; period_end: string; notes: string | null }
type Summary = { totals: Metrics; by_channel: (Metrics & { channel: string })[]; by_campaign: (Metrics & { campaign_id: string; campaign_name: string | null })[]; results: ResultRow[] }

const CHANNELS = ['Instagram', 'Facebook', 'LinkedIn', 'TikTok', 'Google Ads', 'Meta Ads', 'Email', 'SEO / organic', 'Google Business Profile', 'Events', 'Other']
const NUM_FIELDS: [keyof Metrics, string][] = [
  ['spend', 'Spend (USD)'],
  ['impressions', 'Impressions'],
  ['clicks', 'Clicks'],
  ['leads', 'Leads'],
  ['conversions', 'Conversions / sales'],
  ['revenue', 'Revenue (USD)'],
]

const usd = (v: number | null | undefined, digits = 0) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits })}`)
const num = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 0 }))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toFixed(2)}%`)
const roas = (v: number | null | undefined) => (v == null ? '—' : `${v.toFixed(2)}x`)

function iso(d: Date) {
  return d.toISOString().slice(0, 10)
}

function rangeFor(key: string): { from?: string; to?: string } {
  const now = new Date()
  const y = now.getUTCFullYear()
  const m = now.getUTCMonth()
  if (key === 'this_month') return { from: iso(new Date(Date.UTC(y, m, 1))), to: iso(new Date(Date.UTC(y, m + 1, 0))) }
  if (key === 'last_month') return { from: iso(new Date(Date.UTC(y, m - 1, 1))), to: iso(new Date(Date.UTC(y, m, 0))) }
  if (key === '90d') return { from: iso(new Date(now.getTime() - 90 * 86400000)), to: iso(now) }
  return {}
}

function MetricTiles({ t }: { t: Metrics }) {
  const tiles: [string, string][] = [
    ['Spend', usd(t.spend)],
    ['Leads', num(t.leads)],
    ['Cost per lead', usd(t.cost_per_lead, 2)],
    ['Conversions', num(t.conversions)],
    ['Revenue', usd(t.revenue)],
    ['Return on ad spend', roas(t.roas)],
  ]
  return (
    <div className="kpi-grid">
      {tiles.map(([k, v]) => (
        <div key={k} className="kpi-tile">
          <div className="kpi-label">{k}</div>
          <div className="kpi-value">{v}</div>
          <div className="muted small">{v === '—' ? 'Not recorded' : 'Entered manually'}</div>
        </div>
      ))}
    </div>
  )
}

export function ResultsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const [range, setRange] = useState('90d')
  const [campaignId, setCampaignId] = useState('')
  const r = rangeFor(range)
  const qs = new URLSearchParams({ ...(r.from ? { from: r.from } : {}), ...(r.to ? { to: r.to } : {}), ...(campaignId ? { campaign_id: campaignId } : {}) }).toString()
  const { data, error, loading, reload } = useResource<Summary>(orgId ? `/organizations/${orgId}/results?${qs}` : null)
  const campaigns = useResource<{ campaigns: { id: string; name: string }[] }>(orgId ? `/organizations/${orgId}/campaigns` : null)
  const [editing, setEditing] = useState<Partial<ResultRow> | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [deleting, setDeleting] = useState<ResultRow | null>(null)
  const campaignList = campaigns.data?.campaigns || []

  function openNew() {
    const r2 = rangeFor('last_month')
    setErrors({})
    setFormError(null)
    setEditing({ campaign_id: campaignId || campaignList[0]?.id || '', channel: 'Instagram', period_start: r2.from, period_end: r2.to })
  }

  async function save() {
    if (!orgId || !editing) return
    setBusy(true)
    setFormError(null)
    const body: Record<string, unknown> = {
      campaign_id: editing.campaign_id,
      channel: editing.channel,
      period_start: editing.period_start,
      period_end: editing.period_end,
      notes: editing.notes || '',
    }
    for (const [k] of NUM_FIELDS) body[k] = editing[k] ?? ''
    try {
      if (editing.id) await apiRequest(`/organizations/${orgId}/results/${editing.id}`, { method: 'PATCH', body })
      else await apiRequest(`/organizations/${orgId}/results`, { method: 'POST', body })
      setEditing(null)
      toast({ tone: 'success', title: 'Results saved' })
      reload()
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message)
        setErrors(Object.fromEntries(err.details.map((d) => [d.field, d.issue])))
      } else setFormError('Could not save the results.')
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!orgId || !deleting) return
    await apiRequest(`/organizations/${orgId}/results/${deleting.id}`, { method: 'DELETE' })
    setDeleting(null)
    reload()
  }

  const chart = useMemo(() => (data?.by_channel || []).map((c) => ({ channel: c.channel, Leads: c.leads || 0, Conversions: c.conversions || 0 })), [data])

  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page page-wide">
      <PageHeader
        title="Results"
        description="Record what each campaign achieved per channel. ARC works out cost per lead, conversion rate and return on ad spend, and uses it in your Command Center and monthly report."
        actions={
          <>
            <Link to="/app/reports/monthly" className="btn secondary">
              <FileText size={15} aria-hidden="true" /> Monthly report
            </Link>
            <button onClick={openNew} disabled={!campaignList.length}>
              <Plus size={15} aria-hidden="true" /> Add results
            </button>
          </>
        }
      />
      {error && <ErrorState message={error} onRetry={reload} />}
      <div className="filter-row" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <label htmlFor="res-range" className="sr-only">Date range</label>
        <select id="res-range" className="select-inline" value={range} onChange={(e) => setRange(e.target.value)}>
          <option value="this_month">This month</option>
          <option value="last_month">Last month</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
        <label htmlFor="res-campaign" className="sr-only">Campaign</label>
        <select id="res-campaign" className="select-inline" value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
          <option value="">All campaigns</option>
          {campaignList.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      {!campaignList.length && campaigns.data && (
        <EmptyState title="Create a campaign first" body="Results are recorded per campaign and channel." action={<Link to="/app/campaigns/new" className="btn">Create campaign</Link>} />
      )}
      {data && data.results.length === 0 && campaignList.length > 0 && (
        <EmptyState
          title="No results recorded for this period"
          body="Add spend, leads, sales and revenue from your ad platforms, CRM or shop. Until analytics connectors are live, these numbers come only from you — ARC never estimates them."
          action={<button onClick={openNew}><Plus size={15} aria-hidden="true" /> Add results</button>}
        />
      )}
      {data && data.results.length > 0 && (
        <>
          <MetricTiles t={data.totals} />
          <div className="two-up" style={{ marginTop: 18 }}>
            <div className="card chart-card">
              <h2>Leads and conversions by channel</h2>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chart} margin={{ left: -10, right: 8 }}>
                  <CartesianGrid stroke={CHART.grid} vertical={false} />
                  <XAxis dataKey="channel" {...AXIS} />
                  <YAxis {...AXIS} allowDecimals={false} />
                  <Tooltip {...TOOLTIP} cursor={TOOLTIP.cursor} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Leads" fill={CHART.accent} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Conversions" fill={CHART.accent2} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <h2>By channel</h2>
              <DataTable
                rows={data.by_channel}
                rowKey={(c) => c.channel}
                caption="Results by channel"
                columns={[
                  { key: 'c', header: 'Channel', render: (c) => <strong className="small">{c.channel}</strong> },
                  { key: 's', header: 'Spend', render: (c) => usd(c.spend) },
                  { key: 'l', header: 'Leads', render: (c) => num(c.leads) },
                  { key: 'cpl', header: 'Cost / lead', render: (c) => usd(c.cost_per_lead, 2) },
                  { key: 'r', header: 'ROAS', render: (c) => roas(c.roas) },
                ]}
              />
            </div>
          </div>
          <div className="card" style={{ marginTop: 18 }}>
            <h2>All entries</h2>
            <DataTable
              rows={data.results}
              rowKey={(r) => r.id}
              caption="Result entries"
              columns={[
                { key: 'p', header: 'Period', render: (r) => <span className="small nowrap">{r.period_start} → {r.period_end}</span> },
                { key: 'cm', header: 'Campaign', render: (r) => <span className="small">{r.campaign_name}</span> },
                { key: 'ch', header: 'Channel', render: (r) => <span className="small">{r.channel}</span> },
                { key: 's', header: 'Spend', render: (r) => usd(r.spend) },
                { key: 'cl', header: 'Clicks', render: (r) => num(r.clicks) },
                { key: 'l', header: 'Leads', render: (r) => num(r.leads) },
                { key: 'cv', header: 'Conv.', render: (r) => num(r.conversions) },
                { key: 'rv', header: 'Revenue', render: (r) => usd(r.revenue) },
                {
                  key: 'a',
                  header: '',
                  render: (r) => (
                    <span className="nowrap">
                      <button className="link-btn small" onClick={() => { setErrors({}); setFormError(null); setEditing(r) }}>Edit</button>{' '}
                      <button className="link-btn small" onClick={() => setDeleting(r)}>Delete</button>
                    </span>
                  ),
                },
              ]}
            />
          </div>
        </>
      )}

      <Dialog
        open={!!editing}
        onClose={() => setEditing(null)}
        title={editing?.id ? 'Edit results' : 'Add results'}
        footer={
          <>
            <button className="secondary" onClick={() => setEditing(null)}>Cancel</button>
            <button disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save'}</button>
          </>
        }
      >
        {formError && <div className="banner error">{formError}</div>}
        {editing && (
          <>
            <div className="form-grid">
              <Field id="res-f-campaign" label="Campaign" error={errors.campaign_id}>
                <select id="res-f-campaign" value={editing.campaign_id || ''} onChange={(e) => setEditing({ ...editing, campaign_id: e.target.value })}>
                  {campaignList.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </Field>
              <Field id="res-f-channel" label="Channel" error={errors.channel}>
                <input id="res-f-channel" list="res-channels" value={editing.channel || ''} onChange={(e) => setEditing({ ...editing, channel: e.target.value })} />
              </Field>
              <Field id="res-f-start" label="From" error={errors.period_start}>
                <input id="res-f-start" type="date" value={editing.period_start || ''} onChange={(e) => setEditing({ ...editing, period_start: e.target.value })} />
              </Field>
              <Field id="res-f-end" label="To" error={errors.period_end}>
                <input id="res-f-end" type="date" value={editing.period_end || ''} onChange={(e) => setEditing({ ...editing, period_end: e.target.value })} />
              </Field>
              {NUM_FIELDS.map(([k, label]) => (
                <Field key={k} id={`res-f-${k}`} label={label} error={errors[k]}>
                  <input
                    id={`res-f-${k}`}
                    type="number"
                    min="0"
                    inputMode="decimal"
                    value={editing[k] == null ? '' : String(editing[k])}
                    onChange={(e) => setEditing({ ...editing, [k]: e.target.value === '' ? null : Number(e.target.value) })}
                  />
                </Field>
              ))}
            </div>
            <datalist id="res-channels">
              {CHANNELS.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
            <Field id="res-f-notes" label="Notes (optional)" hint="Where the numbers came from, or anything unusual this period.">
              <textarea id="res-f-notes" rows={2} value={editing.notes || ''} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} />
            </Field>
            <p className="muted small" style={{ margin: 0 }}>Leave a field empty if you don't track it. ARC only calculates a ratio when both numbers exist.</p>
          </>
        )}
      </Dialog>
      <ConfirmDialog
        open={!!deleting}
        title="Delete these results?"
        body={`${deleting?.channel} · ${deleting?.period_start} → ${deleting?.period_end}`}
        tone="danger"
        confirmLabel="Delete"
        onConfirm={remove}
        onCancel={() => setDeleting(null)}
      />
    </div>
  )
}

type Report = {
  month: string
  period: { start: string; end: string }
  workspace_name: string
  results: Summary
  activity: { runs_completed: number; deliverables_created: number; approvals_given: number; exports: number; confirmed_published: number; ai_cost_usd: number }
  learnings: { title: string; kind: string }[]
  highlights: string[]
}

function lastMonthKey() {
  const d = new Date()
  d.setUTCDate(1)
  d.setUTCMonth(d.getUTCMonth() - 1)
  return d.toISOString().slice(0, 7)
}

export function MonthlyReportPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [params, setParams] = useSearchParams()
  const month = params.get('month') || lastMonthKey()
  const { data, error, loading } = useResource<Report>(orgId ? `/organizations/${orgId}/reports/monthly?month=${month}` : null)
  const label = new Date(`${month}-01T00:00:00Z`).toLocaleDateString(undefined, { month: 'long', year: 'numeric', timeZone: 'UTC' })

  if (loading && !data) return <PageSkeleton />
  return (
    <div className="page page-wide report-page">
      <PageHeader
        crumbs={[{ label: 'Results', to: '/app/results' }, { label: 'Monthly report' }]}
        title={`Marketing report · ${label}`}
        description={data?.workspace_name}
        actions={
          <span className="no-print" style={{ display: 'flex', gap: 10 }}>
            <label htmlFor="rep-month" className="sr-only">Month</label>
            <input id="rep-month" type="month" className="select-inline" value={month} onChange={(e) => e.target.value && setParams({ month: e.target.value })} />
            {orgId && (
              <>
                <a className="btn secondary" href={`${API_BASE_URL}/organizations/${orgId}/reports/monthly/export?month=${month}&format=pptx`}>
                  PowerPoint
                </a>
                <a className="btn secondary" href={`${API_BASE_URL}/organizations/${orgId}/reports/monthly/export?month=${month}&format=pdf`}>
                  PDF
                </a>
              </>
            )}
            <button className="secondary" onClick={() => window.print()}>
              <Printer size={15} aria-hidden="true" /> Print
            </button>
          </span>
        }
      />
      {error && <ErrorState message={error} />}
      {data && (
        <>
          <h2 className="report-h">Results</h2>
          {data.results.results.length === 0 ? (
            <p className="muted">
              No results were recorded for this month. <Link to="/app/results" className="no-print">Add results</Link>
            </p>
          ) : (
            <>
              <MetricTiles t={data.results.totals} />
              {data.highlights.length > 0 && (
                <ul className="check-list" style={{ marginTop: 14 }}>
                  {data.highlights.map((h) => (
                    <li key={h}>
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              )}
              <div className="card" style={{ marginTop: 14 }}>
                <DataTable
                  rows={data.results.by_campaign}
                  rowKey={(c) => c.campaign_id}
                  caption="Results by campaign"
                  columns={[
                    { key: 'n', header: 'Campaign', render: (c) => <strong className="small">{c.campaign_name}</strong> },
                    { key: 's', header: 'Spend', render: (c) => usd(c.spend) },
                    { key: 'l', header: 'Leads', render: (c) => num(c.leads) },
                    { key: 'cpl', header: 'Cost / lead', render: (c) => usd(c.cost_per_lead, 2) },
                    { key: 'cv', header: 'Conv. rate', render: (c) => pct(c.conversion_rate_pct) },
                    { key: 'r', header: 'Revenue', render: (c) => usd(c.revenue) },
                    { key: 'ro', header: 'ROAS', render: (c) => roas(c.roas) },
                  ]}
                />
              </div>
            </>
          )}

          <h2 className="report-h">What your marketing department did</h2>
          <div className="kpi-grid">
            {[
              ['Campaign runs completed', data.activity.runs_completed],
              ['Deliverables produced', data.activity.deliverables_created],
              ['Approvals given', data.activity.approvals_given],
              ['Exported for publishing', data.activity.exports],
              ['Confirmed published', data.activity.confirmed_published],
            ].map(([k, v]) => (
              <div key={k as string} className="kpi-tile">
                <div className="kpi-label">{k}</div>
                <div className="kpi-value">{v}</div>
              </div>
            ))}
          </div>

          <h2 className="report-h">What we learned</h2>
          {data.learnings.length === 0 ? (
            <p className="muted">No new knowledge was approved this month.</p>
          ) : (
            <ul className="plain-list">
              {data.learnings.map((l) => (
                <li key={l.title}>
                  {l.title} <span className="muted small">({humanize(l.kind)})</span>
                </li>
              ))}
            </ul>
          )}
          <p className="muted small" style={{ marginTop: 28 }}>
            Results are entered by your team, not measured by ARC. Period {data.period.start} to {data.period.end}. AI cost this
            month (estimate): ${data.activity.ai_cost_usd.toFixed(2)}.
          </p>
        </>
      )}
    </div>
  )
}
