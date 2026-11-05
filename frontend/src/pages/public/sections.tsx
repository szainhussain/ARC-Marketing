import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useResource } from '../../hooks/useResource'
import { AGENT_META, agentVideo, type PublicAgent } from '../../lib/agentMeta'
import AgentDetailDialog from '../../components/marketing/AgentDetailDialog'
import Reveal from '../../components/motion/Reveal'
import { ErrorState, Skeleton } from '../../components/ui'
import { INTEGRATION_STATUS_LABEL } from '../../lib/marketing'

export type CatalogItem = {
  key: string
  name: string
  category: string
  status: 'available_tested' | 'architecture_supported' | 'planned'
  detail: string
  prerequisite: string | null
  agents: string[]
}

export type Plan = {
  code: string
  name: string
  tagline: string
  monthly_price_usd: number | null
  price_is_provisional: boolean
  entitlements: Record<string, number | null>
  features: string[]
  overage_note: string
}


const UNREACHABLE = "We couldn't reach the ARC service just now. It may be waking up — try again in a minute."

export function AgentGrid({ limit }: { limit?: number }) {
  const { data, error, reload } = useResource<{ agents: PublicAgent[] }>('/public/agents')
  const [selected, setSelected] = useState<PublicAgent | null>(null)
  const agents = data?.agents || []
  if (error && !data) return <ErrorState message={UNREACHABLE} onRetry={reload} />
  if (!data) return <Skeleton height={140} count={2} />
  return (
    <>
      <div className="agent-public-grid">
        {agents.slice(0, limit).map((a) => {
          const meta = AGENT_META[a.agent_id]
          const Icon = meta?.icon
          return (
            <button key={a.agent_id} className="agent-public-card" onClick={() => setSelected(a)} aria-haspopup="dialog">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="agent-glyph">{Icon && <Icon size={19} aria-hidden="true" />}</span>
                <span className="n">{String(a.number).padStart(2, '0')}</span>
              </div>
              <span className="name">{a.name}</span>
              <span className="role">{a.role}</span>
              <span className="agent-card-foot">
                <span className="small" style={{ color: 'var(--color-accent)' }}>
                  See how it works →
                </span>
                {agentVideo(a.agent_id) && <span className="agent-video-badge">▶ 30s video</span>}
              </span>
            </button>
          )
        })}
      </div>
      <AgentDetailDialog agent={selected} all={agents} onClose={() => setSelected(null)} />
    </>
  )
}

export function IntegrationList({ compact }: { compact?: boolean }) {
  const { data, error, reload } = useResource<{ integrations: CatalogItem[] }>('/public/integrations')
  if (error && !data) return <ErrorState message={UNREACHABLE} onRetry={reload} />
  if (!data) return <Skeleton height={60} count={3} />
  const items = compact ? data.integrations.slice(0, 8) : data.integrations
  return (
    <>
      <div className="status-legend">
        {Object.entries(INTEGRATION_STATUS_LABEL).map(([k, v]) => (
          <span key={k} className={`int-status ${k}`}>
            {v}
          </span>
        ))}
      </div>
      <div className="cap-grid">
        {items.map((i) => (
          <div key={i.key} className="cap">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
              <span className="muted small">{i.category}</span>
              <span className={`int-status ${i.status}`}>{INTEGRATION_STATUS_LABEL[i.status]}</span>
            </div>
            <h3>{i.name}</h3>
            <p>{i.detail}</p>
            {!compact && i.prerequisite && (
              <p className="small" style={{ marginTop: 8 }}>
                <span className="muted">Needs: </span>
                {i.prerequisite}
              </p>
            )}
          </div>
        ))}
      </div>
      <p className="muted small" style={{ marginTop: 16 }}>
        Provider names describe compatibility targets, not partnerships or endorsements.
      </p>
    </>
  )
}

