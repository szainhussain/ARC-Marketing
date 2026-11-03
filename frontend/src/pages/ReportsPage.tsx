import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'

type UsageRow = {
  id: string
  provider: string | null
  model: string | null
  input_tokens: number
  output_tokens: number
  estimated_cost_usd: number
  is_actual: boolean
  created_at: string
}

export default function ReportsPage() {
  const { activeOrganizationId } = useWorkspace()
  const [usage, setUsage] = useState<UsageRow[]>([])

  useEffect(() => {
    if (!activeOrganizationId) return
    apiRequest<{ usage: UsageRow[] }>(`/organizations/${activeOrganizationId}/usage`).then((d) =>
      setUsage(d.usage),
    )
  }, [activeOrganizationId])

  return (
    <div className="page">
      <h1>Reports &amp; usage</h1>
      <div className="card">
        <h2>AI usage (estimates)</h2>
        {usage.length === 0 ? (
          <p className="muted">No usage recorded yet.</p>
        ) : (
          <table className="simple">
            <thead>
              <tr>
                <th>When</th>
                <th>Provider / model</th>
                <th>Tokens (in/out)</th>
                <th>Estimated cost</th>
              </tr>
            </thead>
            <tbody>
              {usage.map((u) => (
                <tr key={u.id}>
                  <td>{new Date(u.created_at).toLocaleString()}</td>
                  <td>
                    {u.provider} / {u.model}
                  </td>
                  <td>
                    {u.input_tokens} / {u.output_tokens}
                  </td>
                  <td>${u.estimated_cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
