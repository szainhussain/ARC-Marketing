import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import type { BusinessProfile } from '../api/types'

const emptyProfile: Partial<BusinessProfile> = {
  business_name: '',
  website: '',
  industry: '',
  regions_served: '',
  business_type: 'b2c',
  products_services: '',
  target_audience: '',
  customer_problem: '',
  differentiators: '',
  primary_goal: '',
  tone_of_voice: '',
  preferred_phrases: '',
  prohibited_phrases: '',
  constraints: '',
}

export default function OnboardingPage() {
  const { activeOrganizationId } = useWorkspace()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<Partial<BusinessProfile>>(emptyProfile)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!activeOrganizationId) return
    let cancelled = false
    apiRequest<{ business_profile: BusinessProfile }>(
      `/organizations/${activeOrganizationId}/business-profile`,
    )
      .then((data) => {
        // Guards against React StrictMode's double effect invocation (and
        // any other duplicate in-flight request): without this, a late
        // response from an earlier, superseded fetch can land after the
        // user has already started editing and silently overwrite what
        // they typed with stale (often empty) data.
        if (!cancelled) setProfile(data.business_profile)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [activeOrganizationId])

  function field<K extends keyof BusinessProfile>(key: K) {
    return {
      id: key as string,
      value: (profile[key] as string) || '',
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
        setProfile((p) => ({ ...p, [key]: e.target.value })),
    }
  }

  async function save(markComplete: boolean) {
    if (!activeOrganizationId) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      await apiRequest(`/organizations/${activeOrganizationId}/business-profile`, {
        method: 'PATCH',
        body: { ...profile, mark_onboarding_completed: markComplete },
      })
      if (markComplete) {
        navigate('/app')
      } else {
        setMessage('Saved. You can come back and finish this later.')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save profile.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="page">Loading…</div>

  return (
    <div className="page">
      <h1>Tell us about your business</h1>
      <p className="muted">
        This is reused across every campaign. You can skip fields and finish later — but a
        workflow run will ask you to fill in anything that materially affects its output.
      </p>
      {error && <div className="banner error">{error}</div>}
      {message && <div className="banner success">{message}</div>}

      <div className="card">
        <h2>Business basics</h2>
        <div className="field">
          <label htmlFor="business_name">Business name</label>
          <input {...field('business_name')} />
        </div>
        <div className="field">
          <label htmlFor="website">Website (optional)</label>
          <input {...field('website')} />
        </div>
        <div className="field">
          <label htmlFor="industry">Industry</label>
          <input {...field('industry')} />
        </div>
        <div className="field">
          <label htmlFor="regions_served">Regions served</label>
          <input {...field('regions_served')} />
        </div>
        <div className="field">
          <label htmlFor="business_type">Business type</label>
          <select {...field('business_type')}>
            <option value="b2b">B2B</option>
            <option value="b2c">B2C</option>
            <option value="both">Both</option>
            <option value="nonprofit">Nonprofit / other</option>
          </select>
        </div>
      </div>

      <div className="card">
        <h2>Offer and audience</h2>
        <div className="field">
          <label htmlFor="products_services">Main products/services</label>
          <textarea {...field('products_services')} rows={2} />
        </div>
        <div className="field">
          <label htmlFor="target_audience">Best-fit audience / customer</label>
          <textarea {...field('target_audience')} rows={2} />
        </div>
        <div className="field">
          <label htmlFor="customer_problem">Customer problem solved</label>
          <textarea {...field('customer_problem')} rows={2} />
        </div>
        <div className="field">
          <label htmlFor="differentiators">Differentiators / proof points</label>
          <textarea {...field('differentiators')} rows={2} />
        </div>
        <div className="field">
          <label htmlFor="primary_goal">Primary campaign goal</label>
          <input {...field('primary_goal')} />
        </div>
      </div>

      <div className="card">
        <h2>Brand</h2>
        <div className="field">
          <label htmlFor="tone_of_voice">Tone of voice</label>
          <input {...field('tone_of_voice')} />
        </div>
        <div className="field">
          <label htmlFor="preferred_phrases">Preferred phrases</label>
          <input {...field('preferred_phrases')} />
        </div>
        <div className="field">
          <label htmlFor="prohibited_phrases">Prohibited phrases</label>
          <input {...field('prohibited_phrases')} />
        </div>
        <div className="field">
          <label htmlFor="constraints">Constraints / disclaimers</label>
          <textarea {...field('constraints')} rows={2} />
        </div>
      </div>

      <button className="secondary" onClick={() => save(false)} disabled={saving}>
        Save and finish later
      </button>{' '}
      <button onClick={() => save(true)} disabled={saving}>
        {saving ? 'Saving…' : 'Save and continue'}
      </button>
    </div>
  )
}
