# Security and Governance — as actually implemented

Maps the non-negotiable rules in
`marketing_department_harness_deliverables/04_GOVERNANCE_AND_INTEGRATIONS.md`
to the actual code, and lists what is **not yet** implemented.

## Implemented

| Rule | Implementation |
|---|---|
| Tenant isolation enforced server-side | `app/services/authorization_service.py:get_membership_or_403` on every org-scoped route; tested in `tests/security/test_tenant_isolation.py` |
| Role-based approval permission | `Membership.can_approve_external_actions()` — only `owner`/`admin`/`marketing_lead`; tested (`test_contributor_cannot_approve_external_action`) |
| Approval tied to exact version + action | `Approval.deliverable_version_id` + `action_payload_hash` (SHA-256); `decide_approval` re-checks the version still matches before accepting a decision |
| Material change invalidates approval | `add_new_version()` sets any `pending` approval on the old version to `invalidated` |
| Re-validate immediately before execution | `execute_manual_handoff()` re-checks kill switch, approval decision, and version match — not just at approval time |
| Idempotency on side-effecting actions | Unique `(organization_id, idempotency_key)` constraints on `Campaign`, `WorkflowRun`, `ExternalAction`; duplicate requests return the existing record |
| Never mark "published" without explicit confirmation | `ExternalAction.publication_status` starts `unverified`; only `confirm_manual_publication()` (a distinct, explicit user action) sets `manually_confirmed_published` |
| Audit trail | `audit_service.record_audit_event()` called on registration-adjacent org/campaign/profile/workflow/deliverable/approval/external-action events; `AuditEvent` has no update/delete route (append-only by construction, not yet enforced at the DB-permission level) |
| Kill switch | `Organization.kill_switch_enabled` (per-org) and `KILL_SWITCH_ENABLED` (global env var), checked in `execute_manual_handoff()` before any external action |
| Usage/budget limits | `Organization.monthly_workflow_limit`, checked before starting a run (`check_monthly_workflow_limit`, raises 429); per-call AI budget check in `AnthropicProvider.generate_structured` (`BudgetExceeded`) |
| CSRF protection | Flask-WTF, token issued via `/auth/csrf-token`, required via `X-CSRFToken` header on every mutating request |
| Secure session cookies | `HttpOnly`, `SameSite=Lax` (configurable), `Secure` forced true in `ProductionConfig` |
| No account enumeration | Identical error message for "no such user" and "wrong password" (tested) |
| Secrets redacted from logs | `app/logging_config.py:RedactingFilter` strips `SECRET_KEY`/`ANTHROPIC_API_KEY` substrings from every log record |
| Untrusted AI output never trusted directly | Every stage output is parsed as JSON and validated against a Marshmallow schema before it can become a `DeliverableVersion`; the AI adapter never calls an external publishing API directly |
| Request IDs | `X-Request-Id` response header + `g.request_id` on every request, included in every error response |

## Explicitly deferred (do not claim these are done)

- **Encrypted credential storage** — `Integration.encrypted_credential_ref`
  is a schema placeholder; no live connector exists yet to populate it, so
  no actual secret-vault integration has been built or tested.
- **Rate limiting** — no per-user/per-IP request rate limiting beyond the
  monthly workflow-run limit.
- **File upload validation** (type/size/malware scanning) — no upload
  route exists yet (`Document` is schema-only).
- **SSO / enterprise identity** — not built.
- **Backup/restore drill, data export/deletion self-service** — not built;
  `docs/IMPLEMENTATION_PLAN.md` lists this under M10 gaps.
- **Prompt-injection test suite against malicious uploaded documents** —
  not applicable yet (no document ingestion into AI context exists; the
  research stage explicitly instructs the model that no external
  retrieval is connected and to work only from user-supplied profile
  fields, which themselves come from authenticated, tenant-scoped forms,
  not arbitrary uploads).
- **Row-level database security** (defense-in-depth beyond application
  checks) — not configured; the spec calls this out as a "consider after
  application-level checks are tested," which they now are.

## Governance test cases from the spec — status

| Test case | Status |
|---|---|
| Contributor attempts to approve → denied | **Tested** (`test_contributor_cannot_approve_external_action`) |
| Org A cannot read Org B's data | **Tested** (`test_tenant_isolation.py`, campaigns + business profile) |
| Approved version edited → old approval invalid | **Tested** (`test_editing_creates_new_version_and_invalidates_pending_approval`) |
| Duplicate idempotent execute → same result, not double-executed | **Tested** (`test_duplicate_idempotency_key_does_not_execute_twice`) |
| Rejected approval cannot execute | **Tested** (`test_rejected_approval_cannot_execute`) |
| Kill switch blocks new external actions | **Implemented, not yet covered by an automated test** — manual verification only |
| Connector disconnected after approval blocks execution | **Not applicable** — no live connector exists to disconnect |
| Budget/usage limit exceeded pauses workflow | **Implemented** (`check_monthly_workflow_limit`, `BudgetExceeded`), **not yet covered by an automated test** |
| Provider timeout → `verification_required`, no blind retry | **Partially implemented** — `AIRequestTimeout` is raised and the stage fails cleanly (no blind retry), but the model generation path (not an external *publishing* action) doesn't use the `verification_required` state, since nothing external was attempted; `verification_required` is modeled on `ExternalAction` for the manual-handoff/future-connector path |

## Pre-launch governance checklist (from the spec) — current status

- [x] Role and permission matrix implemented and tested
- [x] Tenant isolation tests pass
- [x] Approval version/hash enforcement passes
- [x] External actions disabled by default (no connector connected; kill
      switch available)
- [x] Idempotency implemented; ambiguous-outcome handling modeled
      (`verification_required` status exists on `ExternalAction`) but not
      yet exercised, since the only connector (manual handoff) never
      produces an ambiguous outcome
- [ ] Connector credentials encrypted and redacted — N/A, no connector yet
- [x] Usage caps and workflow budgets enforced (monthly + per-call)
- [ ] Kill switch tested — implemented, manual test only
- [ ] Data retention/export/deletion policy documented — not done
- [ ] AI-provider data terms reviewed — not done (no real API key used)
- [x] Audit trail exists for the events listed above
- [ ] Pilot customers understand limitations — N/A, no pilot run yet
