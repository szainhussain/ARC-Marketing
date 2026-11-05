import { useState } from 'react'
import { Copy, Link2, MessageSquare, Pencil } from 'lucide-react'
import { apiRequest, ApiError } from '../api/client'
import { useResource } from '../hooks/useResource'
import { humanize, relativeTime } from '../lib/labels'
import { useToast } from './ui'

type Content = Record<string, unknown>
type Comment = { id: string; author_name: string; is_external: boolean; body: string; created_at: string }

const isStringList = (v: unknown): v is string[] => Array.isArray(v) && v.every((x) => typeof x === 'string')

/** Generic editor for any deliverable: text fields as text, string lists one
 *  per line, anything structured as JSON. The server validates the result
 *  against the deliverable's schema and saves it as a new version. */
export function DeliverableEditor({
  orgId,
  deliverableId,
  content,
  onSaved,
  onCancel,
}: {
  orgId: string
  deliverableId: string
  content: Content
  onSaved: () => void
  onCancel: () => void
}) {
  const toast = useToast()
  const [draft, setDraft] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      Object.entries(content).map(([k, v]) => [k, typeof v === 'string' ? v : isStringList(v) ? v.join('\n') : JSON.stringify(v, null, 2)]),
    ),
  )
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function save() {
    const out: Content = {}
    const local: Record<string, string> = {}
    for (const [k, original] of Object.entries(content)) {
      const text = draft[k] ?? ''
      if (typeof original === 'string') out[k] = text
      else if (isStringList(original)) out[k] = text.split('\n').map((l) => l.trim()).filter(Boolean)
      else {
        try {
          out[k] = JSON.parse(text)
        } catch {
          local[k] = 'This section must stay valid JSON'
        }
      }
    }
    setErrors(local)
    if (Object.keys(local).length) return
    setBusy(true)
    setError(null)
    try {
      const r = await apiRequest<{ brand_check: { passed: boolean; detail: string | null } }>(
        `/organizations/${orgId}/deliverables/${deliverableId}/versions`,
        { method: 'POST', body: { content: out, revision_reason: reason.trim() || 'Edited in ARC' } },
      )
      toast(
        r.brand_check.passed
          ? { tone: 'success', title: 'Saved as a new version. Request approval again when ready.' }
          : { tone: 'error', title: `Saved, but check your brand rules: ${r.brand_check.detail}` },
      )
      onSaved()
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        setErrors(Object.fromEntries(err.details.map((d) => [d.field.replace(/^content\./, ''), d.issue])))
      } else setError('Could not save your changes.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="editor">
      <p className="muted small" style={{ marginTop: 0 }}>
        Saving creates a new version. Any pending approval for the current version is withdrawn automatically.
      </p>
      {error && <div className="banner error">{error}</div>}
      {Object.entries(content).map(([k, original]) => {
        const id = `edit-${deliverableId}-${k}`
        const structured = typeof original !== 'string' && !isStringList(original)
        return (
          <div key={k} className="field">
            <label htmlFor={id}>
              {humanize(k)}
              {isStringList(original) && <span className="muted small"> · one per line</span>}
              {structured && <span className="muted small"> · advanced (JSON)</span>}
            </label>
            <textarea
              id={id}
              rows={structured ? 8 : Math.min(10, Math.max(3, (draft[k] || '').split('\n').length + 1))}
              className={structured ? 'mono small' : undefined}
              value={draft[k] ?? ''}
              onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
              aria-invalid={!!errors[k]}
            />
            {errors[k] && <span className="error" role="alert">{errors[k]}</span>}
          </div>
        )
      })}
      <div className="field">
        <label htmlFor={`edit-${deliverableId}-reason`}>What changed? (optional)</label>
        <input id={`edit-${deliverableId}-reason`} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Shortened captions, fixed the offer date" />
      </div>
      <div className="head-actions">
        <button type="button" disabled={busy} onClick={save}>
          {busy ? 'Saving…' : 'Save new version'}
        </button>
        <button type="button" className="secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  )
}

export function CommentsPanel({ orgId, deliverableId }: { orgId: string; deliverableId: string }) {
  const { data, reload } = useResource<{ comments: Comment[] }>(`/organizations/${orgId}/deliverables/${deliverableId}/comments`)
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const comments = data?.comments || []

  async function post(e: React.FormEvent) {
    e.preventDefault()
    if (!body.trim()) return
    setBusy(true)
    setError(null)
    try {
      await apiRequest(`/organizations/${orgId}/deliverables/${deliverableId}/comments`, { method: 'POST', body: { body } })
      setBody('')
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not post your comment.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="comments">
      {comments.length === 0 ? (
        <p className="muted small">No comments yet. Comments stay inside your workspace; clients only see their own.</p>
      ) : (
        <ul className="comment-list">
          {comments.map((c) => (
            <li key={c.id}>
              <div className="small">
                <strong>{c.author_name}</strong>
                {c.is_external && <span className="tag-chip" style={{ marginLeft: 6 }}>Client</span>}
                <span className="muted"> · {relativeTime(c.created_at)}</span>
              </div>
              <p>{c.body}</p>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={post} className="comment-form">
        <label htmlFor={`comment-${deliverableId}`} className="sr-only">
          Add a comment
        </label>
        <textarea id={`comment-${deliverableId}`} rows={2} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a comment for your team…" />
        <button type="submit" className="secondary" disabled={busy || !body.trim()}>
          {busy ? 'Posting…' : 'Comment'}
        </button>
      </form>
      {error && <div className="banner error">{error}</div>}
    </div>
  )
}

export function ShareForReview({ orgId, approvalId }: { orgId: string; approvalId: string }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [label, setLabel] = useState('')
  const [days, setDays] = useState('7')
  const [url, setUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const links = useResource<{ review_links: { id: string; label: string | null; expires_at: string; revoked_at: string | null; used_at: string | null }[] }>(
    open ? `/organizations/${orgId}/approvals/${approvalId}/review-links` : null,
  )
  const active = (links.data?.review_links || []).filter((l) => !l.revoked_at && !l.used_at && new Date(l.expires_at) > new Date())

  async function withdraw(linkId: string) {
    try {
      await apiRequest(`/organizations/${orgId}/review-links/${linkId}`, { method: 'DELETE' })
      toast({ tone: 'success', title: 'Review link withdrawn' })
      setUrl(null)
      links.reload()
    } catch {
      toast({ tone: 'error', title: 'Could not withdraw the link' })
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const r = await apiRequest<{ url: string }>(`/organizations/${orgId}/approvals/${approvalId}/review-links`, {
        method: 'POST',
        body: { label, days: Number(days) },
      })
      setUrl(r.url)
      links.reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the link.')
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    if (!url) return
    try {
      await navigator.clipboard.writeText(url)
      toast({ tone: 'success', title: 'Link copied' })
    } catch {
      toast({ tone: 'info', title: 'Select the link and copy it manually' })
    }
  }

  if (!open)
    return (
      <button type="button" className="secondary" onClick={() => setOpen(true)}>
        <Link2 size={14} aria-hidden="true" /> Share for client review
      </button>
    )
  return (
    <div className="share-box">
      {url ? (
        <>
          <p className="small" style={{ marginTop: 0 }}>
            Send this link to your client. They can approve, request changes or reject <strong>this exact version</strong>{' '}
            once, without an ARC account. It stops working if you edit the content.
          </p>
          <div className="share-url">
            <label htmlFor={`share-${approvalId}`} className="sr-only">
              Review link
            </label>
            <input id={`share-${approvalId}`} readOnly value={url} onFocus={(e) => e.target.select()} />
            <button type="button" onClick={copy}>
              <Copy size={14} aria-hidden="true" /> Copy
            </button>
          </div>
          <p className="muted small">This is the only time the full link is shown. Withdraw it below if it was sent to the wrong person.</p>
        </>
      ) : (
        <form onSubmit={create} className="share-form">
          <div className="field">
            <label htmlFor={`share-label-${approvalId}`}>Who is it for? (optional)</label>
            <input id={`share-label-${approvalId}`} value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Sara at Trailhead" />
          </div>
          <div className="field">
            <label htmlFor={`share-days-${approvalId}`}>Link works for</label>
            <select id={`share-days-${approvalId}`} value={days} onChange={(e) => setDays(e.target.value)}>
              {['1', '3', '7', '14'].map((d) => (
                <option key={d} value={d}>
                  {d} day{d === '1' ? '' : 's'}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={busy}>
            {busy ? 'Creating…' : 'Create review link'}
          </button>
          <button type="button" className="link-btn" onClick={() => setOpen(false)}>
            Cancel
          </button>
        </form>
      )}
      {active.length > 0 && (
        <ul className="share-links">
          {active.map((l) => (
            <li key={l.id} className="small">
              <span>
                Active link{l.label ? ` for ${l.label}` : ''} · expires {relativeTime(l.expires_at)}
              </span>
              <button type="button" className="link-btn small" onClick={() => withdraw(l.id)}>
                Withdraw
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && <div className="banner error">{error}</div>}
    </div>
  )
}

export function CollabToolbar({
  editing,
  onEdit,
  commentsOpen,
  onToggleComments,
}: {
  editing: boolean
  onEdit: () => void
  commentsOpen: boolean
  onToggleComments: () => void
}) {
  return (
    <div className="collab-toolbar">
      {!editing && (
        <button type="button" className="link-btn" onClick={onEdit}>
          <Pencil size={14} aria-hidden="true" /> Edit
        </button>
      )}
      <button type="button" className="link-btn" onClick={onToggleComments} aria-expanded={commentsOpen}>
        <MessageSquare size={14} aria-hidden="true" /> {commentsOpen ? 'Hide comments' : 'Comments'}
      </button>
    </div>
  )
}
