import { Link } from 'react-router-dom'
import Reveal from '../components/motion/Reveal'
import TiltCard from '../components/motion/TiltCard'

const STEPS = ['Brief', 'Plan', 'Create', 'Review', 'Approve', 'Hand off']

const FEATURES = [
  {
    icon: '◆',
    title: 'Versioned by default',
    body: 'Every deliverable is an immutable version. Editing never overwrites — it creates a new one and invalidates any stale approval.',
  },
  {
    icon: '◎',
    title: 'Approval, not vibes',
    body: 'Consequential actions require a human decision tied to the exact content version and action — re-checked immediately before anything runs.',
  },
  {
    icon: '✓',
    title: 'Honest status, always',
    body: 'If a stage can’t run, it says so. Nothing is fabricated to look like progress — see the real workflow and task state.',
  },
]

export default function LandingPage() {
  return (
    <div>
      <nav className="app-nav">
        <span className="brand">
          <span className="mark" />
          ARC
        </span>
        <span className="spacer" />
        <Link to="/sign-in">Sign in</Link>
        <Link to="/sign-up" className="btn accent">
          Create workspace
        </Link>
      </nav>

      <div className="hero">
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-glow" aria-hidden="true" />

        <span className="tag">
          <span className="dot" />
          Strategy &middot; Plan &middot; Execution
        </span>
        <h1>
          Your marketing department, <span className="accent-text">running on its own.</span>
        </h1>
        <p>
          ARC plans, drafts, and reviews campaigns continuously — and keeps every consequential
          action behind your approval. Nothing is marked published until you confirm it actually
          happened.
        </p>
        <Link to="/sign-up" className="btn accent">
          Start a pilot →
        </Link>

        <div className="workflow-strip">
          {STEPS.map((step, i) => (
            <div style={{ display: 'flex', alignItems: 'flex-start' }} key={step}>
              <div className="workflow-step">
                <div className="num">{i + 1}</div>
                <div className="label">{step}</div>
              </div>
              {i < STEPS.length - 1 && <span className="workflow-arrow">→</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="page">
        <div className="feature-grid">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.08}>
              <TiltCard className="card hoverable">
                <div className="feature-icon">{f.icon}</div>
                <h2>{f.title}</h2>
                <p className="muted" style={{ margin: 0 }}>
                  {f.body}
                </p>
              </TiltCard>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.2}>
          <div className="card" style={{ marginTop: 18 }}>
            <h2>Scope of this pilot</h2>
            <p className="muted" style={{ margin: 0 }}>
              This release runs one coordinated workflow (strategy, research notes, campaign plan,
              content pack, quality review) and a manual export/handoff for publishing — not fully
              autonomous posting, ad spend changes, or guaranteed marketing results.
            </p>
          </div>
        </Reveal>
      </div>
    </div>
  )
}
