# Marketing Department Harness — Governance & Integration Specification
**Version:** 1.0  
**Purpose:** define what AI may do, what requires approval, how integrations are controlled, and how actions are audited.

## 1. Governance model
The product is an AI copilot, not an unconstrained autonomous operator. AI may prepare recommendations and drafts, but the backend enforces permissions and action policy. Human approval is required for most external actions.

### Non-negotiable rules
1. The model cannot grant itself permissions.
2. Approval is tied to the exact action payload and exact content version.
3. A material change invalidates prior approval.
4. Silence is not consent.
5. A successful model response is not proof that an external action succeeded.
6. External action retries must be idempotent or reconciled before retry.
7. Budget, role, tenant, connector scope, and policy checks occur server-side.
8. All meaningful decisions and actions are auditable.
9. The platform can pause workflows and disable external actions.
10. Uploaded files, website content, emails, and third-party data are untrusted inputs.

## 2. Action risk levels
### Level 0 — Internal, reversible work
Examples: summarize provided information, draft a plan, create internal task, generate draft copy, prepare a creative brief.
- May run automatically within configured usage limits.
- Outputs are labelled draft/AI-generated.
- No external side effect.
- Must be tenant-scoped and auditable.

### Level 1 — Low-impact internal changes
Examples: update a draft calendar, revise internal task details, classify a document.
- May run automatically if the user/workspace policy allows.
- Record before/after metadata.
- Reversible changes should have a recovery path.

### Level 2 — External communication or publication
Examples: publish social post, send campaign email, post a public announcement, reply to a customer, submit a listing.
- Requires an authorized human approval for the exact version, destination, and schedule.
- Verify account and scopes.
- Execute only through an allowlisted connector.
- Record result and verification state.

### Level 3 — Financial, contractual, reputational, or sensitive actions
Examples: launch or modify paid campaign spend, increase budget, make a public claim about health/safety/performance, accept contract terms, negotiate pricing, make a purchase, issue a refund.
- Disabled in the first pilot unless a specific policy and control are designed and reviewed.
- Require explicit high-friction approval and a clearly displayed impact/cost.
- Some actions should remain human-only.
- Do not let model-generated content or an inferred budget authorize spending.

### Block / escalate
- Requests to bypass approval or conceal activity.
- Suspected account compromise.
- Unclear legal/regulated claims.
- Unsupported or fabricated proof points.
- Unapproved personal-data use.
- Cross-tenant data exposure.
- Provider outcome is ambiguous.
- Budget/usage limit exceeded.
- Connector permission changed or revoked.

## 3. Approval lifecycle
1. **Prepare:** create external action record with immutable payload and content version.
2. **Validate:** backend checks tenant, actor, action type, connector state, required scopes, budget, and policy.
3. **Request:** create approval request showing action details and payload hash.
4. **Decide:** authorized approver approves, rejects, or requests changes.
5. **Revalidate:** immediately before execution, recheck role, version/hash, connector, policy, budget, expiry, and kill switch.
6. **Execute:** use connector with idempotency key where supported.
7. **Verify:** use provider response or follow-up query to confirm outcome.
8. **Record:** persist result, response metadata, timestamps, and audit events.
9. **Reconcile:** ambiguous outcomes move to `verification_required`; do not blindly retry.

Approval record should include:
- organization ID
- requested by / approver ID
- action type
- destination/account
- content version ID
- payload hash
- planned time
- spend/cost cap where applicable
- policy version
- decision and comment
- expiry
- execution status and verification details

## 4. Roles and permissions
Suggested roles:
- **Owner:** full workspace administration, billing, team, policies, and high-impact approvals.
- **Admin:** manage users, profile, integrations, campaigns; approval rights only if explicitly granted.
- **Marketing lead:** create campaigns, manage deliverables, request approvals, approve allowed Level 2 actions if granted.
- **Contributor:** submit briefs and edit drafts; cannot connect integrations or approve external actions by default.
- **Viewer:** read-only access to authorized workspace records.
- **Platform operator:** platform-level service operations; customer content access is restricted, logged, and support-justified.

Use permission checks at both route and service layers. Never rely on hiding a button in the frontend as authorization.

## 5. Integration strategy
### MVP approach
Start with export/manual handoff as the default execution adapter. This allows the full workflow and approval experience to be validated without prematurely depending on a third-party API's permissions, review process, or account-specific limitations.

Add one live connector only after selecting the pilot channel and confirming:
- API availability and current platform rules
- app registration and review requirements
- required OAuth scopes
- write permissions and account eligibility
- rate limits and token refresh behavior
- terms of service and commercial use
- sandbox/test account availability
- success-verification method
- revocation and disconnect behavior

