import { Suspense, useEffect, useState } from 'react'
import ThemeToggle from './ThemeToggle'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'
import { PageSkeleton } from './ui'
import { API_BASE_URL } from '../lib/apiBase'

const LINKS = [
  { to: '/product', label: 'Product' },
  { to: '/solutions', label: 'Solutions' },
  { to: '/how-it-works', label: 'How it works' },
  { to: '/agents', label: 'Agents' },
  { to: '/pricing', label: 'Pricing' },
]

export default function PublicLayout() {
  const [open, setOpen] = useState(false)
  const { user } = useAuth()
  const location = useLocation()
  useEffect(() => {
    setOpen(false)
    window.scrollTo(0, 0)
  }, [location.pathname])

  return (
    <div>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="site-header">
        <Link to="/" className="brand" aria-label="ARC home">
          <Logo size={26} />
          ARC
        </Link>
        <nav className="site-nav" aria-label="Primary">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <span className="spacer" />
        <div className="site-actions">
          <ThemeToggle />
          {user ? (
            <Link to="/app/dashboard" className="btn desktop">
              Open workspace
            </Link>
          ) : (
            <>
              <Link to="/login" className="signin desktop">
                Sign in
              </Link>
              <Link to="/demo" className="btn secondary desktop">
                Book a demo
              </Link>
              <Link to="/signup" className="btn desktop">
                Start free trial
              </Link>
            </>
          )}
          <button
            className="icon-btn mobile-menu"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>
      {open && (
        <nav id="mobile-nav" className="mobile-nav-panel" aria-label="Mobile">
          {LINKS.map((l) => (
            <Link key={l.to} to={l.to}>
              {l.label}
            </Link>
          ))}
          <Link to="/integrations">Integrations</Link>
          <Link to="/security">Security</Link>
          <Link to="/demo">Book a demo</Link>
          <Link to={user ? '/app/dashboard' : '/login'}>{user ? 'Open workspace' : 'Sign in'}</Link>
          {!user && (
            <Link to="/signup" className="btn" style={{ marginTop: 10, justifyContent: 'center' }}>
              Start free trial
            </Link>
          )}
        </nav>
      )}
      <main id="main" tabIndex={-1}>
        <Suspense fallback={<PageSkeleton />}>
          <Outlet />
        </Suspense>
      </main>
      <footer className="site-footer">
        <div className="footer-grid">
          <div>
            <Link to="/" className="brand" style={{ display: 'flex', gap: 10, alignItems: 'center', fontWeight: 800, color: 'var(--color-fg)' }}>
              <Logo size={24} /> ARC
            </Link>
            <p className="muted small" style={{ maxWidth: 300, marginTop: 12 }}>
              Your marketing department. Always moving. Twelve specialist AI agents, one coordinated workspace, your
              approval on what matters.
            </p>
          </div>
          <div>
            <h4>Product</h4>
            <Link to="/product">Overview</Link>
            <Link to="/solutions">Solutions</Link>
            <Link to="/agents">The 12 agents</Link>
            <Link to="/how-it-works">How it works</Link>
            <Link to="/integrations">Integrations</Link>
            <Link to="/pricing">Pricing</Link>
          </div>
          <div>
            <h4>Trust & legal</h4>
            <Link to="/security">Security</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
            <Link to="/ai-policy">AI Use Policy</Link>
            <Link to="/dpa">DPA</Link>
            <Link to="/legal">All legal documents</Link>
          </div>
          <div>
            <h4>Resources</h4>
            <Link to="/marketing-scorecard">Free marketing scorecard</Link>
            <Link to="/compare/agency">ARC vs an agency</Link>
            <Link to="/docs">Documentation</Link>
            <a href={`${API_BASE_URL}/openapi.json`}>API reference</a>
            <a href={`${API_BASE_URL}/health/ready`}>System status</a>
          </div>
          <div>
            <h4>Company</h4>
            <Link to="/about">About</Link>
            <Link to="/demo">Book a demo</Link>
            <Link to="/contact">Contact</Link>
          </div>
        </div>
        <div className="footer-fine">
          <span>© {new Date().getFullYear()} ARC. Outcomes depend on your business, data, channels and budget.</span>
          <span className="mono">
            Strategy · Plan · Execution · <span data-testid="build">build {__APP_COMMIT__}</span>
          </span>
        </div>
      </footer>
    </div>
  )
}
