import { Link } from 'react-router-dom'

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
        <h1>Your coordinated AI marketing team.</h1>
        <p>
          Plan, create, and review campaigns with a workflow that keeps every deliverable
          versioned and every consequential action behind a human approval. Nothing is marked
          published until you confirm it actually happened.
        </p>
        <Link to="/sign-up" className="btn">
          Start a pilot
        </Link>
      </div>
      <div className="page">
        <div className="card">
          <h2>How it works</h2>
          <p className="muted">
            Brief → Plan → Create → Review → Approve → Hand off. Each stage is a persisted,
            inspectable record — not a hidden chat transcript.
          </p>
        </div>
        <div className="card">
          <h2>Scope of this pilot</h2>
          <p className="muted">
            This release runs one coordinated workflow (strategy, research notes, campaign plan,
            content pack, quality review) and a manual export/handoff for publishing — not fully
            autonomous posting, ad spend changes, or guaranteed marketing results.
          </p>
        </div>
      </div>
    </div>
  )
}
