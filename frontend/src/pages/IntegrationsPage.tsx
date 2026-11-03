import { useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Integration } from '../api/types'

export default function IntegrationsPage() {
  const { activeOrganizationId } = useWorkspace()
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [note, setNote] = useState('')

  useEffect(() => {
    if (!activeOrganizationId) return
    apiRequest<{ integrations: Integration[]; note: string }>(
      `/organizations/${activeOrganizationId}/integrations`,
    ).then((d) => {
      setIntegrations(d.integrations)
      setNote(d.note)
    })
  }, [activeOrganizationId])

  return (
    <div className="page">
      <h1>Integrations</h1>
      <div className="card">
        {integrations.length === 0 ? (
          <p className="muted">{note}</p>
        ) : (
          <ul>
            {integrations.map((i) => (
              <li key={i.id}>
                {i.provider} — {i.state}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