### Connector interface
Each connector should implement a small explicit contract:
- `get_capabilities()`
- `connect()` / OAuth callback flow as applicable
- `health_check()`
- `validate_action(action)`
- `execute_action(action, idempotency_key)`
- `verify_action(action_reference)`
- `disconnect()`

Connector must not accept arbitrary model-generated URLs, shell commands, or unvalidated payloads. Backend builds the allowed payload from validated application data.

### Connector states
`disconnected → connecting → connected → degraded | reauth_required → disconnected`
Store account metadata and granted scopes; never store plaintext credentials in ordinary application tables. Encrypt secrets with a managed key service or use a secure credential vault.

## 6. Data and privacy handling
- Collect only data needed for the selected workflow.
- Clearly explain what is sent to AI providers and connected services.
- Do not use customer content to train models by default unless there is a separate explicit, informed agreement and a lawful basis.
- Document provider retention and processing terms before choosing production vendors.
- Set retention periods for raw uploads, extracted text, generated deliverables, logs, and backups.
- Support data export and deletion requests under the product's documented process and applicable law.
- Separate tenant data at the application and storage layers.
- Use private object storage, short-lived signed links, and authorization checks.
- Restrict support access; log privileged access.
- Redact personal information and secrets from logs where feasible.
- Provide an incident response and breach-notification process appropriate to applicable law.

## 7. Prompt injection and untrusted content
Treat web pages, uploaded documents, copied emails, and third-party content as data, not instructions.
- Separate system policy from retrieved content.
- Never allow retrieved content to change tool permissions.
- Use allowlisted tools and structured arguments.
- Do not expose secrets or cross-tenant context to model prompts.
- Keep execution credentials outside the model context.
- Require backend validation for every proposed action.
- Limit retrieval to authorized documents and URLs.
- Log source references and safety/quality outcomes where practical.
- Test malicious documents and indirect prompt-injection scenarios.

## 8. Usage and budget controls
- Workspace has a plan limit and configurable usage cap.
- Each workflow has a maximum run budget, stage budget, timeout, and retry count.
- Provider spend estimates are tracked separately from confirmed invoice amounts.
- If a limit is reached, pause and notify the user; do not silently switch to a more expensive model.
- Paid-media budget is separate from AI platform usage and never authorized by the subscription.
- Display estimates as estimates until reconciled with provider data.
- Add rate limits per user, organization, endpoint, and provider.

## 9. Audit and incident handling
Audit events should cover:
- sign-in and security-sensitive account events
- role/permission changes
- profile/document changes
- workflow start, pause, resume, cancel, retry
- model/provider stage outcome and usage metadata
- deliverable version creation
- approval request and decision
- connector connect/disconnect/scope change
- external action request, execution attempt, result, and verification
- budget/limit events
- kill-switch activation
- privileged support access

Each event includes actor (user/service), organization, target, timestamp, correlation ID, outcome, and redacted metadata. Audit records should be append-only to ordinary application users. Restrict retention and access according to policy.

### Incident playbook
1. Stop external actions using the kill switch.
2. Identify affected organizations, integrations, workflows, and versions.
3. Preserve relevant logs/audit evidence.
4. Revoke compromised credentials or connector access.
5. Notify the appropriate internal owner and affected customers as required.
6. Remediate and test before re-enabling.
7. Document root cause and corrective actions.

## 10. Governance test cases
- Contributor attempts to approve a public post → denied.
- User from Organization A requests a deliverable in Organization B → no data disclosed.
- Approved version is edited → old approval cannot execute.
- Connector is disconnected after approval → execution blocked.
- Budget limit is exceeded → workflow/action pauses.
- Provider times out after receiving an action → state becomes `verification_required`; no blind duplicate retry.
- Model suggests an unapproved URL/action → backend rejects it.
- Malicious uploaded document requests secrets → secrets remain inaccessible.
- Kill switch is active → new external actions are blocked.
- User has no approval rights but calls API directly → denied and audited.

## 11. Pre-launch governance checklist
- [ ] Role and permission matrix implemented and tested.
- [ ] Tenant isolation tests pass.
- [ ] Approval version/hash enforcement passes.
- [ ] External actions disabled by default.
- [ ] Idempotency and ambiguous-outcome handling implemented.
- [ ] Connector credentials encrypted and redacted.
- [ ] Usage caps and workflow budgets enforced.
- [ ] Kill switch tested.
- [ ] Data retention/export/deletion policy documented.
- [ ] AI-provider data terms reviewed.
- [ ] Audit trail and incident process ready.
- [ ] Pilot customers understand limitations and approval responsibilities.
