import { Link } from 'react-router-dom'
import { useResource } from '../hooks/useResource'

export type Economics = {
  roas: number | null
  gross_margin_pct: number | null
  break_even_roas: number | null
  contribution_profit: number | null
  cost_per_lead: number | null
  customer_acquisition_cost: number | null
  average_order_value: number | null
  payback_orders: number | null
  customer_lifetime_value: number | null
  ltv_to_cac: number | null
  lead_to_customer_pct: number | null
  verdict: 'profitable' | 'losing' | 'break_even' | 'unknown'
  explanation: string
  missing: string[]
  basis: string
}

type Dimension = { key: string; label: string; score: number | null; measured: boolean; basis: string; evidence: string[]; how_scored: string; next_step: string | null }
type GrowthScore = { overall: number | null; measured_dimensions: number; total_dimensions: number; dimensions: Dimension[]; note: string }

const VERDICT: Record<Economics['verdict'], { label: string; cls: string }> = {
  profitable: { label: 'Made money', cls: 'completed' },
  losing: { label: 'Lost money', cls: 'failed' },
  break_even: { label: 'Broke even', cls: 'pending' },
  unknown: { label: 'Not enough data', cls: 'draft' },
}

function num(v: number | null, opts: { currency?: string | null; suffix?: string; digits?: number } = {}) {
  if (v == null) return '-'
  const text = v.toLocaleString(undefined, { maximumFractionDigits: opts.digits ?? 2 })
  // ARC works in US dollars, so amounts read like every other figure on the page.
  const prefix = !opts.currency ? '' : opts.currency === 'USD' ? '$' : `${opts.currency} `
  return `${prefix}${text}${opts.suffix || ''}`
}

/** Whether recorded spend made or lost money at the customer's own margin. */
export function EconomicsPanel({ economics, currency, title = 'Did this spend make money?' }: { economics: Economics; currency?: string | null; title?: string }) {
  const v = VERDICT[economics.verdict]
  const rows: [string, string][] = [
    ['Return on ad spend', num(economics.roas, { suffix: 'x' })],
    ['Break-even return on ad spend', num(economics.break_even_roas, { suffix: 'x' })],
    ['Profit after ad spend', num(economics.contribution_profit, { currency, digits: 0 })],
    ['Cost per lead', num(economics.cost_per_lead, { currency })],
    ['Cost to win a customer', num(economics.customer_acquisition_cost, { currency })],
    ['Leads that became customers', num(economics.lead_to_customer_pct, { suffix: '%', digits: 1 })],
    ['Average order value', num(economics.average_order_value, { currency })],
    ['Customer lifetime value', num(economics.customer_lifetime_value, { currency })],
    ['Lifetime value to acquisition cost', num(economics.ltv_to_cac, { suffix: 'x', digits: 1 })],
  ]
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>{title}</h2>
        <span className={`status-pill ${v.cls}`}>{v.label}</span>
      </div>
      <p style={{ marginTop: 10 }}>{economics.explanation}</p>
      <div className="table-wrap">
        <table className="compare-table">
          <caption className="sr-only">Profit figures</caption>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label}>
                <th scope="row">{label}</th>
                <td>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small" style={{ marginTop: 10 }}>
        {economics.basis}{' '}
        {economics.missing.length > 0 && (
          <>
            Still needed for the full picture: {economics.missing.join(', ')}. <Link to="/app/brand">Add your margin</Link>
          </>
        )}
      </p>
    </div>
  )
}

