# 12-Agent Expansion Roadmap

This is a roadmap, not a status report — none of the 11 additional roles
below are implemented. Only the 5 roles in the pilot workflow (CMO/
planner, research analyst, marketing manager, content creator, quality
reviewer — mapped from the PRD's pilot treatment table) exist today, as
plain `AgentStage` subclasses in `app/agents/`, called synchronously in a
fixed sequence from `app/workflows/campaign_workflow.py`.

## Role → capability mapping

| # | Role | Pilot-today capability | Future capability | Shares services with |
|---|---|---|---|---|
| 1 | CMO | `CMOPlannerStage` → `strategy` deliverable | Budget recommendations, executive oversight dashboard | Marketing Manager (shares campaign context) |
| 2 | Marketing Manager | `MarketingManagerStage` → `campaign_plan` | Task coordination across branching workflows | CMO, Marketing Ops |
| 3 | Social Media Executive | *(none — content_creator produces generic channel variants)* | Channel-specific calendars, post variants, publish *requests* (never autonomous publish) | Content Creator, future Connector registry |
| 4 | PR/Influencer/Events Executive | *(none)* | Media research, outreach drafts, influencer shortlists | Research Analyst |
| 5 | Paid Ads/Digital Marketing Executive | *(none)* | Recommendations + analytics; **spend changes remain human-only (Level 3 action, see governance doc) even after this role ships** | Marketing Manager, future Connector registry |
| 6 | Brand Assets & Content Developer | `ContentCreatorStage` → `content_pack` | Image/video asset generation (e.g. a Higgsfield adapter, server-side only) | — |
| 7 | Market Intelligence & Research Analyst | `ResearchAnalystStage` → `research_notes` | Real web-search/retrieval tool, source citation | CMO |
| 8 | Customer Services Representative | *(none)* | Approved support drafts, knowledge retrieval, escalation | Record Keeper |
| 9 | Website & E-commerce Manager | *(none)* | Website content, product listings, conversion suggestions | Content Developer |
| 10 | Key Accounts Services Manager | *(none)* | Account-specific plans, partner communications | Marketing Manager |
| 11 | Marketing Operations Manager | `QualityReviewerStage` → `qa_report`, plus the approval/governance engine itself | Full QA/governance dashboard, performance reporting | All roles (shared QA gate) |
| 12 | Record Keeper & Scheduling | `audit_service`, `AuditEvent` (shared infrastructure, not a distinct agent) | Calendars, reminders, formal record retention policy | All roles |

## What's already shaped to support expansion (no rewrite needed)

- **Agent/capability registry**: `PIPELINE` list in `campaign_workflow.py`
  is currently a fixed Python list; replacing it with a DB-backed registry
  of `(stage_name, task_type, schema, enabled_for_org)` rows is additive,
  not a rewrite — `AgentStage.run()` already takes a provider and context
  generically.
- **Input/output schemas**: `app/ai/schemas.py` already separates each
  stage's schema from its agent class; adding a new role means adding one
  schema + one `AgentStage` subclass.
- **AI provider adapter**: provider-neutral by design (`app/ai/base.py`);
  adding OpenAI or another provider means one new class in
  `provider_adapter.py`, no change to any agent or workflow code.
- **Connector registry**: `app/integrations/base.py:Connector` is already
  a generic contract; adding a live connector means one new class
  implementing it, registered the way `ManualHandoffConnector` is today.
- **Authorization and policy enforcement**: `authorization_service.py` and
  `Membership` roles are not tied to any specific agent — a new role
  acting on behalf of a workspace still goes through the same
  `get_membership_or_403` + role check.

## What genuinely needs new work before more roles ship

1. **Real task graph with branching/dependencies.** Today's `Task` model
   has the fields for dependency tracking but the workflow only ever
   creates a fixed 5-step linear sequence. A second workflow type (e.g.
   "social calendar workflow" for role #3) needs either a second fixed
   pipeline (simplest, matches current pattern) or a real DAG executor —
   prefer the former until a role genuinely needs branching.
2. **Background queue.** Running 5+ more stages per workflow synchronously
   in the request will not scale; this must land before any role beyond
   today's 5 goes to a pilot (see `docs/DECISIONS.md` D4).
3. **Capability/permission registry per agent role.** Today, "the workflow
   decides what runs" — there's no per-org toggle for "this workspace has
   role #5 (Paid Ads) enabled." Needed before rolling any new role out
   workspace-by-workspace rather than globally.
4. **Per-agent and per-workflow budgets**, beyond today's org-level
   monthly limit and per-call AI budget check — needed once multiple
   workflow types compete for the same monthly budget.
5. **Specialized connectors/knowledge per role** — e.g. role #7 needs a
   real web-search/retrieval tool (today's research stage explicitly tells
   the model no retrieval is connected); role #5 needs an ads-platform
   connector with Level 3 spend controls that are explicitly *not* just
   "a connector with more scopes."

## Human approval requirements by role (future)

Every role above Level 0 (internal, reversible work — see
`docs/SECURITY_AND_GOVERNANCE.md`) needs the same approval gate the pilot
already enforces: content/action tied to an exact version, re-validated
immediately before execution. Roles #3, #4, #8, #9, #10 produce Level 2
external-communication actions (approval required for the exact version +
destination). Role #5 (paid spend) is Level 3 — disabled by default per
governance rules, and "a role exists" must never by itself grant spend
authority; a future spend-approval flow needs its own explicit,
high-friction design, separate from today's manual-handoff approval.

## Testing and evaluation requirements for promoting a new role to production

A new role should not go to pilot customers until it has: a schema-
validated output contract (like today's 5 stages), a unit test with a fake
provider exercising the success path (like
`tests/integration/test_workflow_success_path.py`), a tenant-isolation
test if it introduces new tenant-scoped data, and — if it produces a
Level 2+ action — an approval-lifecycle test modeled on
`tests/integration/test_deliverable_approval_handoff.py`.

## Proposed rollout order

1. Role #7 (Research Analyst) gets a real retrieval tool — highest
   leverage, since it currently explicitly tells the model research is
   unavailable.
2. Role #3 (Social Media Executive) — closest to today's content pack,
   smallest new surface (calendar + variants), natural first "new agent."
3. Role #11 (Marketing Operations) — expand today's QA stage into a real
   operations dashboard once there's more than one workflow to operate.
4. Everything else, driven by actual pilot customer demand rather than
   completeness.

## What should remain human-operated indefinitely

Per the governance spec: contract acceptance, pricing negotiation,
purchases/refunds, paid-media spend changes, and any unsupported/
regulated claim. No role in this roadmap is intended to automate these —
"Paid Ads Executive" (role #5) means *recommendations*, not spend
authority, even once built.
