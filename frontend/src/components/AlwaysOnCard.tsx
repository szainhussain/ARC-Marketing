import { useState } from 'react'
import { Repeat } from 'lucide-react'
import { apiRequest, ApiError } from '../api/client'
import type { Campaign } from '../api/types'
import { useToast } from './ui'

/** Turn a campaign into an always-on monthly cycle. Each month ARC starts a new
 *  department run; drafts still wait for approval and plan limits still apply. */
export default function AlwaysOnCard({ orgId, campaign, onChange }: { orgId: string; campaign: Campaign; onChange: (c: Campaign) => void }) {
  const toast = useToast()
  const on = campaign.recurrence === 'monthly'
  const [day, setDay] = useState(String(campaign.recurrence_day || 1))
  const [busy, setBusy] = useState(false)

  async function save(recurrence: 'monthly' | 'none') {
    setBusy(true)
    try {
      const r = await apiRequest<{ campaign: Campaign }>(`/organizations/${orgId}/campaigns/${campaign.id}/recurrence`, {
        method: 'POST',
        body: { recurrence, recurrence_day: Number(day) },
      })
      onChange(r.campaign)
      toast({ tone: 'success', title: recurrence === 'monthly' ? 'Always-on turned on' : 'Always-on turned off' })
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not update the schedule' })
    } finally {
      setBusy(false)
    }
  }

  const next = campaign.next_run_at ? new Date(campaign.next_run_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' }) : null
  return (
    <div className={`card always-on${on ? ' on' : ''}`}>
      <div className="always-on-row">
        <Repeat size={18} aria-hidden="true" />
        <div style={{ flex: 1, minWidth: 220 }}>
          <h2 style={{ margin: 0 }}>Always-on monthly marketing</h2>
          <p className="muted small" style={{ margin: '4px 0 0' }}>
            {on
              ? `Your department runs this campaign again on day ${campaign.recurrence_day} of every month.${next ? ` Next run: ${next}.` : ''} Drafts always wait for your approval.`
              : 'Repeat this campaign every month: fresh strategy, plan and content, ready for your approval. Uses one campaign run from your plan each month.'}
          </p>
        </div>
        <label htmlFor={`aon-day-${campaign.id}`} className="sr-only">
          Day of the month
        </label>
        <select id={`aon-day-${campaign.id}`} className="select-inline" value={day} onChange={(e) => setDay(e.target.value)} disabled={busy}>
          {Array.from({ length: 28 }, (_, i) => String(i + 1)).map((d) => (
            <option key={d} value={d}>
              Day {d}
            </option>
          ))}
        </select>
        {on ? (
          <>
            {String(campaign.recurrence_day) !== day && (
              <button disabled={busy} onClick={() => save('monthly')}>
                Update day
              </button>
            )}
            <button className="secondary" disabled={busy} onClick={() => save('none')}>
              Turn off
            </button>
          </>
        ) : (
          <button disabled={busy} onClick={() => save('monthly')}>
            Turn on
          </button>
        )}
      </div>
    </div>
  )
}
