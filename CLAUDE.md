# CLAUDE.md — ARC (formerly "Marketing Department Harness")

Project instructions for Claude Code sessions working on this repo. The
product is branded **ARC** ("Strategy. Plan. Execution.") as of
`docs/DECISIONS.md` D10 — the repo folder name and internal code
(`app/`, model/class names, etc.) were deliberately left unrenamed, since
that would be a large, low-value refactor unrelated to branding; only
user-facing surfaces (frontend UI, page title, README) changed. Read
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
- `app/agents/` — the 12 department agents as versioned `AgentSpec`s in
  `definitions.py` (validated by `registry.py` at import), not autonomous
  processes. Each agent has one task_type, one Marshmallow output schema,
  `depends_on`, and a `reads` allowlist the engine enforces. Changing an
  agent's instructions/inputs/schema means bumping its `version`. See
  `docs/AGENT_SYSTEM.md`.
- `app/ai/` — provider-neutral adapter. Never import `anthropic`, `groq`,
  or any SDK outside `app/ai/provider_adapter.py`. Two providers exist
  (`AnthropicProvider`, `GroqProvider`); a third means one new class
  implementing `AIProvider`, nothing else changes. Both SDK clients are
  constructed with `max_retries=0` — keep this on any new provider too,
  or its SDK's internal retry-on-429 sleep can hang a request for tens of
  seconds before this app's own bounded retry/timeout ever sees it (this
  actually happened — a real ~41s hang on a Groq rate limit — see
  `docs/DECISIONS.md` D8).
- `app/workflows/engine.py` — durable, dependency-aware execution. The
  API only enqueues a run (12 `Task`s + `TaskDependency`s); a separate
  `flask worker` process claims tasks atomically, runs agents, retries
  rate limits/timeouts with backoff, recovers expired leases, and unblocks
  dependents. DB-backed, no Redis — see `docs/DECISIONS.md` D11 and
  `docs/OPERATIONS_RUNBOOK.md`. Never call a model from a web request.
  `app/workflows/evaluation.py` holds code-level output checks.
- `app/integrations/` — connector contract, `manual_handoff.py`, and the
  first live connector `wordpress_com.py` (pilot channel chosen by the user,
  D17). Tokens are Fernet-encrypted at rest (`app/crypto.py`) and never
  returned by the API. Other live connectors still need the user to pick
  the channel and confirm API access first.

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
4. Never mark an `ExternalAction` as published from a request, a webhook
   or an agent. `publication_status` becomes `manually_confirmed_published`
   only via the user's own explicit confirmation call, or
   `platform_verified_published` only inside a live connector's worker step
   after it reads the item back from the platform itself (WordPress.com,
   `publishing_service.py`; docs/DECISIONS.md D17). Exporting/handing off
   content is not publishing it. Live connectors re-check kill switch,
   approval and exact version in the worker immediately before acting.
