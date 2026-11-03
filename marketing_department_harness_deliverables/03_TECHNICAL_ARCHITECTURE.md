# Marketing Department Harness — Technical Architecture
**Version:** 1.0  
**Target:** small, modular Flask application that can evolve safely.

## 1. Architecture decision summary
Build a modular monolith first. Use Python Flask for the API, PostgreSQL for production persistence, SQLAlchemy and Alembic for data access/migrations, and an explicit workflow engine implemented in application code. Keep the AI provider behind an adapter. Add a queue (Celery/RQ plus Redis) when long-running jobs need reliable background execution; do not introduce distributed services prematurely.

### Initial stack
- Backend: Python 3.12+ and Flask
- API validation/serialization: Pydantic or Marshmallow; choose one consistently
- Database: PostgreSQL in shared/staging/production; SQLite only for local quick-start if needed
- ORM/migrations: SQLAlchemy + Alembic/Flask-Migrate
- Auth: established session/OIDC solution; secure cookie sessions for browser app where appropriate
- Frontend: React + TypeScript for a scalable app, or server-rendered templates for a smaller prototype; do not maintain both without need
- Background jobs: begin with synchronous local workflow for prototype; move long runs to a queue before pilot
- Files: private object storage in production; local filesystem only for development
- Deployment: Docker, managed PostgreSQL, secret manager, TLS, logs/metrics/error tracking
- Testing: pytest, integration tests, tenant-isolation tests, connector contract tests
- AI: provider adapter with structured output validation, timeouts, cost tracking, and policy checks

## 2. Logical architecture
```text
Browser UI
   |
   v
Flask API / Auth / Tenant Authorization
   |
   +--> Domain services: campaigns, tasks, deliverables, approvals, usage
   |
   +--> Workflow coordinator (explicit state machine)
   |       |
   |       +--> CMO / planner capability
   |       +--> Research capability
   |       +--> Marketing manager capability
   |       +--> Content capability
   |       +--> QA / policy checks
   |
   +--> AI provider adapter
   |
   +--> Integration adapters (initially manual export/handoff)
   |
   +--> PostgreSQL / private file storage / queue
   |
   +--> Audit, structured logs, usage metrics, error tracking
```

The backend is authoritative for workflow state, permissions, approvals, budget enforcement, usage, and external-action status. Model output is untrusted input and must be validated.

