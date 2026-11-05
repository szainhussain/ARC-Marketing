import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ExternalLink, Globe } from 'lucide-react'
import { apiRequest, ApiError } from '../api/client'
import { useResource } from '../hooks/useResource'
import { StatusPill, useToast } from './ui'

type WordPressStatus = { configured: boolean; connected: boolean; state: string; site_url: string | null; site_name: string | null }
type Publication = {
  id: string
  item_index: number | null
  status: 'queued' | 'executing' | 'succeeded' | 'failed'
  publication_status: string
  external_url: string | null
  publish_mode: 'publish' | 'draft' | null
  last_error: string | null
}

/** Integrations page card: connect or disconnect the workspace's WordPress.com site. */
export function WordPressCard({ orgId }: { orgId: string }) {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const { data, reload } = useResource<{ wordpress: WordPressStatus }>(`/organizations/${orgId}/integrations`)
  const [busy, setBusy] = useState(false)
  const handled = useRef(false)
  const wp = data?.wordpress

  useEffect(() => {
    const result = params.get('wordpress')
    if (!result || handled.current) return
    handled.current = true
    if (result === 'connected') toast({ tone: 'success', title: 'WordPress.com connected' })
    else if (result === 'error') toast({ tone: 'error', title: params.get('message') || 'Could not connect WordPress.com' })
    else if (result === 'cancelled') toast({ tone: 'info', title: 'WordPress connection cancelled' })
    const next = new URLSearchParams(params)
    next.delete('wordpress')
    next.delete('message')
    setParams(next, { replace: true })
  }, [params, setParams, toast])

  async function connect() {
    setBusy(true)
    try {
      const r = await apiRequest<{ authorize_url: string }>(`/organizations/${orgId}/integrations/wordpress/connect`, { method: 'POST' })
      window.location.assign(r.authorize_url)
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not start the connection' })
      setBusy(false)
    }
  }
  async function disconnect() {
    setBusy(true)
    try {
      await apiRequest(`/organizations/${orgId}/integrations/wordpress`, { method: 'DELETE' })
      toast({ tone: 'info', title: 'WordPress.com disconnected' })
      reload()
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not disconnect' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div id="wordpress" className="card automation-card" style={{ marginTop: 24, scrollMarginTop: 80 }}>
      <div className="card-head">
        <h2>
          <Globe size={18} aria-hidden="true" /> Publish blog articles to WordPress.com
        </h2>
        {wp && <StatusPill status={wp.connected ? 'active' : wp.state === 'reauth_required' ? 'failed' : 'cancelled'} label={wp.connected ? 'Connected' : wp.state === 'reauth_required' ? 'Reconnect needed' : 'Not connected'} />}
      </div>
      <p className="muted small" style={{ marginTop: -6 }}>
        Your SEO specialist writes a blog article for each campaign. Once you approve it, ARC can publish it to your site or
        save it as a draft. ARC reads the post back from WordPress to confirm it is live, and nothing is posted before approval.
      </p>
      {!wp ? null : !wp.configured ? (
        <p className="small">WordPress publishing isn't switched on for this ARC server yet.</p>
      ) : wp.connected ? (
        <div className="head-actions">
          <span className="small">
            Connected to{' '}
            {wp.site_url ? (
              <a href={wp.site_url} target="_blank" rel="noreferrer">
                {wp.site_name}
              </a>
            ) : (
              wp.site_name
            )}
          </span>
          <button className="secondary small-btn" disabled={busy} onClick={disconnect}>
            Disconnect
          </button>
        </div>
      ) : (
        <div className="head-actions">
          <button disabled={busy} onClick={connect}>
            {busy ? 'Opening WordPress…' : wp.state === 'reauth_required' ? 'Reconnect WordPress.com' : 'Connect WordPress.com'}
          </button>
          <span className="muted small">You'll sign in on WordPress.com and choose the site.</span>
        </div>
      )}
    </div>
  )
}

const LABEL: Record<string, string> = {
  platform_verified_published: 'Live on your site',
  draft_created: 'Saved as a WordPress draft',
  unverified: 'Posted, not yet confirmed live',
}

/** Deliverable card: publish each approved blog article to the connected site. */
export function WordPressPublish({ orgId, deliverableId, approvalId, articles }: { orgId: string; deliverableId: string; approvalId: string; articles: { title?: unknown }[] }) {
  const toast = useToast()
  const [pollMs, setPollMs] = useState<number | undefined>(undefined)
  const status = useResource<{ wordpress: WordPressStatus }>(`/organizations/${orgId}/integrations`)
  const { data, reload } = useResource<{ publications: Publication[] }>(`/organizations/${orgId}/deliverables/${deliverableId}/publications`, { pollMs })
  const pubs = data?.publications || []
  const busy = pubs.some((p) => p.status === 'queued' || p.status === 'executing')
  const [sending, setSending] = useState<number | null>(null)
  useEffect(() => {
    setPollMs(busy ? 3000 : undefined)
  }, [busy])
  if (articles.length === 0) return null
  const wp = status.data?.wordpress

  async function publish(index: number, mode: 'publish' | 'draft') {
    setSending(index)
    try {
      await apiRequest(`/organizations/${orgId}/approvals/${approvalId}/publish/wordpress`, {
        method: 'POST',
        body: { article_index: index, mode },
        idempotencyKey: `wp-${approvalId}-${index}-${mode}`,
      })
      toast({ tone: 'success', title: mode === 'publish' ? 'Publishing to WordPress…' : 'Saving a WordPress draft…' })
      reload()
    } catch (err) {
      toast({ tone: 'error', title: err instanceof ApiError ? err.message : 'Could not publish' })
    } finally {
      setSending(null)
    }
  }

  return (
    <div className="wp-publish">
      <h3>Publish to WordPress.com</h3>
      {wp && !wp.connected ? (
        <p className="small muted">
          Connect your WordPress.com site in <Link to="/app/integrations">Integrations</Link> to publish this article.
        </p>
      ) : (
        <ul className="gen-list">
          {articles.map((a, i) => {
            const pub = pubs.find((p) => p.item_index === i && p.status !== 'failed') || pubs.find((p) => p.item_index === i)
            return (
              <li key={i}>
                <div className="gen-row">
                  <span className="small">{String(a.title || `Article ${i + 1}`)}</span>
                  {!pub || pub.status === 'failed' ? (
                    <span className="head-actions">
                      <button className="small-btn" disabled={sending === i} onClick={() => publish(i, 'publish')}>
                        Publish now
                      </button>
                      <button className="secondary small-btn" disabled={sending === i} onClick={() => publish(i, 'draft')}>
                        Save as draft
                      </button>
                    </span>
                  ) : pub.status === 'succeeded' ? (
                    <span className="head-actions">
                      <StatusPill status="succeeded" label={LABEL[pub.publication_status] || 'Posted'} />
                      {pub.external_url && (
                        <a className="small" href={pub.external_url} target="_blank" rel="noreferrer">
                          View <ExternalLink size={12} aria-hidden="true" />
                        </a>
                      )}
                    </span>
                  ) : (
                    <StatusPill status="running" label={pub.publish_mode === 'draft' ? 'Saving draft…' : 'Publishing…'} />
                  )}
                </div>
                {pub?.status === 'failed' && pub.last_error && <p className="gen-failed small">Couldn't publish: {pub.last_error}</p>}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
