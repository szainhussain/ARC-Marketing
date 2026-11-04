# Marketing Department Harness — Complete Specification Pack


---

# Source document: 01_PRD.md

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


---

# Source document: 02_UI_UX_SPEC.md

# Marketing Department Harness — UI/UX Specification
**Version:** 1.0  
**Design objective:** clear, calm, trustworthy, workflow-led SaaS for SMBs.

## 1. UX principles
- Lead with the work and business outcomes, not a novelty “AI office” animation.
- Make the next action obvious: provide context, review a deliverable, resolve a blocker, or approve an action.
- Show what AI is doing, why it needs input, and what will happen next.
- Keep internal reasoning hidden; expose concise rationale, sources, assumptions, and decisions.
- Never make an external action look complete until confirmed.
- Keep review and approval states visually distinct.
- Design for desktop first, then make all core workflows usable on mobile.
- Prefer progressive disclosure over long forms or dense configuration.

## 2. Information architecture / sitemap
- Public
  - Home
  - How it works
  - Use cases
  - Plans / pilot
  - Trust, security & privacy
  - Sign in / Create account
- App
  - Workspace switcher
  - Overview
  - Campaigns
    - Campaign list
    - New campaign brief
    - Campaign workspace
    - Deliverables
  - Tasks
  - Approvals
  - Reports
  - Brand & business profile
  - Integrations
  - Team & permissions
  - Usage & billing
  - Settings / data export / deletion request
- Platform administration (separate access boundary)
  - Service health
  - Workflow/run diagnostics
  - Usage and abuse controls
  - Support / incident tooling

## 3. Core navigation
Desktop left navigation:
1. Overview
2. Campaigns
3. Tasks
4. Approvals (show count of pending items)
5. Reports
6. Brand profile
7. Integrations
8. Team & settings

Top bar:
- Current organization/workspace
- Search (later if needed)
- Help
- Notifications
- User menu

Mobile:
- Bottom navigation for Overview, Campaigns, Tasks, Approvals
- Secondary destinations under “More”
- Keep the primary action available without horizontal scrolling.

## 4. Key screens
### 4.1 Public landing page
Sections:
1. Clear headline: “Your coordinated AI marketing team.”
2. Subheading explaining plan, create, review, and controlled execution.
3. Primary CTA: “Start a pilot” / “Create workspace”.
4. Workflow strip: Brief → Plan → Create → Review → Execute.
5. Example deliverables and sample workflow timeline.
6. Approval and privacy explanation.
7. Pilot scope and limitations.
8. Pricing or pilot offer, only once validated.
9. FAQ and contact.

Do not imply all 12 department roles are fully autonomous in the first release.

### 4.2 Sign-up and workspace creation
- Email/password or chosen identity provider.
- Verify email before sensitive setup where required.
- Create organization name and workspace slug.
- Display concise privacy and terms links.
- Show loading, failure, retry, and success states.
- Prevent account enumeration in recovery flows.

### 4.3 Progressive onboarding
Use a short wizard with autosave and a progress indicator. Ask only questions needed to produce a useful first campaign.

**Step 1 — Business basics**
- Business name
- Website (optional)
- Industry/category
- Countries/regions served
- Business type: B2B, B2C, both, nonprofit/other

**Step 2 — Offer and audience**
- Main products/services
- Best-fit audience/customer
- Customer problem solved
- Differentiators / proof points
- Primary campaign goal

**Step 3 — Brand**
- Tone of voice
- Preferred and prohibited phrases
- Logo, brand guide, product/service files
- Claims that must not be made
- Competitors (optional)

**Step 4 — Channels and constraints**
- Channels used
- Available budget range (optional)
- Campaign dates
- Approval owner(s)
- Industry/legal restrictions or disclaimers

**Step 5 — Review**
- Summary with edit links
- Clear distinction between required and optional data
- CTA: “Save profile and create first campaign”
- Secondary CTA: “Finish later”

Avoid asking the same question in every agent setup. Shared profile data should be reused; task-specific questions should appear only when material.

### 4.4 Overview dashboard
Primary purpose: show current work, blockers, approvals, and outcomes.

