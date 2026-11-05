import { useEffect, useState } from 'react'
import { Mail, Plus, Upload } from 'lucide-react'
import { apiRequest, ApiError } from '../../api/client'
import { DataTable, Dialog, EmptyState, ErrorState, Field, PageHeader, PageSkeleton, StatusPill, useToast } from '../../components/ui'
import { useWorkspace } from '../../context/WorkspaceContext'
import { useResource } from '../../hooks/useResource'
import { humanize, relativeTime } from '../../lib/labels'

type Sender = { connected: boolean; state: string; provider: string | null; sender_email: string | null; sender_name: string | null; postal_address: string | null; reply_to: string | null; daily_cap: number }
type List = { id: string; name: string; lawful_basis: string; source_description: string; active: number; unsubscribed: number; total: number; created_at: string }
type Batch = {
  id: string; name: string; list_id: string; list_name: string | null; subject: string; body: string; daily_limit: number
  status: 'draft' | 'pending_approval' | 'approved' | 'sending' | 'paused' | 'completed' | 'cancelled'
  last_error: string | null; sent_today: number; counts: Record<'queued' | 'sending' | 'sent' | 'failed' | 'skipped', number>; created_at: string
}
type Overview = { sender: Sender; lists: List[]; batches: Batch[] }
type Draft = { subject: string; message: string; target_type: string; channel: string; from: string; deliverable_id: string }

const BASIS: Record<string, string> = {
  consent: 'They signed up / gave consent',
  existing_customer: 'They are existing customers',
  legitimate_interest: 'Business contacts with a relevant interest',
}
const PILL: Record<Batch['status'], string> = {
  draft: 'cancelled', pending_approval: 'pending', approved: 'approved', sending: 'running', paused: 'retrying', completed: 'succeeded', cancelled: 'cancelled',
}

