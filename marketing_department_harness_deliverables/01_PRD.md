# Marketing Department Harness — Product Requirements Document
**Version:** 1.0  
**Status:** Baseline for paid-pilot discovery and implementation  
**Product:** Marketing Department Harness (working name)

## 1. Executive summary
Marketing Department Harness is a multi-tenant SaaS product that gives small and medium-sized businesses (SMBs) access to a coordinated AI marketing department. It combines a shared business profile, a campaign workflow, specialist AI capabilities, reviewable deliverables, human approvals, and an auditable activity history.

The product is **not** a collection of unrelated chatbots. The system coordinates work through explicit workflows and backend-enforced rules. AI may research, plan, draft, critique, and recommend. Humans approve consequential external actions, especially publishing, sending communications, launching paid campaigns, and changing spend.

The initial paid pilot will prove one complete, repeatable, cross-industry workflow: **campaign brief → research and strategy → campaign plan → content pack → quality review → human approval → controlled handoff or one supported publishing action → outcome report**.

## 2. Product vision and principles
### Vision
Make high-quality, coordinated marketing execution accessible to SMBs without requiring them to hire a full in-house marketing department.

### Product principles
1. **Workflow first:** represent work as tasks, dependencies, versions, approvals, and outcomes.
2. **Human control by default:** external actions require the appropriate approval and authorization.
3. **One source of business truth:** reuse a tenant-scoped business profile, brand assets, audience, offers, and constraints.
4. **Evidence over invention:** distinguish sourced facts, user-provided facts, and AI-generated recommendations.
5. **Modular, understandable software:** begin with a simple Python Flask backend and explicit services; avoid unnecessary agent frameworks.
6. **Progressive capability:** ship one paid end-to-end use case before expanding to the full 12-role concept.
7. **Observable and reversible:** record agent runs, versions, approvals, errors, costs, and external-action outcomes.
8. **Commercial viability:** measure customer value and cost per completed workflow from the pilot.

## 3. Target customers and users
### Primary customer
SMBs across industries that need recurring marketing planning and content but lack sufficient specialist capacity or a coordinated internal marketing team.

### Personas
- **Owner / executive sponsor:** wants visible progress, brand control, measurable business outcomes, and predictable costs.
- **Marketing lead / approver:** provides context, reviews strategy and content, approves external actions, and tracks work.
- **Contributor:** supplies product/service facts, imagery, offers, and feedback.
- **Workspace administrator:** manages users, roles, connected accounts, security settings, and billing.
- **Platform operator:** handles service health, support, abuse prevention, model usage, and incident response without casually accessing customer content.

## 4. Jobs to be done
- Turn a business objective into a coherent campaign plan.
- Create on-brand campaign content faster.
- Understand why a recommendation was made and what information supports it.
- Review, edit, approve, reject, and version deliverables.
- Know which work is queued, running, blocked, awaiting approval, completed, or failed.
- Execute only authorized external actions.
- See work completed, time saved, quality/revision signals, and costs.

## 5. MVP outcome and success criteria
The MVP is successful when a pilot customer can complete the core workflow end-to-end with persisted records and safe approval gates.

### Pilot metrics
**Customer value**
- Time from brief submission to first usable deliverable.
- Customer-reported time saved versus their baseline.
- Workflow completion rate.
- Review time and number of revision cycles.
- First-pass approval rate.

**Quality and trust**
- Brand/factual error rate in reviewed deliverables.
- Percentage of outputs with usable evidence or clearly marked assumptions.
- Unauthorized external actions: target **zero**.
- Approval records linked to the exact version/action: target **100%**.
- Audit trail completeness for state changes and execution attempts.

**Economics**
- AI and integration cost per completed workflow.
- Support time per pilot customer.
- Pilot-to-paid conversion / renewal intent.
- Estimated gross margin by package and workflow.

Set numeric thresholds with pilot customers before the pilot; do not present unvalidated thresholds as proven benchmarks.

## 6. Scope
### In scope for the first paid pilot
1. Organization and user accounts with tenant isolation.
2. Business profile onboarding, including industry, offering, target audience, tone, differentiators, geography, channels, goals, constraints, and source documents.
3. Campaign brief creation and validation.
4. A workflow coordinated by a CMO/planner role, research capability, marketing manager role, creative/content capability, and quality check.
5. Campaign plan and content deliverables saved as versioned records.
6. Task/dependency status, activity feed, run logs, retry/error state.
7. Review, edit, approve, reject, and request-changes flows.
8. Human approval for configured external actions.
9. One initial execution path: manual handoff/export is acceptable; add one publishing integration only after credentials, permissions, and test account are verified.
10. Basic campaign report and workflow-level cost/usage visibility.
11. Audit events, usage limits, kill switch, error reporting, and privacy controls.
12. Responsive desktop-first web interface with usable mobile layouts.

