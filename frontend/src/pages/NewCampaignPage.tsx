import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Campaign } from '../api/types'

export default function NewCampaignPage() {
  const { activeOrganizationId } = useWorkspace()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [objective, setObjective] = useState('')
  const [audience, setAudience] = useState('')
  const [channels, setChannels] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!activeOrganizationId) return
    setError(null)
    setFieldErrors({})
    setSubmitting(true)
    try {
      const data = await apiRequest<{ campaign: Campaign }>(
        `/organizations/${activeOrganizationId}/campaigns`,
        {
          method: 'POST',
          body: {
            name,
            objective,
            audience,
            channels,
            idempotency_key: `create-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          },
        },
      )
      navigate(`/app/campaigns/${data.campaign.id}`)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        const next: Record<string, string> = {}
        for (const d of err.details) next[d.field] = d.issue
        setFieldErrors(next)
      } else {
        setError('Could not create campaign.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <h1>New campaign brief</h1>
      {error && <div className="banner error">{error}</div>}
      <form onSubmit={handleSubmit} className="card">
        <div className="field">
          <label htmlFor="campaign_name">Campaign name</label>
          <input id="campaign_name" value={name} onChange={(e) => setName(e.target.value)} required />
          {fieldErrors.name && <span className="error">{fieldErrors.name}</span>}
        </div>
        <div className="field">
          <label htmlFor="objective">Objective</label>
          <textarea
            id="objective"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            rows={3}
            required
          />
          {fieldErrors.objective && <span className="error">{fieldErrors.objective}</span>}
        </div>
        <div className="field">
          <label htmlFor="audience">Audience (optional)</label>
          <input id="audience" value={audience} onChange={(e) => setAudience(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="channels">Channels (optional, comma separated)</label>
          <input id="channels" value={channels} onChange={(e) => setChannels(e.target.value)} />
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save draft'}
        </button>
      </form>
    </div>
  )
}
