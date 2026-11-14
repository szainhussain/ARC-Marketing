import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle2, ShieldCheck } from 'lucide-react'
import { apiRequest, ApiError } from '../../api/client'
import DeliverableContent from '../../components/DeliverableContent'
import { ErrorState, Field, PageSkeleton } from '../../components/ui'
import { useResource } from '../../hooks/useResource'
import { humanize, relativeTime } from '../../lib/labels'
import { usePageMeta } from '../../lib/seo'

type Review = {
  workspace_name: string
  deliverable_type: string
  version_number: number
  content: Record<string, unknown>
  decision: string
  decided_at: string | null
  can_decide: boolean
  superseded: boolean
  expires_at: string
  comments: { id: string; author_name: string; body: string; created_at: string }[]
}

const DECISION_TEXT: Record<string, string> = {
  approved: 'approved',
  rejected: 'rejected',
  changes_requested: 'sent back with requested changes',
  invalidated: 'replaced by a newer version',
  expired: 'expired',
  revoked: 'withdrawn',
}

/** Public page behind a review link: the client sees one exact version and can
 *  decide once. The token in the URL is the only credential. */
export default function ReviewPage() {
  const { token = '' } = useParams()
  usePageMeta('Review', 'Review marketing work shared with you through ARC.')
  const { data, error, reload } = useResource<Review>(`/public/review/${encodeURIComponent(token)}`)
  const [form, setForm] = useState({ name: '', email: '', comment: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [failure, setFailure] = useState<string | null>(null)

  if (error && !data) return <section className="section" style={{ maxWidth: 720 }}><ErrorState message={error} /></section>
  if (!data) return <PageSkeleton />

  async function decide(decision: 'approved' | 'changes_requested' | 'rejected') {
    const local: Record<string, string> = {}
    if (!form.name.trim()) local.name = 'Required'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) local.email = 'A valid email is required'
    if (decision !== 'approved' && !form.comment.trim()) local.comment = 'Tell the team what to change'
    setErrors(local)
    if (Object.keys(local).length) return
    setBusy(true)
    setFailure(null)
    try {
      await apiRequest(`/public/review/${encodeURIComponent(token)}/decision`, { method: 'POST', body: { decision, ...form } })
      setMessage(decision === 'approved' ? 'Thank you, you approved this version.' : 'Thank you, your feedback was sent to the team.')
      reload()
    } catch (err) {
      setFailure(err instanceof ApiError ? err.message : 'Could not send your decision. Please try again.')
      if (err instanceof ApiError) setErrors(Object.fromEntries(err.details.map((d) => [d.field, d.issue])))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section review-page">
      <h1 className="display-page" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
        {humanize(data.deliverable_type)}
      </h1>
      <p className="muted">
        Shared by {data.workspace_name || 'your marketing team'} · Version {data.version_number} · link expires {relativeTime(data.expires_at)}
      </p>

      {message && (
        <div className="banner success">
          <CheckCircle2 size={15} aria-hidden="true" /> {message}
        </div>
      )}
      {!message && !data.can_decide && (
        <div className="banner warning">
          {data.superseded
            ? 'The team has changed this content since sharing it, so this version can no longer be approved. Ask them for a new link.'
            : `This was ${DECISION_TEXT[data.decision] || data.decision}${data.decided_at ? ` ${relativeTime(data.decided_at)}` : ''}. No further decision is needed.`}
        </div>
      )}

      <div className="card">
        <DeliverableContent deliverableType={data.deliverable_type} content={data.content} />
      </div>

      {data.comments.length > 0 && (
        <div className="card">
          <h2>Feedback</h2>
          <ul className="comment-list">
            {data.comments.map((c) => (
              <li key={c.id}>
                <div className="small">
                  <strong>{c.author_name}</strong> <span className="muted">· {relativeTime(c.created_at)}</span>
                </div>
                <p>{c.body}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.can_decide && !message && (
        <div className="card">
          <h2>Your decision</h2>
          <p className="muted small" style={{ marginTop: -6 }}>
            <ShieldCheck size={13} aria-hidden="true" /> Your decision applies to version {data.version_number} only and is recorded with your name
            and email.
          </p>
          {failure && <div className="banner error">{failure}</div>}
          <div className="form-grid">
            <Field id="rv-name" label="Your name" error={errors.name}>
              <input id="rv-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" />
            </Field>
            <Field id="rv-email" label="Your email" error={errors.email}>
              <input id="rv-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
            </Field>
          </div>
          <Field id="rv-comment" label="Comments (needed if you request changes)" error={errors.comment}>
            <textarea id="rv-comment" rows={3} value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} />
          </Field>
          <div className="head-actions">
            <button type="button" disabled={busy} onClick={() => decide('approved')}>
              Approve
            </button>
            <button type="button" className="secondary" disabled={busy} onClick={() => decide('changes_requested')}>
              Request changes
            </button>
            <button type="button" className="danger" disabled={busy} onClick={() => decide('rejected')}>
              Reject
            </button>
          </div>
        </div>
      )}
      <p className="muted small">Shared securely through ARC. Only people with this link can see this page.</p>
    </section>
  )
}
