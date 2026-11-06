import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AGENT_META } from '../lib/agentMeta'
import { AXIS, CHART, TOOLTIP, costTick } from '../lib/chartTheme'
import { money } from '../lib/labels'
import { EmptyState } from './ui'

export type AgentCost = { agent_id: string; agent_name: string; number: number; executions: number; cost_usd: number }

const ROW = 26

/** Estimated AI cost per agent: a horizontal bar per agent, named, every row labelled. */
export default function CostByAgentChart({ rows }: { rows: AgentCost[] }) {
  if (rows.length === 0) return <EmptyState title="No agent activity in this period" />
  const total = rows.reduce((s, r) => s + (r.cost_usd || 0), 0)
  const runs = rows.reduce((s, r) => s + (r.executions || 0), 0)
  if (total === 0) {
    // Bars of zero width look like a broken chart; say what actually happened instead.
    return (
      <EmptyState
        title="No AI cost in this period"
        body={`${rows.length} agent${rows.length === 1 ? '' : 's'} ran ${runs} time${runs === 1 ? '' : 's'}, all estimated at $0.00, for example on a free or test AI provider.`}
      />
    )
  }
  const data = rows.map((r) => ({ ...r, label: AGENT_META[r.agent_id]?.short || r.agent_name }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * ROW + 40)}>
      <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16 }} barCategoryGap={6}>
        <CartesianGrid stroke={CHART.grid} horizontal={false} />
        <XAxis type="number" {...AXIS} tickFormatter={costTick} />
        <YAxis type="category" dataKey="label" {...AXIS} width={128} interval={0} />
        <Tooltip
          {...TOOLTIP}
          formatter={(v: number, _n, item) => [`${money(v)} · ${item.payload.executions} run${item.payload.executions === 1 ? '' : 's'}`, 'Est. cost']}
          labelFormatter={(label) => data.find((a) => a.label === label)?.agent_name || label}
        />
        <Bar name="Est. cost" dataKey="cost_usd" fill={CHART.accent} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