### Explicitly out of scope for pilot
- All 12 agents operating as independent autonomous services.
- Fully autonomous paid-media account operation or spend changes.
- Autonomous influencer negotiations, contract commitments, or purchase orders.
- Automated pricing, inventory, fulfillment, and order management.
- Full omnichannel customer service or voice calling.
- Guaranteed marketing performance, lead volume, revenue, or ROI.
- Model training on customer data by default.
- Self-modifying agent instructions or uncontrolled agent-to-agent loops.
- Native mobile apps.
- Complex multi-region deployment unless customer/legal needs require it.

## 7. Product roles and capabilities
The original 12-role concept remains the long-term department map. The MVP uses a small number of logical capabilities; these may be workflow stages or service modules rather than 12 separately deployed agents.

| Long-term role | Pilot treatment |
|---|---|
| CMO | Campaign objective framing, strategic direction, decision summary |
| Marketing Manager | Workflow planning, brief clarification, task coordination |
| Market Intelligence & Research | Research synthesis, source notes, competitor/audience hypotheses |
| Brand Assets & Content Developer | Content pack, creative briefs, channel variants |
| Social Media Executive | Content calendar and social-ready variants; no autonomous publishing by default |
| Paid Ads / Digital Marketing | Recommendations only; no spend/account changes |
| PR / Influencer / Events | Roadmap; suggestions only if requested |
| Customer Services Representative | Roadmap |
| Website & E-commerce Manager | Roadmap |
| Key Accounts Services Manager | Roadmap |
| Marketing Operations Manager | Shared workflow, QA, governance, metrics |
| Record Keeper & Scheduling | Shared audit log, calendar, records and reminders |

## 8. Primary user journey
1. Visitor reviews product, plans, limitations, privacy, and pilot offer.
2. User creates an account and organization.
3. User completes shared business profile; can skip nonessential questions and refine later.
4. User adds brand files, product/service information, existing copy, and optional website URL.
5. User creates a campaign using a guided brief.
6. System validates missing information and asks focused follow-up questions.
7. Workflow creates research notes, strategy, plan, and draft content.
8. User reviews each deliverable, edits inline, comments, requests changes, approves, or rejects.
9. If execution is requested, system shows the exact action, account, content/version, destination, schedule, and expected cost (if applicable).
10. Authorized approver confirms; backend checks permission, version, scope, budget, and idempotency before execution.
11. System records the result and verifies success where possible.
12. User reviews summary, outcomes, costs, and next recommendations.

## 9. Functional requirements
Priority: **P0** required for pilot; **P1** useful soon after; **P2** roadmap.

### Accounts, tenants, permissions
- FR-001 (P0): Users can sign up, sign in, sign out, and recover access using a supported secure flow.
- FR-002 (P0): Every customer record is scoped to an organization; cross-tenant access is denied server-side.
- FR-003 (P0): Organization admins can invite/remove members and assign roles.
- FR-004 (P0): Server-side authorization controls every protected route and action.
- FR-005 (P1): Support configurable single sign-on for eligible enterprise customers.

### Business profile and files
- FR-010 (P0): Users can create and edit a structured business profile.
- FR-011 (P0): Users can upload approved file types with size limits and malware/content checks appropriate to deployment.
- FR-012 (P0): Profile and uploaded content are reused in later campaign workflows within the same organization.
- FR-013 (P0): AI must distinguish known facts from assumptions and ask questions when a missing fact materially affects output.
- FR-014 (P1): Website analysis can be added through a constrained, safe retrieval service.

### Campaigns and workflow
- FR-020 (P0): Users can create, edit, duplicate, archive, and view campaigns.
- FR-021 (P0): Each campaign stores objective, audience, offer, geography, channel, timing, budget guidance, constraints, and success metrics.
- FR-022 (P0): A workflow produces a campaign strategy, execution plan, content deliverables, and QA notes.
- FR-023 (P0): Workflow stages, dependencies, timestamps, attempts, and failure states are persisted.
- FR-024 (P0): Users can pause/cancel a running workflow where safe.
- FR-025 (P0): Retry operations are bounded and do not duplicate external actions.
- FR-026 (P1): Users can schedule recurring planning workflows.

### Deliverables and collaboration
- FR-030 (P0): Deliverables are versioned and tied to campaign, task, and producing run.
- FR-031 (P0): Users can view, edit, comment on, approve, reject, and request changes.
- FR-032 (P0): Approval is tied to a specific immutable version and action payload.
- FR-033 (P0): A material change after approval invalidates the approval.
- FR-034 (P1): Support collaborative comments and mentions.

### Execution and integrations
- FR-040 (P0): External actions are disabled unless an enabled integration or explicit manual handoff exists.
- FR-041 (P0): Before execution, backend validates user permission, organization policy, approval, approved version, connected account, budget, and idempotency key.
- FR-042 (P0): External action state is not marked successful until the connector confirms or a verification step supports the result.
- FR-043 (P0): Connector credentials are encrypted and never returned to the browser or placed in logs.
- FR-044 (P1): Support one publishing connector after the pilot's target channel and API access are confirmed.
- FR-045 (P1): Support integration health and reconnect flows.

