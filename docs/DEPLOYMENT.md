# Deployment

**Status: deployed** — frontend on Vercel (usearc.vercel.app), API + worker on
Render, database and file storage on Supabase.

## Free hosting (Vercel + Render free + Supabase free)

| Piece | Where | Notes |
|---|---|---|
| Frontend | Vercel (Hobby) | Root `frontend`; `vercel.json` proxies `/api/*` to Render so cookies are first-party |
| API + agent worker | Render free web service via `render.yaml` | Worker runs in-process (`RUN_EMBEDDED_WORKER=true`, 1 gunicorn worker) |
| PostgreSQL | Supabase free | `DATABASE_URL` = the **Session pooler** URI (Connect button). The direct `db.<ref>.supabase.co` host is IPv6-only on the free plan and Render can't reach it |
| Uploaded files | Supabase Storage (private bucket) | `STORAGE_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (server only), `SUPABASE_STORAGE_BUCKET` |

Supabase can't host the API itself: Edge Functions run TypeScript only, with
short time limits, and agent runs are long-running Python.

Free-tier trade-offs (verify current terms on each provider's pricing page):
the Render service sleeps after ~15 minutes without traffic and takes about a
minute to wake, and the in-process worker pauses while it sleeps (queued
work resumes on the next request; open campaign pages poll, which keeps it
awake during a run). A free Supabase project is paused after about a week
with no database activity and must be restored from its dashboard; an uptime
monitor hitting `/api/v1/health/ready` (which queries the database) every
few minutes prevents both. Supabase's built-in email is for its own Auth
product, which ARC doesn't use, so transactional email needs a separate
provider (e.g. Resend).

### Moving the database from Neon to Supabase

1. Supabase: new project (region East US / us-east-1), save the DB password.
2. Storage → New bucket `arc-uploads`, **Public off**.
3. Render → arc-api → Environment: replace `DATABASE_URL` with the Session
   pooler URI; add `STORAGE_BACKEND=supabase`, `SUPABASE_URL`,
   `SUPABASE_SECRET_KEY`, `SUPABASE_STORAGE_BUCKET=arc-uploads`. Save → redeploy.
   On start, `flask db upgrade` creates the tables and `flask seed-plans` the plans.
4. Optional — keep existing data instead of starting fresh, before step 3:
   `pg_dump --no-owner --no-privileges -Fc "<neon url>" -f arc.dump` then
   `pg_restore --no-owner --no-privileges -d "<supabase session pooler url>" arc.dump`.
5. Check `/api/v1/health/ready` returns `"database": "ok"`, sign up, upload a
   file on the Assets page, then delete the Neon project.

## Processes

| Process | Command | Scale |
|---|---|---|
| API | `gunicorn wsgi:app` (Docker entrypoint runs `flask db upgrade` first) | horizontally |
| Worker | `flask --app wsgi.py worker` | 1+ (claims are atomic) |
| Scheduler (cron) | `flask purge-deleted-workspaces` daily | 1 |
| Frontend | static build (`npm run build`) behind nginx/CDN | — |

No Redis/Celery: the queue is the database (D11). Set
`RATELIMIT_STORAGE_URI=redis://…` if you run several API instances so rate
limits are shared.

## Environment variables

Names only — see `.env.example` for placeholders. Required in production:
`SECRET_KEY`, `DATABASE_URL` (PostgreSQL), `FRONTEND_ORIGIN`,
`AI_PROVIDER` + `ANTHROPIC_API_KEY` or `GROQ_API_KEY`. Optional:
`AI_MODEL`, `AI_TIMEOUT_SECONDS`, `AI_WORKFLOW_BUDGET_USD`,
`WORKER_RETRY_BASE_SECONDS`, `WORKER_RETRY_MAX_SECONDS`,
`RATELIMIT_STORAGE_URI`, `BILLING_PROVIDER` (`none` default in
production), `STRIPE_SECRET_KEY`, `BILLING_WEBHOOK_SECRET`, `TRIAL_DAYS`,
`APPROVAL_TTL_DAYS`, `INVITATION_TTL_DAYS`, `DELETION_GRACE_DAYS`,
`UPLOAD_DIR`, `MAX_UPLOAD_MB`, `STORAGE_BACKEND` (`local` or `supabase`),
`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_STORAGE_BUCKET`,
`KILL_SWITCH_ENABLED`. Never set
`ALLOW_FIXTURE_PROVIDER` or `WEBHOOK_ALLOW_PRIVATE_TARGETS` in production
(`ProductionConfig` forces the fixture provider off).

Frontend build: `VITE_API_BASE_URL=https://api.<domain>/api/v1`.

## Hosting shape (recommended)

- Frontend: Vercel/Netlify/static CDN.
- API + worker: Render, Railway, Fly.io or a container host (two services
  from the same image; the worker overrides the command).
- PostgreSQL: managed, with point-in-time recovery.
- Uploads: `STORAGE_BACKEND=supabase` (`app/storage.py`) — local disk is not
  durable on most PaaS hosts. Another provider means one more class with
  the same `put`/`get`/`delete` methods.
- Cookies: API and frontend on the same registrable domain
  (`app.<domain>` + `api.<domain>`) so `SameSite=Lax` session cookies
  work; `SESSION_COOKIE_SECURE` is forced on in production; HTTPS only.

## CI

`.github/workflows/ci.yml`: backend tests, migration check on a fresh
database, frontend typecheck/build/lint/unit tests, dependency audits, and
the E2E journey with the fixture provider.

## Migrations and rollback

`flask db upgrade` on deploy. Every migration has a `downgrade()`; roll
back with `flask db downgrade <rev>` **after** restoring application code.
Take a database snapshot before each production migration.

## Backup and restore

Daily `pg_dump` (or provider PITR) retained 30 days, plus uploads bucket
versioning. Restore drill: restore to a scratch database, point a staging
API at it, run `GET /api/v1/health/ready` and the E2E journey. **Not yet
performed** — do this before launch.

## Monitoring

Health: `/api/v1/health/live`, `/api/v1/health/ready`. Logs are structured
to stdout with `X-Request-Id` correlation. Alert on: worker not claiming
(oldest `ready` task age), rising `failed` task count, 5xx rate, billing
webhook signature failures. Error tracking (e.g. Sentry) not wired.

## Graceful shutdown

The worker finishes its current task on SIGTERM/SIGINT. A killed worker's
task is recovered automatically when its lease expires.

## Release checklist (before any paid launch)

- [ ] Security: dependency audit clean; secrets in a manager; `SECRET_KEY` rotated from dev
- [ ] Backups: restore drill performed and timed
- [ ] Tenant isolation: full test suite green on the release commit
- [ ] Load: expected workspaces × runs/day fits provider rate limits and worker count
- [ ] Costs: plan AI budgets checked against real provider pricing (placeholders today)
- [ ] Observability: logs shipped, alerts above configured
- [ ] Incident response: who can engage `KILL_SWITCH_ENABLED`, and how fast
- [ ] Integrations: none live; any new connector reviewed against `docs/INTEGRATIONS.md`
- [ ] Legal: Privacy/Terms reviewed by counsel; pricing confirmed
- [ ] Email delivery configured for resets and invitations
