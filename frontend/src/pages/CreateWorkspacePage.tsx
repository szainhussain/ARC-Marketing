import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Organization } from '../api/types'

export default function CreateWorkspacePage() {
  const { refresh } = useAuth()
  const { setActiveOrganizationId } = useWorkspace()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const data = await apiRequest<{ organization: Organization }>('/organizations', {
        method: 'POST',
        body: { name },
      })
      await refresh()
      setActiveOrganizationId(data.organization.id)
      navigate('/app/onboarding')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create workspace.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-narrow">
      <h1>Create your workspace</h1>
      <p className="muted">This is your organization. You can invite teammates later.</p>
      {error && <div className="banner error">{error}</div>}
      <form onSubmit={handleSubmit} className="card">
        <div className="field">
          <label htmlFor="workspace_name">Business or workspace name</label>
          <input
            id="workspace_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating…' : 'Create workspace'}
        </button>
      </form>
    </div>
  )
}
