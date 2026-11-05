export type User = { id: string; email: string; full_name: string; email_verified?: boolean; is_platform_admin?: boolean; mfa_enabled?: boolean }

export type Membership = { organization_id: string; organization_name: string; role: string }

export type Organization = { id: string; name: string; slug: string; status: string }

export type BusinessProfile = {
  organization_id: string
  business_name: string | null
  website: string | null
  industry: string | null
  regions_served: string | null
  business_type: string | null
  products_services: string | null
  target_audience: string | null
  customer_problem: string | null
  differentiators: string | null
  primary_goal: string | null
  tone_of_voice: string | null
  preferred_phrases: string | null
  prohibited_phrases: string | null
  constraints: string | null
  onboarding_completed: boolean
}

export type Campaign = {
  id: string
  organization_id: string
  name: string
  objective: string
  audience: string | null
  offer: string | null
  geography: string | null
  channels: string | null
  start_date: string | null
  end_date: string | null
  budget_guidance: string | null
  constraints: string | null
  success_metrics: string | null
  status: 'draft' | 'active' | 'archived'
  research_urls?: string[]
  recurrence?: 'none' | 'monthly'
  recurrence_day?: number | null
  next_run_at?: string | null
  created_at: string
  updated_at: string
}

export type TaskStatus =
  | 'queued'
  | 'waiting_for_dependency'
  | 'ready'
  | 'running'
  | 'retrying'
  | 'waiting_for_approval'
  | 'scheduled'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export type Task = {
  id: string
  campaign_id: string
  workflow_run_id: string | null
  agent_id: string
  agent_name: string
  agent_number: number | null
  task_type: string | null
  title: string | null
  stage: string
  status: TaskStatus | string
  priority: number
  sequence_index: number
  attempt_count: number
  max_attempts: number
  next_attempt_at: string | null
  last_error_code: string | null
  error_summary: string | null
  deliverable_id: string | null
  depends_on: string[]
  started_at: string | null
  completed_at: string | null
  created_at: string | null
  campaign_name?: string | null
}

export type WorkflowRun = {
  id: string
  campaign_id: string
  workflow_type: string
  status: string
  error_summary: string | null
  estimated_cost_usd: number
  budget_usd: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string | null
  tasks: Task[]
  campaign_name?: string | null
}

export const ACTIVE_RUN_STATUSES = ['queued', 'running']

export type AgentIntegration = { name: string; status: string }

export type AgentStats = {
  succeeded: number
  failed: number
  running: number
  estimated_cost_usd: number
  open_tasks?: number
}

export type AgentInfo = {
  agent_id: string
  number: number
  name: string
  version: string
  role: string
  responsibilities: string[]
  task_type: string
  depends_on: string[]
  reads: string[]
  outputs: string[]
  kpis: string[]
  escalates: string[]
  allowed_tools: string[]
  allowed_integrations: AgentIntegration[]
  budget_policy: { max_cost_per_task_usd: number; max_attempts: number }
  approval_policy: { external_actions: string }
  evaluation_checks: string[]
  settings: { agent_id: string; is_paused: boolean; monthly_budget_usd: number | null }
  status: 'idle' | 'working' | 'paused' | 'workspace_paused'
  stats_30d: AgentStats
}

export type EvaluationResult = { check: string; passed: boolean; detail: string | null }

export type AgentExecution = {
  id: string
  task_id: string
  workflow_run_id: string | null
  agent_id: string
  agent_version: string
  attempt_number: number
  status: string
  provider: string | null
  model: string | null
  input_tokens: number
  output_tokens: number
  estimated_cost_usd: number
  error_code: string | null
  error_summary: string | null
  summary: string | null
  evaluation: EvaluationResult[]
  correlation_id: string | null
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
}

export type OperationsSummary = {
  controls: { automation_paused: boolean; kill_switch_enabled: boolean }
  task_counts: Record<string, number>
  run_counts: Record<string, number>
  pending_approvals: number
  month_to_date: {
    estimated_ai_cost_usd: number
    cost_is_estimate: boolean
    executions_succeeded: number
    executions_failed: number
  }
  latest_runs: WorkflowRun[]
}

export type ActivityEvent = {
  id: string
  actor_user_id: string | null
  action: string
  target_type: string | null
  target_id: string | null
  correlation_id: string | null
  outcome: string
  created_at: string
}

export type DeliverableVersion = {
  id: string
  deliverable_id: string
  version_number: number
  content: Record<string, unknown>
  schema_version: string
  content_hash: string
  revision_reason: string | null
  created_at: string
}

export type Deliverable = {
  id: string
  campaign_id: string
  workflow_run_id: string | null
  deliverable_type: string
  review_status: string
  current_version: DeliverableVersion | null
  versions?: DeliverableVersion[]
}

export type Approval = {
  id: string
  deliverable_id: string
  deliverable_version_id: string
  action_type: string
  action_payload_hash: string
  decision: string
  decision_comment: string | null
  decided_at: string | null
  created_at: string
  deliverable_type?: string | null
  campaign_id?: string | null
  campaign_name?: string | null
  is_current_version?: boolean
  requesting_agent_id?: string | null
  expected_outcome?: string | null
  risk_level?: 'low' | 'medium' | 'high' | null
  risk_checks?: { check: string; passed: boolean; detail: string | null }[]
  expires_at?: string | null
}

export type Integration = {
  id: string
  provider: string
  account_label: string | null
  state: string
  scopes: string | null
}

export type PlatformFieldCheck = {
  label: string
  text: string
  length: number
  limit: number | null
  limit_confirmed: boolean
  fits: boolean | null
  note: string
}

export type PlatformVariantExport = {
  platform: string
  platform_label: string
  fields: PlatformFieldCheck[]
  cta: string
  cta_note?: string
  requirements?: string[]
  asset_checklist: string[]
  source_note: string
}

export type PlatformExport = {
  platform: string
  creative_brief: string
  variant_exports: PlatformVariantExport[]
}

export type ExternalAction = {
  id: string
  approval_id: string
  connector: string
  status: string
  target_platform: string | null
  platform_export: PlatformExport | null
  publication_status: string
  publication_confirmed_at: string | null
  created_at: string
}
