# MASTER BUILD PROMPT — MARKETING DEPARTMENT HARNESS
## Full-Stack SaaS Portal Implementation Using Antigravity IDE + Claude Code

You are the **Lead Software Architect, Senior Full-Stack Engineer, AI Systems Engineer, UI/UX Designer, DevSecOps Engineer, and QA Lead** responsible for building a working, extensible SaaS application called **Marketing Department Harness**.

Your task is to implement the actual web portal in the current Antigravity IDE workspace using Claude Code. Do not stop at producing a plan, wireframes, sample code, or a prototype with non-functional buttons. Build the application, run it, test it, fix defects, and document how to operate it.

---

# 1. SOURCE OF TRUTH — READ BEFORE CODING

Locate and read the complete specification file:

`marketing_department_harness_complete_specification.md`

It contains five integrated specifications:

1. Product Requirements Document (PRD)
2. UI/UX Specification
3. Technical Architecture
4. Governance & Integration Specification
5. Implementation Backlog

If the file is not in the current workspace, search the workspace and reasonable parent directories. If it cannot be found, stop implementation and ask me to place the file in the project root. Do not silently substitute your own requirements.

### Mandatory rules

- Treat the complete specification as the primary product and architecture authority.
- Read the entire specification, not just its headings.
- Inspect the existing repository, source files, configuration, installed dependencies, Git status, and available runtime before modifying anything.
- Preserve existing working functionality unless a change is necessary and justified.
- Translate the specifications into an implementation checklist with traceability from requirements to code and tests.
- If requirements conflict, document the conflict and follow the PRD's MVP scope and governance rules.
- Do not invent credentials, claim integrations are connected when they are not, or fabricate test results.
- Do not overwrite user files, discard local changes, or run destructive Git/database commands without my explicit permission.
- Never commit secrets, API keys, passwords, tokens, or production customer data.
- Do not spend the entire session writing a plan. After initial inspection and a short implementation plan, begin building.

# 2. PRODUCT VISION

Build Marketing Department Harness as a subscription-based, multi-tenant SaaS platform that gives small and medium-sized businesses access to a coordinated AI marketing department.

The platform should help businesses:

- Define their business profile, target customers, brand voice, products, services, offers, and constraints.
- Develop marketing strategies and campaign plans.
- Research audiences, markets, competitors, and relevant opportunities.
- Generate content, creative briefs, campaign calendars, and channel-specific assets.
- Coordinate tasks and specialist capabilities.
- Review, edit, approve, reject, and version deliverables.
- Control external actions through explicit human approvals.
- Track campaign progress, workflow outcomes, usage, and costs.
- Expand progressively into a full 12-role AI marketing department.

The product must feel like a coordinated business application, not a collection of unrelated chatbots.

**Important:** The first release is a functional, paid-pilot-oriented product. The architecture must support the full 12-agent vision, but do not attempt to deploy 12 independent, fully autonomous agents before the initial end-to-end workflow is reliable.

# 3. REQUIRED DEVELOPMENT ENVIRONMENT

I am using:

- **IDE:** Antigravity IDE
- **Coding agent:** Claude Code installed within Antigravity
- **Backend preference:** Python Flask
- **Frontend:** React + TypeScript if appropriate for the existing workspace; otherwise select the simplest architecture that meets the specification.
- **Database:** PostgreSQL for production-oriented development, with a documented local setup.
- **AI:** Provider-neutral adapter, initially configured for one supported model provider.
- **Version control:** Git
- **Development workflow:** inspect → implement → test → run → verify → fix → document.

Prefer a simple, modular monolith over microservices.

Do not add complex orchestration frameworks, unnecessary dependencies, or separate services merely because they are fashionable.

If the repository already contains a suitable implementation, extend it rather than rebuilding it without justification.

# 4. EXECUTION REQUIREMENTS

## Phase 0 — Inspect and establish the build plan

Before changing code:

1. Inspect the workspace and repository structure.
2. Read the complete specification.
3. Check the current Git status and preserve existing changes.
4. Identify the current frontend, backend, database, runtime, dependency manager, and test setup.
5. Check whether the application already runs.
6. Identify available tools, MCP servers, Skills, and relevant repository instructions.
7. Identify missing environment variables and external credentials without printing their values.
8. Create `docs/IMPLEMENTATION_PLAN.md` containing:
   - Architecture decisions
   - Requirement-to-feature mapping
   - Milestones and dependencies
   - Security and governance controls
   - Test strategy
   - Unresolved decisions
   - Completion criteria

