import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest, ApiError } from '../../api/client'
import WorkflowDemo from '../../components/marketing/WorkflowDemo'
import { Field } from '../../components/ui'
import { CAPABILITIES } from '../../lib/marketing'
import { AgentGrid, IntegrationList, PlanComparison, PricingTable, SectionHead } from './sections'
import { CtaPair, FaqList } from './GrowthPages'
import { PRICING_FAQS } from '../../lib/growth'
import { usePageMeta } from '../../lib/seo'

import { API_BASE_URL as API } from '../../lib/apiBase'

export function ProductPage() {
  usePageMeta("Product", "How ARC works as an AI marketing department: twelve agents, two control rooms and an approval system.")
  return (
    <>
      <section className="section">
        <SectionHead
          title="An AI-operated marketing department, not another content tool."
          lede="ARC coordinates twelve specialist agents through one durable workflow, two control rooms and an approval system that keeps people in charge of the decisions that matter."
        />
        <div className="grid-3">
          <div className="card">
            <h3>Business Command Center</h3>
            <p className="muted">
              What is being delivered, what needs your attention, which decisions are waiting, and what each run
              cost. Business metrics stay marked “Not connected” until a real source is attached.
            </p>
          </div>
          <div className="card">
            <h3>Marketing Operations Center</h3>
            <p className="muted">
              Which agent is working on what, the live dependency graph, the task queue, retries, cost per agent, and
              the controls to pause anything.
            </p>
          </div>
          <div className="card">
            <h3>Approval inbox</h3>
            <p className="muted">
              Each decision shows the requesting agent, risk checks, the exact version, what happens next, and when it
              expires.
            </p>
          </div>
        </div>
      </section>
      <section className="section tight">
        <div className="cap-grid">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="cap">
              <span className="agent-glyph">
                <c.icon size={18} aria-hidden="true" />
              </span>
              <h3>{c.title}</h3>
              <p>{c.body}</p>
            </div>
          ))}
        </div>
        <div className="cta-row" style={{ marginTop: 40 }}>
          <Link to="/signup" className="btn lg">
            Start free trial
          </Link>
          <Link to="/how-it-works" className="btn secondary lg">
            How it works
          </Link>
        </div>
      </section>
    </>
  )
}

export function AgentsPage() {
  usePageMeta("The 12 agents", "Meet ARC's twelve specialist marketing agents and what each one does.")
  return (
    <section className="section">
      <SectionHead
        title="Twelve specialists. One department."
        lede="Every agent below is a real, versioned component with its own instructions, output schema, permissions, budget and checks. The details come straight from the running system."
      />
      <AgentGrid />
    </section>
  )
}

