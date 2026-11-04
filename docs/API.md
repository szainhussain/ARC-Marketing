# API Reference (v1)

Base `/api/v1`. Machine-readable spec generated from the live routes:
`GET /api/v1/openapi.json`.

## Conventions

- **Auth:** session cookie (Flask-Login). `GET /auth/csrf-token`, then send
  `X-CSRFToken` on every mutating request.
- **Tenancy:** workspace resources live under `/organizations/{org}/…`;
  membership is checked server-side (403, same message whether or not the
  workspace exists). Another workspace's ids under your path → 404.
- **Errors:** `{"error": {"code", "message", "details": [{"field","issue"}], "request_id"}}`.
  400 validation · 401 auth · 403 permission · 404 · 409 state conflict · 429 plan/rate limit.
- **Correlation:** every response has `X-Request-Id`; agent executions
  carry the run id as `correlation_id`.
- **Idempotency:** `Idempotency-Key` header required on run start and
  external-action execute; `idempotency_key` body field on campaign create.
- **Pagination:** `limit` (≤200) + `offset` on notifications, knowledge and
  the deliverables index; responses include `page: {total, limit, offset}`.

## Endpoints

| Area | Endpoints |
|---|---|
| Health | `GET /health/live`, `GET /health/ready` |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/logout`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/change-password`, `/auth/sign-out-everywhere`, `/auth/verify-email/request`, `/auth/verify-email`; `GET /me` |
| Public | `GET /public/plans`, `/public/agents`, `/public/integrations`; `POST /public/contact` |
| Workspaces | `POST /organizations`; `GET/PATCH /organizations/{org}`; `GET /organizations/{org}/export`; `POST/DELETE /organizations/{org}/deletion` |
| Members | `GET /members`, `PATCH/DELETE /members/{id}`, `POST /invitations`, `DELETE /invitations/{id}`, `POST /invitations/accept` (top level) |
| Business profile | `GET/PATCH /business-profile` |
| Knowledge | `GET/POST /knowledge` (`status`, `q`), `PATCH /knowledge/{id}` |
| Assets | `GET/POST /documents` (multipart `file`), `GET /documents/{id}/download`, `DELETE /documents/{id}` |
| Campaigns | `GET/POST /campaigns`, `GET/PATCH/DELETE /campaigns/{id}`, `GET /campaigns/{id}/deliverables` |
| Execution | `POST /campaigns/{id}/runs` (202, enqueue only), `GET /campaigns/{id}/runs`, `GET /runs/{id}`, `POST /runs/{id}/pause\|resume\|cancel\|approve-start` |
| Agents | `GET /agents`, `GET /agents/{agent}`, `POST /agents/{agent}/pause\|resume`, `PATCH /agents/{agent}/settings` |
| Tasks | `GET /tasks` (`status`, `agent_id`, `run_id`), `POST /tasks/{id}/retry\|cancel`, `GET /tasks/{id}/executions` |
| Deliverables | `GET /deliverables` (`type`, `review_status`, `campaign_id`), `GET /deliverables/{id}`, `GET/POST /deliverables/{id}/versions` |
| Approvals | `GET /approvals` (`decision`), `POST /approvals`, `POST /approvals/{id}/decision` (approved/rejected/changes_requested), `POST /approvals/{id}/revoke`, `POST /approvals/{id}/execute`, `POST /external-actions/{id}/confirm-publication` |
| Calendar | `GET/POST /calendar` (`from`, `to`), `PATCH/DELETE /calendar/{id}`, `POST /calendar/from-deliverable` |
| Integrations | `GET /integrations`, `GET /integrations/catalog`, `PATCH /integrations/{key}` |
| Webhooks | `GET/POST /webhooks`, `DELETE /webhooks/{id}` |
| Analytics | `GET /dashboard` (`days`, `campaign_id`), `GET /analytics` (`days`), `GET /reports/export.csv`, `GET /reports/summary` |
| Usage & billing | `GET /usage`, `GET /billing`, `POST /billing/checkout`, `GET /billing/history`, `POST /billing/test-complete` (test mode only), `POST /billing/webhook` (top level, signed) |
| Policies & ops | `GET /policies`, `PATCH /policies/{action}`, `GET /operations/summary`, `PATCH /operations/controls` |
| Notifications & audit | `GET /notifications` (`unread=1`), `POST /notifications/read`, `GET /activity`, `GET /audit-events` |

Paths in the table are relative to `/organizations/{org}` unless marked.

## Webhooks

Outbound and payment-webhook signing, replay protection, retries and
versioning: see `docs/INTEGRATIONS.md`.
