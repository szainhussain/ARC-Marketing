# Deployment

## Environments

| Environment | Database | AI key | Notes |
|---|---|---|---|
| Local dev | SQLite (`instance/dev.db`) | optional | `requirements-dev.txt`, `flask run` |
| CI (not yet configured) | SQLite (in-memory, `TestingConfig`) | none | `pytest` only; no CI pipeline file exists yet in this repo — see "Not done" below |
| Docker / staging-like | PostgreSQL (compose service) | optional via env | `docker compose up --build` |
| Production | Managed PostgreSQL (not provisioned) | required for real AI output | Not deployed anywhere in this session |

## Docker Compose (local "production-like" run)

```bash
export ANTHROPIC_API_KEY=sk-...   # optional — omit to run in capability_unavailable mode
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker compose up --build
```

- `postgres`: official `postgres:16-alpine`, healthcheck-gated.
- `backend`: builds from the root `Dockerfile` (pinned `python:3.12-slim`),
  `docker-entrypoint.sh` runs `flask db upgrade` then `gunicorn` — migrations
  are not a separate manual step in this path.
- `frontend`: multi-stage build (`frontend/Dockerfile`), served by nginx
  with an SPA fallback (`frontend/nginx.conf`).

Built and smoke-tested in this session (see `docs/TEST_REPORT.md`); a full
`docker compose up` end-to-end run (with real Postgres and the frontend
actually talking to the backend container) was **not** performed — do that
before trusting this path for a pilot.

## Required environment variables for production

See `.env.example` for the full list and safe placeholder values. At
minimum for production:

- `SECRET_KEY` — real random value, not the dev placeholder, injected via
  a secret manager, never committed.
- `DATABASE_URL` — managed PostgreSQL connection string.
- `FRONTEND_ORIGIN` — the real deployed frontend origin (for CORS).
- `SESSION_COOKIE_SECURE=true` (forced on automatically by
  `ProductionConfig` regardless of this env var, as a safety net).
- `ANTHROPIC_API_KEY` — only if AI-generated stages should actually run;
  the app is fully usable without it (clarification/capability-unavailable
  states instead).

## Secret management strategy (design, not yet wired to a real vault)

Application code never logs `SECRET_KEY` or `ANTHROPIC_API_KEY`
(`app/logging_config.py:RedactingFilter`), and no ordinary model field
stores a plaintext credential (`Integration.encrypted_credential_ref` is a
pointer field, not a storage field — unused today since no connector needs
it yet). For a real deployment, inject secrets via your platform's secret
manager (e.g. AWS Secrets Manager, Doppler, Vault) as environment
variables at container start — do not bake them into the image or commit
them to `.env`.

## Database migrations

```bash
export FLASK_APP=wsgi.py
flask db upgrade          # apply
flask db migrate -m "..."  # generate a new migration after model changes
```

Never hand-edit the schema in any environment above local dev — always go
through a migration, including in Docker (handled automatically by
`docker-entrypoint.sh` on container start).

## Backup/restore

**Not implemented or tested in this session.** For PostgreSQL, standard
`pg_dump`/`pg_restore` or your managed provider's point-in-time recovery
applies; no custom tooling exists in this repo. This is a real gap before
a paid pilot — see `docs/IMPLEMENTATION_PLAN.md` M10.

## Monitoring / health checks

`GET /api/v1/health/live` (process up) and `GET /api/v1/health/ready`
(DB reachable) exist and return safe, non-leaking responses. No metrics
exporter, structured trace collector, or alerting is wired up yet — logs
are structured (`app/logging_config.py`) but go to stdout only, with no
shipping/retention configured.

## Not done (be explicit about this before calling anything "production-ready")

- No CI pipeline (GitHub Actions or equivalent) runs tests/lint/migration
  checks automatically on push — the spec's M0.6 task.
- No staging environment exists.
- No TLS termination config (expected to be handled by whatever reverse
  proxy/load balancer fronts the containers in a real deployment — not
  configured here).
- No error-tracking service (Sentry or equivalent) wired up.
- No kill-switch admin UI — flipping `Organization.kill_switch_enabled`
  today means a direct DB update or a future admin route, not built yet.

**Overall readiness assessment: local prototype / pilot candidate, not a
production deployment candidate.** The core workflow, tenant isolation,
and governance gates are real, tested, and browser-verified; what's
missing is operational maturity (CI, backup/restore, monitoring/alerting,
a live AI key actually exercised, and a live publishing channel) rather
than core product logic.
