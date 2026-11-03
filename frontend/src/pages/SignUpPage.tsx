import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function SignUpPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setFieldErrors({})
    setSubmitting(true)
    try {
      await register(email, password, fullName)
      navigate('/create-workspace')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        const next: Record<string, string> = {}
        for (const d of err.details) next[d.field] = d.issue
        setFieldErrors(next)
      } else {
        setError('Registration failed.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-narrow">
      <h1>Create your account</h1>
      {error && <div className="banner error">{error}</div>}
      <form onSubmit={handleSubmit} className="card">
        <div className="field">
          <label htmlFor="full_name">Full name</label>
          <input
            id="full_name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          {fieldErrors.full_name && <span className="error">{fieldErrors.full_name}</span>}
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {fieldErrors.email && <span className="error">{fieldErrors.email}</span>}
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {fieldErrors.password && <span className="error">{fieldErrors.password}</span>}
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/sign-in">Sign in</Link>
      </p>
    </div>
  )
}
