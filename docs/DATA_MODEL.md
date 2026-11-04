# Data Model

SQLAlchemy models in `app/models/`, migrated with Alembic
(`migrations/versions/`). Every tenant-owned table has `organization_id`
and is only queried through routes that first call
`get_membership_or_403(organization_id)`.

| Table | Purpose | Notes |
|---|---|---|
| users | Accounts | `session_version` (bump = revoke all sessions), `email_verified_at` |
| organizations | Workspaces | `automation_paused`, `kill_switch_enabled`, `max_concurrent_tasks`, `default_run_budget_usd`, `timezone`, `status`, `deletion_scheduled_at` |
| memberships | User↔workspace + role | owner, admin, marketing_lead, approver, contributor, analyst, viewer |
| invitations | Pending invites | token stored hashed; expiry; accepted/revoked |
| password_reset_tokens | Reset + email-verification tokens | hashed, single-use, expiring |
| plans | Plan catalog | entitlements/features as JSON; `price_is_provisional`; `stripe_price_ref` |
| subscriptions | Workspace ↔ plan | trialing/active/past_due/cancelled; changed only by verified billing events |
| billing_events | Verified payment-provider events | unique (provider, event_id) → idempotent; billing history |
| business_profiles | Brand/onboarding profile | `onboarding_step` saves wizard progress |
| knowledge_entries | Brand knowledge | `status` proposed/approved/archived, `version`, provenance (`source_run_id`, `source_deliverable_id`, user) |
| documents | Uploaded asset metadata | bytes in storage adapter, checksum |
| campaigns | Briefs | idempotency key unique per workspace |
| workflow_runs | One department run | idempotency key unique per workspace; `budget_usd`, `estimated_cost_usd` |
| tasks | One agent's unit of work | state machine in `models/task.py`; lease, attempts, next_attempt_at |
| task_dependencies | DAG edges | |
| agent_executions | One attempt | agent version, tokens, cost, evaluation JSON, error code, correlation id |
| agent_settings | Per-workspace agent overrides | paused, monthly budget |
| action_policies | Editable policy overrides | locked platform policies aren't stored |
| deliverables / deliverable_versions | Versioned output | versions immutable; content hash |
| approvals | Version-bound decisions | payload hash, risk, expected outcome, expiry, revoked |
| external_actions | Manual handoffs | idempotent; publication only confirmed by a person |
| calendar_entries | Content calendar | `published_confirmed` set by a person only |
| notifications | In-app notifications | per workspace or per user |
| webhook_endpoints / webhook_deliveries | Outbound webhooks | unique (endpoint, event) → no duplicate events |
| integrations | Per-workspace connector state | used to enable/disable export destinations |
| usage_records | AI usage ledger | `is_actual=false` (estimates) |
| audit_events | Append-only audit trail | |
| contact_enquiries | Public form submissions | not tenant data |

Not built from the brief's list: feature flags, evaluation runs,
attribution records, analytics observations (no data sources yet).

## Retention

Workspace deletion: scheduled with a 30-day grace period (agents paused,
kill switch on), then `flask purge-deleted-workspaces` removes all tenant
rows and stored files in FK-safe order (`app/services/data_lifecycle.py`).
Billing events are kept with the workspace reference nulled.