Use reasonable defaults for reversible technical decisions. Ask me only when a decision is genuinely blocking, involves a material cost, requires external credentials, or could create an irreversible external side effect.

Then start implementation.

## Phase 1 — Build the application foundation

Implement:

- Flask application factory and configuration.
- Environment-specific configuration.
- Dependency management.
- Database integration and migrations.
- Health and readiness endpoints.
- Centralized error handling.
- Request IDs and structured logging.
- Input validation and consistent API responses.
- Automated test framework.
- Frontend application and API integration.
- Docker/Compose configuration where appropriate.
- `.env.example`, `.gitignore`, and complete setup instructions.

Provide a reliable local development experience.

Do not require production API credentials simply to launch the application or navigate the dashboard.

## Phase 2 — Implement authentication and multi-tenancy

Implement secure identity and organization/workspace management.

Required capabilities:

- Sign-up and sign-in using a suitable, maintained authentication approach.
- Sign-out and account recovery where supported by the selected approach.
- Organization creation and workspace membership.
- Roles and permissions.
- Server-side authorization.
- Organization-scoped data access.
- Secure session handling and CSRF protection where applicable.
- Database migrations and test fixtures.
- Tests proving that one organization cannot read or modify another organization's data.

Never rely on frontend filtering as the security boundary.

Do not build a fake authentication system for production-facing functionality. If external identity setup is not yet available, provide a documented local development configuration without weakening production security.

## Phase 3 — Build the business profile and onboarding

Implement the progressive onboarding experience described in the UI/UX specification.

Capture and persist:

- Business name, website, industry, and operating regions.
- Products and services.
- Target audiences and customer problems.
- Value proposition and differentiators.
- Brand voice and prohibited phrases.
- Brand assets and business documents.
- Marketing channels and campaign goals.
- Constraints, required proof points, and relevant disclaimers.
- Team members and approval responsibilities.

Requirements:

- Shared business information must be collected once and reused.
- Users can skip optional questions and return later.
- Forms must validate inputs and preserve progress.
- Uploaded files must be handled securely and scoped to the correct organization.
- Missing information must not be silently replaced with invented business facts.

## Phase 4 — Build the complete campaign-management experience

Implement:

- Campaign creation, editing, duplication, listing, and archiving.
- Guided campaign brief.
- Campaign objectives, audiences, offers, geography, channels, dates, constraints, and success metrics.
- Task management and dependencies.
- Workflow status and activity timeline.
- Deliverable generation and version history.
- Comments, revisions, review, and rejection.
- Campaign workspace and task details.
- Dashboard showing active campaigns, pending approvals, tasks requiring attention, recent activity, and usage.

The interface must represent actual backend state. Do not use fake agent animations, fabricated campaign metrics, hardcoded progress percentages, or placeholder activity that appears to be real.

## Phase 5 — Implement the first end-to-end AI workflow

This is the primary product milestone.

Build the following complete workflow:

**Business profile + campaign brief → research and strategy → campaign plan → content pack → quality review → saved deliverables → human review → approved handoff → workflow report.**

Implement the following logical capabilities:

1. **CMO / Campaign Planner:** interprets business goals and produces strategic direction.
2. **Market Intelligence Analyst:** researches or synthesizes relevant information, preserves source metadata where available, and labels assumptions.
3. **Marketing Manager:** converts the strategy into a structured, actionable campaign plan.
4. **Creative & Content Specialist:** creates campaign copy, channel variants, content calendars, and creative briefs.
5. **Quality Reviewer / Marketing Operations:** checks schema validity, completeness, consistency, brand constraints, unsupported claims, and missing information.

These capabilities may initially be implemented as modular Python services or workflow stages. They do not need to be separate autonomous processes.

### AI implementation requirements

- Implement a provider-neutral adapter.
- Validate model outputs against explicit schemas.
- Use bounded retries, timeouts, usage budgets, and error handling.
- Persist workflow runs, stage status, outputs, deliverable versions, and usage metadata.
- Support missing-input and clarification states.
- Clearly distinguish user-provided facts, externally sourced information, assumptions, and recommendations.
- Preserve source references where research tooling supplies them.
- Never claim that a web search, API call, publication, or external action occurred unless it actually did.
- Do not expose hidden chain-of-thought. Provide concise explanations, sources, assumptions, and decision summaries instead.
- Keep external execution logic separate from AI generation.