export default function OutreachPage() {
  const { activeOrganizationId: orgId } = useWorkspace()
  const toast = useToast()
  const [pollMs, setPollMs] = useState<number | undefined>(undefined)
  const { data, error, loading, reload } = useResource<Overview>(orgId ? `/organizations/${orgId}/outreach` : null, { pollMs })
  const sending = !!data?.batches.some((b) => b.status === 'sending')
  useEffect(() => {
    setPollMs(sending ? 5000 : undefined)
  }, [sending])
  const [dialog, setDialog] = useState<null | 'sender' | 'list' | 'batch'>(null)
  const [previewing, setPreviewing] = useState<{ subject: string; text: string; to: string } | null>(null)

  async function act(batch: Batch, action: string, done: string) {
    try {
      await apiRequest(`/organizations/${orgId}/outreach/batches/${batch.id}/${action}`, { method: 'POST' })
      toast({ tone: 'success', title: done })
      reload()
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Something went wrong' })
    }
  }
  async function preview(batch: Batch) {
    try {
      const r = await apiRequest<{ preview: { subject: string; text: string; to: string } }>(`/organizations/${orgId}/outreach/batches/${batch.id}/preview`)
      setPreviewing(r.preview)
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not load the preview' })
    }
  }

  if (!orgId) return null
  if (loading && !data) return <PageSkeleton />
  const sender = data?.sender

  return (
    <div className="page page-wide">
      <PageHeader
        title="Outreach"
        description="Email people on lists you're allowed to contact, from your own email account. Every batch is approved as a whole, sent within a daily limit, and every email has a one-click unsubscribe."
      />
      {error && <ErrorState message={error} />}

      <div className="card">
        <div className="card-head">
          <h2><Mail size={18} aria-hidden="true" /> Sending account</h2>
          {sender && <StatusPill status={sender.connected ? 'active' : 'cancelled'} label={sender.connected ? 'Connected' : sender.state === 'reauth_required' ? 'Reconnect needed' : 'Not connected'} />}
        </div>
        {sender?.connected ? (
          <div className="head-actions">
            <span className="small">
              {humanize(sender.provider || '')} · {sender.sender_name} &lt;{sender.sender_email}&gt; · {sender.postal_address}
            </span>
            <button className="secondary small-btn" onClick={() => setDialog('sender')}>Change</button>
          </div>
        ) : (
          <div className="head-actions">
            <span className="muted small">Connect your Brevo or Resend account. Emails go out from your verified address.</span>
            <button className="small-btn" onClick={() => setDialog('sender')}>Connect sender</button>
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-head">
          <h2>Contact lists</h2>
          <button className="small-btn" onClick={() => setDialog('list')}><Upload size={14} aria-hidden="true" /> Upload list</button>
        </div>
        <DataTable rows={data?.lists || []} rowKey={(r) => r.id} caption="Contact lists"
          empty={<EmptyState title="No contact lists yet" body="Upload a CSV of people you're allowed to email: customers, sign-ups or business contacts. ARC never scrapes contacts." />}
          columns={[
            { key: 'n', header: 'List', render: (r) => <><strong>{r.name}</strong><div className="muted small">{r.source_description}</div></> },
            { key: 'b', header: 'Lawful basis', render: (r) => <span className="small">{BASIS[r.lawful_basis] || humanize(r.lawful_basis)}</span> },
            { key: 'c', header: 'Contacts', render: (r) => <span className="small">{r.active} active{r.unsubscribed ? ` · ${r.unsubscribed} unsubscribed` : ''}</span> },
            { key: 'd', header: 'Added', render: (r) => <span className="small">{relativeTime(r.created_at)}</span> },
          ]} />
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-head">
          <h2>Batches</h2>
          <button className="small-btn" disabled={!data?.lists.length} onClick={() => setDialog('batch')}><Plus size={14} aria-hidden="true" /> New batch</button>
        </div>
        <DataTable rows={data?.batches || []} rowKey={(r) => r.id} caption="Outreach batches"
          empty={<EmptyState title="No batches yet" body="Write one email for a list, get it approved, then ARC sends it a few at a time." />}
          columns={[
            { key: 'n', header: 'Batch', render: (r) => <><strong>{r.name}</strong><div className="muted small">{r.subject} · to {r.list_name}</div>{r.last_error && <div className="small" style={{ color: 'var(--color-warning)' }}>{r.last_error}</div>}</> },
            { key: 's', header: 'Status', render: (r) => <StatusPill status={PILL[r.status]} label={humanize(r.status)} /> },
            { key: 'p', header: 'Progress', render: (r) => <span className="small">{r.counts.sent} sent · {r.counts.queued} to go{r.counts.failed ? ` · ${r.counts.failed} failed` : ''}<div className="muted">{r.sent_today}/{r.daily_limit} today</div></span> },
            {
              key: 'a', header: '', render: (r) => (
                <span className="head-actions" style={{ margin: 0 }}>
                  <button className="secondary small-btn" onClick={() => preview(r)}>Preview</button>
                  {r.status === 'draft' && <button className="small-btn" onClick={() => act(r, 'request-approval', 'Sent for approval')}>Request approval</button>}
                  {r.status === 'pending_approval' && <>
                    <button className="small-btn" onClick={() => act(r, 'approve', 'Batch approved')}>Approve</button>
                    <button className="secondary small-btn" onClick={() => act(r, 'reject', 'Sent back to draft')}>Send back</button>
                  </>}
                  {(r.status === 'approved' || (r.status === 'paused' && !r.last_error?.includes('approve'))) && <button className="small-btn" onClick={() => act(r, 'start', 'Sending started')}>{r.status === 'paused' ? 'Resume' : 'Start sending'}</button>}
                  {r.status === 'sending' && <button className="secondary small-btn" onClick={() => act(r, 'pause', 'Paused')}>Pause</button>}
                  {!['completed', 'cancelled'].includes(r.status) && <button className="secondary small-btn" onClick={() => act(r, 'cancel', 'Batch cancelled')}>Cancel</button>}
                </span>
              ),
            },
          ]} />
      </div>

      <Suppressions orgId={orgId} />

      {dialog === 'sender' && <SenderDialog orgId={orgId} sender={sender} onClose={() => setDialog(null)} onDone={() => { setDialog(null); reload() }} />}
      {dialog === 'list' && <ListDialog orgId={orgId} onClose={() => setDialog(null)} onDone={() => { setDialog(null); reload() }} />}
      {dialog === 'batch' && <BatchDialog orgId={orgId} lists={data?.lists || []} cap={sender?.daily_cap || 200} onClose={() => setDialog(null)} onDone={() => { setDialog(null); reload() }} />}
      <Dialog open={!!previewing} onClose={() => setPreviewing(null)} title="Email preview" wide>
        {previewing && (
          <div className="email-preview">
            <p className="small muted">To: {previewing.to}</p>
            <p><strong>{previewing.subject}</strong></p>
            <pre className="email-preview-body">{previewing.text}</pre>
          </div>
        )}
      </Dialog>
    </div>
  )
}

function useForm<T extends Record<string, unknown>>(initial: T) {
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  async function submit(fn: () => Promise<unknown>) {
    setBusy(true); setErrors({}); setFormError(null)
    try {
      await fn()
      return true
    } catch (err) {
      if (err instanceof ApiError) {
        const map: Record<string, string> = {}
        for (const d of err.details || []) if (d.field) map[d.field] = d.issue
        setErrors(map)
        if (!Object.keys(map).length) setFormError(err.message)
      } else setFormError('Something went wrong.')
      return false
    } finally {
      setBusy(false)
    }
  }
  return { form, setForm, errors, busy, formError, submit }
}

function SenderDialog({ orgId, sender, onClose, onDone }: { orgId: string; sender?: Sender; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const f = useForm({ provider: sender?.provider || 'brevo', api_key: '', sender_email: sender?.sender_email || '', sender_name: sender?.sender_name || '', postal_address: sender?.postal_address || '', reply_to: sender?.reply_to || '' })
  const set = (k: string, v: string) => f.setForm({ ...f.form, [k]: v })
  async function save() {
    if (await f.submit(() => apiRequest(`/organizations/${orgId}/outreach/sender`, { method: 'POST', body: f.form }))) {
      toast({ tone: 'success', title: 'Sender connected' })
      onDone()
    }
  }
  return (
    <Dialog open onClose={onClose} title="Connect your sending account" footer={<><button className="secondary" onClick={onClose}>Cancel</button><button disabled={f.busy} onClick={save}>{f.busy ? 'Checking…' : 'Connect'}</button></>}>
      {f.formError && <div className="banner error">{f.formError}</div>}
      <Field id="snd-provider" label="Email provider">
        <select id="snd-provider" value={f.form.provider} onChange={(e) => set('provider', e.target.value)}>
          <option value="brevo">Brevo</option>
          <option value="resend">Resend</option>
        </select>
      </Field>
      <Field id="snd-key" label="API key" error={f.errors.api_key} hint="Stored encrypted. ARC never shows it again.">
        <input id="snd-key" type="password" autoComplete="off" value={f.form.api_key} onChange={(e) => set('api_key', e.target.value)} />
      </Field>
      <Field id="snd-email" label="From address" error={f.errors.sender_email} hint="Must be verified in your Brevo or Resend account.">
        <input id="snd-email" type="email" value={f.form.sender_email} onChange={(e) => set('sender_email', e.target.value)} />
      </Field>
      <Field id="snd-name" label="From name" error={f.errors.sender_name}>
        <input id="snd-name" value={f.form.sender_name} onChange={(e) => set('sender_name', e.target.value)} />
      </Field>
      <Field id="snd-postal" label="Business postal address" error={f.errors.postal_address} hint="Shown in every email footer, as anti-spam laws require.">
        <input id="snd-postal" value={f.form.postal_address} onChange={(e) => set('postal_address', e.target.value)} />
      </Field>
      <Field id="snd-reply" label="Reply-to (optional)" error={f.errors.reply_to}>
        <input id="snd-reply" type="email" value={f.form.reply_to} onChange={(e) => set('reply_to', e.target.value)} />
      </Field>
    </Dialog>
  )
}

function ListDialog({ orgId, onClose, onDone }: { orgId: string; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const f = useForm({ name: '', lawful_basis: 'consent', source_description: '', csv: '', attest: false })
  const [fileName, setFileName] = useState('')
  async function save() {
    let stats: { added: number; invalid: number; duplicates: number; suppressed: number } | null = null
    const ok = await f.submit(async () => {
      const r = await apiRequest<{ stats: typeof stats }>(`/organizations/${orgId}/outreach/lists`, { method: 'POST', body: f.form })
      stats = r.stats
    })
    if (ok && stats) {
      const s = stats as { added: number; invalid: number; duplicates: number; suppressed: number }
      const extra = [s.invalid && `${s.invalid} invalid`, s.duplicates && `${s.duplicates} duplicates`, s.suppressed && `${s.suppressed} already unsubscribed`].filter(Boolean).join(', ')
      toast({ tone: 'success', title: `${s.added} contacts added${extra ? ` (skipped: ${extra})` : ''}` })
      onDone()
    }
  }
  return (
    <Dialog open onClose={onClose} title="Upload a contact list" footer={<><button className="secondary" onClick={onClose}>Cancel</button><button disabled={f.busy} onClick={save}>{f.busy ? 'Uploading…' : 'Upload'}</button></>}>
      {f.formError && <div className="banner error">{f.formError}</div>}
      <Field id="ls-name" label="List name" error={f.errors.name}>
        <input id="ls-name" value={f.form.name} onChange={(e) => f.setForm({ ...f.form, name: e.target.value })} />
      </Field>
      <Field id="ls-basis" label="Why you're allowed to email them" error={f.errors.lawful_basis}>
        <select id="ls-basis" value={f.form.lawful_basis} onChange={(e) => f.setForm({ ...f.form, lawful_basis: e.target.value })}>
          {Object.entries(BASIS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </Field>
      <Field id="ls-source" label="Where these contacts came from" error={f.errors.source_description} hint="e.g. “newsletter sign-ups on our website” or “cards collected at the Bristol Garden Show”.">
        <input id="ls-source" value={f.form.source_description} onChange={(e) => f.setForm({ ...f.form, source_description: e.target.value })} />
      </Field>
      <Field id="ls-file" label="CSV file" error={f.errors.csv} hint="Columns: email (required), first_name, company, source.">
        <input id="ls-file" type="file" accept=".csv,text/csv" onChange={(e) => {
          const file = e.target.files?.[0]
          if (!file) return
          setFileName(file.name)
          file.text().then((t) => f.setForm((prev) => ({ ...prev, csv: t })))
        }} />
      </Field>
      {fileName && <p className="small muted">{fileName} selected</p>}
      <div className="field checkbox-field">
        <label htmlFor="ls-attest">
          <input id="ls-attest" type="checkbox" checked={f.form.attest} onChange={(e) => f.setForm({ ...f.form, attest: e.target.checked })} />{' '}
          I confirm these contacts were collected lawfully, weren't scraped or bought, and can be emailed for this purpose.
        </label>
        {f.errors.attest && <span className="error" role="alert">{f.errors.attest}</span>}
      </div>
    </Dialog>
  )
}

function BatchDialog({ orgId, lists, cap, onClose, onDone }: { orgId: string; lists: List[]; cap: number; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const f = useForm({ list_id: lists[0]?.id || '', name: '', subject: '', body: '', daily_limit: 25, source_deliverable_id: '' as string })
  const drafts = useResource<{ deliverables: { id: string; campaign_name: string | null; current_version?: { content?: { outreach_drafts?: Omit<Draft, 'from' | 'deliverable_id'>[] } } }[] }>(`/organizations/${orgId}/deliverables?type=outreach_plan`)
  const options: Draft[] = (drafts.data?.deliverables || []).flatMap((d) =>
    (d.current_version?.content?.outreach_drafts || []).map((x) => ({ ...x, from: d.campaign_name || 'Campaign', deliverable_id: d.id })),
  )
  async function save() {
    const body = { ...f.form, source_deliverable_id: f.form.source_deliverable_id || null }
    if (await f.submit(() => apiRequest(`/organizations/${orgId}/outreach/batches`, { method: 'POST', body }))) {
      toast({ tone: 'success', title: 'Batch created. Send it for approval when ready.' })
      onDone()
    }
  }
  return (
    <Dialog open wide onClose={onClose} title="New outreach batch" footer={<><button className="secondary" onClick={onClose}>Cancel</button><button disabled={f.busy} onClick={save}>{f.busy ? 'Saving…' : 'Create batch'}</button></>}>
      {f.formError && <div className="banner error">{f.formError}</div>}
      {options.length > 0 && (
        <Field id="bt-draft" label="Start from a draft your PR specialist wrote (optional)">
          <select id="bt-draft" defaultValue="" onChange={(e) => {
            const d = options[Number(e.target.value)]
            if (d) f.setForm({ ...f.form, subject: d.subject || f.form.subject, body: d.message, name: f.form.name || `${d.from}: ${d.target_type}`, source_deliverable_id: d.deliverable_id })
          }}>
            <option value="">Write my own</option>
            {options.map((d, i) => <option key={i} value={i}>{d.from} · {d.target_type} ({d.channel})</option>)}
          </select>
        </Field>
      )}
      <Field id="bt-list" label="Send to" error={f.errors.list_id}>
        <select id="bt-list" value={f.form.list_id} onChange={(e) => f.setForm({ ...f.form, list_id: e.target.value })}>
          {lists.map((l) => <option key={l.id} value={l.id}>{l.name} ({l.active} active)</option>)}
        </select>
      </Field>
      <Field id="bt-name" label="Batch name" error={f.errors.name}>
        <input id="bt-name" value={f.form.name} onChange={(e) => f.setForm({ ...f.form, name: e.target.value })} />
      </Field>
      <Field id="bt-subject" label="Subject" error={f.errors.subject}>
        <input id="bt-subject" value={f.form.subject} onChange={(e) => f.setForm({ ...f.form, subject: e.target.value })} />
      </Field>
      <Field id="bt-body" label="Email" error={f.errors.body} hint="Use {{first_name}} and {{company}} to personalise. ARC adds the unsubscribe link, your address and why they're receiving it.">
        <textarea id="bt-body" rows={9} value={f.form.body} onChange={(e) => f.setForm({ ...f.form, body: e.target.value })} />
      </Field>
      <Field id="bt-limit" label="Emails per day" error={f.errors.daily_limit} hint={`Up to ${cap} a day for this workspace. Start small to protect your sender reputation.`}>
        <input id="bt-limit" type="number" min={1} max={cap} value={f.form.daily_limit} onChange={(e) => f.setForm({ ...f.form, daily_limit: Number(e.target.value) })} />
      </Field>
    </Dialog>
  )
}

function Suppressions({ orgId }: { orgId: string }) {
  const toast = useToast()
  const { data, reload } = useResource<{ suppressions: { email: string; reason: string; created_at: string }[] }>(`/organizations/${orgId}/outreach/suppressions`)
  const [email, setEmail] = useState('')
  async function add() {
    try {
      await apiRequest(`/organizations/${orgId}/outreach/suppressions`, { method: 'POST', body: { email } })
      setEmail('')
      toast({ tone: 'success', title: 'Added to the do-not-email list' })
      reload()
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not add' })
    }
  }
  return (
    <div className="card" style={{ marginTop: 20 }}>
      <div className="card-head"><h2>Do-not-email list</h2></div>
      <p className="muted small" style={{ marginTop: -6 }}>Everyone who unsubscribes lands here and is never emailed again from this workspace.</p>
      <div className="head-actions">
        <label htmlFor="sup-email" className="sr-only">Email to suppress</label>
        <input id="sup-email" type="email" placeholder="name@example.com" value={email} onChange={(e) => setEmail(e.target.value)} style={{ maxWidth: 320 }} />
        <button className="secondary small-btn" disabled={!email} onClick={add}>Add</button>
      </div>
      <DataTable rows={data?.suppressions || []} rowKey={(r) => r.email} caption="Suppressed emails"
        empty={<EmptyState title="Nobody has unsubscribed yet" />}
        columns={[
          { key: 'e', header: 'Email', render: (r) => <span className="mono small">{r.email}</span> },
          { key: 'r', header: 'Reason', render: (r) => <span className="small">{humanize(r.reason)}</span> },
          { key: 'd', header: 'Since', render: (r) => <span className="small">{relativeTime(r.created_at)}</span> },
        ]} />
    </div>
  )
}
