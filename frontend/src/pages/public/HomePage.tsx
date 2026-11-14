import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'motion/react'
import { Repeat } from 'lucide-react'
import ProductPreview from '../../components/marketing/ProductPreview'
import WorkflowDemo from '../../components/marketing/WorkflowDemo'
import FlowLoop from '../../components/motion/FlowLoop'
import Reveal from '../../components/motion/Reveal'
import { IntegrationList, PricingTable, SectionHead } from './sections'
import { CtaPair, FaqList } from './GrowthPages'
import { HOME_FAQS, MONTHLY_OUTCOMES, SOLUTIONS } from '../../lib/growth'
import { usePageMeta } from '../../lib/seo'

const PROBLEMS = [
  'No time to plan marketing between serving customers',
  'Agency retainers that cost more than they return',
  'Posting that stops whenever work gets busy',
  'Ads launched without a plan or a budget split',
  'A different message on every channel',
  'No clear view of which channel brings enquiries',
  'A full-time marketer you cannot yet justify',
]

export default function HomePage() {
  usePageMeta('')
  const reduce = useReducedMotion()
  const enter = (delay: number) =>
    reduce ? {} : { initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] as const } }

  return (
    <>
      <section className="hero2">
        <motion.span className="pill-tag" {...enter(0)}>
          <span className="dot" aria-hidden="true" /> Built for growing businesses in the UAE
        </motion.span>
        <motion.h1 {...enter(0.05)}>
          Know which marketing drives growth. <em>We&rsquo;ll do the rest.</em>
        </motion.h1>
        <motion.p className="lede" {...enter(0.12)}>
          ARC plans your month, writes every post, ad, email and article, and shows which channels grew your
          business and which did not. Nothing goes out until you approve it.
        </motion.p>
        <motion.div {...enter(0.18)}>
          <CtaPair center />
        </motion.div>
        <motion.p className="hero-note" {...enter(0.24)}>
          14-day free trial · No card needed · Cancel any time
        </motion.p>
        <motion.p {...enter(0.27)} style={{ marginTop: 10 }}>
          <Link to="/growth-audit">Or check your website first with a free Growth Audit →</Link>
        </motion.p>
        <motion.div id="workspace" {...enter(0.3)}>
          <ProductPreview />
        </motion.div>
      </section>

      <section className="section">
        <SectionHead
          title="Marketing shouldn't depend on you finding the time."
          lede="Most small businesses know what they should be doing. It stops when the owner gets busy."
        />
        <Reveal>
          <div className="problem-grid">
            {PROBLEMS.map((p) => (
              <div key={p}>
                <div className="t">{p}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      <div className="rule" />

      <section className="section">
        <SectionHead
          title="Strategy to results, every month. You stay in control."
          lede="One brief becomes a strategy, a dated plan and finished content, checked against your brand rules, and nothing leaves the workspace until you approve it."
        />
        <Reveal>
          <FlowLoop />
        </Reveal>
        <Reveal>
          <WorkflowDemo />
        </Reveal>
      </section>

      <section className="section">
        <SectionHead title="Built around what you need to get done." />
        <div className="cap-grid">
          {SOLUTIONS.map((s) => (
            <Link key={s.slug} to={`/solutions/${s.slug}`} className="cap solution-card">
              <h3 style={{ marginTop: 0 }}>{s.title}</h3>
              <p>{s.short}</p>
              <span className="small solution-more">See how it works →</span>
            </Link>
          ))}
        </div>
        <p style={{ marginTop: 18 }}>
          <Link to="/growth-audit">Not sure where to start? Run a free Growth Audit of your website →</Link>
        </p>
      </section>

      <section className="section">
        <SectionHead
          title="What you get every month."
          lede="Finished work you can approve in minutes, not a blank page and a prompt box."
        />
        <Reveal>
          <div className="cap-grid">
            {MONTHLY_OUTCOMES.map((o) => (
              <div key={o.title} className="cap">
                <h3 style={{ marginTop: 0 }}>{o.title}</h3>
                <p>{o.body}</p>
              </div>
            ))}
          </div>
        </Reveal>
        <p style={{ marginTop: 18 }}>
          <Link to="/agents">See the team behind the work →</Link>
        </p>
      </section>

      <div className="rule" />

      <section className="section">
        <SectionHead
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
          title="Autonomy with guardrails you control."
          lede="Every workspace is isolated. Every consequential action needs a person. Every decision is recorded."
        />
        <dl className="trust-list">
          {[
            ['Tenant isolation', 'Every query is scoped to your workspace on the server, and tested on every release.'],
            ['Scoped agent permissions', 'Agents only see the outputs they need, and have no tools beyond structured drafting.'],
            ['Approval controls', 'Version-locked approvals, expiry, revocation and one pending decision per version.'],
            ['Budget limits', 'Per-run, per-agent and per-plan budgets, enforced before any model call.'],
            ['Audit trail', 'Append-only log of who did what, when, exportable with all your data.'],
            ['Stop everything', 'Pause all agents or engage the kill switch instantly; the backend enforces it.'],
          ].map(([t, b]) => (
            <div key={t}>
              <dt>{t}</dt>
              <dd>{b}</dd>
            </div>
          ))}
        </dl>
        <p className="muted small" style={{ marginTop: 16 }}>
          ARC has not yet obtained SOC 2, ISO 27001 or other certifications. <Link to="/security">Read our security approach.</Link>
        </p>
      </section>

      <section className="section">
        <SectionHead title="Plans that grow with your workload." />
        <PricingTable />
        <p style={{ marginTop: 18 }}>
          <Link to="/compare/agency">Compare ARC with what you spend on an agency today →</Link>
        </p>
      </section>

      <section className="section">
        <SectionHead title="Questions, answered." />
        <FaqList id="home-faq" faqs={HOME_FAQS} />
      </section>

      <section className="final-cta">
        <Reveal>
          <h2>Get next month's marketing off your desk.</h2>
          <p className="lede" style={{ margin: '0 auto 30px', color: 'var(--color-muted-fg)', maxWidth: 560 }}>
            Write one brief. Approve the plan and the content. See what each channel brings in.
          </p>
          <CtaPair center />
          <p className="hero-note">
            <Repeat size={12} aria-hidden="true" /> Each month's results shape the next month's plan.
          </p>
        </Reveal>
      </section>
    </>
  )
}
