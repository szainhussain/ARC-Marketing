export type User = { id: string; email: string; full_name: string }

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
  created_at: string
  updated_at: string
}

export type Task = {
  id: string
  stage: string
  status: string
  attempt_count: number
  error_summary: string | null
  started_at: string | null
  completed_at: string | null
}

export type WorkflowRun = {
  id: string
  campaign_id: string
  workflow_type: string
  status: string
  error_summary: string | null
  estimated_cost_usd: number
  started_at: string | null
  completed_at: string | null
  tasks: Task[]
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
