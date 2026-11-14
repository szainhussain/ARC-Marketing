import { useState } from 'react'
import { ApiError, apiRequest } from '../../api/client'
import { Field } from '../../components/ui'
import { SEGMENTS } from '../../lib/segments'
import { usePageMeta } from '../../lib/seo'
import { CtaPair } from './GrowthPages'
import { SectionHead } from './sections'

type Finding = { area: string; check: string; passed: boolean; impact: string; effort: string; found: string; fix: string | null }
type Audit = {
  url: string
  checks_passed: number
  checks_total: number
  areas: { area: string; passed: number; total: number }[]
  priorities: Finding[]
  passed: Finding[]
  method: string
}
type Speed = { performance_score: number; metrics: { label: string; value: string }[]; source: string }

const LEVEL: Record<string, string> = { high: 'High', medium: 'Medium', low: 'Low' }

export default function GrowthAuditPage() {
  usePageMeta('Free Growth Audit', 'Enter your website and get a prioritised list of what is costing you enquiries: search, conversion, lead capture and tracking. Free, no account needed.')
  const [url, setUrl] = useState('')
  const [industry, setIndustry] = useState('')
  const [goal, setGoal] = useState('')
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [audit, setAudit] = useState<Audit | null>(null)
  const [speed, setSpeed] = useState<Speed | null>(null)
  const [speedNote, setSpeedNote] = useState('')

  const segment = SEGMENTS.find((s) => s.industry === industry)

  async function run(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setAudit(null)
    setSpeed(null)
    setSpeedNote('')
    try {
      const data = await apiRequest<{ audit: Audit }>('/public/growth-audit', { method: 'POST', body: { url, industry, goal, email } })
      setAudit(data.audit)
      // The speed test is slower and optional, so it never holds up the report.
      apiRequest<{ speed: Speed | null; unavailable?: string }>('/public/growth-audit/speed', { method: 'POST', body: { url } })
        .then((s) => (s.speed ? setSpeed(s.speed) : setSpeedNote(s.unavailable || 'Speed test unavailable.')))
        .catch(() => setSpeedNote('The speed test could not be run just now.'))
    } catch (err) {
      const detail = err instanceof ApiError && err.details[0]?.issue
      setError(detail || (err instanceof Error ? err.message : 'The audit could not be completed.'))
    } finally {
      setBusy(false)
    }
  }

  const pct = audit ? Math.round((audit.checks_passed / audit.checks_total) * 100) : 0

  return (
    <section className="section" style={{ maxWidth: 900 }}>
      <SectionHead
        title="Find what is costing you enquiries."
        lede="Enter your website. In a few seconds you get a prioritised list of fixes for search, conversion, lead capture and tracking. Free, and no account is needed."
      />
      <form className="card" onSubmit={run} style={{ display: 'grid', gap: 14 }}>
        <Field id="audit-url" label="Your website" hint="The page your customers land on, usually your home page.">
          <input id="audit-url" type="text" inputMode="url" required placeholder="yourbusiness.ae" value={url} onChange={(e) => setUrl(e.target.value)} />
        </Field>
        <div className="two-up">
          <Field id="audit-industry" label="Type of business">
            <select id="audit-industry" value={industry} onChange={(e) => { setIndustry(e.target.value); setGoal('') }}>
              <option value="">Choose one (optional)</option>
              {SEGMENTS.map((s) => (
                <option key={s.key} value={s.industry}>{s.label}</option>
              ))}
              <option value="Other">Something else</option>
            </select>
          </Field>
          <Field id="audit-goal" label="Main goal right now">
            <select id="audit-goal" value={goal} onChange={(e) => setGoal(e.target.value)}>
              <option value="">Choose one (optional)</option>
              {(segment?.goals || ['More enquiries', 'More sales', 'More repeat customers']).map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </Field>
        </div>
        <Field id="audit-email" label="Email (optional)" hint="Add it if you would like us to follow up about your results. Leave it empty and nothing about you is stored.">
          <input id="audit-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@yourbusiness.ae" />
        </Field>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={busy || !url.trim()}>{busy ? 'Reading your page…' : 'Run my free audit'}</button>
      </form>

      {audit && (
        <div style={{ marginTop: 26 }} aria-live="polite">
          <div className="card score-result">
            <div className="score-ring" style={{ ['--pct' as string]: `${pct}%` }} aria-hidden="true">
              <span>{audit.checks_passed}/{audit.checks_total}</span>
            </div>
            <div>
              <h2 style={{ fontSize: '1.5rem', marginBottom: 6 }}>
                {audit.checks_passed} of {audit.checks_total} checks passed
              </h2>
              <p className="muted" style={{ margin: 0, overflowWrap: 'anywhere' }}>
                {audit.url} · {audit.priorities.length === 0 ? 'No gaps found on this page.' : `${audit.priorities.length} thing${audit.priorities.length > 1 ? 's' : ''} to fix, most valuable first.`}
              </p>
            </div>
          </div>

          <div className="table-wrap" style={{ marginTop: 18 }}>
            <table className="compare-table">
              <caption className="sr-only">Checks passed by area</caption>
              <thead>
                <tr><th scope="col">Area</th><th scope="col">Checks passed</th></tr>
              </thead>
              <tbody>
                {audit.areas.map((a) => (
                  <tr key={a.area}><th scope="row">{a.area}</th><td>{a.passed} of {a.total}</td></tr>
                ))}
                <tr>
                  <th scope="row">Page speed on a phone</th>
                  <td>
                    {speed ? `${speed.performance_score} / 100${speed.metrics[0] ? ` · ${speed.metrics[0].label.toLowerCase()} in ${speed.metrics[0].value}` : ''}` : speedNote || 'Testing…'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {speed && <p className="muted small" style={{ marginTop: 6 }}>Speed: {speed.source}.</p>}

          {audit.priorities.length > 0 && (
            <>
              <h2 style={{ marginTop: 28 }}>What to fix first</h2>
              <ol className="score-gaps">
                {audit.priorities.map((f) => (
                  <li key={f.check} className="card">
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
                      <strong>{f.check}</strong>
                      <span className="muted small">{f.area} · Impact: {LEVEL[f.impact]} · Effort: {LEVEL[f.effort]}</span>
                    </div>
                    <p className="muted" style={{ margin: '6px 0 0' }}>Found: {f.found}</p>
                    <p style={{ margin: '6px 0 0' }}>{f.fix}</p>
                  </li>
                ))}
              </ol>
            </>
          )}

          {audit.passed.length > 0 && (
            <details className="card" style={{ marginTop: 18 }}>
              <summary>What is already working ({audit.passed.length})</summary>
              <ul className="check-list" style={{ marginTop: 12 }}>
                {audit.passed.map((f) => (
                  <li key={f.check}><strong>{f.check}.</strong> <span className="muted">{f.found}</span></li>
                ))}
              </ul>
            </details>
          )}

          <p className="muted small" style={{ marginTop: 14 }}>{audit.method}</p>

          <div className="card" style={{ marginTop: 18 }}>
            <h2>Want these fixed, and the marketing done each month?</h2>
            <p className="muted">
              ARC plans your month, writes the posts, ads, emails and articles, and shows whether each channel made or
              lost money at your margins. You approve everything before it goes out.
            </p>
            <CtaPair />
          </div>
        </div>
      )}
    </section>
  )
}
