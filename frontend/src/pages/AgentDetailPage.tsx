import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import type { AgentExecution, AgentInfo, Task } from '../api/types'
import { useWorkspace } from '../context/WorkspaceContext'
import { usePolling } from '../hooks/usePolling'
import { humanize, money, relativeTime, statusLabel } from '../lib/labels'

type AgentDetail = { agent: AgentInfo; recent_executions: AgentExecution[]; open_tasks: Task[] }

export default function AgentDetailPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const { activeOrganizationId: orgId } = useWorkspace()
  const [data, setData] = useState<AgentDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load(isCancelled: () => boolean = () => false) {
    if (!orgId || !agentId) return
    try {
      const d = await apiRequest<AgentDetail>(`/organizations/${orgId}/agents/${agentId}`)
      if (!isCancelled()) setData(d)
    } catch (err) {
      if (!isCancelled()) setError(err instanceof ApiError ? err.message : 'Could not load agent.')
    }
  }

  usePolling(load, [orgId, agentId], { intervalMs: 5000 })

  async function togglePause() {
    if (!data) return
    setBusy(true)
    setError(null)
    try {
      const verb = data.agent.settings.is_paused ? 'resume' : 'pause'
      await apiRequest(`/organizations/${orgId}/agents/${agentId}/${verb}`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change agent state.')
    } finally {
      setBusy(false)
    }
  }

  if (!data) {
    return (
      <div className="page">
        {error ? <div className="banner error">{error}</div> : <p className="muted">Loading…</p>}
      </div>
    )
  }

  const { agent } = data
  return (
    <div className="page">
      <p className="small">
        <Link to="/app/operations">← Operations</Link>
      </p>
      <div className="page-head">
        <div>
          <p className="eyebrow">
            Agent {String(agent.number).padStart(2, '0')} · v{agent.version}
          </p>
          <h1>{agent.name}</h1>
          <p className="muted">{agent.role}</p>
        </div>
        <div className="head-actions">
          <span className={`status-pill ${agent.status}`}>{statusLabel(agent.status)}</span>
          <button className="secondary" disabled={busy} onClick={togglePause}>
            {agent.settings.is_paused ? 'Resume agent' : 'Pause agent'}
          </button>
        </div>
      </div>
      {error && <div className="banner error">{error}</div>}

      <div className="kpi-grid">
        <div className="kpi-tile">
          <div className="kpi-label">Succeeded (30d)</div>
          <div className="kpi-value">{agent.stats_30d.succeeded}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Failed attempts (30d)</div>
          <div className="kpi-value">{agent.stats_30d.failed}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Open tasks</div>
          <div className="kpi-value">{data.open_tasks.length}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Est. AI cost (30d)</div>
          <div className="kpi-value">{money(agent.stats_30d.estimated_cost_usd)}</div>
          <div className="kpi-sub">estimate</div>
        </div>
      </div>

      <div className="two-col">
        <div className="card">
          <h2>Mandate</h2>
          <Spec label="Responsibilities" items={agent.responsibilities} />
          <Spec label="Produces" items={agent.outputs} />
          <Spec label="Quality bar" items={agent.kpis} />
          <Spec label="Escalates to a person" items={agent.escalates} />
        </div>
        <div className="card">
          <h2>Permissions & limits</h2>
          <Spec label="Waits for" items={agent.depends_on.map(humanize)} empty="Nothing — starts first" />
          <Spec label="May read output of" items={agent.reads.map(humanize)} empty="Only the campaign and brand profile" />
          <Spec label="Tools" items={agent.allowed_tools} />
          <Spec label="Automated checks" items={agent.evaluation_checks.map(humanize)} />
          <div className="deliverable-section">
            <div className="section-label">Budget & retries</div>
            <p className="small">
              Up to {money(agent.budget_policy.max_cost_per_task_usd)} estimated per task ·{' '}
              {agent.budget_policy.max_attempts} attempts max
            </p>
          </div>
          <div className="deliverable-section">
            <div className="section-label">External actions</div>
            <p className="small">
              {agent.approval_policy.external_actions === 'never_executable_spend_is_human_only'
                ? 'Never. Any spend change is a human-only decision.'
                : 'Drafts only. Anything leaving the workspace needs a person’s approval.'}
            </p>
          </div>
          <div className="deliverable-section">
            <div className="section-label">Integrations</div>
            {agent.allowed_integrations.length === 0 ? (
              <p className="small muted">None needed.</p>
            ) : (
              <ul className="deliverable-list">
                {agent.allowed_integrations.map((i) => (
                  <li key={i.name}>
                    {i.name} — <span className="muted">{humanize(i.status)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Recent executions</h2>
        {data.recent_executions.length === 0 ? (
          <p className="muted">This agent hasn't run yet.</p>
        ) : (
          <table className="simple">
            <thead>
              <tr>
                <th>When</th>
                <th>Attempt</th>
                <th>Result</th>
                <th>Model</th>
                <th>Duration</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_executions.map((e) => (
                <tr key={e.id}>
                  <td className="muted">{relativeTime(e.started_at)}</td>
                  <td>#{e.attempt_number}</td>
                  <td>
                    <span className={`status-pill ${e.status}`}>{statusLabel(e.status)}</span>
                  </td>
                  <td className="muted small">{e.model || '—'}</td>
                  <td className="muted small">{e.duration_ms != null ? `${(e.duration_ms / 1000).toFixed(1)}s` : '—'}</td>
                  <td className="small">
                    {e.error_summary ? (
                      <span className="text-danger">{truncate(e.error_summary)}</span>
                    ) : (
                      e.summary
                    )}
                    {e.evaluation.filter((c) => !c.passed).map((c) => (
                      <div key={c.check} className="text-warning">
                        ⚠ {c.detail}
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function Spec({ label, items, empty }: { label: string; items: string[]; empty?: string }) {
  return (
    <div className="deliverable-section">
      <div className="section-label">{label}</div>
      {items.length === 0 ? (
        <p className="small muted">{empty || '—'}</p>
      ) : (
        <ul className="deliverable-list">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function truncate(text: string, n = 160) {
  return text.length > n ? `${text.slice(0, n)}…` : text
}
