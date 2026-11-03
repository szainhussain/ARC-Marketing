# Marketing Department Harness

A multi-tenant SaaS platform that gives SMBs a coordinated AI marketing
workflow: business profile → campaign brief → strategy/research/plan/content
→ quality review → human approval → manual handoff/export. See
`marketing_department_harness_complete_specification.md` for the full
product, UI/UX, architecture, and governance specification this build
follows, and `docs/IMPLEMENTATION_PLAN.md` for what has actually been built
versus what remains.

**Status: local prototype / pilot candidate.** Not production-ready — see
"Known limitations" below and `docs/DECISIONS.md`.

## Stack

- Backend: Python 3.12+ / Flask, SQLAlchemy + Alembic, SQLite (dev) or
  PostgreSQL (docker-compose / production).
- Frontend: React 19 + TypeScript, Vite, React Router.
- AI: provider-neutral adapter, Anthropic implementation included. Runs in a
  documented `capability_unavailable` state when no API key is configured —
  it never fabricates output.
- Auth: email/password, Flask-Login session cookies, Flask-WTF CSRF.

## Local setup (no Docker)

Requires Python 3.12+ (3.14 works too, except `psycopg2-binary`, which has
no prebuilt wheel for very new Python versions yet — local dev uses SQLite
instead, see below) and Node 20+.

### Backend

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt   # SQLite-only deps; use requirements.txt (+ psycopg2) for Postgres
cp .env.example .env                  # already present in this checkout with a generated dev SECRET_KEY
export FLASK_APP=wsgi.py
flask db upgrade                      # creates instance/dev.db
flask run
```

Backend serves on `http://127.0.0.1:5000` (equivalently `http://localhost:5000`).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend serves on `http://localhost:5173` (Vite auto-increments the port,
e.g. to 5174, if 5173 is already in use by something else on your machine —
watch the terminal output).

**Important:** `frontend/.env.local`'s `VITE_API_BASE_URL` and the backend's
`FRONTEND_ORIGIN` (in `.env`) must use the *same hostname* — both
`localhost` or both `127.0.0.1`, not one of each. The backend's session
cookie is `SameSite=Lax`; browsers treat `localhost` and `127.0.0.1` as
different sites, which silently drops the cookie on cross-site fetches even
though CORS allows the request. If you change the frontend port, update
`FRONTEND_ORIGIN` in `.env` to match and restart the backend.

### Tests

```bash
source .venv/Scripts/activate
python -m pytest -q
```

22 tests covering auth, tenant isolation, campaign CRUD + idempotency,
workflow state (needs_input / capability_unavailable / full success path),
deliverable versioning, approval lifecycle, and manual handoff — all
passing as of this build. See `docs/TEST_REPORT.md` for the full run log
and what is *not* covered yet.

## Docker

```bash
docker compose up --build
```

Starts Postgres, the Flask backend (migrations run automatically on
container start via `docker-entrypoint.sh`, then `gunicorn`), and the
built frontend served by nginx. Set `ANTHROPIC_API_KEY` in your shell
environment before running compose if you want AI-generated stages to
actually run; otherwise the workflow correctly reports
`capability_unavailable`.

The Dockerfile and compose file were built and smoke-tested in this
session (image builds, `psycopg2-binary` installs cleanly against the
pinned Python 3.12 base image, and the Flask app factory imports
successfully inside the container). A full `docker compose up` against a
live Postgres container was **not** run end-to-end in this session — do
that before relying on it for a pilot.

## Project layout

```
app/              Flask application (api/, models/, services/, agents/, ai/, workflows/, integrations/)
migrations/       Alembic migrations
tests/            unit/, integration/, security/
frontend/         React + TypeScript app (Vite)
docs/             Architecture, API, security, test report, decisions, deployment,
                  12-agent roadmap + full operating model (docs/AGENT_OPERATING_MODEL.md),
                  tools/dependency evaluation (docs/TOOLS_AND_DEPENDENCIES.md)
.claude/          Project-specific Claude Code agents and skills for continuing this build,
                  plus the ui-ux-pro-max design-guidance skill (pruned install — see
                  docs/TOOLS_AND_DEPENDENCIES.md for what was kept vs. removed)
```

## Known limitations (read before pitching this as "done")

- **No live AI generation tested** without a real `ANTHROPIC_API_KEY` — the
  adapter and schema validation are implemented and unit-tested with a fake
  provider, but never exercised against the real Anthropic API in this
  session.
- **Only manual handoff/export** is implemented for external actions — no
  live publishing connector (that's M11 in the backlog, deliberately
  deferred until a pilot channel is chosen).
- **Milestones M0–M6 are the solid core** (foundation, auth/tenant
  isolation, business profile, campaign CRUD, workflow persistence, AI
  adapter, full 5-stage pipeline) plus the essentials of M7–M9 (versioning,
  approvals, manual handoff). M10 (alerting/backup-restore drills), M11
  (live connector), and M12 (paid pilot instrumentation) are **not**
  implemented — see `docs/IMPLEMENTATION_PLAN.md`.
- Only 6 of the 16 UI/UX spec screens are built (landing, sign-up/in,
  workspace creation, onboarding, dashboard, campaign list/brief/workspace,
  reports, integrations). Team/permissions management, billing, and the
  platform-admin surface are not built.
- Role-based approval permissions exist and are enforced server-side, but
  there is no UI yet to invite teammates or change a member's role — role
  changes currently require direct DB access (tested that way in
  `tests/security/test_tenant_isolation.py`).
- No rate limiting, background job queue, or backup/restore drill yet —
  the workflow runs synchronously in the request, which is acceptable for
  this milestone's single-AI-call-chain but should move to a queue (Celery/
  RQ + Redis) before a real pilot with concurrent users.

## Troubleshooting

- **`psycopg2-binary` fails to build locally**: use
  `requirements-dev.txt` (SQLite) for local dev, or run the backend inside
  Docker where Python 3.12 has a prebuilt wheel available.
- **CSRF 400 errors from the frontend**: the API requires `GET
  /api/v1/auth/csrf-token` first (the frontend's `apiRequest` helper does
  this automatically) and the session cookie to be present — check the
  hostname-matching note above.
- **Workflow always shows `capability_unavailable`**: expected until
  `ANTHROPIC_API_KEY` is set in `.env`.
