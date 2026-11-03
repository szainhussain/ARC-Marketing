# Marketing Department Harness — Implementation Backlog
**Version:** 1.0  
**Purpose:** ordered, testable work items for an AI coding assistant or development team.

## 1. Delivery rules
- Build in vertical slices that run end-to-end.
- Keep the backend a modular Flask application; do not add microservices or a complex agent framework for the MVP.
- Every feature includes tests, error handling, authorization, and documentation.
- Do not start live external publishing until approval, audit, idempotency, and verification gates pass.
- Use environment variables for secrets; commit only `.env.example`.
- No feature is complete until acceptance criteria and regression tests pass.

## 2. Milestones and gates
### M0 — Repository and runnable skeleton
**Goal:** a developer can run the app locally and tests pass.
Tasks:
- M0.1 Create repository structure and README.
- M0.2 Add dependency management, formatting/linting, pytest.
- M0.3 Add Flask app factory and configuration profiles.
- M0.4 Add health/readiness endpoint without leaking internals.
- M0.5 Add Docker/compose for app and PostgreSQL if using containers.
- M0.6 Add CI for lint, tests, and migration checks.
Acceptance:
- Fresh clone can follow documented setup.
- App starts with missing optional AI keys and clearly disables AI functions.
- Health endpoint returns stable status.
- No secrets committed.

### M1 — Identity, organization, tenant isolation
**Goal:** authenticated users can access only their workspace data.
Tasks:
- M1.1 Implement authentication using a vetted session/OIDC approach.
- M1.2 Add users, organizations, memberships, and role models.
- M1.3 Add active organization context and membership validation.
- M1.4 Add server-side permission decorators/service helpers.
- M1.5 Add database migrations and seed/test fixtures.
- M1.6 Add security tests for cross-tenant read/write attempts.
Acceptance:
- Unauthenticated requests are denied on protected routes.
- Membership and role are checked server-side.
- Cross-tenant resource access returns safe denial without data leakage.
- Session/cookie protections are configured for the chosen auth approach.

### M2 — Business profile and document metadata
**Goal:** capture reusable company and brand context.
Tasks:
- M2.1 Create business profile schema and CRUD routes.
- M2.2 Add frontend onboarding steps and validation.
- M2.3 Add document metadata model and private storage abstraction.
- M2.4 Add file type/size validation and safe error handling.
- M2.5 Add profile summary and edit flows.
- M2.6 Add tenant-isolation and validation tests.
Acceptance:
- Required profile fields validate; optional fields can be skipped.
- Profile persists and is associated with the organization.
- File metadata and storage are tenant-scoped.
- No public file URL is exposed without authorization.

### M3 — Campaign CRUD and guided brief
**Goal:** create and manage a campaign before invoking AI.
Tasks:
- M3.1 Create campaign model and request/response schemas.
- M3.2 Implement create/list/read/update/archive endpoints.
- M3.3 Build campaign brief form and review step.
- M3.4 Add validation for dates, objective, channel, audience, and constraints.
- M3.5 Add idempotency for campaign creation where applicable.
Acceptance:
- User can save a draft, edit it, and return later.
- Invalid fields produce clear errors.
- Campaign is always scoped to active organization.
- Saving a campaign does not start a workflow automatically.

### M4 — Workflow/task persistence
**Goal:** represent campaign work as durable state.
Tasks:
- M4.1 Add workflow run, task, and task dependency models.
- M4.2 Define allowed state transitions and transition service.
- M4.3 Add start-run endpoint with idempotency key.
- M4.4 Add run/task status endpoints and activity timeline.
- M4.5 Add pause/cancel behavior between stages.
- M4.6 Add bounded retry metadata and safe error summaries.
Acceptance:
- Run/task state survives app restart.
- Invalid transitions are rejected.
- Duplicate start requests do not create duplicate runs when same idempotency key is used.
- Failed stage and reason are visible to authorized users.
- Cancel prevents future stages from starting.

### M5 — AI provider adapter and structured outputs
**Goal:** invoke one provider safely and consistently.
Tasks:
- M5.1 Define provider interface and typed error classes.
- M5.2 Implement one provider adapter behind configuration.
- M5.3 Add schema validation for every output type.
- M5.4 Add timeouts, bounded retries, and rate-limit handling.
- M5.5 Record provider/model metadata and usage when available.
- M5.6 Redact sensitive data from logs.
Acceptance:
- App remains usable when provider key is absent or provider is down.
- Invalid model output is rejected or retried within a small configured limit.
- Provider errors do not expose keys or raw stack traces to the user.
- Usage records link to the workflow/run.
- Provider can be swapped without changing domain workflow code.

### M6 — Campaign workflow vertical slice
**Goal:** turn a valid brief into a saved campaign pack.
Tasks:
- M6.1 Implement CMO/planner stage.
- M6.2 Implement research synthesis stage with source/assumption labels; if web research is not yet available, use supplied context and mark scope clearly.
- M6.3 Implement marketing plan stage.
- M6.4 Implement content pack stage.
- M6.5 Implement quality checks and output schema validation.
- M6.6 Save deliverables and immutable versions.
- M6.7 Add workflow summary and error recovery.
Acceptance:
- A test campaign generates strategy, plan, and content deliverables.
- Outputs are saved and can be read after restart.
- Missing material inputs trigger clarification or labelled assumptions.
- Every stage has a persisted status and run reference.
- A failed stage can be retried without deleting prior completed stages.

