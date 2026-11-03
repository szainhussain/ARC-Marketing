# API Reference (v1) — as actually implemented

Base path: `/api/v1`. All routes except `/auth/*` and `/health/*` require
an authenticated session (`401` otherwise). All `/organizations/<id>/*`
routes additionally require active membership in that organization (`403`
otherwise, identical message whether the org exists or not).

This deviates from the flatter endpoint list sketched in
`03_TECHNICAL_ARCHITECTURE.md` (e.g. `/api/v1/campaigns` assuming an
implicit "active organization") by putting `organization_id` explicitly in
the path for every tenant-scoped resource — chosen for unambiguous tenant
scoping in both the route and the server-side membership check. The
request/response error envelope, idempotency-key usage, and status-code
conventions (403/404/409/429) follow the technical spec as drafted.

## Error envelope

```json
{"error": {"code": "VALIDATION_ERROR", "message": "...", "details": [{"field": "...", "issue": "..."}], "request_id": "uuid"}}
```

## Auth

| Method | Path | Notes |
|---|---|---|
| GET | `/auth/csrf-token` | Call first; sets the session cookie and returns the token for `X-CSRFToken` |
| POST | `/auth/register` | `{email, password, full_name}` → 201, logs in |
| POST | `/auth/login` | `{email, password}` → 200; generic error message (no account enumeration) |
| POST | `/auth/logout` | requires login |
| GET | `/me` | current user + memberships (org id, name, role) |

## Health

| Method | Path | Notes |
|---|---|---|
| GET | `/health/live` | always 200 if the process is up |
| GET | `/health/ready` | 200 if a DB query succeeds, else 503 — never leaks internals |

## Organizations / business profile

| Method | Path | Notes |
|---|---|---|
| POST | `/organizations` | `{name}` → creates org + owner membership |
| GET | `/organizations/<org_id>/business-profile` | creates an empty row on first read |
| PATCH | `/organizations/<org_id>/business-profile` | partial update; `mark_onboarding_completed: true` sets `onboarding_completed` |

## Campaigns

| Method | Path | Notes |
|---|---|---|
| GET | `/organizations/<org_id>/campaigns` | list, newest first |
| POST | `/organizations/<org_id>/campaigns` | requires `name`, `objective`; `idempotency_key` optional but recommended |
| GET | `/organizations/<org_id>/campaigns/<id>` | |
| PATCH | `/organizations/<org_id>/campaigns/<id>` | partial update |
| DELETE | `/organizations/<org_id>/campaigns/<id>` | archives (status → `archived`), does not hard-delete |
| GET | `/organizations/<org_id>/campaigns/<id>/deliverables` | all deliverables for the campaign |

## Workflow runs

| Method | Path | Notes |
|---|---|---|
| POST | `/organizations/<org_id>/campaigns/<id>/runs` | **requires** `Idempotency-Key` header (or `idempotency_key` in body) — 400 without it; 202 with the run (synchronous in this build — see `docs/DECISIONS.md` D4) |
| GET | `/organizations/<org_id>/runs/<run_id>` | run + ordered task list |
| POST | `/organizations/<org_id>/runs/<run_id>/cancel` | only valid from `created`/`queued`/`running`/`needs_input`; 409 otherwise |

## Deliverables and versions

| Method | Path | Notes |
|---|---|---|
| GET | `/organizations/<org_id>/deliverables/<id>` | current version only |
| GET | `/organizations/<org_id>/deliverables/<id>/versions` | full history |
| POST | `/organizations/<org_id>/deliverables/<id>/versions` | `{content: {...}, revision_reason?}` → new version; invalidates any pending approval on the previous version |

## Approvals and external actions

| Method | Path | Notes |
|---|---|---|
| POST | `/organizations/<org_id>/approvals` | `{deliverable_id, action_type?, action_payload?}` → ties to the deliverable's *current* version at request time |
| POST | `/organizations/<org_id>/approvals/<id>/decision` | `{decision: approved\|rejected\|changes_requested, comment?}` — 403 unless the actor's role can approve; 409 if not `pending` |
| POST | `/organizations/<org_id>/approvals/<approval_id>/execute` | **requires** `Idempotency-Key`; re-validates kill switch, approval decision, and version match immediately before "executing" (packaging) the manual handoff; 409 on any mismatch. Optional body field `target_platform` (`meta_instagram`\|`google_ads`\|`tiktok_ads`) — only meaningful when the deliverable is a `content_pack`; adds a `platform_export` to the response formatted to that platform's composer limits (see `app/integrations/export_formats.py`). 400 for an unrecognized platform. This never calls any external platform API — still manual copy/paste handoff. |
| POST | `/organizations/<org_id>/external-actions/<id>/confirm-publication` | the *only* way `publication_status` becomes `manually_confirmed_published` |

## Integrations, reports, audit

| Method | Path | Notes |
|---|---|---|
| GET | `/organizations/<org_id>/integrations` | always empty in this build + an explanatory `note` — no live connector exists |
| GET | `/organizations/<org_id>/reports/summary` | campaign/run counts + estimated AI cost, labeled `cost_basis: "estimate"` |
| GET | `/organizations/<org_id>/usage` | last 200 `UsageRecord` rows |
| GET | `/organizations/<org_id>/audit-events` | last 200 `AuditEvent` rows, newest first |

## Not implemented (do not assume these exist)

- Document upload (`Document` model exists, no route).
- Comments on deliverables.
- Team invite / role-change endpoints (role changes require direct DB
  access today).
- Any `/organizations/<id>/integrations/<provider>/connect` OAuth flow.
- Password reset / account recovery.
