import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { apiRequest, ApiError } from '../../api/client'
import { usePageMeta } from '../../lib/seo'

/** Public page behind the unsubscribe link in outreach emails. A click is
 *  required here so link-scanning tools can't unsubscribe people; mail apps
 *  use the separate one-click header endpoint. */
export default function UnsubscribePage() {
  const { token = '' } = useParams()
  usePageMeta('Unsubscribe', 'Stop receiving these emails.')
  const [done, setDone] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function unsubscribe() {
    setBusy(true)
    setError(null)
    try {
      const r = await apiRequest<{ from: string }>(`/outreach/unsubscribe/${encodeURIComponent(token)}`, { method: 'POST' })
      setDone(r.from)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page" style={{ maxWidth: 560, margin: '64px auto' }}>
      <div className="card">
        {done ? (
          <>
            <h1 style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <CheckCircle2 aria-hidden="true" /> You're unsubscribed
            </h1>
            <p>{done} won't email you again from these campaigns.</p>
          </>
        ) : (
          <>
            <h1>Unsubscribe</h1>
            <p>Stop receiving these emails. This takes effect straight away.</p>
            {error && <div className="banner error">{error}</div>}
            <button disabled={busy} onClick={unsubscribe}>
              {busy ? 'Unsubscribing…' : 'Unsubscribe'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
