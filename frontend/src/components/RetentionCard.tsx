import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Field } from './ui'

const REASONS = [
  'Too expensive for us right now',
  'Not getting enough results',
  'Missing a feature or integration we need',
  'Too much work to review and approve',
  'Only needed it for one campaign',
  'Switching to another tool or agency',
  'Something else',
]

/** "Thinking of leaving?": offers alternatives first, then sends the request
 *  and reason to the ARC team. Subscription changes themselves only happen
 *  through the payment provider, so this records the request. */
export default function RetentionCard({ orgId, workspaceName, planName }: { orgId: string; workspaceName: string; planName: string }) {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState(REASONS[0])
  const [comment, setComment] = useState('')
  const [wants, setWants] = useState<'cancel' | 'pause' | 'feedback'>('cancel')
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [error, setError] = useState<string | null>(null)

  async function send(e: React.FormEvent) {
    e.preventDefault()
    if (!user) return
    setStatus('sending')
    setError(null)
    const message = [
      `Request: ${wants === 'cancel' ? 'Cancel subscription' : wants === 'pause' ? 'Pause subscription for a month' : 'Feedback only'}`,
      `Workspace: ${workspaceName} (${orgId})`,
      `Plan: ${planName}`,
      `Reason: ${reason}`,
      comment.trim() && `Comment: ${comment.trim()}`,
    ]
      .filter(Boolean)
      .join('\n')
    try {
      await apiRequest('/public/contact', { method: 'POST', body: { name: user.full_name, email: user.email, company: workspaceName, topic: 'cancellation', message } })
      setStatus('sent')
    } catch (err) {
      setStatus('idle')
      setError(err instanceof ApiError ? err.message : 'Could not send your request. Please try again.')
    }
  }

  if (!open)
    return (
      <p className="muted small" style={{ marginTop: 18 }}>
        Thinking of cancelling or pausing?{' '}
        <button type="button" className="link-btn small" onClick={() => setOpen(true)}>
          Tell us first
        </button>
      </p>
    )

  return (
    <div className="card retention-card" style={{ marginTop: 18 }}>
      <h2>Before you go</h2>
      {status === 'sent' ? (
        <div className="banner success">
          Thanks — the ARC team has your request and will reply to {user?.email} within one business day. Your plan stays
          active until then.
        </div>
      ) : (
        <>
          <p className="muted small" style={{ marginTop: -6 }}>These often solve the problem without losing your work:</p>
          <ul className="retention-options">
            <li>
              <strong>Pause all agents</strong> — nothing runs or uses your plan until you resume.{' '}
              <Link to="/app/settings/automation">Automation settings →</Link>
            </li>
            <li>
              <strong>Move to a smaller plan</strong> — keep your workspace, history and brand profile. Choose a plan above.
            </li>
            <li>
              <strong>Get help from a strategist</strong> — a call to get better results from ARC. <Link to="/demo">Book a call →</Link>
            </li>
            <li>
              <strong>Export your data</strong> any time from <Link to="/app/settings/security">Security settings</Link>.
            </li>
          </ul>
          <form onSubmit={send}>
            {error && <div className="banner error">{error}</div>}
            <fieldset className="field" style={{ border: 'none', padding: 0 }}>
              <legend className="small" style={{ fontWeight: 600, marginBottom: 6 }}>What would you like to do?</legend>
              <div className="seg" role="radiogroup" aria-label="Request type">
                {(
                  [
                    ['cancel', 'Cancel'],
                    ['pause', 'Pause for a month'],
                    ['feedback', 'Just give feedback'],
                  ] as const
                ).map(([k, l]) => (
                  <button key={k} type="button" role="radio" aria-checked={wants === k} aria-pressed={wants === k} onClick={() => setWants(k)}>
                    {l}
                  </button>
                ))}
              </div>
            </fieldset>
            <Field id="ret-reason" label="Main reason">
              <select id="ret-reason" value={reason} onChange={(e) => setReason(e.target.value)}>
                {REASONS.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </Field>
            <Field id="ret-comment" label="Anything we could have done better? (optional)">
              <textarea id="ret-comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
            </Field>
            <div className="head-actions">
              <button type="submit" disabled={status === 'sending'}>
                {status === 'sending' ? 'Sending…' : 'Send to the ARC team'}
              </button>
              <button type="button" className="secondary" onClick={() => setOpen(false)}>
                Never mind
              </button>
            </div>
            <p className="muted small" style={{ marginBottom: 0 }}>
              Cancelling takes effect at the end of the period you paid for. See <Link to="/refunds">Refunds and Cancellation</Link>.
            </p>
          </form>
        </>
      )}
    </div>
  )
}