5. If `ANTHROPIC_API_KEY` is unset (or any provider call fails in a way
   that isn't a real model/schema problem), raise `ProviderUnavailable` and
   let the workflow fail that stage with a `capability_unavailable:` prefix
   in `error_summary`. Never have a stage return fabricated content when
   the provider isn't actually configured.
6. All AI output is validated against a Marshmallow schema in
   `app/ai/schemas.py` before it touches a deliverable. Don't persist raw
   model text as a deliverable's content. The prompt built in
   `_build_prompt()` includes a per-field type hint generated from the
   schema itself (`_describe_field()`) — keep it schema-derived rather
   than hand-written per field if you add a new schema; a real test
   against Groq showed weaker-instruction-following models substitute
   objects for plain-string lists (and vice versa) without an explicit
   hint, which schema validation then correctly rejects rather than
   silently accepting.
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
cd frontend && npm test        # Vitest component tests
bash scripts/run_e2e.sh       # E2E journey (needs `npm run dev` running)
```

## Local dev gotcha: hostname must match between frontend and backend

`frontend/.env.local`'s `VITE_API_BASE_URL` and the backend's
`FRONTEND_ORIGIN` (`.env`) must use the same hostname (`localhost` or
`127.0.0.1`, not a mix) — the session cookie is `SameSite=Lax`, and
browsers treat those two hostnames as different sites even though CORS
allows the cross-port request. This caused a real bug during this build
(see `docs/TEST_REPORT.md`); don't reintroduce it.

## SaaS foundation (plans, billing, policies, knowledge)

- Plan limits are data (`plans.entitlements_json`) enforced in services —
  check `check_entitlement()` before adding any new metered action.
- Subscription state changes only in `billing_service.process_event()`
  from a verified webhook. Never set a plan directly from a user request.
- Locked action policies (`ACTION_POLICY_DEFAULTS` with `locked=True`)
  are platform boundaries; don't add an API path that loosens them.
- Agents receive knowledge only via `approved_knowledge_for_agents()`.
- `AI_PROVIDER=fixture` is for E2E only (D16); keep it gated.
- New tenant-scoped endpoints must be added to
  `tests/security/test_saas_isolation.py` (or a sibling).

## Testing conventions

- `tests/conftest.py` has `register_and_login`, `create_org`,
  `complete_profile`, `create_campaign` helpers — use them instead of
  re-deriving the auth/org dance in every test.
- Tests that need a deliverable without a real AI call should call
  `create_deliverable_with_first_version()` directly inside
  `app.app_context()`, the way `tests/integration/test_deliverable_approval_handoff.py`
  does — or use `tests/fakes.py` (`FakeProvider`, `use_provider`) which
  patches `app.workflows.engine.get_provider`, then call
  `app.workflows.engine.drain()` to run the worker loop inline, the way
  `tests/integration/test_engine.py` does. Don't call a real AI API from a
  test.
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
  loss bug during this build; the dashboard already has this guard,
  reports/campaign-list pages don't yet since they're read-only (lower
  risk), but apply it to any new page with form state.
- Render deliverable content through `components/DeliverableContent.tsx`
  (one renderer per `deliverable_type`, e.g. `Strategy`, `CampaignPlan`),
  not a raw `JSON.stringify(...)` dump — that was the actual UI before a
  redesign fixed it. Adding a new deliverable type (per
  `docs/12_AGENT_ROADMAP.md`) means adding one renderer function
  there, keyed into `RENDERERS`; keep the collapsible "View raw JSON"
  fallback for transparency/debugging.
- Design tokens live in `index.css`'s `:root` (ARC's dark theme — near-
  black background, electric cyan/indigo accent — chosen via the
  `.claude/skills/ui-ux-pro-max` skill's color catalog, see
  `docs/DECISIONS.md` D10; query the skill again for new palette/style
  decisions rather than guessing).
- Animation goes through `frontend/src/components/motion/` (`Reveal` for
  scroll-triggered fade-in, `TiltCard` for the 3D hover effect,
  `AnimatedNumber` for counting KPI values) — don't add raw `motion.div`
  usage or hand-rolled animation loops elsewhere; extend these three or
  add a new one in the same directory. `Reveal` and `AnimatedNumber`
  already handle `prefers-reduced-motion` internally (via `motion`'s
  `useReducedMotion`) — don't re-guard them.

## Platform export formatting (not a connector)

`app/integrations/export_formats.py` formats an already-approved
`content_pack` to Meta/Instagram, Google Ads, or TikTok Ads composer
limits for manual copy-paste — no API calls, no OAuth, no posting/
spending. See `docs/DECISIONS.md` D9. If you add a field or platform:
cite an official source in the `FieldCheck`/docstring, or set
`limit_confirmed=False` — never fill in a commonly-repeated-but-unofficial
number (this already happened once for real: Instagram's caption limit
and TikTok's ad-text limit aren't published anywhere official, and are
deliberately left unconfirmed rather than guessed at "2200" or similar).

## What NOT to do without asking first

- Don't add a live publishing connector (Meta, LinkedIn, etc.) without the
  user first choosing a pilot channel and confirming API access — see
  `docs/12_AGENT_ROADMAP.md`.
- Don't relax `sandbox`/CSRF/session settings to "make dev easier" — fix
  the actual hostname/CORS config instead (see the gotcha above).
- Don't claim a milestone (M7–M12 in `docs/IMPLEMENTATION_PLAN.md`) is done
  without adding a real test for it and updating `docs/TEST_REPORT.md`.
