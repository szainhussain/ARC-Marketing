# Security and Governance — as actually implemented

No certification (SOC 2, ISO 27001) or formal compliance status (GDPR
etc.) has been obtained or is claimed. This lists real controls and gaps.

## Identity, sessions, roles

| Control | Implementation | Test |
|---|---|---|
| Password hashing | Werkzeug PBKDF2 (`models/user.py`) | — |
| Session cookies | HttpOnly, SameSite=Lax, Secure in production | — |
| Session revocation | `users.session_version` is part of the session id; password reset, password change, "sign out everywhere" bump it | `test_password_reset_flow_revokes_old_sessions`, `test_change_password_and_sign_out_everywhere` |
| Password reset | Hashed single-use token, 60-min expiry, no account enumeration | same |
| Email verification | Hashed token, 2-day expiry | — (manual) |
| CSRF | Flask-WTF, `X-CSRFToken` on every mutating request (exempt: public contact form, signed billing webhook) | existing suite |
| Rate limiting | Flask-Limiter on login (10/min), register (10/h), forgot/reset (5–10/h), contact (5/h), verify (5/h) | disabled in TestingConfig |
| Roles | owner, admin, marketing_lead (Marketing Manager), approver, contributor, analyst, viewer; checked server-side per route | `test_viewer_cannot_administer`, `test_viewer_cannot_control_runs` |
| Owner protection | Only owners grant/remove owner; last owner can't be demoted | `test_last_owner_cannot_be_demoted` |
| MFA | **Designed, not built** (planned: TOTP with recovery codes, enforced per workspace) | — |

## Tenant isolation

`get_membership_or_403` on every org-scoped route; ids from one workspace
used under another workspace's path return 404. Every endpoint added in
this build has a cross-tenant test: `tests/security/test_tenant_isolation.py`,
`test_operations_isolation.py`, `test_saas_isolation.py`, plus E2E step 14.

## Agents and AI

- Agents can only call structured generation. No code path lets a model
  run SQL, shell commands, filesystem operations or arbitrary HTTP.
- Each agent receives only allow-listed upstream outputs (engine-enforced).
- Prompts mark all business, campaign and knowledge text as untrusted data
  (`_build_prompt`); outputs are schema-validated, then checked in code
  for prohibited phrases and invented contact details.
- Provider error text (which can contain account ids) is logged
  server-side only; users see plain messages.
- No agent can change spend (`paid_media` policy), send messages, or publish.

## Human approval and emergency stop

Approvals bind version + payload hash, expire (14 days), can be revoked,
one pending per version, re-checked before export; editing invalidates.
Workspace "pause all agents", per-agent pause, per-run pause/cancel, kill
switch (`test_kill_switch_and_disabled_destination_block_exports`) and the
deployment-wide `KILL_SWITCH_ENABLED` are backend-enforced. Locked policies
(external handoff, public replies, spend, commitments) can't be loosened
(`test_locked_policies_cannot_be_loosened`).

## Input/output, uploads, SSRF

- JSON inputs validated per route; React escapes output by default; API
  responses carry `Content-Security-Policy: default-src 'none'`,
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
  `Permissions-Policy`, HSTS in production.
- SQL only through SQLAlchemy parameters.
- Uploads: extension allowlist, MIME match, magic-byte check, UTF-8 check
  for text, size limit, random storage keys, path-traversal guard,
  attachment-only downloads (`test_upload_validation`).
- SSRF: the only server-side fetches are Stripe (fixed host) and outbound
  webhooks (HTTPS only, resolved addresses must be public, no redirects)
  (`test_webhook_ssrf_and_signed_delivery`). Knowledge source URLs are
  never fetched.

## Secrets

Provider keys, Stripe key and webhook secrets are environment variables
(use a secret manager in production; `.env` is local only). Logs redact
known secret values (`logging_config.RedactingFilter`). Tokens are stored
hashed. Exports exclude secrets (`test_export_excludes_secrets_and_deletion_purges`).
**Rotation:** rotate `SECRET_KEY` (invalidates all sessions), provider
keys and `BILLING_WEBHOOK_SECRET` via the secret manager and restart;
outbound webhook secrets are rotated by creating a new endpoint.

## Data lifecycle

Export: admins download all workspace data as JSON. Deletion: owner
schedules (30-day grace, agents paused, kill switch on), then
`flask purge-deleted-workspaces` (cron) deletes everything.

## Audit

Append-only `audit_events` for auth-adjacent, workspace, policy, member,
billing, run, task, approval, export, knowledge, calendar and webhook
actions; viewable at `/app/audit-log` and included in exports.

## Gaps (do not claim done)

MFA; SSO; row-level DB security; malware scanning of uploads; dependency
scanning beyond `npm audit`/`pip-audit` in CI; encrypted credential vault
for live connectors (none exist); email delivery for resets/invites;
legal review of Privacy/Terms drafts; AI provider data-processing terms
review.