export function PricingTable() {
  const { data, error, reload } = useResource<{ plans: Plan[]; pricing_note: string }>('/public/plans')
  if (error && !data) return <ErrorState message={UNREACHABLE} onRetry={reload} />
  if (!data) return <Skeleton height={300} />
  return (
    <>
      <div className="notice">{data.pricing_note}</div>
      <div className="pricing-grid">
        {data.plans.map((p) => (
          <div key={p.code} className={`plan${p.code === 'growth' ? ' featured' : ''}`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>{p.name}</strong>
              {p.code === 'growth' && <span className="int-status architecture_supported">Most teams</span>}
            </div>
            <div className="price">
              {p.monthly_price_usd == null ? 'Custom' : `$${p.monthly_price_usd}`}
              {p.monthly_price_usd != null && <small> /month · provisional</small>}
            </div>
            <p className="muted small" style={{ margin: 0 }}>
              {p.tagline}
            </p>
            <ul>
              <li>
                <Check size={15} /> {fmt(p.entitlements.monthly_workflow_runs)} campaign runs / month
              </li>
              <li>
                <Check size={15} /> {fmt(p.entitlements.seats)} seats
              </li>
              <li>
                <Check size={15} /> {fmt(p.entitlements.active_campaigns)} active campaigns
              </li>
              <li>
                <Check size={15} /> {p.entitlements.monthly_ai_budget_usd == null ? 'Custom' : `$${p.entitlements.monthly_ai_budget_usd}`} AI
                budget / month (est.)
              </li>
              {p.features.map((f) => (
                <li key={f}>
                  <Check size={15} /> {f}
                </li>
              ))}
            </ul>
            <span className="muted small">{p.overage_note}</span>
            <Link to={p.monthly_price_usd == null ? '/contact' : '/signup'} className={`btn${p.code === 'growth' ? ' accent' : ' secondary'}`} style={{ justifyContent: 'center', marginTop: 'auto' }}>
              {p.monthly_price_usd == null ? 'Talk to us' : 'Start with ' + p.name}
            </Link>
          </div>
        ))}
      </div>
    </>
  )
}

const COMPARE_ROWS: { label: string; key: string; money?: boolean }[] = [
  { label: 'Campaign runs per month', key: 'monthly_workflow_runs' },
  { label: 'Active campaigns', key: 'active_campaigns' },
  { label: 'Team seats', key: 'seats' },
  { label: 'Knowledge entries', key: 'knowledge_entries' },
  { label: 'Agent executions per month', key: 'monthly_agent_executions' },
  { label: 'Approved exports per month', key: 'monthly_exports' },
  { label: 'AI budget per month (est.)', key: 'monthly_ai_budget_usd', money: true },
  { label: 'AI budget per run (est.)', key: 'max_run_budget_usd', money: true },
]

export function PlanComparison() {
  const { data } = useResource<{ plans: Plan[] }>('/public/plans')
  if (!data) return null
  const plans = data.plans
  return (
    <div className="table-wrap">
      <table className="compare-table plan-compare">
        <caption className="sr-only">Plan comparison</caption>
        <thead>
          <tr>
            <th scope="col">Compare plans</th>
            {plans.map((p) => (
              <th key={p.code} scope="col" className={p.code === 'growth' ? 'arc-col' : ''}>
                {p.name}
                <div className="muted small">{p.monthly_price_usd == null ? 'Custom' : `$${p.monthly_price_usd}/mo`}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">All 12 agents</th>
            {plans.map((p) => (
              <td key={p.code}>
                <Check size={15} aria-label="Included" />
              </td>
            ))}
          </tr>
          {COMPARE_ROWS.map((r) => (
            <tr key={r.key}>
              <th scope="row">{r.label}</th>
              {plans.map((p) => {
                const v = p.entitlements[r.key]
                return <td key={p.code}>{v == null ? (p.monthly_price_usd == null ? 'Custom' : 'Unlimited') : r.money ? `$${v}` : v.toLocaleString()}</td>
              })}
            </tr>
          ))}
          <tr>
            <th scope="row">Approval inbox, audit log, data export</th>
            {plans.map((p) => (
              <td key={p.code}>
                <Check size={15} aria-label="Included" />
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function fmt(v: number | null | undefined) {
  return v == null ? 'Unlimited' : String(v)
}

export function SectionHead({ title, lede }: { title: string; lede?: string }) {
  return (
    <Reveal>
      <h2 className="display-h">{title}</h2>
      {lede && <p className="lede">{lede}</p>}
    </Reveal>
  )
}