### Governance, observability, reporting
- FR-050 (P0): Every significant state change, approval decision, execution attempt, and admin action generates an audit event.
- FR-051 (P0): Organization-level limits control usage and workflow execution.
- FR-052 (P0): A platform/operator kill switch can stop new runs and external actions.
- FR-053 (P0): Users can see workflow status, deliverables, errors requiring action, and basic usage.
- FR-054 (P0): Reports separate completed activity from measured business outcomes.
- FR-055 (P0): Errors are understandable to users without exposing secrets or internal stack traces.
- FR-056 (P1): Add structured traces, alerting, and per-model/provider cost attribution.

## 10. Non-functional requirements
- Security: least privilege, secure sessions/tokens, rate limits, input validation, secret management, dependency updates, and tenant isolation tests.
- Privacy: documented data handling, retention, export/deletion process, and clear treatment of uploaded data and AI providers.
- Reliability: persistent workflow state, bounded retries, idempotency, graceful provider failure, and recoverable jobs.
- Performance: use asynchronous jobs for long-running AI/research workflows; keep ordinary UI/API interactions responsive.
- Accessibility: keyboard navigation, semantic labels, visible focus, adequate contrast, and screen-reader-friendly status updates.
- Maintainability: modular Flask blueprints/services, typed/validated request and response schemas, migrations, tests, and configuration via environment.
- Portability: containerized deployment and provider-neutral AI adapter.
- Observability: structured logs, request IDs, workflow/run IDs, metrics, and redaction of sensitive values.

## 11. User stories and acceptance criteria
### Story A — Create a campaign
**As a marketing lead**, I want to create a campaign brief so that the system can produce a plan and content relevant to my business.

Acceptance:
- Required fields are validated with field-level errors.
- Campaign is associated with the active organization.
- A duplicate submission does not create duplicate campaigns when an idempotency key is provided.
- The user can save a draft without starting AI work.

### Story B — Run the campaign workflow
**As a marketing lead**, I want the system to coordinate specialist work so that I receive a complete campaign pack.

Acceptance:
- The backend creates a workflow/run record before calling a provider.
- Each stage has a persisted state and bounded retry behavior.
- Outputs conform to a schema and are stored as versioned deliverables.
- Missing material inputs produce a clarification state instead of fabricated facts.
- Failure is visible and can be retried without losing prior outputs.

### Story C — Approve content
**As an authorized approver**, I want to approve an exact version so that only reviewed content can be sent or published.

Acceptance:
- Approval displays destination/action and exact content version.
- The server verifies role, version, policy, and status.
- Any material edit creates a new version and requires a new approval.
- Rejected content cannot be executed.
- Approval decision and timestamp are audited.

### Story D — Execute an external action
**As an organization admin**, I want the system to perform only authorized actions.

Acceptance:
- Execution is blocked without valid approval and connector authorization.
- A unique idempotency key prevents duplicate external execution on retry.
- Connector response and any verification evidence are saved.
- Ambiguous outcomes are marked `verification_required`, not falsely marked successful.
- The user can stop future actions through a kill switch.

### Story E — Understand results
**As an owner**, I want a report that distinguishes activity from results.

Acceptance:
- Report shows deliverables created, approvals, execution state, and usage/cost where available.
- Business metrics are shown only when connected data supports them.
- Estimates and recommendations are labelled as such.
- Report period and data source are visible.

## 12. Assumptions and validation plan
Assumptions to validate:
- SMBs value a coordinated workflow more than standalone copy generation.
- Campaign planning and content execution is valuable across multiple industries.
- Human approvals improve trust without making the workflow too slow.
- Customers will pay for reliable completion, not merely access to prompts.
- A narrow, reliable pilot can support acceptable unit economics.

Validation:
1. Interview 8–12 target SMB decision-makers across at least three industries.
2. Test a clickable prototype and observe users completing a campaign brief.
3. Run 3–5 concierge/pilot workflows with real business context and human review.
4. Measure time saved, revisions, quality, willingness to pay, and actual cost to deliver.
5. Decide whether to proceed, narrow the ICP, or change the first use case.

## 13. Release gates
- Gate 0: PRD and pilot workflow approved.
- Gate 1: Prototype usability tested.
- Gate 2: Auth, tenant isolation, persistence, and one workflow pass automated tests.
- Gate 3: Approval, audit, budget, kill-switch, and idempotency tests pass.
- Gate 4: Pilot customer can complete workflow with support and understand the limits.
- Gate 5: Cost, quality, and renewal evidence justify expansion.

## 14. Open decisions
These must be resolved before production integration:
- First pilot channel and whether publishing is manual handoff or a live connector.
- AI provider/model selection, retention terms, and cost controls.
- Initial subscription price and included usage.
- Hosting region and applicable privacy/legal requirements.
- Identity provider and email delivery service.
- Upload limits and supported file types.
- Data retention defaults and deletion/export service-level expectations.

## 15. Product promise and limitation language
Recommended promise: **“A coordinated AI marketing team that plans and prepares campaigns with you, keeps work visible, and asks for approval before consequential external actions.”**

Avoid promises such as “fully autonomous marketing,” “guaranteed growth,” “zero human work,” or guaranteed leads/revenue.
