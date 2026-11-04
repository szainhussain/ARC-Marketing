# Implementation Plan

Written at the start of the build session covered by this plan, and kept
accurate afterward rather than describing aspirational scope. Milestone IDs
match `marketing_department_harness_deliverables/05_IMPLEMENTATION_BACKLOG.md`.

## Architecture decisions (see docs/DECISIONS.md for full rationale)

- Modular Flask monolith, SQLAlchemy + Alembic, Marshmallow for schema
  validation (not Pydantic — simpler Flask integration).
- SQLite for local dev/test (the host machine's Python 3.14 has no
  prebuilt `psycopg2-binary` wheel yet); PostgreSQL via Docker/production,
  using a pinned Python 3.12 base image where the wheel installs cleanly.
- Session-cookie auth (Flask-Login) + Flask-WTF CSRF, not JWT — simplest
  correct option for a single first-party SPA talking to this API with no
  OAuth/identity-provider requirement yet.
- Workflow runs synchronously in the request (no Celery/RQ yet) — the
  pipeline is 5 sequential AI calls, acceptable for this milestone; a queue
  is the explicit next step before a real pilot with concurrent users.
- AI provider: Anthropic only, behind `app/ai/provider_adapter.py`'s
  provider-neutral interface.

## Requirement-to-feature mapping (milestones actually built)

| Milestone | Status | Evidence |
|---|---|---|
| M0 — runnable skeleton | **Done** | App factory, config profiles, health/ready endpoints, structured logging + redaction, pytest, Docker + compose, `.env.example` |
| M1 — identity/org/tenant isolation | **Done** | Register/login/logout, `Organization`/`Membership`, `get_membership_or_403`, `tests/security/test_tenant_isolation.py` |
| M2 — business profile | **Partial** | CRUD API + onboarding UI done; `Document` model exists but file upload endpoint is **not** implemented |
| M3 — campaign CRUD + brief | **Done** | Create/list/read/update/archive, idempotency key, validation, UI |
| M4 — workflow/task persistence | **Done** | `WorkflowRun`/`Task` models, state machine, idempotent start-run endpoint, cancel endpoint |
| M5 — AI provider adapter | **Done** | `AIProvider` interface, `AnthropicProvider` + `NullProvider`, typed errors, schema validation, bounded retry, budget check |
| M6 — campaign workflow vertical slice | **Done** | All 5 stages wired, deliverables + versions persisted, tested with a fake provider (`test_workflow_success_path.py`) |
| M7 — review/editing/versioning | **Partial** | `add_new_version` + API done, invalidates stale approvals; no diff view, no comments model exposed via API yet |
| M8 — approval/governance engine | **Partial** | `Approval` model, role-gated decision, re-validation before execution, audit events, org-level monthly workflow limit, kill switch (`Organization.kill_switch_enabled` + global `KILL_SWITCH_ENABLED`); **no per-run budget enforcement beyond the AI adapter's own budget check**, no admin UI to flip the kill switch (DB/env only) |
| M9 — manual handoff/export | **Done** | `ManualHandoffConnector`, `ExternalAction` model, publication status kept separate from handoff status, idempotent execute endpoint |
| M10 — reporting/ops readiness | **Partial** | Summary + usage report endpoints and UI done; no alerting, no backup/restore drill, no support runbook |
| M11 — live integration | **Not started** | Deliberately deferred — no pilot channel chosen yet |
| M12 — paid pilot | **Not started** | Out of scope for this session |

## Security and governance controls implemented

- Server-side tenant scoping on every route (`get_membership_or_403`).
- Role-based approval permission (`Membership.can_approve_external_actions`).
- Immutable deliverable versions; edits always create a new version.
- Approval tied to `(deliverable_version_id, action_payload_hash)`; stale
  approvals are invalidated automatically and re-checked before execution.
- Idempotency keys with unique DB constraints on campaign creation,
  workflow-run start, and external-action execution.
- Append-only audit log (`AuditEvent`) on every significant state change.
- Kill switch checked immediately before external-action execution.
- CSRF protection on all mutating routes; generic (non-enumerating) login
  error message; secrets redacted from logs.
- Cross-tenant access denial tested in `tests/security/test_tenant_isolation.py`.

Not yet implemented: rate limiting, encrypted-at-rest credential storage
(no live connector exists yet to need it), file upload malware scanning,
SSO.

## Test strategy and results

See `docs/TEST_REPORT.md` for the full run. Summary: 22 backend tests
(unit + integration + security), all passing; frontend type-checks and
builds cleanly; full user journey (sign-up → workspace → onboarding →
campaign → workflow run) verified in a real headless browser, which
surfaced and led to fixing two real bugs (see `docs/TEST_REPORT.md`).

## Completion criteria for this session

Met: app starts from documented instructions; frontend talks to backend;
migrations work; auth + org scoping enforced and tested; core campaign
workflow runs end-to-end (including the full success path with a fake
provider); deliverables persist and version; approval logic is
server-enforced; manual handoff correctly distinguishes "handed off" from
"published"; dashboard reflects real persisted data; loading/empty/error
states implemented on every built screen; tests actually run; browser
verification actually performed; no secrets committed.

Not met / explicitly deferred: live AI generation against a real API key
(never exercised in this session — no key available); live publishing
connector; background job queue; full 16-screen UI/UX spec (6 of 16
screens built); billing; SSO; backup/restore drill; alerting.

## Unresolved decisions (carried from the PRD, still open)

- First pilot channel for a future live connector.
- Production AI provider contract/retention terms and cost controls.
- Subscription price and included usage.
- Hosting region and applicable privacy/legal requirements.
- Identity provider (if SSO becomes a requirement) and transactional email
  service (password reset isn't implemented yet — see "Explicitly out of
  scope" below).

## Explicitly out of scope for this session (not silently skipped)

- Password reset / account recovery flow (FR-001 mentions it; not built).
- Team invite flow (role changes currently require direct DB access).
- File upload endpoint for `Document` (model exists, route does not).
- Comments on deliverables (model would need adding; not in `app/models/`).
- Notifications.
- Any of M11 (live connector) or M12 (paid pilot instrumentation).

## MaaS brief — staged delivery (started 2026-11-03)

The MaaS master brief arrived truncated after §17; billing/plans use
documented defaults until the rest is supplied.

| Stage | Scope | Status |
|---|---|---|
| 1 | 12 real agents (versioned specs, schemas, `reads` allowlist, budgets, evaluation); durable DB-backed engine + `flask worker` (deps, retries/backoff, leases, pause/resume/cancel, budgets); Operations Center (`/app/operations`, agent detail, tasks, approvals inbox, activity, workspace controls) | **Done**, see TEST_REPORT "Stage 1" |
| 2 | Business Command Center dashboard, public site pages, remaining app routes | Not started |
| 3 | Billing/plans models and limits (needs brief §18+) | Not started |
| 4 | Integrations framework beyond manual export | Not started; no live connector without user approval |

### Status update (2026-11-04)

Brief received in full (§1–25). Milestones 0–10 and 12–13 are implemented
and tested locally; Milestone 11 (live integrations) is built to the
supported boundary (catalog, enable/disable, signed webhooks, manual
export) and blocked on credentials and your pilot-channel choice. See
`docs/PRODUCT_REQUIREMENTS.md` for the per-requirement matrix and
`docs/TEST_REPORT.md` "Stage 2" for evidence.

Next concrete tasks: deploy (API + worker + Postgres + frontend), wire
email delivery, choose a pilot channel for the first live connector, MFA,
real provider pricing for cost estimates, Stripe test-mode run.
