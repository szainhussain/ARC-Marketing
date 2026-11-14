import { Component, type ErrorInfo, type ReactNode } from 'react'

/** Last line of defence: a render error shows a recovery screen instead of a blank page. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ARC render error', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main role="alert" style={{ maxWidth: 520, margin: '18vh auto', padding: '0 20px', textAlign: 'center' }}>
        <h1 style={{ fontSize: 24 }}>Something went wrong on this page.</h1>
        <p className="muted">Your work is saved. Reload to carry on; if it keeps happening, contact us and we will look into it.</p>
        <p style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 20 }}>
          <button className="btn" onClick={() => window.location.reload()}>
            Reload
          </button>
          <a className="btn secondary" href="/">
            Go to the home page
          </a>
        </p>
      </main>
    )
  }
}
