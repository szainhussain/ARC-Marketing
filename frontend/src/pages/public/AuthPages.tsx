import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../../api/client'
import { Field } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useWorkspace } from '../../context/WorkspaceContext'

function fieldErrors(err: unknown): Record<string, string> {
  return err instanceof ApiError ? Object.fromEntries(err.details.map((d) => [d.field, d.issue])) : {}
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      const next = params.get('next')
      navigate(next && next.startsWith('/') && !next.startsWith('//') ? next : '/app/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the ARC service. It may be waking up — try again in a minute.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <h1>Welcome back</h1>
        <p className="muted">Sign in to your marketing workspace.</p>
        {error && <div className="banner error" role="alert">{error}</div>}
        <Field id="login-email" label="Email">
          <input id="login-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field id="login-password" label="Password">
          <input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="small" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 0 }}>
          <Link to="/forgot-password">Forgot password?</Link>
          <Link to={`/signup${params.get('next') ? `?next=${encodeURIComponent(params.get('next') as string)}` : ''}`}>Create an account</Link>
        </p>
      </form>
    </div>
  )
}

export function SignupPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [accepted, setAccepted] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    const local: Record<string, string> = {}
    if (!form.full_name.trim()) local.full_name = 'Required'
    if (!accepted) local.accept_terms = 'Please accept the Terms of Service and Privacy Policy'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) local.email = 'A valid email is required'
    if (form.password.length < 8) local.password = 'Must be at least 8 characters'
    setErrors(local)
    if (Object.keys(local).length) return
    setBusy(true)
    setError(null)
    try {
      await register(form.email, form.password, form.full_name, accepted)
      const next = params.get('next')
      navigate(next && next.startsWith('/accept-invite') ? next : '/create-workspace')
    } catch (err) {
      setErrors(fieldErrors(err))
      setError(err instanceof ApiError ? err.message : 'Could not reach the ARC service. It may be waking up — try again in a minute.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit} noValidate>
        <h1>Build your marketing team</h1>
        <p className="muted">Create your account. You’ll set up your workspace next.</p>
        {error && <div className="banner error" role="alert">{error}</div>}
        <Field id="su-name" label="Full name" error={errors.full_name}>
          <input id="su-name" autoComplete="name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        </Field>
        <Field id="su-email" label="Email" error={errors.email}>
          <input id="su-email" type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field id="su-password" label="Password" error={errors.password} hint="At least 8 characters.">
          <input id="su-password" type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        <div className={`consent${errors.accept_terms ? ' has-error' : ''}`}>
          <input
            id="su-terms"
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            aria-invalid={!!errors.accept_terms}
            aria-describedby={errors.accept_terms ? 'su-terms-error' : undefined}
          />
          <label htmlFor="su-terms">
            I agree to the{' '}
            <Link to="/terms" target="_blank">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link to="/privacy" target="_blank">
              Privacy Policy
            </Link>
            .
          </label>
        </div>
        {errors.accept_terms && (
          <p id="su-terms-error" className="small text-danger" role="alert" style={{ marginTop: -6 }}>
            {errors.accept_terms}
          </p>
        )}
        <button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="small muted" style={{ marginBottom: 0 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  )
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const r = await apiRequest<{ message: string }>('/auth/forgot-password', { method: 'POST', body: { email } })
      setMessage(r.message)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send reset link.')
    }
  }
  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <h1>Reset password</h1>
        {message ? (
          <>
            <div className="banner success">{message}</div>
            <p className="muted small">
              Email delivery isn’t configured in this deployment yet; administrators can find the link in the server log.
            </p>
          </>
        ) : (
          <>
            <p className="muted">We’ll send a reset link if an account exists for this email.</p>
            {error && <div className="banner error">{error}</div>}
            <Field id="fp-email" label="Email">
              <input id="fp-email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <button type="submit">Send reset link</button>
          </>
        )}
        <p className="small" style={{ marginBottom: 0 }}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </form>
    </div>
  )
}

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await apiRequest('/auth/reset-password', { method: 'POST', body: { token: params.get('token'), password } })
      setDone(true)
      window.setTimeout(() => navigate('/login'), 1500)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reset password.')
    }
  }
  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <h1>Choose a new password</h1>
        {done ? (
          <div className="banner success">Password updated. Every other session was signed out. Redirecting…</div>
        ) : (
          <>
            {error && <div className="banner error">{error}</div>}
            <Field id="rp-password" label="New password" hint="At least 8 characters.">
              <input id="rp-password" type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <button type="submit">Update password</button>
          </>
        )}
      </form>
    </div>
  )
}

export function AcceptInvitePage() {
  const [params] = useSearchParams()
  const { user, loading, refresh } = useAuth()
  const { setActiveOrganizationId } = useWorkspace()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const token = params.get('token') || ''
  const next = `/accept-invite?token=${encodeURIComponent(token)}`

  async function accept() {
    setError(null)
    try {
      const r = await apiRequest<{ organization_id: string }>('/invitations/accept', { method: 'POST', body: { token } })
      await refresh()
      setActiveOrganizationId(r.organization_id)
      navigate('/app/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not accept the invitation.')
    }
  }

  if (loading) return <div className="auth-wrap">Loading…</div>
  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <h1>Join a workspace</h1>
        {error && <div className="banner error">{error}</div>}
        {user ? (
          <>
            <p className="muted">Signed in as {user.email}. The invitation must be for this email.</p>
            <button onClick={accept}>Accept invitation</button>
          </>
        ) : (
          <>
            <p className="muted">Sign in or create an account with the invited email to accept.</p>
            <div className="cta-row" style={{ justifyContent: 'flex-start' }}>
              <Link className="btn" to={`/login?next=${encodeURIComponent(next)}`}>
                Sign in
              </Link>
              <Link className="btn secondary" to={`/signup?next=${encodeURIComponent(next)}`}>
                Create account
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const { user, refresh } = useAuth()
  const [state, setState] = useState<'pending' | 'ok' | 'error'>('pending')
  const [message, setMessage] = useState('')
  useEffect(() => {
    if (!user) return
    let cancelled = false
    apiRequest('/auth/verify-email', { method: 'POST', body: { token: params.get('token') } })
      .then(() => {
        if (!cancelled) {
          setState('ok')
          refresh()
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setState('error')
          setMessage(err instanceof ApiError ? err.message : 'Verification failed.')
        }
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id])
  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <h1>Verify email</h1>
        {!user && (
          <p>
            Please <Link to={`/login?next=${encodeURIComponent(`/verify-email?token=${params.get('token') || ''}`)}`}>sign in</Link> first.
          </p>
        )}
        {user && state === 'pending' && <p className="muted">Verifying…</p>}
        {state === 'ok' && <div className="banner success">Email verified.</div>}
        {state === 'error' && <div className="banner error">{message}</div>}
        <Link to="/app/dashboard">Go to your workspace</Link>
      </div>
    </div>
  )
}