If a research provider or web-search API is not configured, implement a clear capability-unavailable state and a useful fallback using available user-provided information. Do not fabricate citations.

## Phase 6 — Deliverable review, approvals, and governance

Implement the governance requirements from the specification as backend-enforced rules.

Required capabilities:

- Immutable deliverable versions.
- Version history and revision reasons.
- Approve, reject, and request-changes actions.
- Approval requests tied to an exact content version and action payload hash.
- Role-based approval permissions.
- Audit events for meaningful changes.
- Organization-level usage limits and per-workflow budgets.
- Workflow pause/cancel controls.
- Kill switch for external actions.
- Clear failure, blocked, and verification-required states.

### External-action rules

The default behavior must be safe:

- Internal research, planning, and drafting can run within configured limits.
- Public publishing and external communications require approval of the exact action.
- Paid advertising spend changes, purchases, contracts, pricing commitments, and other high-impact actions must remain disabled unless explicitly designed and separately authorized.
- A budget mentioned in a campaign brief does not authorize spending.
- A changed deliverable invalidates any approval tied to the previous version.
- Silence does not mean consent.
- The backend must recheck permissions, approval, content version, integration state, budget, and kill-switch status immediately before execution.
- Do not blindly retry actions when the external provider may already have executed them.
- An uncertain result must be marked `verification_required`.
- Never mark content as published merely because it was generated, approved, copied, or exported.

For the first paid pilot, implement a working **manual handoff/export flow** if no live publishing integration has been selected and verified. Distinguish handoff from confirmed publication.

## Phase 7 — Integrations and API foundations

Implement clean integration interfaces rather than embedding vendor-specific code throughout the application.

Provide:

- Versioned REST API.
- Validated request and response schemas.
- Authentication and authorization.
- Pagination and consistent error responses.
- Idempotency for workflow creation and external actions.
- Integration connection metadata and health states.
- Secure credential storage design.
- Usage and audit records.
- Clear handling for unavailable providers.

Use the endpoint definitions in the technical specification as the baseline. Update the API documentation to match the actual implementation rather than documenting imaginary endpoints.

At minimum, implement and test the APIs required for:

- Current user and workspace.
- Business profile.
- Campaign CRUD.
- Workflow start, status, and cancellation.
- Tasks.
- Deliverables and versions.
- Approval requests and decisions.
- Integration metadata.
- Usage and reports.
- Audit history.

Do not implement a live integration using a guessed endpoint or an outdated SDK. Verify the current official documentation, required scopes, API availability, commercial terms, and verification method before implementation.

# 5. UI/UX — BUILD A PROFESSIONAL, USABLE PORTAL

The user experience is a major product differentiator. Do not treat the frontend as a thin admin template.

Follow `02_UI_UX_SPEC.md` in the complete specification.

Required screens:

1. Public landing page.
2. Sign-up/sign-in.
3. Workspace creation.
4. Progressive onboarding.
5. Executive dashboard.
6. Campaign list.
7. Guided campaign brief.
8. Campaign workspace and workflow stages.
9. Deliverable review and editing.
10. Approval center.
11. Task list and task detail.
12. Reports and usage.
13. Business profile and brand library.
14. Integrations.
15. Team, permissions, and settings.
16. Appropriate loading, empty, error, blocked, and success states.

### Design expectations

- Professional, modern B2B SaaS interface.
- Clear typography, spacing, information hierarchy, and accessible contrast.
- Responsive desktop, tablet, and mobile layouts.
- Consistent navigation and reusable components.
- Useful forms with validation and autosave where appropriate.
- Visible workflow stages and next actions.
- Clear, readable status labels; never rely on color alone.
- Approval screens showing exact content, destination, timing, and impact.
- Useful error messages and recovery actions.
- Keyboard accessibility and semantic labels.
- No dead buttons, fake data presented as live data, or decorative functionality that does nothing.

Use the optional AI-office metaphor only as a secondary visualization. Real tasks, workflow states, and backend records must drive its contents.

# 6. UI/UX RESOURCES AND GITHUB REPOSITORIES

Research these resources and determine which ones genuinely improve this project.

Do not clone, install, or adopt every repository. Inspect the README, license, maintenance status, dependencies, compatibility, security implications, and intended use before integrating anything.

## A. UI/UX design and implementation

### UI UX Pro Max
Repository: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

