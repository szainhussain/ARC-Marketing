import { Link } from 'react-router-dom'

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
        <span className="brand">Marketing Department Harness</span>
        <span className="spacer" />
        <Link to="/sign-in">Sign in</Link>
        <Link to="/sign-up" className="btn">
          Create workspace
        </Link>
      </nav>

      <div className="hero">
        <span className="tag">AI marketing, with a human in the loop</span>
        <h1>Your coordinated AI marketing team.</h1>
        <p>
          Plan, create, and review campaigns with a workflow that keeps every deliverable
          versioned and every consequential action behind a human approval. Nothing is marked
          published until you confirm it actually happened.
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
          {FEATURES.map((f) => (
            <div className="card hoverable" key={f.title}>
              <div className="feature-icon">{f.icon}</div>
              <h2>{f.title}</h2>
              <p className="muted" style={{ margin: 0 }}>
                {f.body}
              </p>
            </div>
          ))}
        </div>

        <div className="card" style={{ marginTop: 18 }}>
          <h2>Scope of this pilot</h2>
          <p className="muted" style={{ margin: 0 }}>
            This release runs one coordinated workflow (strategy, research notes, campaign plan,
            content pack, quality review) and a manual export/handoff for publishing — not fully
            autonomous posting, ad spend changes, or guaranteed marketing results.
          </p>
        </div>
      </div>
    </div>
  )
}
