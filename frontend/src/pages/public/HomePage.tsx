import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import { Lock, Repeat } from 'lucide-react'
import ProductPreview from '../../components/marketing/ProductPreview'
import WorkflowDemo from '../../components/marketing/WorkflowDemo'
import Reveal from '../../components/motion/Reveal'
import { AgentGrid, IntegrationList, PricingTable, SectionHead } from './sections'
import { CAPABILITIES } from '../../lib/marketing'

const PROBLEMS = [
  'Too many disconnected tools',
  'Strategy that never reaches execution',
  'Content production bottlenecks',
  'Inconsistent brand messaging',
  'Campaigns that are hard to measure',
  'Repetitive manual coordination',
  'Reporting without actionable learning',
]

const LIFECYCLE = ['Understand', 'Strategize', 'Plan', 'Create', 'Review', 'Execute', 'Measure', 'Improve']

export default function HomePage() {
  const reduce = useReducedMotion()
  const enter = (delay: number) =>
    reduce ? {} : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] as const } }

  return (
    <>
      <section className="hero2">
        <motion.span className="pill-tag" {...enter(0)}>
          <span className="dot" aria-hidden="true" /> Your marketing department. Always moving.
        </motion.span>
        <motion.h1 {...enter(0.05)}>
          A full marketing team. <em>Working as one.</em>
        </motion.h1>
        <motion.p className="lede" {...enter(0.12)}>
          Meet your AI-powered marketing department. Twelve specialist agents plan, create, coordinate, optimize, and
          learn together—so your business can move from marketing ideas to measurable execution without managing a
          dozen disconnected tools.
        </motion.p>
        <motion.div className="cta-row" {...enter(0.18)}>
          <Link to="/signup" className="btn lg">
            Build your marketing team
          </Link>
          <a href="#workspace" className="btn secondary lg">
            Explore the workspace
          </a>
        </motion.div>
        <motion.p className="hero-note" {...enter(0.24)}>
          One coordinated system. Clear controls. Work you can measure.
        </motion.p>
        <motion.div id="workspace" {...enter(0.3)}>
          <ProductPreview />
        </motion.div>
      </section>

      <section className="section">
        <SectionHead
          eyebrow="The problem"
          title="Marketing shouldn't be a full-time job in coordination."
          lede="Most teams don't lack ideas. They lose them between tools, handoffs and status meetings."
        />
        <Reveal>
          <div className="problem-grid">
            {PROBLEMS.map((p, i) => (
              <div key={p}>
                <div className="n">{String(i + 1).padStart(2, '0')}</div>
                <div className="t">{p}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      <div className="rule" />

      <section className="section">
        <SectionHead
          eyebrow="The system"
          title="From brief to execution, one coordinated system."
          lede="Your CMO agent sets direction, the Marketing Manager plans it, ten specialists build it, Operations checks it — and nothing leaves the workspace until you approve it."
        />
        <Reveal>
          <div className="lifecycle" aria-label="Campaign lifecycle">
            {LIFECYCLE.map((s, i) => (
              <span key={s} style={{ display: 'contents' }}>
                <span className="step">{s}</span>
                {i < LIFECYCLE.length - 1 && (
                  <span className="arrow" aria-hidden="true">
                    →
                  </span>
                )}
              </span>
            ))}
          </div>
        </Reveal>
        <Reveal>
          <WorkflowDemo />
        </Reveal>
      </section>

      <section className="section">
        <SectionHead
          eyebrow="The team"
          title="Meet the twelve agents."
          lede="Each one has its own job, its own output format, its own permissions and its own quality checks. Open any card to see exactly what it can and can't do."
        />
        <AgentGrid />
      </section>

      <div className="rule" />

      <section className="section">
        <SectionHead eyebrow="Capabilities" title="Everything a marketing department does. Coordinated." />
        <div className="cap-grid">
          {CAPABILITIES.map((c, i) => (
            <Reveal key={c.title} delay={(i % 3) * 0.05}>
              <div className="cap" style={{ height: '100%' }}>
                <span className="agent-glyph">
                  <c.icon size={18} aria-hidden="true" />
                </span>
                <h3>{c.title}</h3>
                <p>{c.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="section">
        <SectionHead
          eyebrow="Integrations"
          title="Honest about what's connected."
          lede="We label every integration by what's actually built. Today ARC exports approved work in each platform's format; live connectors arrive as they're verified."
        />
        <IntegrationList compact />
        <p style={{ marginTop: 18 }}>
          <Link to="/integrations">See every integration and its prerequisites →</Link>
        </p>
      </section>

      <div className="rule" />

      <section className="section">
        <SectionHead
          eyebrow="Security and trust"
          title="Autonomy with guardrails you control."
          lede="Every workspace is isolated. Every consequential action needs a person. Every decision is recorded."
        />
        <div className="cap-grid">
          {[
            ['Tenant isolation', 'Every query is scoped to your workspace on the server, and tested on every release.'],
            ['Scoped agent permissions', 'Agents only see the outputs they need, and have no tools beyond structured drafting.'],
            ['Approval controls', 'Version-locked approvals, expiry, revocation and one pending decision per version.'],
            ['Budget limits', 'Per-run, per-agent and per-plan budgets, enforced before any model call.'],
            ['Audit trail', 'Append-only log of who did what, when — exportable with all your data.'],
            ['Stop everything', 'Pause all agents or engage the kill switch instantly; the backend enforces it.'],
          ].map(([t, b]) => (
            <div key={t} className="cap">
              <span className="agent-glyph">
                <Lock size={17} aria-hidden="true" />
              </span>
              <h3>{t}</h3>
              <p>{b}</p>
            </div>
          ))}
        </div>
        <p className="muted small" style={{ marginTop: 16 }}>
          ARC has not yet obtained SOC 2, ISO 27001 or other certifications. <Link to="/security">Read our security approach.</Link>
        </p>
      </section>

      <section className="section">
        <SectionHead eyebrow="Pricing" title="Plans that grow with your workload." />
        <PricingTable />
      </section>

      <section className="final-cta">
        <Reveal>
          <h2>Give your marketing goals a team that keeps moving.</h2>
          <p className="lede" style={{ margin: '0 auto 30px', color: 'var(--color-muted-fg)', maxWidth: 560 }}>
            Bring your strategy, execution, and performance into one coordinated workspace.
          </p>
          <div className="cta-row">
            <Link to="/signup" className="btn lg">
              Build your marketing team
            </Link>
          </div>
          <p className="hero-note">
            <Repeat size={12} aria-hidden="true" /> Less coordination. More execution. Marketing that learns as it works.
          </p>
        </Reveal>
      </section>
    </>
  )
}
