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
    apiRequest<{ summary: Summary }>(`/organizations/${activeOrganizationId}/reports/summary`).then(
      (d) => setSummary(d.summary),
    )
    apiRequest<{ campaigns: Campaign[] }>(`/organizations/${activeOrganizationId}/campaigns`).then(
      (d) => setCampaigns(d.campaigns),
    )
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
        <div className="card">
          <h2>Workspace summary</h2>
          <table className="simple">
            <tbody>
              <tr>
                <td>Campaigns</td>
                <td>{summary.total_campaigns}</td>
              </tr>
              <tr>
                <td>Workflow runs completed</td>
                <td>
                  {summary.completed_workflow_runs} / {summary.total_workflow_runs}
                </td>
              </tr>
              <tr>
                <td>Estimated AI cost ({summary.cost_basis})</td>
                <td>${summary.estimated_ai_cost_usd.toFixed(4)}</td>
              </tr>
            </tbody>
          </table>
          <p className="muted">{summary.note}</p>
        </div>
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
