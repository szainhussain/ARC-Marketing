# Test Report

All tests and verification steps below were actually run in this session
(not claimed from memory). Commands and real output are reproduced.

## Backend: pytest

```
$ source .venv/Scripts/activate
$ python -m pytest -q
......................                                                   [100%]
22 passed in 2.84s
```

Coverage by area:

- **Auth** (`test_auth_and_campaigns.py`): registration field validation,
  generic login-failure message (no account enumeration), unauthenticated
  requests denied.
- **Campaign CRUD** (`test_auth_and_campaigns.py`): create/list/update/
  archive, required-field validation, idempotent creation (duplicate key →
  same record, not a duplicate row).
- **Workflow state** (`test_workflow_run.py`,
  `test_workflow_success_path.py`): `needs_input` when the business
  profile is incomplete; `failed` with a `capability_unavailable:`-prefixed
  error when no AI provider is configured; idempotent run start; missing
  idempotency key rejected; **full 5-stage success path** against a fake
  provider — all deliverables created, run reaches `completed`, 5 usage
  records written.
- **Deliverable/approval/handoff lifecycle**
  (`test_deliverable_approval_handoff.py`): editing creates a new version
  and invalidates the pending approval on the old one; approve → execute
  → `publication_status` stays `unverified` until an explicit confirm
  call, never auto-marked published; rejected approval cannot execute
  (409); duplicate idempotency key on execute returns the same
  `ExternalAction`, not a second one.
- **Tenant isolation** (`test_tenant_isolation.py`): a user in Org A
  cannot read Org A's campaigns or business profile after switching to
  Org B (403, and Org B's own data remains reachable — not a blanket auth
  failure); a `contributor`-role member cannot approve an external action
  (403).
- **State machine** (`test_state_machine.py`): allowed transition
  succeeds; disallowed transition raises `Conflict` and leaves state
  unchanged.

Zero warnings in the final run (fixed several `SQLAlchemy 2.0` legacy
`.query.get()` deprecation warnings and one FK-ordering warning on
`drop_all()` along the way).

## Frontend: build + lint

```
$ cd frontend && npm run build
✓ 49 modules transformed, built in ~0.8–1s, 0 errors

$ npm run lint
2 warnings (react-refresh/only-export-components, both in context files — benign), 0 errors
```

## Docker

```
$ docker build -t mdh-backend:test .
... psycopg2_binary-2.9.10-cp312-cp312-manylinux... installed successfully ...
#16 DONE — image built

$ docker run --rm --entrypoint python -e SECRET_KEY=test -e DATABASE_URL=sqlite:////tmp/test.db mdh-backend:test \
    -c "from app import create_app; app = create_app('testing'); print('app OK:', app.name)"
app OK: app
```

Confirms the Dockerfile builds and the Flask app factory imports cleanly
inside the pinned-Python-3.12 image — including `psycopg2-binary`, which
fails to install on the host machine's Python 3.14 (see `docs/DECISIONS.md`
D2). **Not run**: a full `docker compose up` against a live Postgres
container, or a migration run inside the container against real Postgres.
Test image and container were removed after verification.

## Browser verification (real headless Chromium via Playwright)

Full journey driven end-to-end through the actual running frontend +
backend (not just API calls): landing page → sign up → create workspace →
onboarding (business profile form) → dashboard → new campaign brief →
campaign workspace → run workflow. Screenshots captured at every step.

This surfaced **two real bugs**, both fixed and re-verified in this
session:

1. **Accessibility bug — labels not associated with inputs.** Every form
   used `<label>Text</label>` as a sibling of its `<input>`, with no
   `htmlFor`/`id` pairing. This isn't just a screen-reader problem (which
   the spec explicitly requires — "semantic labels"): it's how
   `getByLabel` found nothing and the first browser run couldn't even get
   past the sign-up form. Fixed across `SignUpPage`, `SignInPage`,
   `CreateWorkspacePage`, `NewCampaignPage`, and `OnboardingPage` (14
   fields via its shared `field()` helper).

2. **Real data-loss race condition in the onboarding form.** React 19's
   StrictMode double-invokes mount effects in development. `OnboardingPage`'s
   `useEffect` fetched the business profile and called `setProfile(...)`
   unconditionally. Depending on exact network timing, a stale, superseded
   GET response could resolve *after* the user had already started typing
   and silently overwrite their input — reproduced twice with different
   subsets of fields wiped each time (confirming it was a timing race, not
   a deterministic logic bug), traced by capturing the actual PATCH request
   body the browser sent and comparing it against a fresh direct API test.
   Fixed with the standard cancellation-flag guard (`cancelled` boolean
   returned from the effect's cleanup function); verified clean across 3
   repeated full-journey runs afterward.

Also fixed during this verification: the frontend's `VITE_API_BASE_URL`
pointed at `127.0.0.1:5000` while Vite (port 5173 being already in use by
an unrelated project on this machine) served the app from
`localhost:5174`. Browsers treat `127.0.0.1` and `localhost` as different
sites, so the `SameSite=Lax` session cookie was silently dropped on every
cross-site fetch — registration appeared to fail with "CSRF session token
is missing" even though CORS was correctly configured. Fixed by pointing
the frontend at `localhost` and documenting the gotcha in `README.md` and
`CLAUDE.md`.

Final state after fixes, confirmed across 3 repeated runs: onboarding data
saves correctly, the dashboard and campaign workspace render real
persisted data, and the workflow run correctly reaches `status: failed`
with a clear `capability_unavailable` message on the first stage (expected
and correct, since no `ANTHROPIC_API_KEY` is configured) — nothing is
fabricated. Console had only the expected pair of benign `401` entries
from the initial unauthenticated `/me` probe before login.

Minor known gap not fixed in this session: `DashboardPage`,
`CampaignListPage`, `ReportsPage`, and `IntegrationsPage` have the same
unguarded fetch-on-mount shape as the original `OnboardingPage` bug, but
since they're read-only displays (no form input to lose), the consequence
of the same race is a wasted duplicate network call, not data loss — left
as a documented cleanup item rather than fixed under time pressure for a
non-data-loss case.

## What was not tested

- No load/concurrency testing.
- No test against a real Anthropic API call (no key available in this
  session) — only against the fake-provider success path and the
  no-provider-configured failure path.
- No automated test for the kill switch or the monthly usage limit (both
  implemented; manual-only verification, see `docs/SECURITY_AND_GOVERNANCE.md`).
- No accessibility audit beyond the label-association fix above (no
  axe-core or similar scan run).
- No cross-browser testing (Chromium only).