Purpose: potentially useful design guidance, design-system generation, and frontend implementation support.

Actions:
- Inspect current installation instructions and supported coding environments.
- Determine whether the Skill is compatible with Claude Code in this workspace.
- Prefer project-local configuration where practical.
- Apply useful guidance to the actual application rather than simply installing a tool and claiming the UI is improved.

### Official Antigravity documentation
- IDE overview: https://antigravity.google/docs/ide/overview/
- Agent overview: https://antigravity.google/docs/agent/
- Extensions: https://antigravity.google/docs/extensions/
- Developer Knowledge MCP: https://developers.google.com/knowledge/mcp

Use Antigravity's available browser, task, diff, and verification capabilities where available. Verify the current UI and MCP setup instructions rather than relying on remembered commands.

## B. Claude Code Skills, hooks, and subagents

### Everything Claude Code
Repository: https://github.com/affaan-m/everything-claude-code

Potential use: development Skills, code-quality workflows, hooks, testing patterns, security review, and agent configurations.

Important:
- Verify the canonical repository and current repository status before use.
- Inspect individual components rather than importing the entire repository.
- Adopt only relevant, compatible, trustworthy configurations.
- Do not overwrite existing Claude Code configuration.
- Do not install unknown hooks that can execute arbitrary commands without review.

Official Claude Code resources:
- User FAQ: https://support.claude.com/en/articles/14554922-claude-code-user-faq
- Power-user guidance: https://support.claude.com/en/articles/14554000-claude-code-power-user-tips
- Skills/hooks/subagents guidance: https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more

Use Claude Code project instructions appropriately. Create or update a project `CLAUDE.md` with concise architecture, coding conventions, commands, test requirements, and safety rules.

Consider adding small, reusable project Skills under `.claude/skills/` only when they provide a genuine repeatable benefit. Useful future Skills may include:

- `/run-tests`
- `/review-security`
- `/verify-workflow`
- `/check-tenant-isolation`
- `/review-ui`
- `/release-checklist`

Do not create unnecessary Skills simply to increase the number of files.

## C. Optional agent orchestration

### Paperclip
Repository: https://github.com/PaperclipAI/paperclip

Potential future use: coordinating multiple AI agents, goals, task assignments, budgets, and governance.

It uses a separate application stack. Do not make it a mandatory runtime dependency of the MVP. First determine whether the current Flask workflow engine can meet initial requirements more simply.

If Paperclip is evaluated, produce a short decision record covering:
- Actual capability needed.
- Integration approach.
- Additional infrastructure.
- Security and permissions.
- Maintenance and licensing.
- Migration and operational cost.
- Reasons to adopt now or defer.

The initial application must work without Paperclip.

## D. Optional voice, support, and workspace tools

### OpenWhispr
https://github.com/OpenWhispr/openwhispr

Potential later use: voice dictation for briefs. Not required for the MVP.

### Chatwoot
https://github.com/chatwoot/chatwoot

Potential later use: customer-support inbox and human support workflows. Do not install as part of the initial build unless the pilot requirements justify it.

### AppFlowy
https://github.com/AppFlowy-IO/AppFlowy

Potential later use: internal knowledge/workspace functionality. Not a required customer-facing dependency.

### n8n
https://github.com/n8n-io/n8n

Potential later use: optional automation and third-party integration workflows.

Before commercial use or deployment, verify the current license, edition restrictions, hosting implications, security, and whether direct API adapters would be simpler.

### Higgsfield
https://docs.higgsfield.ai/

Potential later use: image/video generation through a server-side adapter, subject to current API access, pricing, permissions, and terms.

Do not expose generation API keys in the frontend. Record generated asset metadata and usage costs.

### Open-SEO and CAP video tooling

These names may refer to multiple projects or products. Do not guess the repository or install an ambiguous package. Ask me for the exact link if the functionality becomes necessary.

## Repository adoption rule

For every proposed external repository or package:

1. Confirm the correct repository.
2. Inspect its current README, release activity, license, dependencies, and security posture.
3. Check compatibility with the selected stack and Claude Code workflow.
4. Explain its specific business or engineering value.
5. Choose the smallest useful integration.
6. Pin versions where appropriate.
7. Add documentation and tests for any adopted functionality.
8. Defer it if the benefit does not justify the complexity.

Maintain `docs/TOOLS_AND_DEPENDENCIES.md` listing adopted, evaluated, deferred, and rejected tools with rationale.