Recommended layout:
- Header: “Good morning” optional; workspace name; primary CTA “Create campaign”.
- Four compact summary cards: Active campaigns, Tasks needing attention, Pending approvals, Usage this period.
- “Needs your attention” list sorted by urgency.
- Active campaigns table/list with stage, owner, next action, last update.
- Recent activity feed with actor, event, timestamp.
- Performance snapshot only when real connected data exists.
- Empty state with one clear next step.

Do not display made-up ROI or generic vanity metrics.

### 4.5 Campaign creation / brief
Use a structured form, not a blank chat-only interface.
Fields:
- Campaign name
- Objective (awareness, engagement, leads, sales, retention, launch, other)
- Offer/product/service
- Target audience
- Geography/language
- Channel(s)
- Key message / CTA
- Start/end dates
- Budget guidance (optional; never treated as authorization to spend)
- Success metrics
- Required facts and proof
- Constraints / prohibited claims
- Attachments
- “What else should the team know?” free text

Behavior:
- Autosave draft.
- Inline examples and plain-language help.
- “Review brief” step before running.
- Clarification questions limited to material gaps.
- Explicit “Generate plan and draft content” action with estimated usage if available.

### 4.6 Campaign workspace
Three-column desktop layout when width allows:
- Left: campaign stages and task list.
- Center: selected deliverable / brief / plan.
- Right: status, evidence/assumptions, comments, version history, and next action.
On smaller screens, collapse to tabs or stacked panels.

Stage rail:
1. Brief
2. Research
3. Strategy
4. Plan
5. Content
6. Quality review
7. Approval
8. Execution
9. Results

Status vocabulary:
- Draft
- Queued
- In progress
- Needs your input
- Awaiting approval
- Approved
- Executing
- Completed
- Failed
- Cancelled
- Verification required

Each status must have a clear textual label; do not rely on color alone.

### 4.7 Deliverable review
Header:
- Deliverable title
- Type (strategy, calendar, copy, creative brief, report)
- Version number
- Status
- Produced by workflow stage
- Last updated

Body:
- Editable content or readable preview
- Evidence/source notes when applicable
- “Known facts”, “Assumptions”, and “Needs confirmation” sections as relevant
- Comments and revision history

Actions:
- Edit
- Request changes
- Approve this version
- Reject
- Export/copy
- “Prepare external action” only if the deliverable is eligible

When requesting changes, collect a concise reason and preserve the previous version.

### 4.8 Approval center
List columns/cards:
- Action/deliverable
- Destination/account
- Exact version
- Requested by / requested at
- Risk/impact level
- Planned schedule
- Estimated spend, if any
- Status

Approval detail must show:
- Exact content or action payload
- Account/destination and audience
- Timing
- Cost/spend limit if applicable
- Relevant policy warnings
- What approval authorizes—and what it does not authorize
- Approve, reject, or request changes

Require an explicit confirmation for high-impact actions. Do not treat opening a screen, silence, or prior approval of another version as consent.

### 4.9 Tasks
Filters: status, campaign, stage, assigned capability, due date, needs input.
Task details:
- Purpose and expected output
- Dependencies
- Inputs and linked files
- Current state and attempts
- Output and error message
- Retry/cancel controls only when safe
- Audit/activity history

### 4.10 Reports
- Workflow summary: completed stages, deliverables, approvals, execution outcomes.
- Usage/cost summary with period and data source.
- Business outcomes only from connected, attributable data.
- Label estimates and recommendations.
- Provide CSV export later if it materially helps pilot customers.
- Never conflate content production with business performance.

### 4.11 Business profile and brand library
- Structured profile with edit history.
- Brand assets and documents with filename, type, date, and access scope.
- Mark outdated or superseded documents.
- Show how profile data is reused.
- Allow delete/export requests subject to documented retention and legal requirements.
- Do not expose a document to another organization.

### 4.12 Integrations
For each connector:
- Purpose and permissions requested
- Connected account identity
- Granted scopes
- Last health check
- Connect / reconnect / disconnect
- Data accessed and actions enabled
- Clear warnings for write permissions
- Never display tokens or secrets.

### 4.13 Optional “AI office” visualization
May be used as a secondary view or onboarding illustration, not the primary control surface. Each agent/role should map to real tasks and states. Avoid fake animation that suggests work is happening when no workflow run exists. Every status should be traceable to persisted backend records.

