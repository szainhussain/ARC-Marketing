const TASK_STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  waiting_for_dependency: 'Waiting on dependency',
  ready: 'Ready',
  running: 'Running',
  retrying: 'Retrying',
  waiting_for_approval: 'Waiting for approval',
  scheduled: 'Scheduled',
  succeeded: 'Succeeded',
  failed: 'Failed',
  cancelled: 'Cancelled',
  // run statuses
  created: 'Created',
  paused: 'Paused',
  needs_input: 'Needs input',
  awaiting_approval: 'Awaiting approval',
  completed: 'Completed',
  // agent statuses
  idle: 'Idle',
  working: 'Working',
  workspace_paused: 'Workspace paused',
}

export function statusLabel(status: string): string {
  return TASK_STATUS_LABELS[status] || status.replace(/_/g, ' ')
}

const ACRONYMS: Record<string, string> = { qa: 'QA', seo: 'SEO', cmo: 'CMO', pr: 'PR', ai: 'AI', usd: 'USD', url: 'URL', cta: 'CTA', faq: 'FAQ', kpi: 'KPI' }

export function humanize(value: string): string {
  const words = value.replace(/_/g, ' ').split(' ').map((w) => ACRONYMS[w.toLowerCase()] || w)
  const text = words.join(' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  const then = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`).getTime()
  const seconds = Math.round((Date.now() - then) / 1000)
  if (seconds < 0) {
    const s = -seconds
    if (s < 60) return `in ${s}s`
    if (s < 3600) return `in ${Math.round(s / 60)}m`
    if (s < 86400) return `in ${Math.round(s / 3600)}h`
    const days = Math.round(s / 86400)
    return `in ${days} day${days === 1 ? '' : 's'}`
  }
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`
  return `${Math.round(seconds / 86400)}d ago`
}

export function money(value: number | null | undefined): string {
  return `$${(value || 0).toFixed(value && value < 1 ? 4 : 2)}`
}