## 3. Recommended project layout
```text
marketing-harness/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── organizations.py
│   │       ├── business_profile.py
│   │       ├── campaigns.py
│   │       ├── tasks.py
│   │       ├── deliverables.py
│   │       ├── approvals.py
│   │       ├── integrations.py
│   │       └── reports.py
│   ├── models/
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── membership.py
│   │   ├── business_profile.py
│   │   ├── campaign.py
│   │   ├── task.py
│   │   ├── workflow_run.py
│   │   ├── deliverable.py
│   │   ├── approval.py
│   │   ├── integration.py
│   │   ├── usage_record.py
│   │   └── audit_event.py
│   ├── schemas/
│   ├── services/
│   │   ├── campaign_service.py
│   │   ├── task_service.py
│   │   ├── workflow_service.py
│   │   ├── approval_service.py
│   │   ├── authorization_service.py
│   │   ├── usage_service.py
│   │   ├── audit_service.py
│   │   └── report_service.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── cmo_planner.py
│   │   ├── research_analyst.py
│   │   ├── marketing_manager.py
│   │   ├── content_creator.py
│   │   └── quality_reviewer.py
│   ├── ai/
│   │   ├── base.py
│   │   ├── provider_adapter.py
│   │   └── schemas.py
│   ├── workflows/
│   │   ├── campaign_workflow.py
│   │   └── state_machine.py
│   ├── integrations/
│   │   ├── base.py
│   │   └── manual_handoff.py
│   └── storage/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── contract/
├── frontend/                 # if React is selected
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 4. Domain model
Use UUIDs for public-facing identifiers. Add `organization_id` to every tenant-owned record and enforce ownership in every query. Consider database row-level security as defense in depth after application-level checks are tested.

### Core entities
- `users`: identity and account status.
- `organizations`: tenant/workspace, settings, status, usage plan.
- `memberships`: user ↔ organization relationship and role.
- `business_profiles`: structured business and brand context, versioned where appropriate.
- `documents`: metadata, private storage key, checksum, content type, status, organization scope.
- `campaigns`: brief, objective, audience, channel, dates, constraints, status.
- `tasks`: workflow work items, stage, dependencies, status, attempt count, input/output references.
- `workflow_runs`: workflow type/version, state, start/end, error summary, cost totals.
- `agent_runs`: logical capability run, model/provider metadata, structured input/output references, token/cost data, status.
- `deliverables`: type, current version pointer, status, campaign/task/run links.
- `deliverable_versions`: immutable version content, schema version, creator/run, checksum.
- `approvals`: action type, exact deliverable version/action payload hash, requester, approver, decision, timestamps, expiry.
- `integrations`: provider, account metadata, encrypted credential reference, scopes, health state, enabled actions.
- `external_actions`: action payload hash, idempotency key, connector, status, response metadata, verification status.
- `usage_records`: metered units, provider, model, estimated/actual cost, workflow/run reference.
- `audit_events`: actor, organization, action, target, timestamp, correlation ID, redacted metadata.
- `comments`: user, target object/version, body, timestamp.
- `notifications`: organization/user, type, payload reference, delivery state.

### Important relationships and constraints
- Organization membership is required for customer access.
- Campaign, task, deliverable, approval, integration, usage, and audit data are organization-scoped.
- Deliverable versions are immutable; edits create a new version.
- Approval refers to an immutable version and action payload hash.
- External action has a unique `(organization_id, idempotency_key)` constraint.
- Workflow run transitions are validated by application state machine.
- Secrets never appear in ordinary model fields or API responses.

## 5. State machines
### Workflow run
`created → queued → running → needs_input | awaiting_approval | completed | failed | cancelled`
- `needs_input` resumes only after required input is supplied.
- `awaiting_approval` waits for a decision; it must not execute the action by itself.
- `completed` means the internal workflow completed; it does not imply an external action succeeded.
- `failed` can be retried only under bounded retry policy.
- `cancelled` blocks new stages; already-started external actions may require verification.

### Task
`pending → ready → running → needs_input | awaiting_approval | completed | failed | cancelled`

### External action
`prepared → awaiting_approval → approved → executing → succeeded | failed | verification_required | cancelled`
- An approval may be revoked before execution if policy allows and execution has not begun.
- If content/action payload hash changes, prior approval is invalid.
- Ambiguous provider timeouts must result in reconciliation/verification, not blind retries.

## 6. Workflow orchestration
Keep the campaign workflow explicit and inspectable:
1. Validate campaign brief and profile completeness.
2. Create workflow run and task graph in a database transaction.
3. Generate strategy/research plan from user facts and clearly labelled assumptions.
4. Retrieve approved documents and relevant context within tenant scope.
5. Run research capability using permitted sources; preserve source metadata when available.
6. Draft campaign plan.
7. Generate content pack from approved plan and brand profile.
8. Run schema, completeness, prohibited-claim, brand, and factual consistency checks.
9. Save deliverables and versions.
10. Move workflow to `awaiting_approval` only for a defined external action; content review can be a separate human review state.
11. Generate a concise completion summary and usage record.
12. If a failure occurs, persist the failed stage and safe error summary.

Avoid unbounded agent-to-agent conversations. Each stage has a clear contract, input schema, output schema, timeout, retry rule, and budget.

## 7. AI adapter contract
Create a provider-neutral interface such as:
- `generate_structured(task_type, input_data, output_schema, context, budget, correlation_id)`
- Returns validated structured data, provider/model metadata, token usage if available, cost estimate, and warnings.
- Raises typed errors: `ProviderUnavailable`, `RateLimited`, `InvalidOutput`, `BudgetExceeded`, `Timeout`.
- Supports timeout and bounded retries.
- Logs redacted metadata only.
- Does not directly call external publishing APIs.

### Output validation
- Parse JSON/structured output.
- Validate against a schema.
- Reject or repair invalid output with a small bounded retry count.
- Check required fields, content limits, and safety/brand constraints.
- Label assumptions and uncertain claims.
- Never treat model-generated URLs, permissions, or action requests as trusted.

## 8. API contracts (v1 draft)
All routes require authentication unless explicitly public. All customer routes require active organization membership. Use JSON, consistent errors, pagination, and request/correlation IDs.

### Common response/error pattern
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please correct the highlighted fields.",
    "details": [{"field": "objective", "issue": "Required"}],
    "request_id": "uuid"
  }
}
```

### Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/me` | Current user and workspace memberships |
| GET/PATCH | `/api/v1/business-profile` | Read/update active organization's profile |
| POST/GET | `/api/v1/campaigns` | Create/list campaigns |
| GET/PATCH/DELETE | `/api/v1/campaigns/{campaign_id}` | Read/update/archive campaign |
| POST | `/api/v1/campaigns/{campaign_id}/runs` | Start workflow; returns run ID and status |
| GET | `/api/v1/runs/{run_id}` | Workflow status and stage summary |
| POST | `/api/v1/runs/{run_id}/cancel` | Request safe cancellation |
| GET | `/api/v1/tasks` | Filter/paginate tasks |
| GET | `/api/v1/deliverables/{deliverable_id}` | Read current version |
| GET | `/api/v1/deliverables/{deliverable_id}/versions` | Version history |
| POST | `/api/v1/deliverables/{deliverable_id}/versions` | Create a new version/edit |
| POST | `/api/v1/approvals` | Request approval for exact action/version |
| POST | `/api/v1/approvals/{approval_id}/decision` | Approve/reject/request changes |
| GET | `/api/v1/approvals` | List pending/recent approvals |
| POST | `/api/v1/external-actions/{action_id}/execute` | Execute approved action through backend policy checks |
| GET | `/api/v1/integrations` | List integration metadata/health |
| POST | `/api/v1/integrations/{provider}/connect` | Start provider OAuth/connection flow |
| POST | `/api/v1/integrations/{integration_id}/disconnect` | Disconnect integration |
| GET | `/api/v1/reports/summary` | Workflow/usage summary |
| GET | `/api/v1/usage` | Usage by period |
| GET | `/api/v1/audit-events` | Authorized audit history |

### API requirements
- Validate UUIDs, types, lengths, enums, dates, and file sizes.
- Use pagination (`limit`, `cursor`) for lists.
- Use `Idempotency-Key` on workflow start and external action creation/execution.
- Return `202 Accepted` for queued long-running work.
- Use `409 Conflict` for invalid state/version conflicts.
- Use `403 Forbidden` for permission denial and avoid leaking cross-tenant existence.
- Use `429 Too Many Requests` for rate/usage limits.
- Never trust organization ID from request body alone; derive/validate from active membership.
- Approval decision payload includes `decision`, optional `comment`, and expected version/hash.
- Document request/response schemas before frontend integration.

## 9. Background jobs and reliability
Before paid pilot, run long workflows in a durable background queue. Requirements:
- Persist job intent before enqueueing.
- Job handler rechecks state and permission/policy before each stage.
- Bounded retries with exponential backoff for transient provider failures.
- Do not retry non-idempotent external actions blindly.
- Use a reconciliation job for actions with ambiguous outcomes.
- Store job and workflow IDs together.
- Dead-letter/failed job inspection path.
- Cancellation checked between stages.
- Enforce maximum runtime and usage budget per run.

## 10. Security and privacy controls
- HTTPS everywhere outside local development.
- Secure, HttpOnly, SameSite cookies or a carefully managed token strategy.
- CSRF protection for cookie-authenticated mutation routes.
- Password hashing or delegated identity provider.
- Rate limiting and abuse detection.
- Encrypted integration secrets using a managed key/secret service.
- Strict file type/size checks and safe document processing.
- Prompt-injection resistance: treat uploads and web pages as untrusted data, never instructions; tools are allowlisted and permissions come from backend policy.
- Redact secrets, tokens, and sensitive content from logs.
- Tenant-isolation tests for every resource type.
- Backup and restore tests; documented retention and deletion procedures.
- Dependency scanning, patching, and incident response plan.
- No model-generated direct database queries or unrestricted shell/browser actions.

## 11. Deployment and environments
- Local: `.env`, local database/container, test AI key with low budget.
- CI: lint, type/schema checks, unit tests, migrations, security/tenant tests.
- Staging: production-like managed DB, test integrations, synthetic data.
- Production: managed Postgres, private object storage, secret manager, queue/worker, TLS, error tracking, backups, alerting.
- Use separate credentials and databases per environment.
- Use migration-based schema changes; never rely on ad hoc production schema edits.
- Add health endpoints for liveness/readiness without exposing internals.

## 12. Testing strategy
- Unit: state transitions, permissions, budgets, schema validation, versioning.
- Integration: API + database + workflow persistence.
- Security: cross-tenant read/write attempts, role bypass, CSRF, secret leakage.
- Contract: AI provider and connector response handling.
- Workflow: success, missing input, invalid model output, provider timeout, budget exhaustion, cancellation, retry.
- Approval: stale version, unauthorized approver, changed payload, rejected action, revoked integration.
- External action: duplicate retry, ambiguous timeout, connector failure, verification required.
- UI: keyboard navigation, loading/error/empty states, approval confirmation.
- Load/cost: representative workflow volume and model usage.

## 13. Implementation order
1. App factory/configuration, database, migrations, health endpoint.
2. Auth, organization, membership, tenant authorization.
3. Business profile and campaign CRUD.
4. Task/run/deliverable models and state transitions.
5. AI adapter and schema validation.
6. Campaign workflow and persisted deliverables.
7. Review/versioning/comments.
8. Approval service and audit log.
9. Manual handoff / export.
10. Usage reporting, limits, kill switch, operational monitoring.
11. First supported connector after access and channel decision.