export function HowItWorksPage() {
  usePageMeta("How it works", "From brief to approved, published work: how ARC's agents, approvals and exports fit together.")
  const steps = [
    ['Set up your workspace', 'Business profile, brand voice, prohibited phrases, goals, channels, budgets and approval policies.'],
    ['Write a brief', 'Objective, audience, channels, dates and budget guidance for a campaign.'],
    ['Agents run in order', 'CMO → Research → Marketing Manager → specialists in parallel → Ops quality gate → Record Keeper. Each waits for its inputs.'],
    ['Problems are handled, not hidden', 'Rate limits and timeouts retry with backoff. Anything that truly fails stops, says why, and waits for you.'],
    ['You review and approve', 'Approvals lock to the exact version. You — or your client, through a secure review link — approve each piece.'],
    ['Publish', 'Export approved work in each platform’s format, or send it automatically to Zapier or Make to post. ARC never spends money.'],
    ['It learns', 'The Record Keeper proposes learnings; once approved they inform future strategy and planning.'],
  ]
  return (
    <>
      <section className="section">
        <SectionHead title="From brief to approved work, step by step." />
        <ol className="timeline" style={{ maxWidth: 760 }}>
          {steps.map(([t, b], i) => (
            <li key={t} className="info">
              <span className="timeline-dot" aria-hidden="true" />
              <div>
                <div style={{ fontWeight: 700 }}>
                  {i + 1}. {t}
                </div>
                <div className="muted">{b}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>
      <section className="section tight">
        <WorkflowDemo />
      </section>
      <section className="section tight">
        <h2>What runs automatically, and what waits for you</h2>
        <div className="grid-3">
          <div className="card">
            <h3>Automated (when you allow it)</h3>
            <ul className="deliverable-list">
              <li>Research, planning and drafting</li>
              <li>Task creation, ordering and retries</li>
              <li>Quality checks and reporting</li>
              <li>Knowledge proposals</li>
            </ul>
          </div>
          <div className="card">
            <h3>Always needs a person</h3>
            <ul className="deliverable-list">
              <li>Anything leaving the workspace — approved first, every time</li>
              <li>Public replies on sensitive issues</li>
              <li>Payments, contracts and commitments</li>
              <li>Any ad spend change — agents can’t do this at all</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  )
}

export function IntegrationsPublicPage() {
  usePageMeta("Integrations", "Which platforms ARC exports to and connects with today, and what is planned.")
  return (
    <section className="section">
      <SectionHead
        title="Connected where it's real. Labelled where it isn't."
        lede="Each integration shows its true status and what it needs before it can go live."
      />
      <IntegrationList />
    </section>
  )
}

export function SecurityPage() {
  usePageMeta("Security", "Tenant isolation, approvals, audit logs and data controls in ARC.")
  return (
    <section className="section">
      <SectionHead title="Security, governance and data controls." />
      <div className="notice">
        ARC has not obtained SOC 2, ISO 27001 or any other certification, and makes no formal compliance claim (for
        example GDPR). This page describes controls that exist in the product today.
      </div>
      <div className="prose">
        <h2>Tenant isolation</h2>
        <p>Every workspace-scoped request is authorized on the server against your membership before any data is read. Cross-workspace access is covered by automated tests for every endpoint.</p>
        <h2>Roles and least privilege</h2>
        <p>Owner, Administrator, Marketing Manager, Approver, Contributor, Analyst and Viewer roles. Only approvers can decide approvals; only owners manage billing and deletion.</p>
        <h2>Agents are sandboxed by design</h2>
        <p>Agents can only produce structured drafts validated against a schema. They cannot run SQL, shell commands, file operations or arbitrary web requests, and only receive the specific outputs of agents they depend on. Business-profile text and retrieved knowledge are passed as untrusted data, never as instructions.</p>
        <h2>Approvals and emergency stop</h2>
        <p>Approvals are bound to an exact version and payload hash, expire, can be revoked, and are re-checked immediately before any export. Owners and admins can pause all agents or engage a kill switch that the backend enforces.</p>
        <h2>Accounts and sessions</h2>
        <p>Passwords are hashed, sign-in and reset endpoints are rate-limited, sessions use HttpOnly cookies with CSRF protection, and a password reset or “sign out everywhere” revokes every other session. Two-factor sign-in with any authenticator app, plus single-use recovery codes, is available in Security settings. Owners and admins can download the full audit log as CSV.</p>
        <h2>Your data</h2>
        <p>Admins can export all workspace data as JSON. Owners can schedule deletion; data is permanently purged after a 30-day grace period. Uploaded files are type- and content-checked and only downloadable by members.</p>
        <h2>Secrets</h2>
        <p>Provider keys live on the server only. Webhook payloads in both directions are HMAC-signed with replay protection; outbound webhooks refuse private and internal addresses.</p>
        <h2>Legal and data protection</h2>
        <p>
          Read our <Link to="/privacy">Privacy Policy</Link>, <Link to="/dpa">Data Processing Agreement</Link>,{' '}
          <Link to="/ai-policy">AI Use Policy</Link> and the list of <Link to="/subprocessors">sub-processors</Link>.
        </p>
        <h2>Report a vulnerability</h2>
        <p>
          Please use the <Link to="/contact">contact form</Link> with topic “Security”.
        </p>
      </div>
    </section>
  )
}

export function PricingPage() {
  usePageMeta('Pricing', 'ARC plans from $149/month with all twelve agents. 14-day free trial, no card needed, cancel any time.')
  return (
    <>
      <section className="section">
        <SectionHead
          title="A marketing department for less than one hire."
          lede="Every plan includes all twelve agents, approvals and exports. Start with a 14-day free trial — no card needed — and cancel any time."
        />
        <PricingTable />
        <p style={{ marginTop: 18 }}>
          <Link to="/compare/agency">Compare ARC with what you spend on an agency or in-house time →</Link>
        </p>
      </section>
      <section className="section tight">
        <h2>Compare plans</h2>
        <PlanComparison />
      </section>
      <section className="section tight">
        <div className="card addon-card">
          <div>
            <h2>Strategist add-on: a human on your side</h2>
            <p className="muted" style={{ margin: 0 }}>
              A marketing strategist who reviews your plan each month, joins a monthly call and runs a quarterly
              review with you. Priced with you on a call.
            </p>
          </div>
          <Link to="/demo" className="btn secondary">
            Talk to us
          </Link>
        </div>
      </section>
      <section className="section tight">
        <h2>Pricing questions</h2>
        <FaqList id="pricing-faq" faqs={PRICING_FAQS} />
        <div style={{ marginTop: 28 }}>
          <CtaPair />
        </div>
      </section>
    </>
  )
}

export function AboutPage() {
  usePageMeta("About", "Why ARC exists: marketing that operates, not just generates.")
  return (
    <section className="section">
      <SectionHead title="Marketing that operates, not just generates." />
      <div className="prose">
        <p>
          ARC exists because most businesses don't need another tool that writes posts. They need the coordination
          a marketing department provides: a strategy, a plan, specialists working in the right order, quality checks,
          and a record of what was decided and learned.
        </p>
        <p>
          Our goal is not to make marketing look autonomous. It's to make it operate autonomously, measurably,
          recoverably and safely — with people controlling the decisions that matter.
        </p>
        <p>
          We're honest about limits: outcomes depend on your business, data, channels and budget, and we label every
          estimate and every integration that isn't connected yet.
        </p>
      </div>
    </section>
  )
}

export function ContactPage() {
  usePageMeta("Contact", "Talk to the ARC team about sales, support, partnerships or security.")
  const [form, setForm] = useState({ name: '', email: '', company: '', topic: 'sales', message: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    const local: Record<string, string> = {}
    if (!form.name.trim()) local.name = 'Required'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) local.email = 'A valid email is required'
    if (form.message.trim().length < 10) local.message = 'Tell us a little more (10+ characters)'
    setErrors(local)
    if (Object.keys(local).length) return
    setStatus('sending')
    setError(null)
    try {
      await apiRequest('/public/contact', { method: 'POST', body: form })
      setStatus('sent')
    } catch (err) {
      setStatus('idle')
      if (err instanceof ApiError) {
        setErrors(Object.fromEntries(err.details.map((d) => [d.field, d.issue])))
        setError(err.message)
      } else setError('Could not send your message.')
    }
  }

  return (
    <section className="section" style={{ maxWidth: 640 }}>
      <SectionHead title="Talk to us." lede="Sales, support, partnerships or security — we reply by email." />
      {status === 'sent' ? (
        <div className="banner success">Thanks — your message was received. We'll reply by email.</div>
      ) : (
        <form className="card" onSubmit={submit} noValidate>
          {error && <div className="banner error">{error}</div>}
          <Field id="c-name" label="Name" error={errors.name}>
            <input id="c-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" />
          </Field>
          <Field id="c-email" label="Work email" error={errors.email}>
            <input id="c-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
          </Field>
          <Field id="c-company" label="Company (optional)">
            <input id="c-company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} autoComplete="organization" />
          </Field>
          <Field id="c-topic" label="Topic">
            <select id="c-topic" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })}>
              <option value="sales">Sales</option>
              <option value="support">Support</option>
              <option value="partnership">Partnership</option>
              <option value="security">Security</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field id="c-message" label="Message" error={errors.message}>
            <textarea id="c-message" rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
          </Field>
          <button type="submit" disabled={status === 'sending'}>
            {status === 'sending' ? 'Sending…' : 'Send message'}
          </button>
        </form>
      )}
    </section>
  )
}

