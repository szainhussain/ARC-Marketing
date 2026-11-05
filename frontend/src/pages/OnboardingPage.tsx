import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check, Globe } from 'lucide-react'
import { apiRequest, ApiError } from '../api/client'
import { ErrorState, Field, PageHeader, PageSkeleton, useToast } from '../components/ui'
import { useWorkspace } from '../context/WorkspaceContext'

type Profile = Record<string, string | number | boolean | null | string[]>
type ImportResult = {
  suggested: Record<string, string | null>
  found: { title: string | null; headings: string[]; paragraphs: string[] }
  source_url: string
}

const FIELD_LABELS: Record<string, string> = {
  business_name: 'Business name',
  website: 'Website',
  business_description: 'What the business does',
  language: 'Content language',
}

function WebsiteImport({ orgId, profile, onApply }: { orgId: string; profile: Profile; onApply: (patch: Profile) => void }) {
  const [url, setUrl] = useState(String(profile.website || ''))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ filled: string[]; found: ImportResult['found'] } | null>(null)

  async function run(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const r = await apiRequest<ImportResult>(`/organizations/${orgId}/business-profile/import-website`, { method: 'POST', body: { url } })
      const patch: Profile = {}
      const filled: string[] = []
      for (const [k, v] of Object.entries(r.suggested)) {
        if (v && !String(profile[k] ?? '').trim()) {
          patch[k] = v
          filled.push(FIELD_LABELS[k] || k)
        }
      }
      onApply(patch)
      setResult({ filled, found: r.found })
    } catch (err) {
      setError(err instanceof ApiError ? err.details[0]?.issue || err.message : 'Could not read that website.')
    } finally {
      setBusy(false)
    }
  }

  function append(key: string, text: string) {
    const current = String(profile[key] ?? '').trim()
    if (current.includes(text)) return
    onApply({ [key]: current ? `${current}
${text}` : text })
  }

  return (
    <div className="card import-card">
      <form onSubmit={run} className="import-row">
        <Globe size={18} aria-hidden="true" className="import-icon" />
        <div style={{ flex: 1, minWidth: 220 }}>
          <label htmlFor="import-url" className="import-label">
            Import from your website
          </label>
          <input id="import-url" type="text" inputMode="url" placeholder="yourbusiness.com" value={url} onChange={(e) => setUrl(e.target.value)} />
        </div>
        <button type="submit" disabled={busy || !url.trim()}>
          {busy ? 'Reading…' : 'Import'}
        </button>
      </form>
      <p className="muted small" style={{ margin: '8px 0 0' }}>
        ARC reads your public homepage once and fills in empty fields. Nothing is saved until you click Save.
      </p>
      {error && (
        <div className="banner error" role="alert" style={{ marginTop: 12, marginBottom: 0 }}>
          {error}
        </div>
      )}
      {result && (
        <div className="import-result" aria-live="polite">
          <p className="small" style={{ margin: '12px 0 8px' }}>
            {result.filled.length ? (
              <>
                <Check size={14} aria-hidden="true" style={{ color: 'var(--color-success)' }} /> Filled in: {result.filled.join(', ')}.
              </>
            ) : (
              'Your fields were already filled in, so nothing was changed.'
            )}
          </p>
          {(result.found.headings.length > 0 || result.found.paragraphs.length > 0) && (
            <>
              <p className="muted small" style={{ margin: '0 0 6px' }}>
                Also found on your site — add anything useful:
              </p>
              <ul className="import-found">
                {[...result.found.headings, ...result.found.paragraphs].map((t) => (
                  <li key={t}>
                    <span>{t}</span>
                    <span className="import-actions">
                      <button type="button" className="link-btn small" onClick={() => append('products_services', t)}>
                        + Products
                      </button>
                      <button type="button" className="link-btn small" onClick={() => append('differentiators', t)}>
                        + Differentiators
                      </button>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  )
}

type FieldDef = { key: string; label: string; type?: 'text' | 'textarea' | 'select' | 'url'; options?: [string, string][]; hint?: string; required?: boolean }

const SECTIONS: { title: string; description: string; fields: FieldDef[] }[] = [
  {
    title: 'Business',
    description: 'The basics every agent works from.',
    fields: [
      { key: 'business_name', label: 'Business name', required: true },
      { key: 'business_description', label: 'What the business does', type: 'textarea' },
      { key: 'industry', label: 'Industry', required: true },
      { key: 'website', label: 'Website', type: 'url', hint: 'Used as context. ARC only reads it when you click Import.' },
      { key: 'business_type', label: 'Business model', type: 'select', options: [['b2c', 'B2C'], ['b2b', 'B2B'], ['both', 'Both'], ['nonprofit', 'Nonprofit'], ['other', 'Other']] },
      { key: 'regions_served', label: 'Countries and markets' },
    ],
  },
  {
    title: 'Offer & audience',
    description: 'Who you serve and why they choose you.',
    fields: [
      { key: 'products_services', label: 'Main products/services', type: 'textarea', required: true },
      { key: 'target_audience', label: 'Best-fit audience / customer', type: 'textarea', required: true, hint: 'Ideal customer profiles and segments.' },
      { key: 'customer_problem', label: 'Problem you solve', type: 'textarea' },
      { key: 'differentiators', label: 'Value proposition & differentiators', type: 'textarea' },
      { key: 'competitors', label: 'Competitors', type: 'textarea', hint: 'Names only; agents won\'t invent facts about them.' },
    ],
  },
  {
    title: 'Brand voice',
    description: 'How you sound — and what you never say.',
    fields: [
      { key: 'tone_of_voice', label: 'Tone of voice', type: 'textarea' },
      { key: 'preferred_phrases', label: 'Preferred phrases / messaging guidelines', type: 'textarea' },
      { key: 'prohibited_phrases', label: 'Prohibited phrases', type: 'textarea', hint: 'Comma or line separated. Every agent output is checked against these in code.' },
      { key: 'constraints', label: 'Legal / compliance constraints', type: 'textarea' },
    ],
  },
  {
    title: 'Goals & channels',
    description: 'What success looks like and where you market.',
    fields: [
      { key: 'primary_goal', label: 'Primary campaign goal', required: true },
      { key: 'channels', label: 'Channels you use', hint: 'e.g. Instagram, TikTok, Google Ads, email' },
      { key: 'budget_range', label: 'Typical monthly marketing budget', type: 'select', options: [['', 'Prefer not to say'], ['<1k', 'Under $1k'], ['1k-5k', '$1k–5k'], ['5k-20k', '$5k–20k'], ['20k+', '$20k+']] },
      { key: 'existing_systems', label: 'Existing marketing systems', type: 'textarea', hint: 'CRM, analytics, email tools…' },
      { key: 'reporting_expectations', label: 'Reporting expectations', type: 'textarea' },
    ],
  },
  {
    title: 'Operating preferences',
    description: 'Language, time zone and how much autonomy you want.',
    fields: [
      { key: 'timezone', label: 'Time zone', hint: 'e.g. Europe/London' },
      { key: 'language', label: 'Content language', hint: 'e.g. English (UK)' },
    ],
  },
]

export function ProfileForm({ mode }: { mode: 'wizard' | 'edit' }) {
  const { activeOrganizationId: orgId } = useWorkspace()
  const navigate = useNavigate()
  const toast = useToast()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [step, setStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!orgId) return
    let cancelled = false
    apiRequest<{ business_profile: Profile }>(`/organizations/${orgId}/business-profile`)
      .then((d) => {
        if (cancelled) return
        setProfile(d.business_profile)
        if (mode === 'wizard') setStep(Math.min(Number(d.business_profile.onboarding_step) || 0, SECTIONS.length))
      })
      .catch((err) => !cancelled && setError(err instanceof ApiError ? err.message : 'Could not load profile.'))
    return () => {
      cancelled = true
    }
  }, [orgId, mode])

  if (error && !profile) return <ErrorState message={error} />
  if (!profile) return <PageSkeleton />

  const sections = mode === 'wizard' ? (step < SECTIONS.length ? [SECTIONS[step]] : []) : SECTIONS

  async function save(nextStep?: number, complete = false) {
    if (!orgId || !profile) return
    const fields = sections.flatMap((s) => s.fields)
    const local: Record<string, string> = {}
    if (complete || mode === 'edit') {
      for (const f of fields) if (f.required && !String(profile[f.key] || '').trim()) local[f.key] = 'Required'
    }
    if (String(profile.website || '') && !/^https?:\/\//.test(String(profile.website))) local.website = 'Start with https://'
    setErrors(local)
    if (Object.keys(local).length) return
    setSaving(true)
    setError(null)
    try {
      const body: Record<string, unknown> = {}
      for (const f of SECTIONS.flatMap((s) => s.fields)) body[f.key] = profile[f.key] ?? ''
      if (nextStep != null) body.onboarding_step = nextStep
      if (complete) body.mark_onboarding_completed = true
      const r = await apiRequest<{ business_profile: Profile }>(`/organizations/${orgId}/business-profile`, { method: 'PATCH', body })
      setProfile(r.business_profile)
      if (nextStep != null) setStep(nextStep)
      if (complete) {
        toast({ title: 'Profile saved. Your team is ready.', tone: 'success' })
        navigate('/app/campaigns/new')
      } else if (mode === 'edit') toast({ title: 'Brand profile saved', tone: 'success' })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save.')
    } finally {
      setSaving(false)
    }
  }

  const input = (f: FieldDef) => {
    const common = {
      id: `bp-${f.key}`,
      value: String(profile[f.key] ?? ''),
      onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
        setProfile((p) => ({ ...(p as Profile), [f.key]: e.target.value })),
    }
    if (f.type === 'textarea') return <textarea rows={3} {...common} />
    if (f.type === 'select')
      return (
        <select {...common}>
          {f.options?.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      )
    return <input type={f.type === 'url' ? 'url' : 'text'} {...common} />
  }

  return (
    <>
      {mode === 'wizard' && (
        <div className="wizard-steps" aria-label="Onboarding steps">
          {[...SECTIONS.map((s) => s.title), 'Automation & review'].map((t, i) => (
            <button key={t} className={i === step ? 'chip active' : 'chip'} onClick={() => setStep(i)} aria-current={i === step ? 'step' : undefined}>
              {i < step && <Check size={13} aria-hidden="true" />} {i + 1}. {t}
            </button>
          ))}
        </div>
      )}
      {error && <ErrorState message={error} />}
      {orgId && (mode === 'edit' || step === 0) && (
        <WebsiteImport orgId={orgId} profile={profile} onApply={(patch) => setProfile((p) => ({ ...(p as Profile), ...patch }))} />
      )}
      {sections.map((s) => (
        <div key={s.title} className="card">
          <h2>{s.title}</h2>
          <p className="muted small" style={{ marginTop: -8 }}>{s.description}</p>
          <div className="form-grid">
            {s.fields.map((f) => (
              <Field key={f.key} id={`bp-${f.key}`} label={`${f.label}${f.required ? ' *' : ''}`} hint={f.hint} error={errors[f.key]}>
                {input(f)}
              </Field>
            ))}
          </div>
        </div>
      ))}
      {mode === 'wizard' && step >= SECTIONS.length && (
        <div className="card">
          <h2>Automation & review</h2>
          <p className="muted">
            By default your agents research, plan and draft on their own; anything that leaves the workspace needs your
            approval, and no agent can ever change ad spend. You can tighten this so runs wait for an approver before
            starting, set budgets and concurrency, or pause everything at any time.
          </p>
          <p>
            <Link to="/app/settings/automation">Review automation policies →</Link>
          </p>
          {(profile.completeness_warnings as string[])?.length > 0 && (
            <div className="banner warning">
              Still missing: {(profile.completeness_warnings as string[]).map((w) => w.replace(/_/g, ' ')).join(', ')}. Agents
              won't start until these are filled in.
            </div>
          )}
        </div>
      )}
      <div className="head-actions">
        {mode === 'wizard' ? (
          <>
            {step > 0 && <button className="secondary" onClick={() => setStep(step - 1)}>Back</button>}
            {step < SECTIONS.length ? (
              <button disabled={saving} onClick={() => save(step + 1)}>{saving ? 'Saving…' : 'Save and continue'}</button>
            ) : (
              <button disabled={saving} onClick={() => save(SECTIONS.length, true)}>Finish and create a campaign</button>
            )}
            <span className="muted small">Progress is saved at every step.</span>
          </>
        ) : (
          <button disabled={saving} onClick={() => save()}>{saving ? 'Saving…' : 'Save brand profile'}</button>
        )}
      </div>
    </>
  )
}

export default function OnboardingPage() {
  return (
    <div className="page">
      <PageHeader eyebrow="Setup" title="Set up your marketing department" description="Tell your agents about the business. You can change any of this later in Brand profile." />
      <ProfileForm mode="wizard" />
    </div>
  )
}

export function BrandPage() {
  return (
    <div className="page">
      <PageHeader title="Brand profile" description="Every agent reads this. Prohibited phrases are enforced in code on every output."
        actions={<Link to="/app/knowledge" className="btn secondary">Knowledge library</Link>} />
      <ProfileForm mode="edit" />
    </div>
  )
}
