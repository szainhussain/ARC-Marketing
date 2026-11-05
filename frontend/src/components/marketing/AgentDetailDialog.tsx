import { AGENT_META, type PublicAgent } from '../../lib/agentMeta'
import { humanize } from '../../lib/labels'
import { Dialog } from '../ui'

const STATUS_LABEL: Record<string, string> = {
  manual_export_available: 'Available — manual export',
  available_after_approval: 'Available — publishes after your approval',
  planned: 'Planned — not built yet',
  not_connected: 'Not connected',
}

export default function AgentDetailDialog({
  agent,
  all,
  onClose,
}: {
  agent: PublicAgent | null
  all: PublicAgent[]
  onClose: () => void
}) {
  if (!agent) return <Dialog open={false} onClose={onClose} title="">{null}</Dialog>
  const meta = AGENT_META[agent.agent_id]
  const name = (id: string) => all.find((a) => a.agent_id === id)?.name || humanize(id)
  const collaborators = all.filter((a) => a.depends_on.includes(agent.agent_id)).map((a) => a.name)
  return (
    <Dialog open={!!agent} onClose={onClose} title={`${String(agent.number).padStart(2, '0')} · ${agent.name}`} wide>
      <p style={{ marginTop: 0 }}>{agent.role}</p>
      {meta && <p className="muted small">Example: {meta.example}</p>}
      <div className="form-grid">
        <Block title="What it does" items={agent.responsibilities} />
        <Block title="Produces" items={agent.outputs} />
        <Block title="Inputs (waits for)" items={agent.depends_on.length ? agent.depends_on.map(name) : ['The campaign brief and your brand profile']} />
        <Block title="Hands work to" items={collaborators.length ? collaborators : ['Final record for your team']} />
        <Block title="Quality checks" items={[...agent.kpis, ...agent.evaluation_checks.map(humanize)]} />
        <Block title="Asks a person when" items={agent.escalates} />
        <Block
          title="Tools & integrations"
          items={[
            'Structured AI generation (validated against a schema)',
            ...agent.allowed_integrations.map((i) => `${i.name}: ${STATUS_LABEL[i.status] || humanize(i.status)}`),
          ]}
        />
        <Block
          title="What it automates vs. what you decide"
          items={[
            'Automates: research, planning and drafting within its budget and retry limits.',
            agent.approval_policy.external_actions === 'never_executable_spend_is_human_only'
              ? 'You decide: every spend change. No agent can change ad spend.'
              : 'You decide: anything that leaves the workspace needs your approval.',
          ]}
        />
      </div>
      <p className="muted small mono" style={{ marginBottom: 0 }}>
        agent_id: {agent.agent_id} · version {agent.version} · output: {agent.task_type}
      </p>
    </Dialog>
  )
}

function Block({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="deliverable-section">
      <div className="section-label">{title}</div>
      <ul className="deliverable-list">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  )
}