export function DocsPage() {
  usePageMeta("Docs", "Getting started with ARC, the agents, runs, security and the API.")
  return (
    <section className="section">
      <SectionHead title="Docs" lede="Start here, then go deeper." />
      <div className="cap-grid">
        {[
          ['Getting started', 'Create a workspace, complete onboarding, write a brief, and run the department.', '/signup'],
          ['The 12 agents', 'What each agent does, what it reads, what it produces and when it asks you.', '/agents'],
          ['How runs work', 'Dependencies, retries, pausing, approvals and the knowledge loop.', '/how-it-works'],
          ['Security model', 'Isolation, roles, approvals, data export and deletion.', '/security'],
        ].map(([t, b, to]) => (
          <Link key={t} to={to} className="cap" style={{ color: 'inherit', textDecoration: 'none' }}>
            <h3 style={{ marginTop: 0 }}>{t}</h3>
            <p>{b}</p>
          </Link>
        ))}
        <a className="cap" href={`${API}/openapi.json`} style={{ color: 'inherit', textDecoration: 'none' }}>
          <h3 style={{ marginTop: 0 }}>API reference (OpenAPI)</h3>
          <p>Generated from the live route map. Session-cookie auth with CSRF; every response has an X-Request-Id.</p>
        </a>
        <div className="cap">
          <h3 style={{ marginTop: 0 }}>Webhooks</h3>
          <p>
            Signed with <code>ARC-Signature: t=…,v1=…</code> (HMAC-SHA256 of <code>t.body</code>). Reject timestamps older
            than 5 minutes and dedupe on <code>ARC-Event-Id</code>. Retries: 6 attempts with exponential backoff.
          </p>
        </div>
      </div>
    </section>
  )
}