## 5. Design system
### Visual direction
Professional, warm, focused, modern B2B SaaS. Use a restrained neutral base and one primary accent. Reserve strong semantic colors for meaningful statuses. Avoid overly playful robot imagery or “sci-fi command center” visuals.

### Typography
- Use a readable sans-serif family with a clear hierarchy.
- Body text 14–16 px equivalent; dense data tables can be smaller but must remain readable.
- Clear heading hierarchy and generous line spacing.

### Layout and spacing
- 8-point spacing scale.
- Content max width around 1200–1360 px for desktop views.
- Use consistent cards, dividers, and alignment.
- Prefer one dominant CTA per screen.
- Avoid excessive cards within cards.

### Components
- Button: primary, secondary, tertiary, destructive, disabled/loading.
- Input: text, textarea, select, date, file upload.
- Status badge with icon + text.
- Progress/stage rail.
- Task row and campaign row.
- Deliverable viewer/editor.
- Approval summary panel.
- Activity timeline.
- Empty state.
- Toast and inline error.
- Confirmation modal for consequential actions.
- Usage meter.
- Source/assumption panel.
- Version history.

### Interaction standards
- Every async action has loading, success, failure, and retry states.
- Disable duplicate submission while request is in flight.
- Use optimistic UI only for reversible low-risk changes.
- Require server confirmation for approval and external action status.
- Keep unsaved changes visible and recoverable.
- Keyboard-accessible controls and focus states.
- Never use color as the only status signal.

## 6. Responsive behavior
- Desktop: full navigation and three-column campaign workspace.
- Tablet: collapsible sidebar and two-column or tabbed workspace.
- Mobile: stacked layout, simplified stage navigation, single-column review, approval actions easy to reach.
- Wide tables convert to cards or horizontal scrolling with a clear cue.
- File uploads and editing must remain usable on mobile.

## 7. Content and microcopy rules
- Use plain, direct language.
- Prefer “AI is preparing a draft” over “agent is thinking”.
- Prefer “Needs your approval before publishing” over vague “action required”.
- Explain why a blocker exists and how to resolve it.
- Never say “published”, “sent”, or “completed” before verified confirmation.
- Mark AI-generated assumptions and unverified recommendations.
- Be explicit about cost, destination, and permission scope before external actions.

## 8. Prototype acceptance checklist
- A first-time user can understand the product promise in under one minute.
- A user can complete onboarding without answering optional questions.
- A user can create a campaign and understand what happens next.
- Workflow status is visible and not dependent on animation.
- A reviewer can inspect exact content/version and approve or request changes.
- An unapproved action cannot be initiated from the UI or API.
- Errors provide a useful next step without exposing secrets.
- Main flows work at mobile widths and with keyboard navigation.


---

# Source document: 03_TECHNICAL_ARCHITECTURE.md

# Marketing Department Harness — Technical Architecture
**Version:** 1.0  
**Target:** small, modular Flask application that can evolve safely.

## 1. Architecture decision summary
Build a modular monolith first. Use Python Flask for the API, PostgreSQL for production persistence, SQLAlchemy and Alembic for data access/migrations, and an explicit workflow engine implemented in application code. Keep the AI provider behind an adapter. Add a queue (Celery/RQ plus Redis) when long-running jobs need reliable background execution; do not introduce distributed services prematurely.

### Initial stack
- Backend: Python 3.12+ and Flask
- API validation/serialization: Pydantic or Marshmallow; choose one consistently
- Database: PostgreSQL in shared/staging/production; SQLite only for local quick-start if needed
- ORM/migrations: SQLAlchemy + Alembic/Flask-Migrate
- Auth: established session/OIDC solution; secure cookie sessions for browser app where appropriate
- Frontend: React + TypeScript for a scalable app, or server-rendered templates for a smaller prototype; do not maintain both without need
- Background jobs: begin with synchronous local workflow for prototype; move long runs to a queue before pilot
- Files: private object storage in production; local filesystem only for development
- Deployment: Docker, managed PostgreSQL, secret manager, TLS, logs/metrics/error tracking
- Testing: pytest, integration tests, tenant-isolation tests, connector contract tests
- AI: provider adapter with structured output validation, timeouts, cost tracking, and policy checks

