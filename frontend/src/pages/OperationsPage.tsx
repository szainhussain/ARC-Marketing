import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import type { ActivityEvent, AgentInfo, OperationsSummary, Task } from '../api/types'
import WorkflowGraphPanel from '../components/WorkflowGraphPanel'
import AnimatedNumber from '../components/motion/AnimatedNumber'
import { useWorkspace } from '../context/WorkspaceContext'
import { usePolling } from '../hooks/usePolling'
import { humanize, money, relativeTime, statusLabel } from '../lib/labels'

export default function OperationsPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [summary, setSummary] = useState<OperationsSummary | null>(null)
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [openTasks, setOpenTasks] = useState<Task[]>([])
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  async function load(isCancelled: () => boolean = () => false) {
    if (!orgId) return
    try {
      const [s, a, t, e] = await Promise.all([
        apiRequest<OperationsSummary>(`/organizations/${orgId}/operations/summary`),
        apiRequest<{ agents: AgentInfo[] }>(`/organizations/${orgId}/agents`),
        apiRequest<{ tasks: Task[] }>(`/organizations/${orgId}/tasks?status=open`),
        apiRequest<{ events: ActivityEvent[] }>(`/organizations/${orgId}/activity?limit=15`),
      ])
      if (isCancelled()) return
      setSummary(s)
      setAgents(a.agents)
      setOpenTasks(t.tasks)
      setEvents(e.events)
    } catch (err) {
      if (!isCancelled()) setError(err instanceof ApiError ? err.message : 'Could not load operations.')
    }
  }

  usePolling(load, [orgId], { intervalMs: 4000 })

  async function act(key: string, fn: () => Promise<unknown>) {
    setBusy(key)
    setError(null)
    try {
      await fn()
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'That action failed.')
    } finally {
      setBusy(null)
    }
  }

  function toggleControl(field: 'automation_paused' | 'kill_switch_enabled', value: boolean) {
    return act(field, () =>
      apiRequest(`/organizations/${orgId}/operations/controls`, { method: 'PATCH', body: { [field]: value } }),
    )
  }

  function toggleAgent(agent: AgentInfo) {
    const verb = agent.settings.is_paused ? 'resume' : 'pause'
    return act(agent.agent_id, () =>
      apiRequest(`/organizations/${orgId}/agents/${agent.agent_id}/${verb}`, { method: 'POST' }),
    )
  }

  if (!summary) {
    return (
      <div className="page">
        <h1>Operations</h1>
        {error ? <div className="banner error">{error}</div> : <p className="muted">Loading…</p>}
      </div>
    )
  }

  const counts = summary.task_counts
  const running = counts.running || 0
  const queued = (counts.ready || 0) + (counts.retrying || 0) + (counts.waiting_for_dependency || 0)
  const failed = counts.failed || 0
  const blocked = counts.waiting_for_dependency || 0
  const retrying = counts.retrying || 0
  const working = agents.filter((a) => a.status === 'working').length
  const paused = agents.filter((a) => a.status === 'paused' || a.status === 'workspace_paused').length
  const successRate = summary.month_to_date.executions_succeeded + summary.month_to_date.executions_failed
    ? Math.round((summary.month_to_date.executions_succeeded / (summary.month_to_date.executions_succeeded + summary.month_to_date.executions_failed)) * 100)
    : null
  const latest = summary.latest_runs[0]

  return (
    <div className="page page-wide">
      <div className="page-head">
        <div>
          <h1>Marketing Operations Center</h1>
          <p className="muted">
            Your 12 agents, their task queue, and the controls that stop them. Agents only produce drafts —
            nothing leaves this workspace without a person's approval.
          </p>
        </div>
      </div>

      {error && <div className="banner error">{error}</div>}

      <div className="card controls-bar">
        <div className="control">
          <div>
            <div className="control-title">Automation</div>
            <div className="muted small">
              {summary.controls.automation_paused
                ? 'Paused — the worker will not start any new agent task.'
                : 'Running — agents pick up ready tasks automatically.'}
            </div>
          </div>
          <button
            className={summary.controls.automation_paused ? '' : 'secondary'}
            disabled={busy === 'automation_paused'}
            onClick={() => toggleControl('automation_paused', !summary.controls.automation_paused)}
          >
            {summary.controls.automation_paused ? 'Resume all agents' : 'Pause all agents'}
          </button>
        </div>
        <div className="control">
          <div>
            <div className="control-title">External-action kill switch</div>
            <div className="muted small">
              {summary.controls.kill_switch_enabled
                ? 'On — exports and handoffs are blocked.'
                : 'Off — approved deliverables can be exported for manual handoff.'}
            </div>
          </div>
          <button
            className={summary.controls.kill_switch_enabled ? '' : 'danger'}
            disabled={busy === 'kill_switch_enabled'}
            onClick={() => toggleControl('kill_switch_enabled', !summary.controls.kill_switch_enabled)}
          >
            {summary.controls.kill_switch_enabled ? 'Turn off kill switch' : 'Engage kill switch'}
          </button>
        </div>
      </div>

      <div className="kpi-grid">
        <Kpi label="Running now" value={running} sub="tasks being worked" />
        <Kpi label="In queue" value={queued} sub="ready, retrying or waiting" />
        <Kpi label="Failed" value={failed} sub="need a person to retry" to="/app/tasks?status=failed" />
        <Kpi label="Agents working" value={working} sub={`${12 - working - paused} idle · ${paused} paused`} />
        <Kpi label="Blocked" value={blocked} sub="waiting on another agent" />
        <Kpi label="Retry queue" value={retrying} sub="rate limits & timeouts" to="/app/tasks?status=retrying" />
        <Kpi label="Pending approvals" value={summary.pending_approvals} sub="in your inbox" to="/app/approvals" />
        <div className="kpi-tile">
          <div className="kpi-label">AI cost this month</div>
          <div className="kpi-value">{money(summary.month_to_date.estimated_ai_cost_usd)}</div>
          <div className="kpi-sub">estimate, not an invoice</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Execution success (month)</div>
          <div className="kpi-value">{successRate == null ? '—' : `${successRate}%`}</div>
          <div className="kpi-sub">
            <Link to="/app/settings/automation">Budgets & concurrency →</Link>
          </div>
        </div>
      </div>

      {latest && (
        <div className="card">
          <div className="card-head">
            <h2>
              Latest run{latest.campaign_name ? ` · ${latest.campaign_name}` : ''}{' '}
              <span className={`status-pill ${latest.status}`}>{statusLabel(latest.status)}</span>
            </h2>
            <Link to={`/app/campaigns/${latest.campaign_id}`}>Open campaign →</Link>
          </div>
          {latest.error_summary && <div className="banner warning">{latest.error_summary}</div>}
          <WorkflowGraphPanel tasks={latest.tasks} orgId={orgId as string} />
        </div>
      )}

      <h2 className="section-title">Agents</h2>
      <div className="agent-grid">
        {agents.map((agent) => (
          <div key={agent.agent_id} className={`card agent-card ${agent.status}`}>
            <div className="agent-card-head">
              <span className="agent-num">{String(agent.number).padStart(2, '0')}</span>
              <span className={`status-pill ${agent.status}`}>{statusLabel(agent.status)}</span>
            </div>
            <Link to={`/app/operations/agents/${agent.agent_id}`} className="agent-name">
              {agent.name}
            </Link>
            <p className="muted small agent-role">{agent.role}</p>
            <div className="agent-stats small">
              <span>{agent.stats_30d.succeeded} done</span>
              <span>{agent.stats_30d.failed} failed</span>
              <span>{agent.stats_30d.open_tasks || 0} open</span>
              <span>{money(agent.stats_30d.estimated_cost_usd)}</span>
            </div>
            <button className="secondary small-btn" disabled={busy === agent.agent_id} onClick={() => toggleAgent(agent)}>
              {agent.settings.is_paused ? 'Resume agent' : 'Pause agent'}
            </button>
          </div>
        ))}
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-head">
            <h2>Open tasks</h2>
            <Link to="/app/tasks">All tasks →</Link>
          </div>
          {openTasks.length === 0 ? (
            <p className="muted">No open tasks. Start a campaign run to put the department to work.</p>
          ) : (
            <table className="simple">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Campaign</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {openTasks.slice(0, 12).map((t) => (
                  <tr key={t.id}>
                    <td>{t.agent_name}</td>
                    <td className="muted">{t.campaign_name}</td>
                    <td>
                      <span className={`status-pill ${t.status}`}>{statusLabel(t.status)}</span>
                      {t.status === 'retrying' && t.next_attempt_at && (
                        <span className="muted small"> {relativeTime(t.next_attempt_at)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="card">
          <h2>Activity</h2>
          {events.length === 0 ? (
            <p className="muted">No activity yet.</p>
          ) : (
            <ul className="activity-feed">
              {events.map((ev) => (
                <li key={ev.id}>
                  <span>{humanize(ev.action.replace(/\./g, ' '))}</span>
                  <span className="muted small">{relativeTime(ev.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function Kpi({ label, value, sub, to }: { label: string; value: number; sub: string; to?: string }) {
  const body = (
    <div className="kpi-tile">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        <AnimatedNumber value={value} />
      </div>
      <div className="kpi-sub">{sub}</div>
    </div>
  )
  return to ? (
    <Link to={to} className="kpi-link">
      {body}
    </Link>
  ) : (
    body
  )
}
