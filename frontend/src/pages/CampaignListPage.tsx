import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Campaign } from '../api/types'

export default function CampaignListPage() {
  const { activeOrganizationId } = useWorkspace()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!activeOrganizationId) return
    apiRequest<{ campaigns: Campaign[] }>(`/organizations/${activeOrganizationId}/campaigns`)
      .then((d) => setCampaigns(d.campaigns))
      .finally(() => setLoading(false))
  }, [activeOrganizationId])

  return (
    <div className="page">
      <h1>Campaigns</h1>
      <Link to="/app/campaigns/new" className="btn">
        New campaign
      </Link>
      <div className="card" style={{ marginTop: 16 }}>
        {loading ? (
          <p className="muted">Loading…</p>
        ) : campaigns.length === 0 ? (
          <p className="muted">No campaigns yet.</p>
        ) : (
          <table className="simple">
            <thead>
              <tr>
                <th>Name</th>
                <th>Objective</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/app/campaigns/${c.id}`}>{c.name}</Link>
                  </td>
                  <td>{c.objective}</td>
                  <td>
                    <span className={`status-pill ${c.status}`}>{c.status}</span>
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
