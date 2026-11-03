import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import DeliverableContent from '../components/DeliverableContent'
import PlatformExportView from '../components/PlatformExportView'
import { useWorkspace } from '../context/WorkspaceContext'
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

export default function CampaignWorkspacePage() {
  const { campaignId } = useParams<{ campaignId: string }>()
  const { activeOrganizationId } = useWorkspace()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [run, setRun] = useState<WorkflowRun | null>(null)
  const [deliverables, setDeliverables] = useState<Deliverable[]>([])
  const [approvalsByDeliverable, setApprovalsByDeliverable] = useState<Record<string, Approval>>({})
  const [actionsByApproval, setActionsByApproval] = useState<Record<string, ExternalAction>>({})
  const [platformByDeliverable, setPlatformByDeliverable] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  const orgId = activeOrganizationId

  const loadAll = useCallback(async () => {
    if (!orgId || !campaignId) return
    const [campaignData, deliverablesData] = await Promise.all([
      apiRequest<{ campaign: Campaign }>(`/organizations/${orgId}/campaigns/${campaignId}`),
      apiRequest<{ deliverables: Deliverable[] }>(
        `/organizations/${orgId}/campaigns/${campaignId}/deliverables`,
      ),
    ])
    setCampaign(campaignData.campaign)
    setDeliverables(deliverablesData.deliverables)
  }, [orgId, campaignId])

  useEffect(() => {
    loadAll().catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load.'))
  }, [loadAll])

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
      await loadAll()
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

  if (!campaign) return <div className="page">Loading…</div>

  return (
    <div className="page">
      <h1>{campaign.name}</h1>
      <p className="muted">{campaign.objective}</p>
      {error && <div className="banner error">{error}</div>}

      <div className="card">
        <h2>Workflow</h2>
        {!run && (
          <button onClick={startRun} disabled={starting}>
            {starting ? 'Starting…' : 'Run campaign workflow'}
          </button>
        )}
        {run && (
          <>
            <p>
              Status: <span className={`status-pill ${run.status}`}>{run.status}</span>
            </p>
            {run.error_summary && <div className="banner warning">{run.error_summary}</div>}
            <table className="simple">
              <thead>
                <tr>
                  <th>Stage</th>
                  <th>Status</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {run.tasks.map((t) => (
                  <tr key={t.id}>
                    <td>{t.stage}</td>
                    <td>
                      <span className={`status-pill ${t.status}`}>{t.status}</span>
                    </td>
                    <td className="muted">{t.error_summary || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      <div className="card">
        <h2>Deliverables</h2>
        {deliverables.length === 0 && (
          <p className="muted">
            No deliverables yet. They appear here once the workflow completes a stage
            successfully — nothing is fabricated if a stage cannot run.
          </p>
        )}
        {deliverables.map((d) => {
          const approval = approvalsByDeliverable[d.id]
          const action = approval ? actionsByApproval[approval.id] : undefined
          return (
            <div key={d.id} className="card">
              <h2 style={{ textTransform: 'capitalize' }}>{d.deliverable_type.replace('_', ' ')}</h2>
              <p className="muted">
                Version {d.current_version?.version_number} · review:{' '}
                <span className={`status-pill ${d.review_status}`}>{d.review_status}</span>
              </p>
              <DeliverableContent deliverableType={d.deliverable_type} content={d.current_version?.content} />

              {!approval && (
                <button onClick={() => requestApproval(d.id)}>Request approval to hand off</button>
              )}
              {approval && (
                <div>
                  <p>
                    Approval: <span className={`status-pill ${approval.decision}`}>{approval.decision}</span>
                  </p>
                  {approval.decision === 'pending' && (
                    <>
                      <button onClick={() => decide(d.id, approval.id, 'approved')}>Approve</button>{' '}
                      <button className="danger" onClick={() => decide(d.id, approval.id, 'rejected')}>
                        Reject
                      </button>
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
                        Export for manual handoff
                      </button>
                    </div>
                  )}
                  {action && (
                    <div style={{ marginTop: 10 }}>
                      <div className="banner success">
                        Handed off (export package generated). Publication status:{' '}
                        <strong>{action.publication_status}</strong>.
                        {action.publication_status === 'unverified' && (
                          <>
                            {' '}
                            This has <u>not</u> been marked published.{' '}
                            <button onClick={() => confirmPublication(approval.id, action.id)}>
                              I posted this myself — confirm
                            </button>
                          </>
                        )}
                      </div>
                      {action.platform_export && <PlatformExportView export={action.platform_export} />}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
