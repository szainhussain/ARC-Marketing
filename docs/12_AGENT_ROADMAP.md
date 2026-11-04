# 12-Agent Roadmap

> **Update 2026-11-04:** all 12 agents are implemented (see
> `docs/AGENT_SYSTEM.md`). What remains on this roadmap is each agent's
> *live tool/integration* (search, analytics, CRM, publishing), listed in
> `docs/INTEGRATIONS.md`. The text below is the original planning view.


This is a roadmap, not a status report — none of the 7 additional roles
below are implemented. Only the 5 roles in the pilot workflow exist today,
as plain `AgentStage` subclasses in `app/agents/`, called synchronously in
a fixed sequence from `app/workflows/campaign_workflow.py`.

**For the full per-role spec** (mission, inputs, outputs, tools,
permissions, acceptance criteria, escalation rules, usage limits, and the
overlap boundaries that keep these 12 roles from stepping on each other),
see `docs/AGENT_OPERATING_MODEL.md`. This file keeps the condensed
rollout-planning view; that file is the source of truth for role
definitions.

Role names here match the refined operating model (a few names were
sharpened from the original PRD's pilot-treatment table — e.g. "Social
Media Executive" → "Social Media & Community Manager", "Marketing
Operations Manager" was split from quality/reporting duties into two
distinct roles (11 and 12) to fix an accountability overlap the original
table had: QA/reporting is now exclusively role 12's job, not shared with
role 11's operations-execution job).

## Role → capability mapping

| # | Role | Pilot-today capability | Future capability | Hands off to |
|---|---|---|---|---|
| 1 | Chief Marketing Officer | `CMOPlannerStage` → `strategy` deliverable | Budget-envelope recommendations, executive escalation | → 2 |
| 2 | Marketing Manager | `MarketingManagerStage` → `campaign_plan` | Task coordination across branching workflows | → 3, 4, 5, 6, 9, 10 |
| 3 | Social Media & Community Manager | *(none — `content_creator`'s generic variants are the closest analog)* | Channel calendars, post variants, publish *requests* (never autonomous publish) | → human approval → 11 |
| 4 | PR, Influencer & Events Manager | *(none)* | Media research, outreach drafts, influencer shortlists, event coordination | → human approval → 11 |
| 5 | Performance Marketing Manager | *(none)* | Paid-channel recommendations; **spend changes remain human-only (Level 3) permanently, not just until this role ships** | → human (spend decisions never automate) |
| 6 | Brand, Creative & Content Studio | `ContentCreatorStage` → `content_pack` | Richer `CampaignAsset` schema (see operating model doc), image/video briefs | → 3, 4, 5, 9 |
| 7 | Market Intelligence & Research Analyst | `ResearchAnalystStage` → `research_notes` | Real web-search/retrieval tool, source citation | → 1, 4 |
| 8 | Customer Experience & Support Agent | *(none)* | Draft support responses, lead qualification, ticket classification | → human review |
| 9 | Website, SEO & E-commerce Manager | *(none)* | SEO findings, listing quality, conversion recommendations | → human approval → 11 |
| 10 | Key Accounts & Partnerships Manager | *(none)* | Account plans, partner communications | → human approval → 11 |
| 11 | Marketing Operations Manager | *(none — no connectors to operate yet)* | Routes **already-approved** work into CRM/fulfillment systems | → 12 (for reporting) |
| 12 | Reporting, Scheduling & Quality Analyst | `QualityReviewerStage` → `qa_report` (QA only; scheduling/broader reporting not built) | The sole quality gate (`validation_status`) + recurring scheduling + performance reporting | → 2 (routes fixes), 1 (strategy-level misses) |

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
   "social calendar workflow" for role #3, Social Media & Community
   Manager) needs either a second fixed
   pipeline (simplest, matches current pattern) or a real DAG executor —
   prefer the former until a role genuinely needs branching.
2. **Background queue.** Running 5+ more stages per workflow synchronously
   in the request will not scale; this must land before any role beyond
   today's 5 goes to a pilot (see `docs/DECISIONS.md` D4).
3. **Capability/permission registry per agent role.** Today, "the workflow
   decides what runs" — there's no per-org toggle for "this workspace has
   role #5 (Performance Marketing) enabled." Needed before rolling any new
   role out workspace-by-workspace rather than globally.
4. **Per-agent and per-workflow budgets**, beyond today's org-level
   monthly limit and per-call AI budget check — needed once multiple
   workflow types compete for the same monthly budget.
5. **Specialized connectors/knowledge per role** — e.g. role #7 (Research
   Analyst) needs a real web-search/retrieval tool (today's research stage
   explicitly tells the model no retrieval is connected); role #5
   (Performance Marketing) needs an ads-platform connector with Level 3
   spend controls that are explicitly *not* just "a connector with more
   scopes."

## Human approval requirements by role (future)

Every role above Level 0 (internal, reversible work — see
`docs/SECURITY_AND_GOVERNANCE.md`) needs the same approval gate the pilot
already enforces: content/action tied to an exact version, re-validated
immediately before execution. Roles #3, #4, #9, #10 produce Level 2
external-communication actions (approval required for the exact version +
destination); role #8 (Customer Experience & Support) drafts are Level 2
too — every reply to an actual customer routes through the same approval
path, even a "routine" classification. Role #5 (Performance Marketing,
paid spend) is Level 3 — disabled by default per governance rules, and "a
role exists" must never by itself grant spend authority; a future spend-
approval flow needs its own explicit, high-friction design, separate from
today's manual-handoff approval. Role #11 (Marketing Operations) is the
one exception with a narrow Level 1 execute permission, strictly limited
to already-approved record syncing — see `docs/AGENT_OPERATING_MODEL.md`
for exactly why that doesn't violate the "no agent gets execute by
default" rule.

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
2. Role #3 (Social Media & Community Manager) — closest to today's content
   pack, smallest new surface (calendar + variants), natural first "new
   agent."
3. Role #12 (Reporting, Scheduling & Quality Analyst) — expand today's QA
   stage into real scheduling and a performance-reporting surface once
   there's more than one workflow to track.
4. Role #11 (Marketing Operations) only after there's a real connector
   for it to route approved work into — it has nothing to operate until
   then.
5. Everything else, driven by actual pilot customer demand rather than
   completeness.

## What should remain human-operated indefinitely

Per the governance spec: contract acceptance, pricing negotiation,
purchases/refunds, paid-media spend changes, and any unsupported/
regulated claim. No role in this roadmap is intended to automate these —
"Performance Marketing Manager" (role #5) means *recommendations*, not
spend authority, even once built; see `docs/AGENT_OPERATING_MODEL.md` for
why its `propose` permission is a hard ceiling, not a stepping stone.