## 2. Logical architecture
```text
Browser UI
   |
   v
Flask API / Auth / Tenant Authorization
   |
   +--> Domain services: campaigns, tasks, deliverables, approvals, usage
   |
   +--> Workflow coordinator (explicit state machine)
   |       |
   |       +--> CMO / planner capability
   |       +--> Research capability
   |       +--> Marketing manager capability
   |       +--> Content capability
   |       +--> QA / policy checks
   |
   +--> AI provider adapter
   |
   +--> Integration adapters (initially manual export/handoff)
   |
   +--> PostgreSQL / private file storage / queue
   |
   +--> Audit, structured logs, usage metrics, error tracking
```

The backend is authoritative for workflow state, permissions, approvals, budget enforcement, usage, and external-action status. Model output is untrusted input and must be validated.

## 3. Recommended project layout
```text
marketing-harness/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── organizations.py
│   │       ├── business_profile.py
│   │       ├── campaigns.py
│   │       ├── tasks.py
│   │       ├── deliverables.py
│   │       ├── approvals.py
│   │       ├── integrations.py
│   │       └── reports.py
│   ├── models/
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── membership.py
│   │   ├── business_profile.py
│   │   ├── campaign.py
│   │   ├── task.py
│   │   ├── workflow_run.py
│   │   ├── deliverable.py
│   │   ├── approval.py
│   │   ├── integration.py
│   │   ├── usage_record.py
│   │   └── audit_event.py
│   ├── schemas/
│   ├── services/
│   │   ├── campaign_service.py
│   │   ├── task_service.py
│   │   ├── workflow_service.py
│   │   ├── approval_service.py
│   │   ├── authorization_service.py
│   │   ├── usage_service.py
│   │   ├── audit_service.py
│   │   └── report_service.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── cmo_planner.py
│   │   ├── research_analyst.py
│   │   ├── marketing_manager.py
│   │   ├── content_creator.py
│   │   └── quality_reviewer.py
│   ├── ai/
│   │   ├── base.py
│   │   ├── provider_adapter.py
│   │   └── schemas.py
│   ├── workflows/
│   │   ├── campaign_workflow.py
│   │   └── state_machine.py
│   ├── integrations/
│   │   ├── base.py
│   │   └── manual_handoff.py
│   └── storage/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── contract/
├── frontend/                 # if React is selected
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 4. Domain model
Use UUIDs for public-facing identifiers. Add `organization_id` to every tenant-owned record and enforce ownership in every query. Consider database row-level security as defense in depth after application-level checks are tested.

### Core entities
- `users`: identity and account status.
- `organizations`: tenant/workspace, settings, status, usage plan.
- `memberships`: user ↔ organization relationship and role.
- `business_profiles`: structured business and brand context, versioned where appropriate.
- `documents`: metadata, private storage key, checksum, content type, status, organization scope.
- `campaigns`: brief, objective, audience, channel, dates, constraints, status.
- `tasks`: workflow work items, stage, dependencies, status, attempt count, input/output references.
- `workflow_runs`: workflow type/version, state, start/end, error summary, cost totals.
- `agent_runs`: logical capability run, model/provider metadata, structured input/output references, token/cost data, status.
- `deliverables`: type, current version pointer, status, campaign/task/run links.
- `deliverable_versions`: immutable version content, schema version, creator/run, checksum.
- `approvals`: action type, exact deliverable version/action payload hash, requester, approver, decision, timestamps, expiry.
- `integrations`: provider, account metadata, encrypted credential reference, scopes, health state, enabled actions.
- `external_actions`: action payload hash, idempotency key, connector, status, response metadata, verification status.
- `usage_records`: metered units, provider, model, estimated/actual cost, workflow/run reference.
- `audit_events`: actor, organization, action, target, timestamp, correlation ID, redacted metadata.
- `comments`: user, target object/version, body, timestamp.
- `notifications`: organization/user, type, payload reference, delivery state.

### Important relationships and constraints
- Organization membership is required for customer access.
- Campaign, task, deliverable, approval, integration, usage, and audit data are organization-scoped.
- Deliverable versions are immutable; edits create a new version.
- Approval refers to an immutable version and action payload hash.
- External action has a unique `(organization_id, idempotency_key)` constraint.
- Workflow run transitions are validated by application state machine.
- Secrets never appear in ordinary model fields or API responses.

## 5. State machines
### Workflow run
`created → queued → running → needs_input | awaiting_approval | completed | failed | cancelled`
- `needs_input` resumes only after required input is supplied.
- `awaiting_approval` waits for a decision; it must not execute the action by itself.
- `completed` means the internal workflow completed; it does not imply an external action succeeded.
- `failed` can be retried only under bounded retry policy.
- `cancelled` blocks new stages; already-started external actions may require verification.

### Task
`pending → ready → running → needs_input | awaiting_approval | completed | failed | cancelled`

### External action
`prepared → awaiting_approval → approved → executing → succeeded | failed | verification_required | cancelled`
- An approval may be revoked before execution if policy allows and execution has not begun.
- If content/action payload hash changes, prior approval is invalid.
- Ambiguous provider timeouts must result in reconciliation/verification, not blind retries.

## 6. Workflow orchestration
Keep the campaign workflow explicit and inspectable:
1. Validate campaign brief and profile completeness.
2. Create workflow run and task graph in a database transaction.
3. Generate strategy/research plan from user facts and clearly labelled assumptions.
4. Retrieve approved documents and relevant context within tenant scope.
5. Run research capability using permitted sources; preserve source metadata when available.
6. Draft campaign plan.
7. Generate content pack from approved plan and brand profile.
8. Run schema, completeness, prohibited-claim, brand, and factual consistency checks.
9. Save deliverables and versions.
10. Move workflow to `awaiting_approval` only for a defined external action; content review can be a separate human review state.
11. Generate a concise completion summary and usage record.
12. If a failure occurs, persist the failed stage and safe error summary.

Avoid unbounded agent-to-agent conversations. Each stage has a clear contract, input schema, output schema, timeout, retry rule, and budget.

## 7. AI adapter contract
Create a provider-neutral interface such as:
- `generate_structured(task_type, input_data, output_schema, context, budget, correlation_id)`
- Returns validated structured data, provider/model metadata, token usage if available, cost estimate, and warnings.
- Raises typed errors: `ProviderUnavailable`, `RateLimited`, `InvalidOutput`, `BudgetExceeded`, `Timeout`.
- Supports timeout and bounded retries.
- Logs redacted metadata only.
- Does not directly call external publishing APIs.

### Output validation
- Parse JSON/structured output.
- Validate against a schema.
- Reject or repair invalid output with a small bounded retry count.
- Check required fields, content limits, and safety/brand constraints.
- Label assumptions and uncertain claims.
- Never treat model-generated URLs, permissions, or action requests as trusted.

## 8. API contracts (v1 draft)
All routes require authentication unless explicitly public. All customer routes require active organization membership. Use JSON, consistent errors, pagination, and request/correlation IDs.

### Common response/error pattern
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please correct the highlighted fields.",
    "details": [{"field": "objective", "issue": "Required"}],
    "request_id": "uuid"
  }
}
```

### Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/me` | Current user and workspace memberships |
| GET/PATCH | `/api/v1/business-profile` | Read/update active organization's profile |
| POST/GET | `/api/v1/campaigns` | Create/list campaigns |
| GET/PATCH/DELETE | `/api/v1/campaigns/{campaign_id}` | Read/update/archive campaign |
| POST | `/api/v1/campaigns/{campaign_id}/runs` | Start workflow; returns run ID and status |
| GET | `/api/v1/runs/{run_id}` | Workflow status and stage summary |
| POST | `/api/v1/runs/{run_id}/cancel` | Request safe cancellation |
| GET | `/api/v1/tasks` | Filter/paginate tasks |
| GET | `/api/v1/deliverables/{deliverable_id}` | Read current version |
| GET | `/api/v1/deliverables/{deliverable_id}/versions` | Version history |
| POST | `/api/v1/deliverables/{deliverable_id}/versions` | Create a new version/edit |
| POST | `/api/v1/approvals` | Request approval for exact action/version |
| POST | `/api/v1/approvals/{approval_id}/decision` | Approve/reject/request changes |
| GET | `/api/v1/approvals` | List pending/recent approvals |
| POST | `/api/v1/external-actions/{action_id}/execute` | Execute approved action through backend policy checks |
| GET | `/api/v1/integrations` | List integration metadata/health |
| POST | `/api/v1/integrations/{provider}/connect` | Start provider OAuth/connection flow |
| POST | `/api/v1/integrations/{integration_id}/disconnect` | Disconnect integration |
| GET | `/api/v1/reports/summary` | Workflow/usage summary |
| GET | `/api/v1/usage` | Usage by period |
| GET | `/api/v1/audit-events` | Authorized audit history |