/** Six-dimension Growth Score. Unmeasured dimensions say what is missing; they are never estimated. */
export function GrowthScoreCard({ orgId }: { orgId: string }) {
  const { data } = useResource<GrowthScore>(`/organizations/${orgId}/growth-score`)
  if (!data) return null
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div style={{ display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
        <div className="score-ring" style={{ ['--pct' as string]: `${data.overall ?? 0}%` }} aria-hidden="true">
          <span>{data.overall ?? '-'}</span>
        </div>
        <div style={{ flex: '1 1 260px' }}>
          <h2 style={{ margin: 0 }}>Growth Score{data.overall != null ? `: ${data.overall} out of 100` : ''}</h2>
          <p className="muted small" style={{ margin: '6px 0 0' }}>{data.note}</p>
        </div>
      </div>
      <div className="table-wrap" style={{ marginTop: 14 }}>
        <table className="compare-table">
          <caption className="sr-only">Growth Score by dimension</caption>
          <thead>
            <tr>
              <th scope="col">Dimension</th>
              <th scope="col">Score</th>
              <th scope="col">What it rests on</th>
            </tr>
          </thead>
          <tbody>
            {data.dimensions.map((d) => (
              <tr key={d.key}>
                <th scope="row">{d.label}</th>
                <td>{d.measured ? d.score : <span className="muted">Not measured</span>}</td>
                <td>
                  {d.evidence.map((e) => (
                    <div key={e}>{e}</div>
                  ))}
                  {d.next_step && <div className="muted">{d.next_step}</div>}
                  <details>
                    <summary className="muted small">How this is scored</summary>
                    <span className="muted small">{d.how_scored}</span>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

type CostReport = {
  basis: string
  totals: { calls: number; input_tokens: number; cached_input_tokens: number; output_tokens: number; cost_usd: number }
  by_model: { provider: string; model: string; calls: number; input_tokens: number; cached_input_tokens: number; output_tokens: number; cost_usd: number }[]
  by_campaign: { campaign_id: string | null; campaign_name: string; calls: number; cost_usd: number; failed_calls: number }[]
  reliability: { agent_calls: number; failed_calls: number; repeated_calls: number; calls_per_task: number | null; failures_by_reason: Record<string, number> }
  budget: { month_cost_usd: number; monthly_allowance_usd: number | null; used_pct: number | null; level: 'ok' | 'warning' | 'over' | 'none'; message: string }
  cache_note: string
}

const usd = (v: number) => `$${v.toFixed(v > 0 && v < 1 ? 4 : 2)}`

/** AI cost for the last 30 days: budget used, cost by model and campaign, and wasted calls. */
export function CostPanel({ orgId }: { orgId: string }) {
  const { data } = useResource<CostReport>(`/organizations/${orgId}/cost-report?days=30`)
  if (!data) return null
  const b = data.budget
  const pill = b.level === 'over' ? 'failed' : b.level === 'warning' ? 'pending' : 'completed'
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>AI cost · last 30 days</h2>
        {b.level !== 'none' && <span className={`status-pill ${pill}`}>{b.message}</span>}
      </div>
      <p className="muted small" style={{ marginTop: 8 }}>
        {usd(b.month_cost_usd)} this month{b.monthly_allowance_usd != null ? ` of a $${b.monthly_allowance_usd} allowance` : ''}. {data.basis}
      </p>
      <div className="table-wrap">
        <table className="compare-table">
          <caption>By model</caption>
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th scope="col">Calls</th>
              <th scope="col">Tokens in</th>
              <th scope="col">Of which cached</th>
              <th scope="col">Tokens out</th>
              <th scope="col">Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {data.by_model.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">No AI calls in this period.</td>
              </tr>
            )}
            {data.by_model.map((m) => (
              <tr key={`${m.provider}-${m.model}`}>
                <th scope="row" className="mono small">{m.provider} · {m.model}</th>
                <td>{m.calls}</td>
                <td>{m.input_tokens.toLocaleString()}</td>
                <td>{m.cached_input_tokens.toLocaleString()}</td>
                <td>{m.output_tokens.toLocaleString()}</td>
                <td>{usd(m.cost_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.by_campaign.length > 0 && (
        <div className="table-wrap" style={{ marginTop: 14 }}>
          <table className="compare-table">
            <caption>By campaign</caption>
            <thead>
              <tr>
                <th scope="col">Campaign</th>
                <th scope="col">Agent calls</th>
                <th scope="col">Failed</th>
                <th scope="col">Est. cost</th>
              </tr>
            </thead>
            <tbody>
              {data.by_campaign.map((c) => (
                <tr key={c.campaign_id || 'other'}>
                  <th scope="row">{c.campaign_name}</th>
                  <td>{c.calls}</td>
                  <td>{c.failed_calls}</td>
                  <td>{usd(c.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="muted small" style={{ marginTop: 12 }}>
        {data.reliability.failed_calls} failed and {data.reliability.repeated_calls} repeated agent calls out of {data.reliability.agent_calls}
        {data.reliability.calls_per_task != null ? ` (${data.reliability.calls_per_task} calls per task)` : ''}. {data.cache_note}
      </p>
    </div>
  )
}
