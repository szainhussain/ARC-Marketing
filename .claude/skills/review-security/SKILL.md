---
name: review-security
description: Security review of a change against this project's governance rules (tenant isolation, approval/version integrity, idempotency, secret handling). Use before merging any change that touches app/api, app/services, or auth/approval/external-action logic.
---

Checklist, grounded in `docs/SECURITY_AND_GOVERNANCE.md` and `/CLAUDE.md`'s
non-negotiable rules — go through each one against the actual diff, not
from memory:

1. **Tenant scoping.** Does every new/changed route call
   `get_membership_or_403(organization_id)` before touching data? Is
   `organization_id` ever trusted from a request body field instead of the
   membership check? Grep for the route's queries — do they all filter by
   `organization_id`?
2. **Role checks.** If the action should be role-gated (e.g. approval
   decisions), is the check server-side (`Membership.role` /
   `can_approve_external_actions()`), not just a hidden frontend button?
3. **Deliverable/version integrity.** Does any new "edit" path create a
   new `DeliverableVersion` rather than mutating one in place? Does it
   invalidate pending approvals on the old version, following
   `add_new_version()`?
4. **Approval/execution re-validation.** Does any new external-action path
   re-check kill switch, approval decision, and current-version match
   *immediately before* executing — not just at approval-request time?
   Model it on `execute_manual_handoff()`.
5. **Idempotency.** Does a new side-effecting endpoint accept and enforce
   an idempotency key via a unique DB constraint, the way `Campaign`,
   `WorkflowRun`, and `ExternalAction` do?
6. **Secrets.** No real secret in code, `.env.example`, logs, or error
   messages. Check `app/logging_config.py`'s `RedactingFilter` still
   covers any new secret-bearing config value.
7. **AI output trust.** Is new AI-sourced data validated against a
   Marshmallow schema before being persisted or acted on? Does a provider
   failure degrade to a clean `capability_unavailable` state instead of
   fabricating output?
8. **Error messages.** Do new error paths avoid leaking stack traces,
   internal paths, or distinguishing "resource doesn't exist" from "you
   don't have access" (both should look identical to the caller)?

Run or write a test for anything you find broken — see `check-tenant-isolation`
for the cross-tenant test pattern. Report findings as: file/line, what's
wrong, concrete failure scenario, severity. Don't report something as a
finding if it's explicitly documented as deferred in
`docs/SECURITY_AND_GOVERNANCE.md`'s "explicitly deferred" section (e.g. no
rate limiting exists yet — that's known, not a new finding) — unless the
change you're reviewing was supposed to address it.
