import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { ErrorState, Field, PageHeader } from '../components/ui'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Campaign } from '../api/types'

const FIELDS: { key: string; label: string; area?: boolean; type?: string; hint?: string; required?: boolean }[] = [
  { key: 'name', label: 'Campaign name', required: true },
  { key: 'objective', label: 'Objective', area: true, required: true, hint: 'What should this campaign achieve? Be specific — e.g. “500 trial sign-ups from UK hikers by June”.' },
  { key: 'audience', label: 'Audience', area: true, hint: 'Leave blank to use your brand profile’s audience.' },
  { key: 'offer', label: 'Offer', hint: 'Product, promotion or message to lead with.' },
  { key: 'channels', label: 'Channels', hint: 'Comma separated, e.g. Instagram, TikTok, Google Ads, email' },
  { key: 'geography', label: 'Geography' },
  { key: 'start_date', label: 'Start date', type: 'date' },
  { key: 'end_date', label: 'End date', type: 'date' },
  { key: 'budget_guidance', label: 'Budget guidance', hint: 'A range is fine. Agents recommend splits; you decide spend.' },
  { key: 'success_metrics', label: 'How you’ll judge success', area: true },
  { key: 'constraints', label: 'Constraints', area: true, hint: 'Claims to avoid, legal notes, dates to avoid…' },
]

export default function NewCampaignPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState<Record<string, string>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [key] = useState(() => `create-${Date.now()}-${Math.random().toString(36).slice(2)}`)

  async function submit(e: FormEvent, run: boolean) {
    e.preventDefault()
    if (!orgId) return
    const local: Record<string, string> = {}
    if (!form.name?.trim()) local.name = 'Required'
    if (!form.objective?.trim()) local.objective = 'Required'
    if (form.start_date && form.end_date && form.end_date < form.start_date) local.end_date = 'Must be on or after the start date'
    setErrors(local)
    if (Object.keys(local).length) return
    setError(null)
    setSubmitting(true)
    try {
      const data = await apiRequest<{ campaign: Campaign }>(`/organizations/${orgId}/campaigns`, {
        method: 'POST',
        body: { ...form, idempotency_key: key },
      })
      if (run) {
        await apiRequest(`/organizations/${orgId}/campaigns/${data.campaign.id}/runs`, {
          method: 'POST',
          idempotencyKey: `${key}-run`,
        })
      }
      navigate(`/app/campaigns/${data.campaign.id}${run ? '/workflow' : ''}`)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        setErrors(Object.fromEntries(err.details.map((d) => [d.field, d.issue])))
      } else setError('Could not create campaign.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page">
      <PageHeader
        crumbs={[{ label: 'Campaigns', to: '/app/campaigns' }, { label: 'New brief' }]}
        title={params.get('ask') ? 'Ask your marketing team' : 'New campaign brief'}
        description="Describe what you want. Your CMO agent turns it into strategy, and the rest of the department builds from there."
      />
      {error && <ErrorState message={error} />}
      <form className="card" onSubmit={(e) => submit(e, false)} noValidate>
        <div className="form-grid">
          {FIELDS.map((f) => (
            <Field key={f.key} id={`c-${f.key}`} label={`${f.label}${f.required ? ' *' : ''}`} hint={f.hint} error={errors[f.key]}>
              {f.area ? (
                <textarea id={`c-${f.key}`} rows={3} value={form[f.key] || ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              ) : (
                <input id={`c-${f.key}`} type={f.type || 'text'} value={form[f.key] || ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              )}
            </Field>
          ))}
        </div>
        <div className="head-actions">
          <button type="button" disabled={submitting} onClick={(e) => submit(e as unknown as FormEvent, true)}>
            {submitting ? 'Working…' : 'Save and run the department'}
          </button>
          <button type="submit" className="secondary" disabled={submitting}>
            Save draft
          </button>
        </div>
      </form>
    </div>
  )
}
