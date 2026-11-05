import { useEffect, useState } from 'react'
import { ImagePlus } from 'lucide-react'
import { apiRequest, ApiError } from '../api/client'
import { useResource } from '../hooks/useResource'
import { API_BASE_URL } from '../lib/apiBase'
import { useToast } from './ui'

type Img = { id: string; item_index: number; status: 'queued' | 'running' | 'succeeded' | 'failed'; error_summary: string | null; document_id: string | null; aspect_ratio: string }

import { IMAGE_ITEMS as ITEMS } from '../lib/imageItems'

/** On-brand image generation for each post, variant or ad in a deliverable. */
export default function DeliverableImages({ orgId, deliverableId, type, content }: { orgId: string; deliverableId: string; type: string; content: Record<string, unknown> }) {
  const toast = useToast()
  const cfg = ITEMS[type]
  const items = (cfg && Array.isArray(content[cfg.key]) ? (content[cfg.key] as Record<string, unknown>[]) : []).slice(0, 20)
  const [pollMs, setPollMs] = useState<number | undefined>(undefined)
  const { data, reload } = useResource<{ images: Img[] }>(`/organizations/${orgId}/deliverables/${deliverableId}/images`, { pollMs })
  const images = data?.images || []
  const busy = images.some((i) => i.status === 'queued' || i.status === 'running')
  useEffect(() => {
    setPollMs(busy ? 3000 : undefined)
  }, [busy])
  const [sending, setSending] = useState<number | null>(null)
  if (!cfg || items.length === 0) return null

  async function generate(index: number) {
    setSending(index)
    try {
      await apiRequest(`/organizations/${orgId}/deliverables/${deliverableId}/images`, { method: 'POST', body: { item_index: index } })
      setPollMs(3000)
      reload()
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not start the image' })
    } finally {
      setSending(null)
    }
  }

  return (
    <div className="gen-images">
      <h3>Images</h3>
      <p className="muted small" style={{ marginTop: -4 }}>Generated from your Brand Kit and this item's copy. Saved to Assets.</p>
      <ul className="gen-list">
        {items.map((it, i) => {
          const mine = images.filter((im) => im.item_index === i)
          return (
            <li key={i}>
              <div className="gen-row">
                <span className="small">{cfg.label(it, i)}</span>
                <button type="button" className="secondary small-btn" disabled={sending === i} onClick={() => generate(i)}>
                  <ImagePlus size={14} aria-hidden="true" /> {mine.length ? 'Generate another' : 'Generate image'}
                </button>
              </div>
              {mine.length > 0 && (
                <div className="gen-thumbs">
                  {mine.map((im) =>
                    im.status === 'succeeded' && im.document_id ? (
                      <a key={im.id} href={`${API_BASE_URL}/organizations/${orgId}/documents/${im.document_id}/download`} title="Download image">
                        <img src={`${API_BASE_URL}/organizations/${orgId}/documents/${im.document_id}/download?inline=1`} alt={`Generated image for ${cfg.label(it, i)}`} loading="lazy" style={{ aspectRatio: im.aspect_ratio.replace(':', ' / ') }} />
                      </a>
                    ) : im.status === 'failed' ? (
                      <span key={im.id} className="gen-failed small">
                        {im.error_summary?.startsWith('capability_unavailable') ? 'Image generation isn’t connected yet. Add a Gemini API key to turn it on.' : `Couldn’t generate: ${im.error_summary}`}
                      </span>
                    ) : (
                      <span key={im.id} className="gen-pending small">Generating…</span>
                    ),
                  )}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