### M7 — Review, editing, versioning
**Goal:** users can review outputs and preserve revisions.
Tasks:
- M7.1 Add deliverable and version endpoints.
- M7.2 Add editable review UI.
- M7.3 Add request-changes/reject/approve-draft review states.
- M7.4 Add comments and revision reason.
- M7.5 Add version diff or clear version history.
Acceptance:
- Editing creates a new immutable version.
- Prior versions remain readable to authorized users.
- Material edits invalidate any related approval.
- Reviewer can identify the current version and producing workflow run.

### M8 — Approval and governance engine
**Goal:** enforce approval before external actions.
Tasks:
- M8.1 Implement action risk levels and policy registry.
- M8.2 Add approval model and immutable payload hash.
- M8.3 Implement role-based approval decisions.
- M8.4 Revalidate permissions/version/hash immediately before execution.
- M8.5 Add organization usage limit and per-run budget enforcement.
- M8.6 Add kill switch.
- M8.7 Add audit events for all significant state changes.
Acceptance:
- API cannot bypass approval by skipping the frontend.
- Changed content/version cannot use stale approval.
- Non-authorized users cannot approve.
- Active kill switch blocks external actions.
- Exceeding usage budget pauses the workflow and informs the user.
- Audit record exists for approval request, decision, and execution attempt.

### M9 — Manual handoff / export
**Goal:** enable a useful, safe pilot without a live connector.
Tasks:
- M9.1 Create export package for approved content and schedule.
- M9.2 Show action destination and copy/download controls.
- M9.3 Record handoff status separately from publication status.
- M9.4 Add user confirmation to record external result if not automatically verifiable.
Acceptance:
- Export is available only to authorized workspace users.
- UI does not claim content was published merely because it was exported.
- Manual handoff is auditable and can be distinguished from verified execution.

### M10 — Reporting, usage, and operational readiness
**Goal:** measure pilot value and operate safely.
Tasks:
- M10.1 Build workflow summary report.
- M10.2 Add usage/cost display with estimated versus actual labels.
- M10.3 Add structured logs, request IDs, workflow IDs, and error tracking.
- M10.4 Add operational alerts for repeated failures and budget anomalies.
- M10.5 Test database backup/restore and data export/deletion process.
- M10.6 Write support and incident runbooks.
Acceptance:
- Reports do not invent business outcomes.
- Usage is attributable to organization and workflow.
- Errors are traceable without logging secrets.
- Recovery and kill-switch procedures are documented and tested.

### M11 — First live integration (only after channel decision)
**Goal:** enable one external action safely.
Tasks:
- M11.1 Choose target channel based on pilot customer demand and API feasibility.
- M11.2 Document scopes, app-review requirements, and platform terms.
- M11.3 Implement OAuth and secure credential storage.
- M11.4 Implement connector contract, health check, validation, execution, and verification.
- M11.5 Add idempotency and ambiguous-outcome reconciliation.
- M11.6 Add connector contract tests and sandbox tests.
- M11.7 Add reconnect/disconnect and permission-change handling.
Acceptance:
- No action executes without approval and backend policy validation.
- Tokens are encrypted and never exposed to the browser/logs.
- Duplicate retries cannot create duplicate posts/actions where idempotency is supported; otherwise reconciliation occurs before retry.
- Ambiguous outcomes become `verification_required`.
- Integration can be disconnected and future execution is blocked.

### M12 — Paid pilot and expansion decision
**Goal:** test customer value and economics with real usage.
Tasks:
- M12.1 Prepare pilot onboarding, support guide, and limitations page.
- M12.2 Instrument time-to-first-deliverable, revision count, completion rate, and cost.
- M12.3 Run pilot workflows with 3–5 customers if feasible.
- M12.4 Interview users after completed workflows.
- M12.5 Produce go/no-go review against predefined criteria.
Acceptance:
- Each pilot has baseline, usage/cost, quality feedback, and willingness-to-pay evidence.
- Expansion decision is based on evidence, not feature volume.
- Risks and unresolved issues are documented.

## 3. Suggested backlog fields
Track each ticket with:
- ID
- Title
- User/business outcome
- Priority (P0/P1/P2)
- Dependencies
- Acceptance criteria
- Test cases
- Risk/security considerations
- Estimate (only after technical discovery)
- Status
- Owner

## 4. Cross-cutting definition of done
A ticket is complete only when:
- Acceptance criteria pass.
- Unit/integration/security tests are added where applicable.
- Authorization and tenant scoping are verified.
- Errors and loading states are handled.
- Logs are useful and redact secrets.
- API/UI docs are updated.
- Migrations and rollback considerations are documented.
- No unrelated complexity has been introduced.

## 5. Recommended initial ticket sequence
1. M0.1–M0.6 runnable skeleton and CI.
2. M1.1–M1.6 authentication and tenant isolation.
3. M2.1–M2.6 business profile.
4. M3.1–M3.5 campaign brief.
5. M4.1–M4.6 workflow persistence.
6. M5.1–M5.6 provider adapter.
7. M6.1–M6.7 end-to-end campaign pack.
8. M7.1–M7.5 review/versioning.
9. M8.1–M8.7 governance.
10. M9.1–M9.4 manual handoff.
11. M10.1–M10.6 reporting and readiness.
12. M11 only after channel decision.
13. M12 paid pilot and expansion gate.

## 6. First build instruction for an AI coding assistant
Implement only **Milestone M0** first. Before writing code, inspect the repository and report the existing structure. Then create the smallest runnable Flask application, configuration, health endpoint, tests, README, and `.env.example`. Do not implement agents, integrations, billing, or frontend features in M0. Run tests and report exact commands/results. After M0 is accepted, proceed to M1.