### API requirements
- Validate UUIDs, types, lengths, enums, dates, and file sizes.
- Use pagination (`limit`, `cursor`) for lists.
- Use `Idempotency-Key` on workflow start and external action creation/execution.
- Return `202 Accepted` for queued long-running work.
- Use `409 Conflict` for invalid state/version conflicts.
- Use `403 Forbidden` for permission denial and avoid leaking cross-tenant existence.
- Use `429 Too Many Requests` for rate/usage limits.
- Never trust organization ID from request body alone; derive/validate from active membership.
- Approval decision payload includes `decision`, optional `comment`, and expected version/hash.
- Document request/response schemas before frontend integration.

## 9. Background jobs and reliability
Before paid pilot, run long workflows in a durable background queue. Requirements:
- Persist job intent before enqueueing.
- Job handler rechecks state and permission/policy before each stage.
- Bounded retries with exponential backoff for transient provider failures.
- Do not retry non-idempotent external actions blindly.
- Use a reconciliation job for actions with ambiguous outcomes.
- Store job and workflow IDs together.
- Dead-letter/failed job inspection path.
- Cancellation checked between stages.
- Enforce maximum runtime and usage budget per run.

## 10. Security and privacy controls
- HTTPS everywhere outside local development.
- Secure, HttpOnly, SameSite cookies or a carefully managed token strategy.
- CSRF protection for cookie-authenticated mutation routes.
- Password hashing or delegated identity provider.
- Rate limiting and abuse detection.
- Encrypted integration secrets using a managed key/secret service.
- Strict file type/size checks and safe document processing.
- Prompt-injection resistance: treat uploads and web pages as untrusted data, never instructions; tools are allowlisted and permissions come from backend policy.
- Redact secrets, tokens, and sensitive content from logs.
- Tenant-isolation tests for every resource type.
- Backup and restore tests; documented retention and deletion procedures.
- Dependency scanning, patching, and incident response plan.
- No model-generated direct database queries or unrestricted shell/browser actions.

## 11. Deployment and environments
- Local: `.env`, local database/container, test AI key with low budget.
- CI: lint, type/schema checks, unit tests, migrations, security/tenant tests.
- Staging: production-like managed DB, test integrations, synthetic data.
- Production: managed Postgres, private object storage, secret manager, queue/worker, TLS, error tracking, backups, alerting.
- Use separate credentials and databases per environment.
- Use migration-based schema changes; never rely on ad hoc production schema edits.
- Add health endpoints for liveness/readiness without exposing internals.

## 12. Testing strategy
- Unit: state transitions, permissions, budgets, schema validation, versioning.
- Integration: API + database + workflow persistence.
- Security: cross-tenant read/write attempts, role bypass, CSRF, secret leakage.
- Contract: AI provider and connector response handling.
- Workflow: success, missing input, invalid model output, provider timeout, budget exhaustion, cancellation, retry.
- Approval: stale version, unauthorized approver, changed payload, rejected action, revoked integration.
- External action: duplicate retry, ambiguous timeout, connector failure, verification required.
- UI: keyboard navigation, loading/error/empty states, approval confirmation.
- Load/cost: representative workflow volume and model usage.

## 13. Implementation order
1. App factory/configuration, database, migrations, health endpoint.
2. Auth, organization, membership, tenant authorization.
3. Business profile and campaign CRUD.
4. Task/run/deliverable models and state transitions.
5. AI adapter and schema validation.
6. Campaign workflow and persisted deliverables.
7. Review/versioning/comments.
8. Approval service and audit log.
9. Manual handoff / export.
10. Usage reporting, limits, kill switch, operational monitoring.
11. First supported connector after access and channel decision.


---

# Source document: 04_GOVERNANCE_AND_INTEGRATIONS.md

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


---

# Source document: 05_IMPLEMENTATION_BACKLOG.md

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
