import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import DeliverableContent from '../components/DeliverableContent'
import { CollabToolbar, CommentsPanel, DeliverableEditor, ShareForReview } from '../components/DeliverableCollab'
import PlatformExportView from '../components/PlatformExportView'
import WorkflowGraphPanel from '../components/WorkflowGraphPanel'
import AlwaysOnCard from '../components/AlwaysOnCard'
import DeliverableImages from '../components/DeliverableImages'
import { WordPressPublish } from '../components/WordPressPublish'
import { supportsImages } from '../lib/imageItems'
import { PageHeader, PageSkeleton, Tabs } from '../components/ui'
import { useNavigate } from 'react-router-dom'
import { useWorkspace } from '../context/WorkspaceContext'
import { usePolling } from '../hooks/usePolling'
import { humanize, money, relativeTime, statusLabel } from '../lib/labels'
import { ACTIVE_RUN_STATUSES } from '../api/types'
import { API_BASE_URL } from '../lib/apiBase'
import type { Approval, Campaign, Deliverable, ExternalAction, WorkflowRun } from '../api/types'

function uuid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

const PLATFORM_OPTIONS = [
  { value: '', label: 'Generic export (no platform formatting)' },
  { value: 'meta_instagram', label: 'Meta / Instagram' },
  { value: 'google_ads', label: 'Google Ads (Responsive Search Ads)' },
  { value: 'tiktok_ads', label: 'TikTok Ads' },
]

type Section = 'overview' | 'workflow' | 'deliverables'

