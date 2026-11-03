# Architecture

## Logical architecture

```
Browser (React SPA)
   |  fetch, credentials: include, X-CSRFToken
   v
Flask API (app/api/v1/*) --- Flask-Login session auth, CSRF
   |
   +--> app/services/*            domain logic; every call starts with
   |                              get_membership_or_403(organization_id)
   |
   +--> app/workflows/campaign_workflow.py   synchronous pipeline orchestrator
   |       |
   |       +--> app/agents/{cmo_planner,research_analyst,marketing_manager,
   |       |                 content_creator,quality_reviewer}.py
   |       +--> app/ai/provider_adapter.py (AnthropicProvider | NullProvider)
   |
   +--> app/integrations/manual_handoff.py   the only connector implemented
   |
   +--> SQLAlchemy models (app/models/*.py) --- SQLite (dev) / PostgreSQL (prod)
   |
   +--> app/services/audit_service.py --- AuditEvent (append-only)
```

The backend is authoritative for workflow state, permissions, approvals,
and external-action status. Model output is never trusted directly — it is
parsed as JSON and validated against a Marshmallow schema
(`app/ai/schemas.py`) before it can become a `DeliverableVersion`.

## Request lifecycle for a mutating route

1. `@login_required` (Flask-Login) — 401 if no session.
2. `get_membership_or_403(organization_id)` — 403 if the user has no
   membership in that org; identical error whether the org exists or not.
3. Route-specific role check where relevant (e.g.
   `Membership.can_approve_external_actions()` for approval decisions).
4. Service function does the work inside the current request's DB session,
   `db.session.flush()` for intermediate reads, `db.session.commit()` once
   at the end of a successful service call.
5. `audit_service.record_audit_event(...)` for anything state-changing.
6. Errors raise a typed `AppError` subclass (`app/services/errors.py`);
   `app/api/error_handlers.py` converts it to the standard envelope:
   ```json
   {"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}
   ```

## Data model

See `app/models/*.py` for the authoritative field list. Every tenant-owned
table has `organization_id` as a required, indexed foreign key. IDs are
UUIDv4 strings (`String(36)`) for cross-DB compatibility (SQLite has no
native UUID type).

Key relationships:
- `Organization` 1—1 `BusinessProfile`, 1—N `Membership`, `Campaign`,
  `WorkflowRun`, `Deliverable`, `Approval`, `ExternalAction`, `UsageRecord`,
  `AuditEvent`, `Integration`, `Document`.
- `Campaign` 1—N `Task`, `WorkflowRun`, `Deliverable`.
- `Deliverable` 1—N `DeliverableVersion` (immutable), with
  `current_version_id` pointing at the active one.
- `Approval` references one `Deliverable` + one exact `DeliverableVersion`
  + an `action_payload_hash` (SHA-256 of the JSON-serialized action
  payload). `add_new_version()` invalidates any `pending` `Approval` tied
  to the version it replaces.
- `ExternalAction` references one `Approval`; tracks `status` (handoff
  execution state) and `publication_status` (kept deliberately separate —
  see D5 in `docs/DECISIONS.md` and the governance rules in
  `docs/SECURITY_AND_GOVERNANCE.md`).

## State machines

Defined as transition dicts next to each model
(`app/models/task.py:TASK_TRANSITIONS`,
`app/models/workflow_run.py:RUN_TRANSITIONS`) and enforced by
`app/workflows/state_machine.py:apply_transition()`, which raises `Conflict`
(HTTP 409) on an invalid transition rather than silently allowing it.

`WorkflowRun`: `created → queued → running → needs_input | awaiting_approval
| completed | failed | cancelled`. In the current synchronous
implementation, `start_campaign_workflow` moves a run from `created`
straight through `running` to its terminal state within one request (see
D4 in `docs/DECISIONS.md`).

`Task`: `pending → ready → running → needs_input | awaiting_approval |
completed | failed | cancelled`. The campaign workflow currently only uses
`running → completed` and `running → failed`; `needs_input` at the task
level and the `ready`/dependency-ordering states are modeled for a future
multi-branch workflow but not yet exercised (the pipeline is a fixed
5-stage sequence).

`ExternalAction`: `prepared → ... → succeeded | failed |
verification_required`, independent of `publication_status`
(`not_applicable → unverified → manually_confirmed_published`).

## AI adapter contract

`app/ai/base.py:AIProvider.generate_structured(task_type, input_data,
output_schema, context, budget_usd, timeout_seconds, correlation_id)` →
`AIResult(data, provider, model, input_tokens, output_tokens,
estimated_cost_usd, warnings)`.

Typed errors (`app/ai/errors.py`): `ProviderUnavailable`, `RateLimited`,
`InvalidOutput`, `BudgetExceeded`, `AIRequestTimeout`. The workflow
orchestrator (`campaign_workflow.py:_run_pipeline`) catches all of these,
marks the current task `failed` with a safe (no stack trace, no key
material) `error_summary`, and stops — it does not attempt later stages
with missing upstream context.

`AnthropicProvider` and `GroqProvider` (OpenAI-compatible, added in D8)
both do one bounded repair retry (2 attempts total) if the model's JSON
doesn't parse or doesn't validate against the schema, then raise
`InvalidOutput`. Estimated cost is computed from a clearly-labeled
placeholder per-token rate (`provider_adapter.py`) — not a real invoice
figure; see the "estimate" labeling in the reports API and UI. Both
provider SDK clients are constructed with `max_retries=0` — the SDKs'
own default retry-on-429/5xx behavior sleeps internally and would
otherwise block a single call for far longer than this app's own
timeout/retry budget before the typed error ever surfaces (observed: a
~41s hang on a real Groq rate limit before this was disabled). The prompt
built in `_build_prompt()` includes a per-field type hint derived from
each Marshmallow field (`_describe_field()`) — added after a real
schema-validation failure where an open-weight model substituted objects
for a plain-string list field; see `docs/DECISIONS.md` D8 for the full
story.

## Frontend architecture

React 19 + TypeScript + Vite, no server-side rendering. `AuthContext`
(current user + memberships, via `/me`) and `WorkspaceContext` (active
organization, persisted to `localStorage`) wrap the app;
`ProtectedRoute` gates `/app/*`. `src/api/client.ts` centralizes the
CSRF-token dance and the standard error envelope → `ApiError`. See
`CLAUDE.md` for the `htmlFor`/`id` and stale-fetch-guard conventions that
came out of real bugs caught during this build.

## What would need to change for the full 12-agent vision

See `docs/12_AGENT_EXPANSION_ROADMAP.md`. The short version: the
`AgentStage` base class, provider-neutral `AIProvider` interface, and
`Connector` contract are already shaped to support more stages/roles and
more connectors without a rewrite — what's missing for the full vision is
(a) a task graph with real branching/dependencies instead of a fixed
5-step sequence, (b) a background queue, and (c) a capability/permission
registry per agent role instead of today's implicit "every stage can do
anything the workflow lets it do."