# 7. MCP SERVERS — USE SELECTIVELY AND SECURELY

MCP may help Claude Code access external documentation, GitHub, issue trackers, databases, or approved developer tools.

MCP is an optional development and integration mechanism, not a requirement to make every runtime feature depend on MCP.

### Official reference

Claude Code MCP guidance:
https://support.claude.com/en/articles/14554922-claude-code-user-faq

Google Developer Knowledge MCP:
https://developers.google.com/knowledge/mcp

### Your tasks

1. Inspect currently configured MCP servers and available tools.
2. Determine whether the existing setup is sufficient.
3. Identify only the MCP servers that materially improve development or the product.
4. Check each server's source, current setup instructions, permissions, authentication, and trustworthiness.
5. Propose additions before making changes that require credentials, broad permissions, or installation of untrusted code.
6. Preserve existing MCP configuration.
7. Never print secrets or commit tokens.
8. Verify configured servers actually work before relying on them.

Potential development-time MCP capabilities include:

- Official documentation search.
- GitHub repository and issue access.
- Approved database inspection in a local development environment.
- Browser-based verification.
- Project-specific tools.

Do not expose development MCP servers as customer-facing production tools by default.

For the product itself, prefer explicit, permission-controlled backend adapters for business integrations. Introduce a runtime MCP client only when a clear product requirement justifies the extra security, lifecycle, and operational complexity.

Do not create a large `.mcp.json` full of unverified servers. If a project-level MCP configuration is appropriate, document each server, permissions, required environment variables, and safe setup procedure.

# 8. EXTERNAL API AND INTEGRATION ROADMAP

The product must be integration-ready, but the MVP should not depend on every external platform.

Investigate the following as candidate integrations. Verify current official documentation, authentication, scopes, API limitations, review requirements, pricing, and terms before implementing any connector.

## Marketing and publishing
- Meta for Developers: https://developers.facebook.com/docs/
- LinkedIn Developers: https://learn.microsoft.com/en-us/linkedin/
- TikTok for Developers: https://developers.tiktok.com/
- Google Ads API: https://developers.google.com/google-ads/api/docs/start
- Google Analytics 4: https://developers.google.com/analytics/devguides/collection/ga4
- YouTube Data API: https://developers.google.com/youtube/v3

## Automation and operations
- n8n: https://github.com/n8n-io/n8n
- Chatwoot: https://github.com/chatwoot/chatwoot
- Paperclip: https://github.com/PaperclipAI/paperclip

## AI model providers
- Anthropic documentation: https://docs.anthropic.com/
- OpenAI API documentation: https://platform.openai.com/docs/

Use a provider-neutral interface so model selection can evolve without rewriting campaign and governance logic.

Do not assume that Claude Code's own authentication provides production API access for the SaaS application. Keep development-agent credentials separate from customer-facing application credentials.

### Connector implementation pattern

Each integration should expose a small explicit contract appropriate to its capabilities, such as:

- `get_capabilities()`
- `health_check()`
- `validate_action(action)`
- `execute_action(action, idempotency_key)`
- `verify_action(action_reference)`
- `disconnect()`

Use OAuth where appropriate, securely store credentials, minimize scopes, support disconnect/revocation, and revalidate permissions before execution.

Build a connector only after selecting a specific pilot channel and confirming the necessary access. The initial release must remain usable through manual handoff if live publishing is not feasible.

# 9. DESIGN FOR THE FULL 12-AGENT VISION

The first workflow is the launch product, not the final product.

Architect the system so it can expand into these 12 logical department roles without requiring a complete rewrite:

1. Chief Marketing Officer — strategy, business goals, budget recommendations, executive oversight.
2. Marketing Manager — campaign planning, task coordination, and workflow management.
3. Social Media Executive — channel plans, social calendars, post variants, and publishing requests.
4. PR, Influencer & Events Executive — media research, outreach drafts, influencer shortlists, and event planning.
5. Paid Ads / Digital Marketing Executive — campaign recommendations, analytics, and controlled advertising operations.
6. Brand Assets & Content Developer — copy, creative briefs, images, video assets, and brand consistency.
7. Market Intelligence & Research Analyst — market, customer, competitor, and trend research.
8. Customer Services Representative — approved customer-support drafts, knowledge retrieval, and escalation.
9. Website & E-commerce Manager — website content, product listings, merchandising, and conversion improvements.
10. Key Accounts Services Manager — account-specific plans, retailer support, and partner communications.
11. Marketing Operations Manager — workflow quality, approvals, campaign operations, and performance reporting.
12. Record Keeper & Scheduling — audit records, calendars, reminders, documentation, and workflow history.

