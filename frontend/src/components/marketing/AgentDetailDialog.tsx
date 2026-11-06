import { useState } from 'react'
import { AGENT_META, agentVideo, type PublicAgent } from '../../lib/agentMeta'
import { humanize } from '../../lib/labels'
import { Dialog, Tabs } from '../ui'
import AgentVideo from './AgentVideo'

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
  return (
    <Dialog open={!!agent} onClose={onClose} title={`${String(agent.number).padStart(2, '0')} · ${agent.name}`} wide>
      {/* keyed so each agent opens on the Read view */}
      <AgentDetailBody key={agent.agent_id} agent={agent} all={all} />
    </Dialog>
  )
}

function AgentDetailBody({ agent, all }: { agent: PublicAgent; all: PublicAgent[] }) {
  const [view, setView] = useState<'read' | 'watch'>('read')
  const hasVideo = !!agentVideo(agent.agent_id)
  const meta = AGENT_META[agent.agent_id]
  const name = (id: string) => all.find((a) => a.agent_id === id)?.name || humanize(id)
  const collaborators = all.filter((a) => a.depends_on.includes(agent.agent_id)).map((a) => a.name)
  return (
    <>
      <p style={{ marginTop: 0 }}>{agent.role}</p>
      {hasVideo && (
        <Tabs
          label="How to learn about this agent"
          value={view}
          onChange={setView}
          tabs={[
            { value: 'read', label: 'Read' },
            { value: 'watch', label: '▶ Watch (30s)' },
          ]}
        />
      )}
      {view === 'watch' && hasVideo ? (
        <AgentVideo agentId={agent.agent_id} title={agent.name} />
      ) : (
        <>
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
        </>
      )}
    </>
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
