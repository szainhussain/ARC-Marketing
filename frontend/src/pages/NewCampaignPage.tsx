import { useState, type FormEvent } from 'react'
import { SEGMENTS } from '../lib/segments'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { ErrorState, Field, PageHeader } from '../components/ui'
import { useWorkspace } from '../context/WorkspaceContext'
import type { Campaign } from '../api/types'

const FIELDS: { key: string; label: string; area?: boolean; type?: string; hint?: string; required?: boolean }[] = [
  { key: 'name', label: 'Campaign name', required: true },
  { key: 'objective', label: 'Objective', area: true, required: true, hint: 'What should this campaign achieve? Be specific, e.g. “500 trial sign-ups from UK hikers by June”.' },
  { key: 'audience', label: 'Audience', area: true, hint: 'Leave blank to use your brand profile’s audience.' },
  { key: 'offer', label: 'Offer', hint: 'Product, promotion or message to lead with.' },
  { key: 'channels', label: 'Channels', hint: 'Comma separated, e.g. Instagram, TikTok, Google Ads, email' },
  { key: 'geography', label: 'Geography' },
  { key: 'start_date', label: 'Start date', type: 'date' },
  { key: 'end_date', label: 'End date', type: 'date' },
  { key: 'budget_guidance', label: 'Budget guidance', hint: 'A range is fine. Agents recommend splits; you decide spend.' },
  { key: 'success_metrics', label: 'How you’ll judge success', area: true },
  { key: 'constraints', label: 'Constraints', area: true, hint: 'Claims to avoid, legal notes, dates to avoid…' },
  { key: 'research_urls', label: 'Pages to research (optional)', area: true, hint: 'Up to 5 public links, one per line, competitor sites, review pages, market reports. Your research agent reads them (sites that block automated reading are skipped) and cites them.' },
]

// Starting points; every field stays editable and nothing is sent until saved.
// Playbooks for the business types ARC serves first come before the generic ones.
const TEMPLATES: { id: string; label: string; values: Record<string, string> }[] = [
  ...SEGMENTS.map((s) => ({ id: `playbook-${s.key}`, label: s.label, values: { ...s.playbook } })),
  { id: 'launch', label: 'Product launch', values: { name: 'Product launch', objective: 'Launch [product] and reach [number] sign-ups or sales in the first [weeks] weeks.', offer: 'Launch offer or early-access price', channels: 'Instagram, LinkedIn, email, Google Ads', success_metrics: 'Sign-ups or sales, cost per acquisition, launch-week reach' } },
  { id: 'monthly', label: 'Monthly always-on', values: { name: 'Monthly marketing: [month]', objective: 'Keep a steady flow of enquiries this month with consistent posting and one featured offer.', channels: 'Instagram, Facebook, Google Business Profile', success_metrics: 'Enquiries or bookings, posting consistency, engagement rate' } },
  { id: 'promo', label: 'Seasonal promotion', values: { name: 'Seasonal promotion', objective: 'Drive [revenue/orders] during [season or event] with a time-limited offer.', offer: '[Discount or bundle] until [end date]', channels: 'Instagram, email, Meta ads', success_metrics: 'Orders, revenue, return on ad spend', constraints: 'State the end date clearly; no misleading urgency.' } },
  { id: 'leads', label: 'B2B lead generation', values: { name: 'Lead generation', objective: 'Generate [number] qualified leads from [segment] this quarter.', offer: 'Free consultation, demo or guide', channels: 'LinkedIn, email, website', success_metrics: 'Qualified leads, cost per lead, meetings booked' } },
  { id: 'event', label: 'Event or webinar', values: { name: 'Event promotion', objective: 'Get [number] registrations for [event] on [date].', channels: 'LinkedIn, email, Instagram', success_metrics: 'Registrations, attendance rate, follow-up meetings' } },
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
      <div className="template-row" role="group" aria-label="Start from a template">
        <span className="muted small">Start from a template:</span>
        {TEMPLATES.map((t) => (
          <button
            key={t.id}
            type="button"
            className="chip"
            onClick={() => setForm((f) => ({ ...t.values, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v.trim())) }))}
          >
            {t.label}
          </button>
        ))}
      </div>
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