### Future architecture requirements

Create a clear separation between:

- Agent/capability registry.
- Agent instructions and versioning.
- Input/output schemas.
- Workflow orchestration.
- Task and dependency management.
- Business context and knowledge retrieval.
- AI provider adapter.
- Tool and connector registry.
- Authorization and policy enforcement.
- Approval engine.
- Usage and budget controls.
- Audit and observability.
- User interface and reporting.

Use explicit contracts for agent inputs and outputs. Store task ownership, status, dependencies, run history, and deliverable references in the backend.

A future agent must not receive broader permissions simply because it has a new role name. Every tool call must be checked against organization permissions and the action policy.

### Expansion plan

Create `docs/12_AGENT_EXPANSION_ROADMAP.md` describing:

- How each of the 12 roles maps to capabilities.
- Which roles can share services.
- Which roles require specialized connectors or knowledge.
- Agent input/output contracts.
- Dependencies between agents.
- Human approval requirements.
- Per-agent and per-workflow budgets.
- Testing and evaluation requirements.
- Proposed rollout order.
- What should remain human-operated.
- Criteria for promoting a capability into production.

Keep this roadmap separate from the immediate MVP implementation. Do not build empty agent modules just to claim all 12 agents exist.

# 10. DATA MODEL AND BACKEND RULES

Follow the technical specification and implement the necessary domain entities, including:

- Users
- Organizations
- Memberships
- Business profiles
- Documents
- Campaigns
- Tasks and dependencies
- Workflow runs
- Agent/capability runs
- Deliverables
- Immutable deliverable versions
- Approvals
- Integrations
- External actions
- Usage records
- Audit events
- Comments
- Notifications where required

All tenant-owned records must be scoped to an organization.

Use database migrations, constraints, transactions, and validated state transitions.

Keep workflow and approval rules in backend services, not duplicated only in frontend code.

Use idempotency keys for operations where duplicate requests could create duplicate work or external side effects.

Do not allow model output to execute arbitrary SQL, shell commands, browser actions, URLs, or external requests.

Treat uploaded documents, website content, retrieved text, and third-party data as untrusted input. Protect against prompt injection and cross-tenant data exposure.

# 11. PRODUCTION-QUALITY ENGINEERING

Implement and document:

- Environment-based configuration.
- Secret management strategy.
- Input validation and safe error responses.
- Rate limits and usage limits where appropriate.
- Secure authentication and session handling.
- CSRF protection where applicable.
- Tenant-isolation tests.
- Database migrations and backup/restore considerations.
- File upload restrictions and private storage.
- Structured logging with sensitive-data redaction.
- Provider timeouts, bounded retries, and error recovery.
- External-action idempotency and reconciliation.
- Audit history.
- Usage and cost attribution.
- Health/readiness checks.
- Dependency and security review.
- Data export/deletion approach.
- Kill switch and incident procedures.
- Clear development, staging, and production configuration.

Do not label the application “production-ready” merely because it runs locally. Document any missing credentials, external reviews, compliance decisions, or deployment work.

# 12. TESTING AND VERIFICATION

Testing is part of implementation, not an optional final step.

Create and run appropriate tests for:

### Backend
- Authentication and permissions.
- Tenant isolation.
- Business profile and campaign CRUD.
- Input/output schema validation.
- Workflow state transitions.
- Workflow persistence.
- AI provider errors and timeouts.
- Usage limits and budgets.
- Deliverable versioning.
- Approval rules.
- Stale approvals.
- Audit events.
- Idempotency.
- Kill switch.
- Connector failure and ambiguous outcomes.

### Frontend
- Main navigation and page rendering.
- Form validation.
- Loading, empty, error, and success states.
- Campaign creation and review.
- Deliverable editing and version history.
- Approval flow.
- Responsive layouts.
- Keyboard accessibility.
- API failure handling.

### End-to-end
Verify the following journey:

1. A user signs in.
2. The user creates or selects an organization.
3. The user completes the business profile.
4. The user creates a campaign.
5. The workflow generates or safely reports the inability to generate deliverables.
6. The user reviews saved deliverables.
7. Editing creates a new version.
8. Approval is correctly enforced.
9. The user can export or hand off approved content.
10. The application accurately reports whether the content was handed off, published, or remains unverified.
11. Workflow status and usage remain available after restarting the application.

