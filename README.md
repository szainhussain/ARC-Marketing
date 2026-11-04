# ARC — Your marketing department. Always moving.

**ARC** is a multi-tenant SaaS "Marketing Department as a Service": 12
specialist AI agents (CMO, Marketing Manager, Social, PR & Partnerships,
Paid Media, Creative, Research, Customer Insights, SEO & Growth, Key
Accounts, Marketing Ops/QA, Record Keeper) run each campaign through a
durable dependency graph, with version-bound human approvals on anything
that leaves the workspace. It never posts, sends or spends on your behalf.

**Status:** feature-complete against the MaaS brief for local use and
tested (77 backend, 10 frontend, 18-step E2E). **Not deployed.** Live
publishing/ads/analytics connectors and email delivery need credentials —
see `docs/PRODUCT_REQUIREMENTS.md` and `docs/INTEGRATIONS.md`.

## Stack

- Backend: Flask app factory, SQLAlchemy + Alembic, SQLite (dev) / PostgreSQL,
  DB-backed task queue + `flask worker`, Flask-Login sessions, CSRF,
  Flask-Limiter, Marshmallow schemas, OpenAPI at `/api/v1/openapi.json`.
- AI: provider-neutral adapter (Anthropic, Groq); no provider → honest
  `capability_unavailable`, never fabricated output.
- Frontend: React 19 + TypeScript + Vite, React Router, Motion, Recharts,
  Lucide; design tokens in `frontend/src/index.css` (D13).

## Run locally

```bash
python -m venv .venv && source .venv/Scripts/activate   # macOS/Linux: .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then set GROQ_API_KEY or ANTHROPIC_API_KEY
export FLASK_APP=wsgi.py
flask db upgrade && flask seed-plans
flask run                       # terminal 1: API on :5000
flask worker                    # terminal 2: agent worker (runs stay "Queued" without it)
cd frontend && npm install && cp .env.example .env.local && npm run dev   # terminal 3
```

Keep the hostname consistent: `VITE_API_BASE_URL` (frontend) and
`FRONTEND_ORIGIN` (backend) must both use `localhost` (session cookie is
`SameSite=Lax`).

Open the site, click **Build your marketing team**, complete onboarding,
create a campaign and choose **Save and run the department**. Watch it in
**Operations**. Billing runs in a clearly labelled TEST MODE locally.

## Tests

```bash
python -m pytest -q                       # backend
cd frontend && npm run build && npm run lint && npm test
bash scripts/run_e2e.sh                   # E2E journey (needs `npm run dev`), fixture AI, throwaway DB
```

Results and what was *not* executed: `docs/TEST_REPORT.md`.

## Docker

`docker compose up --build` starts Postgres, the API (migrations + plan
seed on start), the worker and the nginx-served frontend. Not yet run end
to end against Postgres in this environment.

## Documentation

`docs/PRODUCT_REQUIREMENTS.md` (status matrix) · `ARCHITECTURE.md` ·
`AGENT_SYSTEM.md` · `AGENT_WORKFLOWS.md` · `DATA_MODEL.md` · `API.md` ·
`SECURITY_AND_GOVERNANCE.md` · `INTEGRATIONS.md` · `BILLING_AND_PLANS.md` ·
`DEPLOYMENT.md` (incl. release checklist) · `OPERATIONS_RUNBOOK.md` ·
`DECISIONS.md` · `TEST_REPORT.md` · `IMPLEMENTATION_PLAN.md` ·
`TOOLS_AND_SKILLS.md` · `12_AGENT_ROADMAP.md`.

## Known limitations

- No live social/ads/analytics/CRM connectors (manual export only); no
  business metrics (spend, conversions, revenue) until one is connected.
- No email delivery: password-reset and verification links are logged
  server-side in dev; invitation links are shown to the admin to share.
- Stripe adapter implemented but not exercised; prices are provisional.
- AI costs are estimates from placeholder per-token prices.
- MFA, SSO, recurring/scheduled campaign programs, OpenAI adapter: not built.
- Groq free tier (8k tokens/min) makes a full run take several minutes;
  the worker retries automatically.

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
