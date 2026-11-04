import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import type { Task } from '../api/types'
import { useWorkspace } from '../context/WorkspaceContext'
import { usePolling } from '../hooks/usePolling'
import { relativeTime, statusLabel } from '../lib/labels'

const FILTERS = [
  { value: 'open', label: 'Open' },
  { value: 'running', label: 'Running' },
  { value: 'retrying', label: 'Retrying' },
  { value: 'failed', label: 'Failed' },
  { value: 'succeeded', label: 'Succeeded' },
  { value: '', label: 'All' },
]

export default function TasksPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const [params] = useSearchParams()
  const [filter, setFilter] = useState(params.get('status') || 'open')
  const [q, setQ] = useState('')
  const [tasks, setTasks] = useState<Task[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  async function load(isCancelled: () => boolean = () => false) {
    if (!orgId) return
    try {
      const qs = filter ? `?status=${filter}` : ''
      const d = await apiRequest<{ tasks: Task[] }>(`/organizations/${orgId}/tasks${qs}`)
      if (!isCancelled()) setTasks(d.tasks)
    } catch (err) {
      if (!isCancelled()) setError(err instanceof ApiError ? err.message : 'Could not load tasks.')
    }
  }

  usePolling(load, [orgId, filter], { intervalMs: 4000 })

  async function act(task: Task, verb: 'retry' | 'cancel') {
    setBusy(task.id)
    setError(null)
    try {
      await apiRequest(`/organizations/${orgId}/tasks/${task.id}/${verb}`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Could not ${verb} task.`)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="page page-wide">
      <h1>Task queue</h1>
      <p className="muted">
        Every unit of agent work. Tasks wait for their dependencies, retry automatically on rate limits and
        timeouts, and stop for a person when they can't proceed.
      </p>
      {error && <div className="banner error">{error}</div>}

      <div className="filter-row" role="tablist" aria-label="Filter tasks by status">
        {FILTERS.map((f) => (
          <button
            key={f.value || 'all'}
            role="tab"
            aria-selected={filter === f.value}
            className={filter === f.value ? 'chip active' : 'chip'}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="filter-bar">
        <div className="search-field">
          <label htmlFor="task-search" className="sr-only">Search tasks</label>
          <input id="task-search" type="search" placeholder="Search by agent or campaign" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>
      <div className="card">
        {tasks === null ? (
          <p className="muted">Loading…</p>
        ) : tasks.length === 0 ? (
          <p className="muted">No tasks match this filter.</p>
        ) : (
          <table className="simple">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Campaign</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Note</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {tasks.filter((t) => !q || `${t.agent_name} ${t.campaign_name}`.toLowerCase().includes(q.toLowerCase())).map((t) => (
                <tr key={t.id}>
                  <td>
                    <Link to={`/app/operations/agents/${t.agent_id}`}>{t.agent_name}</Link>
                  </td>
                  <td>
                    <Link to={`/app/campaigns/${t.campaign_id}`} className="muted">
                      {t.campaign_name}
                    </Link>
                  </td>
                  <td>
                    <span className={`status-pill ${t.status}`}>{statusLabel(t.status)}</span>
                  </td>
                  <td className="muted">
                    {t.attempt_count}/{t.max_attempts}
                  </td>
                  <td className="small muted note-cell">
                    {t.status === 'retrying' && t.next_attempt_at
                      ? `Next try ${relativeTime(t.next_attempt_at)}. `
                      : ''}
                    {t.error_summary}
                  </td>
                  <td className="nowrap">
                    {t.status === 'failed' && (
                      <button className="small-btn" disabled={busy === t.id} onClick={() => act(t, 'retry')}>
                        Retry
                      </button>
                    )}
                    {['ready', 'retrying', 'waiting_for_dependency', 'running'].includes(t.status) && (
                      <button
                        className="secondary small-btn"
                        disabled={busy === t.id}
                        onClick={() => act(t, 'cancel')}
                      >
                        Cancel
                      </button>
                    )}
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