Run the application and use Antigravity's browser capabilities or another available browser-testing tool to inspect actual pages where possible.

Fix defects discovered during testing and rerun relevant tests. Do not claim a test passed if it was not run.

# 13. DEVELOPMENT EXECUTION RULES

Use a milestone-based implementation sequence:

- M0: runnable project foundation.
- M1: authentication, organizations, and tenant isolation.
- M2: business profile and document metadata.
- M3: campaign CRUD and brief.
- M4: persistent workflow and task state.
- M5: AI provider adapter and structured outputs.
- M6: complete campaign workflow and deliverables.
- M7: review, editing, and versioning.
- M8: approvals, budgets, audit, and kill switch.
- M9: manual handoff/export.
- M10: reporting, usage, monitoring, and operational readiness.
- M11: one live integration, only after selecting the pilot channel and verifying API access.
- M12: paid-pilot instrumentation and expansion decision.

Work in vertical slices. Keep the app runnable after each significant milestone.

Use subagents in Claude Code if they are available and materially useful. Good parallel tasks include independent UI review, security review, test review, and documentation research. Assign clear scopes, avoid concurrent edits to the same files, and integrate their findings before declaring completion.

Do not delegate core architectural decisions without reviewing the results.

Do not wait for me to approve every ordinary implementation detail. Use good engineering judgment for reversible decisions, but request confirmation before costly, destructive, security-sensitive, or externally consequential actions.

If context or time becomes constrained, finish a coherent working slice, record remaining work, and continue from the saved backlog rather than leaving the project in an undocumented half-state.

# 14. REQUIRED PROJECT DOCUMENTATION

Create or maintain:

- `README.md` — installation, configuration, startup, tests, and troubleshooting.
- `CLAUDE.md` — project instructions for future Claude Code sessions.
- `.env.example` — variable names and safe placeholder values only.
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/SECURITY_AND_GOVERNANCE.md`
- `docs/TOOLS_AND_DEPENDENCIES.md`
- `docs/12_AGENT_EXPANSION_ROADMAP.md`
- `docs/TEST_REPORT.md`
- `docs/DECISIONS.md` — material architecture and product decisions.
- `docs/DEPLOYMENT.md`

Keep the documentation synchronized with the code. Do not document features that have not been implemented as though they are already available.

# 15. DEFINITION OF DONE

The task is not complete merely because files have been created.

Before declaring completion, verify:

- The project starts using the documented instructions.
- The frontend can communicate with the backend.
- The database schema and migrations work.
- Authentication and organization scoping are enforced.
- The core campaign workflow is usable.
- Deliverables are persisted and versioned.
- Approval logic is enforced server-side.
- The first external-action path is safely controlled.
- The dashboard reflects real persisted data.
- Loading, empty, error, and success states work.
- Relevant automated tests have been run.
- Browser verification has been performed where available.
- No secrets have been committed.
- Known limitations are documented.
- The full 12-agent expansion architecture is documented without falsely claiming it is already implemented.

At the end, provide a concise but specific implementation report with:

1. Features actually completed.
2. Architecture and important decisions.
3. Files and major modules created or changed.
4. Setup and startup commands.
5. Environment variables and external credentials still needed, without revealing secrets.
6. Tests run and their actual results.
7. Browser verification completed.
8. Integrations actually connected versus merely prepared.
9. Security controls implemented and remaining risks.
10. Known bugs or incomplete requirements.
11. Recommended next milestone.
12. A clear assessment of readiness: local prototype, pilot candidate, or production deployment candidate—with reasons.

# 16. YOUR FIRST ACTION

Start now.

1. Inspect the current Antigravity workspace and repository.
2. Locate and read `marketing_department_harness_complete_specification.md` in full.
3. Check the available runtime, Git status, installed tools, Skills, and MCP configuration.
4. Create the implementation plan and project decision log.
5. Begin implementing the highest-priority working slice.
6. Run tests, start the app, inspect the UI, and fix problems.
7. Continue through the milestones without stopping at a plan or a static mockup.

**The objective is a working, tested, extensible Marketing Department Harness web portal—not merely a proposed architecture or a set of code files.**

Build the MVP carefully, preserve the human-approval model, keep the code modular and understandable, and make the future 12-agent marketing department a deliberate next stage rather than an uncontrolled first release.
