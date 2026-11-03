import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Campaign } from '../api/types'

type Summary = {
  total_campaigns: number
  total_workflow_runs: number
  completed_workflow_runs: number
  estimated_ai_cost_usd: number
  cost_basis: string
  note: string
}

export default function DashboardPage() {
  const { activeOrganizationId } = useWorkspace()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])

  useEffect(() => {
    if (!activeOrganizationId) return
    let cancelled = false
    apiRequest<{ summary: Summary }>(`/organizations/${activeOrganizationId}/reports/summary`).then(
      (d) => {
        if (!cancelled) setSummary(d.summary)
      },
    )
    apiRequest<{ campaigns: Campaign[] }>(`/organizations/${activeOrganizationId}/campaigns`).then(
      (d) => {
        if (!cancelled) setCampaigns(d.campaigns)
      },
    )
    return () => {
      cancelled = true
    }
  }, [activeOrganizationId])

  if (!activeOrganizationId) {
    return (
      <div className="page">
        <div className="banner warning">
          No workspace selected yet. <Link to="/create-workspace">Create one</Link>.
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <h1>Overview</h1>

      {summary && (
        <>
          <div className="kpi-grid">
            <div className="kpi-tile">
              <div className="kpi-label">Campaigns</div>
              <div className="kpi-value">{summary.total_campaigns}</div>
            </div>
            <div className="kpi-tile">
              <div className="kpi-label">Workflow runs</div>
              <div className="kpi-value">
                {summary.completed_workflow_runs}
                <span style={{ fontSize: '1rem', color: 'var(--color-muted-fg)', fontWeight: 600 }}>
                  {' '}
                  / {summary.total_workflow_runs}
                </span>
              </div>
              <div className="kpi-sub">completed</div>
            </div>
            <div className="kpi-tile">
              <div className="kpi-label">Estimated AI cost</div>
              <div className="kpi-value">${summary.estimated_ai_cost_usd.toFixed(4)}</div>
              <div className="kpi-sub">{summary.cost_basis}</div>
            </div>
          </div>
          <p className="muted" style={{ marginTop: -6, marginBottom: 20 }}>
            {summary.note}
          </p>
        </>
      )}

      <div className="card">
        <h2>Recent campaigns</h2>
        {campaigns.length === 0 ? (
          <p className="muted">
            No campaigns yet. <Link to="/app/campaigns/new">Create your first campaign</Link>.
          </p>
        ) : (
          <table className="simple">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.slice(0, 5).map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/app/campaigns/${c.id}`}>{c.name}</Link>
                  </td>
                  <td>
                    <span className={`status-pill ${c.status}`}>{c.status}</span>
                  </td>
                  <td>{new Date(c.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