export default function CampaignWorkspacePage({ section = 'overview' }: { section?: Section }) {
  const { campaignId } = useParams<{ campaignId: string }>()
  const { activeOrganizationId } = useWorkspace()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [run, setRun] = useState<WorkflowRun | null>(null)
  const [deliverables, setDeliverables] = useState<Deliverable[]>([])
  const [approvalsByDeliverable, setApprovalsByDeliverable] = useState<Record<string, Approval>>({})
  const [actionsByApproval, setActionsByApproval] = useState<Record<string, ExternalAction>>({})
  const [platformByDeliverable, setPlatformByDeliverable] = useState<Record<string, string>>({})
  const [editingId, setEditingId] = useState<string | null>(null)
  const [commentsOpen, setCommentsOpen] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [runBusy, setRunBusy] = useState(false)

  const orgId = activeOrganizationId

  const loadAll = useCallback(
    async (isCancelled: () => boolean = () => false) => {
      if (!orgId || !campaignId) return
      try {
        const [campaignData, deliverablesData, runsData] = await Promise.all([
          apiRequest<{ campaign: Campaign }>(`/organizations/${orgId}/campaigns/${campaignId}`),
          apiRequest<{ deliverables: Deliverable[] }>(
            `/organizations/${orgId}/campaigns/${campaignId}/deliverables`,
          ),
          apiRequest<{ workflow_runs: WorkflowRun[] }>(
            `/organizations/${orgId}/campaigns/${campaignId}/runs`,
          ),
        ])
        if (isCancelled()) return
        setCampaign(campaignData.campaign)
        setDeliverables(deliverablesData.deliverables)
        setRun(runsData.workflow_runs[0] || null)
      } catch (err) {
        if (!isCancelled()) setError(err instanceof ApiError ? err.message : 'Failed to load.')
      }
    },
    [orgId, campaignId],
  )

  // Agents run in the background worker, so poll while the run is active.
  const runActive = !!run && ACTIVE_RUN_STATUSES.includes(run.status)
  usePolling(loadAll, [loadAll], { intervalMs: 3000, active: runActive })

  const navigate = useNavigate()

  async function controlRun(verb: 'pause' | 'resume' | 'cancel' | 'approve-start') {
    if (!orgId || !run) return
    setRunBusy(true)
    setError(null)
    try {
      await apiRequest(`/organizations/${orgId}/runs/${run.id}/${verb}`, { method: 'POST' })
      await loadAll()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Could not ${verb} the run.`)
    } finally {
      setRunBusy(false)
    }
  }

  async function retryTask(taskId: string) {
    if (!orgId) return
    setError(null)
    try {
      await apiRequest(`/organizations/${orgId}/tasks/${taskId}/retry`, { method: 'POST' })
      // Show the change immediately; the next poll brings the full state.
      setRun((prev) =>
        prev && {
          ...prev,
          status: 'running',
          error_summary: null,
          tasks: prev.tasks.map((t) =>
            t.id === taskId ? { ...t, status: 'ready', attempt_count: 0, error_summary: null } : t,
          ),
        },
      )
      await loadAll()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not retry this task.')
    }
  }

  async function startRun() {
    if (!orgId || !campaignId) return
    setError(null)
    setStarting(true)
    try {
      const data = await apiRequest<{ workflow_run: WorkflowRun }>(
        `/organizations/${orgId}/campaigns/${campaignId}/runs`,
        { method: 'POST', idempotencyKey: uuid() },
      )
      setRun(data.workflow_run)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not start workflow.')
    } finally {
      setStarting(false)
    }
  }

  async function requestApproval(deliverableId: string) {
    if (!orgId) return
    try {
      const data = await apiRequest<{ approval: Approval }>(`/organizations/${orgId}/approvals`, {
        method: 'POST',
        body: { deliverable_id: deliverableId },
      })
      setApprovalsByDeliverable((prev) => ({ ...prev, [deliverableId]: data.approval }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not request approval.')
    }
  }

  async function decide(deliverableId: string, approvalId: string, decision: string) {
    if (!orgId) return
    try {
      const data = await apiRequest<{ approval: Approval }>(
        `/organizations/${orgId}/approvals/${approvalId}/decision`,
        { method: 'POST', body: { decision } },
      )
      setApprovalsByDeliverable((prev) => ({ ...prev, [deliverableId]: data.approval }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not record decision.')
    }
  }

  async function execute(approvalId: string, targetPlatform: string) {
    if (!orgId) return
    try {
      const data = await apiRequest<{ external_action: ExternalAction }>(
        `/organizations/${orgId}/approvals/${approvalId}/execute`,
        {
          method: 'POST',
          idempotencyKey: uuid(),
          body: targetPlatform ? { target_platform: targetPlatform } : undefined,
        },
      )
      setActionsByApproval((prev) => ({ ...prev, [approvalId]: data.external_action }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not hand off this deliverable.')
    }
  }

  async function confirmPublication(approvalId: string, actionId: string) {
    if (!orgId) return
    try {
      const data = await apiRequest<{ external_action: ExternalAction }>(
        `/organizations/${orgId}/external-actions/${actionId}/confirm-publication`,
        { method: 'POST' },
      )
      setActionsByApproval((prev) => ({ ...prev, [approvalId]: data.external_action }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not record confirmation.')
    }
  }

  if (!campaign) return <PageSkeleton />

  return (
    <div className="page">
      <PageHeader
        crumbs={[{ label: 'Campaigns', to: '/app/campaigns' }, { label: campaign.name }]}
        title={campaign.name}
        description={campaign.objective}
      />
      <Tabs
        label="Campaign sections"
        value={section}
        onChange={(v) => navigate(`/app/campaigns/${campaignId}${v === 'overview' ? '' : `/${v}`}`)}
        tabs={[
          { value: 'overview', label: 'Overview' },
          { value: 'workflow', label: 'Workflow' },
          { value: 'deliverables', label: 'Deliverables', count: deliverables.length },
        ]}
      />
      {error && <div className="banner error">{error}</div>}

      {section === 'overview' && orgId && <AlwaysOnCard orgId={orgId} campaign={campaign} onChange={setCampaign} />}
      {section === 'overview' && <CampaignBrief campaign={campaign} />}

      {section !== 'deliverables' && (<div className="card">
        <div className="card-head">
          <h2>
            Department run{' '}
            {run && <span className={`status-pill ${run.status}`}>{statusLabel(run.status)}</span>}
          </h2>
          <div className="head-actions">
            {run && run.status === 'awaiting_approval' && (
              <button className="small-btn" disabled={runBusy} onClick={() => controlRun('approve-start')}>
                Approve start
              </button>
            )}
            {run && ['queued', 'running'].includes(run.status) && (
              <button className="secondary small-btn" disabled={runBusy} onClick={() => controlRun('pause')}>
                Pause
              </button>
            )}
            {run && run.status === 'paused' && (
              <button className="small-btn" disabled={runBusy} onClick={() => controlRun('resume')}>
                Resume
              </button>
            )}
            {run && !['completed', 'cancelled'].includes(run.status) && (
              <button className="danger small-btn" disabled={runBusy} onClick={() => controlRun('cancel')}>
                Cancel run
              </button>
            )}
            {(!run || ['completed', 'cancelled', 'failed', 'needs_input'].includes(run.status)) && (
              <button onClick={startRun} disabled={starting}>
                {starting ? 'Queuing…' : run ? 'Start a new run' : 'Run the marketing department'}
              </button>
            )}
          </div>
        </div>
        {!run && (
          <p className="muted">
            Starting a run queues work for all 12 agents. Each waits for the agents it depends on, then
            produces a draft deliverable for you to review. The worker process must be running (
            <code>flask worker</code>).
          </p>
        )}
        {run && (
          <>
            <p className="muted small">
              Started {relativeTime(run.created_at)} · estimated AI cost {money(run.estimated_cost_usd)}
              {run.budget_usd != null && ` of ${money(run.budget_usd)} run budget`}
              {runActive && ' · updating live'}
            </p>
            {run.error_summary && (
              <div className="banner warning">
                {run.error_summary}
                {run.error_summary.includes('Business profile is missing') && (
                  <div style={{ marginTop: 10 }}>
                    <Link className="btn small-btn" to="/app/onboarding">Complete your business profile</Link>{' '}
                    <span className="small">Then come back and click <strong>Start a new run</strong>.</span>
                  </div>
                )}
              </div>
            )}
            {run.status === 'queued' && run.tasks.every((t) => t.attempt_count === 0) && (
              <div className="banner warning">
                Queued and waiting for the worker. If nothing changes, make sure <code>flask worker</code> is
                running.
              </div>
            )}
            <WorkflowGraphPanel tasks={run.tasks} orgId={orgId as string} />
            <table className="simple">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Note</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {run.tasks.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <Link to={`/app/operations/agents/${t.agent_id}`}>{t.agent_name}</Link>
                    </td>
                    <td>
                      <span className={`status-pill ${t.status}`}>{statusLabel(t.status)}</span>
                    </td>
                    <td className="muted">
                      {t.attempt_count}/{t.max_attempts}
                    </td>
                    <td className="muted small note-cell">
                      {t.status === 'retrying' && t.next_attempt_at
                        ? `Rate-limited or timed out; next try ${relativeTime(t.next_attempt_at)}.`
                        : t.error_summary || ''}
                    </td>
                    <td>
                      {t.status === 'failed' && run.status !== 'cancelled' && (
                        <button className="small-btn" onClick={() => retryTask(t.id)}>
                          Retry
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>)}

      {section !== 'workflow' && (<section className="deliverables" aria-labelledby="deliverables-h">
        <h2 id="deliverables-h">Deliverables</h2>
        {deliverables.length === 0 && (
          <p className="muted">
            No deliverables yet. Each agent's draft appears here as soon as it finishes; nothing is
            fabricated if an agent cannot run.
          </p>
        )}
        {orderDeliverables(deliverables, run).map((d) => {
          const approval = approvalsByDeliverable[d.id]
          const action = approval ? actionsByApproval[approval.id] : undefined
          return (
            <div key={d.id} className="card">
              <h2>{humanize(d.deliverable_type)}</h2>
              <p className="muted">
                Version {d.current_version?.version_number} ·{' '}
                <span className={`status-pill ${d.review_status}`}>{d.review_status}</span>
              </p>
              {orgId && (
                <CollabToolbar
                  editing={editingId === d.id}
                  onEdit={() => setEditingId(d.id)}
                  commentsOpen={!!commentsOpen[d.id]}
                  onToggleComments={() => setCommentsOpen((prev) => ({ ...prev, [d.id]: !prev[d.id] }))}
                />
              )}
              {editingId === d.id && orgId && d.current_version?.content ? (
                <DeliverableEditor
                  orgId={orgId}
                  deliverableId={d.id}
                  content={d.current_version.content as Record<string, unknown>}
                  onCancel={() => setEditingId(null)}
                  onSaved={() => {
                    setEditingId(null)
                    setApprovalsByDeliverable((prev) => {
                      const next = { ...prev }
                      delete next[d.id]
                      return next
                    })
                    loadAll()
                  }}
                />
              ) : (
                <DeliverableContent deliverableType={d.deliverable_type} content={d.current_version?.content} />
              )}
              {orgId && editingId !== d.id && supportsImages(d.deliverable_type) && d.current_version?.content && (
                <DeliverableImages orgId={orgId} deliverableId={d.id} type={d.deliverable_type} content={d.current_version.content as Record<string, unknown>} />
              )}
              {orgId && (
                <p className="export-links small">
                  Download:{' '}
                  {(['xlsx', 'pptx', 'pdf'] as const).map((f, i) => (
                    <span key={f}>
                      {i > 0 && ' · '}
                      <a href={`${API_BASE_URL}/organizations/${orgId}/deliverables/${d.id}/export?format=${f}`}>
                        {f === 'xlsx' ? 'Excel' : f === 'pptx' ? 'PowerPoint' : 'PDF'}
                      </a>
                    </span>
                  ))}
                </p>
              )}
              {commentsOpen[d.id] && orgId && <CommentsPanel orgId={orgId} deliverableId={d.id} />}
              {d.deliverable_type === 'social_calendar' && orgId && <CalendarImport orgId={orgId} deliverableId={d.id} />}

              {!approval && (
                <button style={{ marginTop: 14 }} onClick={() => requestApproval(d.id)}>Request approval</button>
              )}
              {approval && (
                <div>
                  <p>
                    Approval: <span className={`status-pill ${approval.decision}`}>{approval.decision}</span>
                  </p>
                  {approval.decision === 'pending' && (
                    <>
                      <button onClick={() => decide(d.id, approval.id, 'approved')}>Approve</button>{' '}
                      <button className="secondary" onClick={() => decide(d.id, approval.id, 'changes_requested')}>
                        Request changes
                      </button>{' '}
                      <button className="danger" onClick={() => decide(d.id, approval.id, 'rejected')}>
                        Reject
                      </button>
                      {orgId && (
                        <div style={{ marginTop: 10 }}>
                          <ShareForReview orgId={orgId} approvalId={approval.id} />
                        </div>
                      )}
                    </>
                  )}
                  {approval.decision === 'approved' && !action && (
                    <div style={{ marginTop: 10 }}>
                      {d.deliverable_type === 'content_pack' && (
                        <div className="field" style={{ maxWidth: 360 }}>
                          <label htmlFor={`platform-${d.id}`}>Format for platform (optional)</label>
                          <select
                            id={`platform-${d.id}`}
                            value={platformByDeliverable[d.id] || ''}
                            onChange={(e) =>
                              setPlatformByDeliverable((prev) => ({ ...prev, [d.id]: e.target.value }))
                            }
                          >
                            {PLATFORM_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <button onClick={() => execute(approval.id, platformByDeliverable[d.id] || '')}>
                        Export for publishing
                      </button>
                    </div>
                  )}
                  {action && (
                    <div style={{ marginTop: 10 }}>
                      <div className="banner success">
                        Exported, and sent to any Zapier or Make automation you connected. Status:{' '}
                        <strong>{action.publication_status === 'unverified' ? 'not confirmed as published' : 'published'}</strong>.
                        {action.publication_status === 'unverified' && (
                          <>
                            {' '}
                            <button onClick={() => confirmPublication(approval.id, action.id)}>
                              Mark as published
                            </button>
                          </>
                        )}
                      </div>
                      {action.platform_export && <PlatformExportView export={action.platform_export} />}
                    </div>
                  )}
                  {approval.decision === 'approved' && d.deliverable_type === 'site_optimization_plan' && orgId && (
                    <WordPressPublish
                      orgId={orgId}
                      deliverableId={d.id}
                      approvalId={approval.id}
                      articles={(((d.current_version?.content as Record<string, unknown> | undefined)?.blog_articles as { title?: unknown }[]) || [])}
                    />
                  )}
                </div>
              )}
            </div>
          )
        })}
      </section>)}
    </div>
  )
}

function orderDeliverables(deliverables: Deliverable[], run: WorkflowRun | null): Deliverable[] {
  const rank = new Map<string, number>()
  run?.tasks.forEach((t) => {
    if (t.deliverable_id) rank.set(t.deliverable_id, t.sequence_index)
  })
  return deliverables.slice().sort((a, b) => (rank.get(a.id) ?? 999) - (rank.get(b.id) ?? 999))
}


function CampaignBrief({ campaign }: { campaign: Campaign }) {
  const rows: [string, string | null][] = [
    ['Audience', campaign.audience],
    ['Offer', campaign.offer],
    ['Channels', campaign.channels],
    ['Geography', campaign.geography],
    ['Dates', campaign.start_date || campaign.end_date ? `${campaign.start_date || '—'} → ${campaign.end_date || '—'}` : null],
    ['Budget guidance', campaign.budget_guidance],
    ['Success metrics', campaign.success_metrics],
    ['Constraints', campaign.constraints],
    ['Pages to research', campaign.research_urls?.length ? campaign.research_urls.join(', ') : null],
  ]
  const filled = rows.filter(([, v]) => v)
  if (filled.length === 0) return null
  return (
    <div className="card">
      <h2>Brief</h2>
      <div className="form-grid">
        {filled.map(([k, v]) => (
          <div key={k} className="deliverable-section">
            <div className="section-label">{k}</div>
            <p className="deliverable-prose small">{v}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function CalendarImport({ orgId, deliverableId }: { orgId: string; deliverableId: string }) {
  const [start, setStart] = useState(() => new Date(Date.now() + 86400000).toISOString().slice(0, 10))
  const [message, setMessage] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  async function importIt() {
    setErr(null)
    try {
      const r = await apiRequest<{ created: number }>(`/organizations/${orgId}/calendar/from-deliverable`, {
        method: 'POST',
        body: { deliverable_id: deliverableId, start_date: start },
      })
      setMessage(`${r.created} posts added to the content calendar.`)
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : 'Could not add to calendar.')
    }
  }
  return (
    <div className="card" style={{ background: 'var(--color-bg-elevated)' }}>
      <strong className="small">Schedule these posts</strong>
      <p className="muted small">Adds one post per day from the start date to your content calendar. Nothing is published automatically.</p>
      {message ? (
        <div className="banner success">{message} <Link to="/app/calendar">Open calendar →</Link></div>
      ) : (
        <div className="head-actions">
          <label htmlFor={`cal-start-${deliverableId}`} className="small">Start date</label>
          <input id={`cal-start-${deliverableId}`} type="date" className="select-inline" value={start} onChange={(e) => setStart(e.target.value)} />
          <button className="small-btn" onClick={importIt}>Add to calendar</button>
        </div>
      )}
      {err && <div className="banner error">{err}</div>}
    </div>
  )
}
