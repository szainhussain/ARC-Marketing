import { useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { ArrowRight, Check, CheckCircle2, ShieldCheck } from 'lucide-react'
import { apiRequest, ApiError } from '../../api/client'
import { Field } from '../../components/ui'
import { useResource } from '../../hooks/useResource'
import { LOOP, SCORECARD, SOLUTIONS } from '../../lib/growth'
import { faqJsonLd, useJsonLd, usePageMeta, type Faq } from '../../lib/seo'
import { SectionHead, type Plan } from './sections'

// ---- Shared pieces ---------------------------------------------------------

export function LoopDiagram() {
  return (
    <ol className="loop" aria-label="How ARC runs your marketing">
      {LOOP.map((s, i) => (
        <li key={s.k} className={'highlight' in s && s.highlight ? 'loop-step approve' : 'loop-step'}>
          <span className="loop-n">{String(i + 1).padStart(2, '0')}</span>
          <span className="loop-k">
            {'highlight' in s && s.highlight && <ShieldCheck size={15} aria-hidden="true" />} {s.k}
          </span>
          <span className="loop-d">{s.d}</span>
        </li>
      ))}
    </ol>
  )
}

export function FaqList({ id, faqs }: { id: string; faqs: Faq[] }) {
  useJsonLd(id, faqJsonLd(faqs))
  return (
    <div className="faq">
      {faqs.map((f) => (
        <details key={f.q}>
          <summary>{f.q}</summary>
          <p>{f.a}</p>
        </details>
      ))}
    </div>
  )
}

export function CtaPair({ center }: { center?: boolean }) {
  return (
    <div className="cta-row" style={center ? { justifyContent: 'center' } : undefined}>
      <Link to="/signup" className="btn lg">
        Start free trial
      </Link>
      <Link to="/demo" className="btn secondary lg">
        Book a demo
      </Link>
    </div>
  )
}

// ---- Solutions -------------------------------------------------------------

export function SolutionsPage() {
  usePageMeta('Solutions', 'How ARC runs marketing for product launches, local businesses, online stores and B2B lead generation.')
  return (
    <section className="section">
      <SectionHead
        title="One department, shaped around your goal."
        lede="Pick the situation closest to yours to see which agents do the work and what you get back."
      />
      <div className="cap-grid">
        {SOLUTIONS.map((s) => (
          <Link key={s.slug} to={`/solutions/${s.slug}`} className="cap solution-card">
            <h3 style={{ marginTop: 0 }}>{s.title}</h3>
            <p>{s.short}</p>
            <span className="small solution-more">
              See how it works <ArrowRight size={13} aria-hidden="true" />
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}

export function SolutionPage() {
  const { slug } = useParams()
  const s = SOLUTIONS.find((x) => x.slug === slug)
  usePageMeta(s ? s.title : 'Solutions', s?.short)
  if (!s) return <Navigate to="/solutions" replace />
  return (
    <>
      <section className="section">
        <nav aria-label="Breadcrumb" className="crumbs" style={{ marginBottom: 14 }}>
          <Link to="/solutions">Solutions</Link>
          <span className="crumb-sep">/</span>
          <span aria-current="page">{s.title}</span>
        </nav>
        <h1 className="display-page">{s.title}</h1>
        <p className="lede">{s.short}</p>
        <p className="muted">
          <strong style={{ color: 'var(--color-fg)' }}>Built for:</strong> {s.who}
        </p>
        <CtaPair />
      </section>
      <section className="section tight">
        <div className="two-up">
          <div className="card">
            <h2>Sound familiar?</h2>
            <ul className="plain-list">
              {s.pains.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h2>What you get back</h2>
            <ul className="check-list">
              {s.delivers.map((d) => (
                <li key={d.agent}>
                  <Check size={15} aria-hidden="true" />
                  <span>
                    <strong>{d.agent}:</strong> {d.output}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="banner success" style={{ marginTop: 8 }}>
          {s.outcome}
        </div>
      </section>
      <section className="section tight">
        <h2>How it runs</h2>
        <LoopDiagram />
      </section>
    </>
  )
}

// ---- Book a demo -----------------------------------------------------------

export function DemoPage() {
  usePageMeta('Book a demo', 'See ARC run a campaign for your business in a 30-minute walkthrough.')
  const [form, setForm] = useState({ name: '', email: '', company: '', team: '1-5', goal: 'Launch a product or offer', message: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    const local: Record<string, string> = {}
    if (!form.name.trim()) local.name = 'Required'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) local.email = 'A valid email is required'
    setErrors(local)
    if (Object.keys(local).length) return
    setStatus('sending')
    setError(null)
    const message = [`Demo request`, `Team size: ${form.team}`, `Main goal: ${form.goal}`, form.message.trim() && `Notes: ${form.message.trim()}`]
      .filter(Boolean)
      .join('\n')
    try {
      await apiRequest('/public/contact', { method: 'POST', body: { name: form.name, email: form.email, company: form.company, topic: 'demo', message } })
      setStatus('sent')
    } catch (err) {
      setStatus('idle')
      if (err instanceof ApiError) {
        setErrors(Object.fromEntries(err.details.map((d) => [d.field, d.issue])))
        setError(err.message)
      } else setError('Could not send your request. Please try again in a minute.')
    }
  }

  return (
    <section className="section">
      <div className="two-up demo-layout">
        <div>
          <SectionHead title="See ARC run your marketing." />
          <p className="lede">A 30-minute walkthrough with your own business as the example.</p>
          <ul className="check-list">
            {[
              'We run a real campaign brief for your business, live',
              'You see all twelve agents, the approval inbox and the exports',
              'We map ARC to your channels, team and budget',
              'Optional: how the strategist add-on works',
            ].map((t) => (
              <li key={t}>
                <Check size={15} aria-hidden="true" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
          <p className="muted small">Prefer to try it yourself? <Link to="/signup">Start a free 14-day trial</Link> — no card needed.</p>
        </div>
        {status === 'sent' ? (
          <div className="card">
            <CheckCircle2 size={28} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
            <h2 style={{ marginTop: 10 }}>Request received</h2>
            <p className="muted">We’ll email you within one business day to agree a time. In the meantime you can start a free trial.</p>
            <Link to="/signup" className="btn">
              Start free trial
            </Link>
          </div>
        ) : (
          <form className="card" onSubmit={submit} noValidate>
            {error && <div className="banner error">{error}</div>}
            <Field id="d-name" label="Name" error={errors.name}>
              <input id="d-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" />
            </Field>
            <Field id="d-email" label="Work email" error={errors.email}>
              <input id="d-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
            </Field>
            <Field id="d-company" label="Company (optional)">
              <input id="d-company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} autoComplete="organization" />
            </Field>
            <div className="form-grid">
              <Field id="d-team" label="Team size">
                <select id="d-team" value={form.team} onChange={(e) => setForm({ ...form, team: e.target.value })}>
                  {['Just me', '1-5', '6-20', '21-100', '100+'].map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </Field>
              <Field id="d-goal" label="Main goal">
                <select id="d-goal" value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })}>
                  {[...SOLUTIONS.map((s) => s.title), 'Replace or support an agency', 'Something else'].map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </Field>
            </div>
            <Field id="d-message" label="Anything we should know? (optional)" error={errors.message}>
              <textarea id="d-message" rows={3} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
            </Field>
            <button type="submit" disabled={status === 'sending'} style={{ width: '100%', justifyContent: 'center' }}>
              {status === 'sending' ? 'Sending…' : 'Request a demo'}
            </button>
            <p className="muted small" style={{ marginBottom: 0 }}>
              We use these details only to arrange your demo. See our <Link to="/privacy">Privacy Policy</Link>.
            </p>
          </form>
        )}
      </div>
    </section>
  )
}

// ---- Free marketing scorecard ----------------------------------------------

export function ScorecardPage() {
  usePageMeta('Free marketing scorecard', 'Score your marketing in 2 minutes and get a prioritised list of what to fix first.')
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [done, setDone] = useState(false)
  const answered = Object.keys(answers).length
  const max = SCORECARD.length * 3
  const score = Object.values(answers).reduce((a, b) => a + b, 0)
  const pct = Math.round((score / max) * 100)
  const gaps = SCORECARD.filter((q) => (answers[q.id] ?? 0) < 3).sort((a, b) => (answers[a.id] ?? 0) - (answers[b.id] ?? 0))
  const band = pct >= 75 ? 'Strong foundation' : pct >= 45 ? 'Good start, clear gaps' : 'Early stage'

  return (
    <section className="section" style={{ maxWidth: 860 }}>
      <SectionHead
        title="How healthy is your marketing?"
        lede="Eight questions, two minutes. You get a score and a prioritised list of what to fix first. Nothing is stored or sent anywhere."
      />
      {!done ? (
        <form
          className="scorecard"
          onSubmit={(e) => {
            e.preventDefault()
            if (answered === SCORECARD.length) setDone(true)
          }}
        >
          {SCORECARD.map((q, i) => (
            <fieldset key={q.id} className="card score-q">
              <legend>
                <span className="muted small">
                  {i + 1}/{SCORECARD.length} · {q.area}
                </span>
                <span className="score-q-text">{q.q}</span>
              </legend>
              <div className="score-options">
                {q.options.map((o) => {
                  const id = `${q.id}-${o.points}-${o.label.length}`
                  return (
                    <label key={o.label} htmlFor={id} className={answers[q.id] === o.points ? 'selected' : ''}>
                      <input
                        id={id}
                        type="radio"
                        name={q.id}
                        checked={answers[q.id] === o.points}
                        onChange={() => setAnswers({ ...answers, [q.id]: o.points })}
                      />
                      {o.label}
                    </label>
                  )
                })}
              </div>
            </fieldset>
          ))}
          <button type="submit" disabled={answered < SCORECARD.length}>
            {answered < SCORECARD.length ? `Answer all questions (${answered}/${SCORECARD.length})` : 'See my score'}
          </button>
        </form>
      ) : (
        <div>
          <div className="card score-result">
            <div className="score-ring" style={{ ['--pct' as string]: `${pct}%` }} aria-hidden="true">
              <span>{pct}</span>
            </div>
            <div>
              <h2 style={{ fontSize: '1.6rem', marginBottom: 6 }}>{band}</h2>
              <p className="muted" style={{ margin: 0 }}>
                {score} of {max} points. {gaps.length === 0 ? 'Every area is in good shape.' : `${gaps.length} area${gaps.length > 1 ? 's' : ''} to improve, most urgent first:`}
              </p>
            </div>
          </div>
          {gaps.length > 0 && (
            <ol className="score-gaps">
              {gaps.map((g) => (
                <li key={g.id} className="card">
                  <strong>{g.area}</strong>
                  <p className="muted" style={{ margin: '4px 0 0' }}>
                    {g.tip}
                  </p>
                </li>
              ))}
            </ol>
          )}
          <div className="card" style={{ marginTop: 18 }}>
            <h2>Let ARC fix these for you</h2>
            <p className="muted">
              ARC writes your strategy, plans every month, drafts the content, checks it against your brand rules and
              keeps a record of what worked — you just approve.
            </p>
            <CtaPair />
            <button type="button" className="link-btn" style={{ marginTop: 14 }} onClick={() => { setAnswers({}); setDone(false) }}>
              Start again
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// ---- ARC vs agency / in-house calculator -----------------------------------

const FALLBACK_PRICES: Record<string, number> = { launch: 149, growth: 399, scale: 999 }

export function AgencyComparePage() {
  usePageMeta('ARC vs an agency', 'Compare what you spend on an agency, freelancers or in-house hours with an ARC plan.')
  const { data } = useResource<{ plans: Plan[] }>('/public/plans')
  const prices = useMemo(() => {
    const out: Record<string, { name: string; price: number }> = {}
    for (const p of data?.plans || []) if (p.monthly_price_usd != null) out[p.code] = { name: p.name, price: p.monthly_price_usd }
    if (!Object.keys(out).length) for (const [k, v] of Object.entries(FALLBACK_PRICES)) out[k] = { name: k[0].toUpperCase() + k.slice(1), price: v }
    return out
  }, [data])
  const [agency, setAgency] = useState('')
  const [hours, setHours] = useState('')
  const [rate, setRate] = useState('')
  const [plan, setPlan] = useState('growth')
  const [kept, setKept] = useState('25')

  const n = (v: string) => Math.max(0, Number(v) || 0)
  const current = n(agency) + n(hours) * 4.33 * n(rate)
  const arcPlan = prices[plan]?.price ?? 0
  const remainingHours = n(hours) * (n(kept) / 100)
  const withArc = arcPlan + remainingHours * 4.33 * n(rate)
  const diff = current - withArc
  const filled = n(agency) > 0 || n(hours) > 0
  const money = (v: number) => `$${Math.round(v).toLocaleString()}`

  return (
    <section className="section">
      <SectionHead
        title="ARC vs an agency or in-house time."
        lede="Enter what marketing costs you today. The calculation uses only your numbers and the published plan price — it is an estimate, not a promise."
      />
      <div className="two-up">
        <form className="card" onSubmit={(e) => e.preventDefault()}>
          <h2>What you spend today</h2>
          <Field id="cmp-agency" label="Agency or freelancer fees per month (USD)" hint="Leave at 0 if you don't use one.">
            <input id="cmp-agency" inputMode="decimal" type="number" min="0" placeholder="0" value={agency} onChange={(e) => setAgency(e.target.value)} />
          </Field>
          <div className="form-grid">
            <Field id="cmp-hours" label="Team hours on marketing per week">
              <input id="cmp-hours" inputMode="decimal" type="number" min="0" placeholder="0" value={hours} onChange={(e) => setHours(e.target.value)} />
            </Field>
            <Field id="cmp-rate" label="Cost per hour (USD)">
              <input id="cmp-rate" inputMode="decimal" type="number" min="0" placeholder="0" value={rate} onChange={(e) => setRate(e.target.value)} />
            </Field>
          </div>
          <h2 style={{ marginTop: 10 }}>With ARC</h2>
          <div className="form-grid">
            <Field id="cmp-plan" label="ARC plan">
              <select id="cmp-plan" value={plan} onChange={(e) => setPlan(e.target.value)}>
                {Object.entries(prices).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v.name} — {money(v.price)}/mo
                  </option>
                ))}
              </select>
            </Field>
            <Field id="cmp-kept" label="Team time you still spend (%)" hint="Reviewing and approving. Your own estimate.">
              <input id="cmp-kept" type="number" min="0" max="100" value={kept} onChange={(e) => setKept(e.target.value)} />
            </Field>
          </div>
        </form>
        <div className="card compare-result" aria-live="polite">
          <h2>Your estimate</h2>
          {!filled ? (
            <p className="muted">Enter your current costs to see the comparison.</p>
          ) : (
            <>
              <div className="compare-row">
                <span>Today</span>
                <strong>{money(current)}/mo</strong>
              </div>
              <div className="compare-row">
                <span>With ARC ({prices[plan]?.name})</span>
                <strong>{money(withArc)}/mo</strong>
              </div>
              <div className={`compare-total ${diff >= 0 ? 'good' : ''}`}>
                <span>{diff >= 0 ? 'Estimated monthly saving' : 'ARC costs more by'}</span>
                <strong>{money(Math.abs(diff))}</strong>
              </div>
              <p className="muted small">
                {diff >= 0 ? `About ${money(diff * 12)} a year. ` : ''}Assumes {kept || 0}% of today’s hours stay with your team for review, and 4.33 weeks per month.
                Results depend on your business, channels and budget.
              </p>
            </>
          )}
          <CtaPair />
        </div>
      </div>
      <div className="table-wrap" style={{ marginTop: 32 }}>
        <table className="compare-table responsive">
          <thead>
            <tr>
              <th></th>
              <th>Typical agency</th>
              <th>Freelancers</th>
              <th>ARC</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Strategy, plan and content in one place', 'Often', 'Rarely', 'Yes — twelve coordinated agents'],
              ['Start time', 'Weeks of onboarding', 'Days per freelancer', 'Same day'],
              ['You approve every piece before it goes out', 'Depends on the agency', 'Depends', 'Always — version-locked approvals'],
              ['Complete record of decisions and work', 'Reports', 'Rarely', 'Audit log and exportable data'],
              ['Cancel any time', 'Usually a notice period', 'Per project', 'Yes'],
            ].map(([k, a, f, arc]) => (
              <tr key={k}>
                <td data-label="">
                  <strong>{k}</strong>
                </td>
                <td data-label="Typical agency">{a}</td>
                <td data-label="Freelancers">{f}</td>
                <td data-label="ARC" className="arc-col">
                  {arc}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
