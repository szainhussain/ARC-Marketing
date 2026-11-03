# CLAUDE.md — Marketing Department Harness

Project instructions for Claude Code sessions working on this repo. Read
`marketing_department_harness_complete_specification.md` and
`docs/IMPLEMENTATION_PLAN.md` before making architectural changes.

## What this is

A multi-tenant SaaS app coordinating an AI marketing workflow behind
backend-enforced approvals. Not a chatbot wrapper — campaigns, tasks,
deliverable versions, and approvals are all persisted, versioned records.
See `docs/DECISIONS.md` for why things are built the way they are.

## Architecture at a glance

- Modular Flask monolith (`app/`), not microservices. Don't introduce a
  queue, message bus, or separate services unless a real throughput/
  reliability need justifies it (see `docs/DECISIONS.md`).
- `app/models/` — SQLAlchemy models, every tenant-owned table has an
  `organization_id` column.
- `app/services/` — business logic. Routes call services; services never
  trust `organization_id` from anywhere except
  `authorization_service.get_membership_or_403()`.
- `app/agents/` — thin stage classes (CMO planner, research analyst,
  marketing manager, content creator, quality reviewer), not autonomous
  processes. Each stage has one task_type and one Marshmallow output schema.
- `app/ai/` — provider-neutral adapter. Never import `anthropic` (or any
  SDK) outside `app/ai/provider_adapter.py`.
- `app/workflows/campaign_workflow.py` — the one pipeline that exists today
  (strategy → research_notes → campaign_plan → content_pack → qa_report),
  run synchronously in the request. Stops cleanly on the first failed
  stage; does not roll back already-completed stages.
- `app/integrations/` — connector contract + `manual_handoff.py` (the only
  implemented connector). A live publishing connector is explicitly
  deferred — see `docs/12_AGENT_EXPANSION_ROADMAP.md` and `docs/DECISIONS.md`.

## Non-negotiable rules (do not relax these for convenience)

1. Every org-scoped route calls `get_membership_or_403(organization_id)`
   before touching data. Never read `organization_id` from a request body
   as the access-control boundary.
2. A `DeliverableVersion` is immutable once created. "Editing" always means
   `add_new_version()`, which also invalidates any pending `Approval` tied
   to the previous version.
3. An `Approval` is tied to an exact `deliverable_version_id` +
   `action_payload_hash`. Re-check both immediately before executing
   anything in `external_action_service.py` — don't trust an earlier check.
4. Never mark an `ExternalAction` as published. `publication_status` only
   becomes `manually_confirmed_published` via the user's own explicit
   confirmation call. Exporting/handing off content is not publishing it.
5. If `ANTHROPIC_API_KEY` is unset (or any provider call fails in a way
   that isn't a real model/schema problem), raise `ProviderUnavailable` and
   let the workflow fail that stage with a `capability_unavailable:` prefix
   in `error_summary`. Never have a stage return fabricated content when
   the provider isn't actually configured.
6. All AI output is validated against a Marshmallow schema in
   `app/ai/schemas.py` before it touches a deliverable. Don't persist raw
   model text as a deliverable's content.
7. Idempotency keys are required (and enforced via a unique DB constraint)
   on campaign creation, workflow-run start, and external-action execution.

## Commands

```bash
# Backend tests (from repo root, venv activated)
python -m pytest -q

# Backend dev server
export FLASK_APP=wsgi.py && flask run

# New migration after changing app/models/*.py
export FLASK_APP=wsgi.py && flask db migrate -m "describe the change" && flask db upgrade

# Frontend
cd frontend && npm run dev     # dev server
cd frontend && npm run build   # typecheck + production build
cd frontend && npm run lint
```

## Local dev gotcha: hostname must match between frontend and backend

`frontend/.env.local`'s `VITE_API_BASE_URL` and the backend's
`FRONTEND_ORIGIN` (`.env`) must use the same hostname (`localhost` or
`127.0.0.1`, not a mix) — the session cookie is `SameSite=Lax`, and
browsers treat those two hostnames as different sites even though CORS
allows the cross-port request. This caused a real bug during this build
(see `docs/TEST_REPORT.md`); don't reintroduce it.

## Testing conventions

- `tests/conftest.py` has `register_and_login`, `create_org`,
  `complete_profile`, `create_campaign` helpers — use them instead of
  re-deriving the auth/org dance in every test.
- Tests that need a deliverable without a real AI call should call
  `create_deliverable_with_first_version()` directly inside
  `app.app_context()`, the way `tests/integration/test_deliverable_approval_handoff.py`
  does — or monkeypatch `app.workflows.campaign_workflow.get_provider` with
  a fake `AIProvider`, the way `tests/integration/test_workflow_success_path.py`
  does. Don't call the real Anthropic API from a test.
- Any new tenant-scoped resource needs a cross-tenant-denial test in
  `tests/security/`.

## Frontend conventions

- Every `<label>` needs a matching `htmlFor`/`id` pair — this isn't just
  accessibility, Playwright's `getByLabel` (and screen readers) depend on
  it, and we caught a real bug this way during browser verification.
- Any `useEffect` that fetches-then-`setState` on mount needs the
  cancellation-flag guard (see `OnboardingPage.tsx`) — React 19 StrictMode
  double-invokes mount effects in dev, and an unguarded late response can
  silently overwrite state a user already changed. This caused a real data
  loss bug during this build; the dashboard/reports/campaign-list pages
  don't yet have this guard since they're read-only (lower risk), but
  apply it to any new page with form state.

## What NOT to do without asking first

- Don't add a live publishing connector (Meta, LinkedIn, etc.) without the
  user first choosing a pilot channel and confirming API access — see
  `docs/12_AGENT_EXPANSION_ROADMAP.md`.
- Don't relax `sandbox`/CSRF/session settings to "make dev easier" — fix
  the actual hostname/CORS config instead (see the gotcha above).
- Don't claim a milestone (M7–M12 in `docs/IMPLEMENTATION_PLAN.md`) is done
  without adding a real test for it and updating `docs/TEST_REPORT.md`.
