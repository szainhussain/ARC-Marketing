# The 12-Agent Department — Operating Model

This is the detailed role design referenced by
`docs/12_AGENT_ROADMAP.md`. It defines all 12 roles with
machine-readable-shaped contracts (mission, inputs, outputs, tools,
permissions, acceptance criteria, escalation rules, usage limits), refined
to eliminate overlapping responsibility and unclear accountability.

**Update (2026-11-03):** all 12 agents now exist as code — see
`docs/AGENT_SYSTEM.md` for what is implemented and `app/agents/definitions.py`
for the source of truth. This document remains the role design they were
built from; where the two differ, the code and AGENT_SYSTEM.md win.

## Design principles (how overlap and unclear accountability are avoided)

1. **One artifact type, one producing agent.** Every deliverable type has
   exactly one agent that creates it. Other agents *consume* it as a typed
   input; they never edit another agent's deliverable directly — they
   either request changes (via the Marketing Manager) or flag an issue
   (via the Reporting/Scheduling/QA Analyst).
2. **Typed contracts, not free text.** Agents exchange structured records
   (see each role's Output schema below), the same way the existing
   pilot's `app/ai/schemas.py` validates every stage's output. A future
   agent cannot "coordinate by hoping the other agent understood a
   paragraph" — mirrors the explicit instruction in this task's brief.
3. **Permission is a property of the action, not the role name.** A new
   agent never gets broader rights because it has an impressive title —
   permission is computed the same way `authorization_service.py` already
   computes it: tenant membership + role + the action's governance Level
   (0–3, defined in `docs/SECURITY_AND_GOVERNANCE.md`). No agent below is
   ever granted Level 3 (financial/contractual/spend/regulated-claim)
   execute rights — those stay human-only regardless of role.
4. **Strategy vs. planning vs. execution are three different layers, three
   different agents.** The CMO decides *why* (positioning, priorities,
   budget envelope recommendation). The Marketing Manager decides *what,
   when, and who* (task breakdown, sequencing, specialist assignment). A
   specialist agent decides *how* (the actual draft/plan/action for its
   domain). No specialist sets its own priority or budget; no planner
   writes creative/technical content itself.
5. **Operations vs. quality are two different gates, two different
   agents.** The Marketing Operations Manager owns getting *approved*
   output into business systems (CRM, lead routing, fulfillment). The
   Reporting/Scheduling/QA Analyst owns *whether* output was good enough
   to approve in the first place, plus the audit/reporting trail. One
   moves approved work forward; the other decides what counts as
   approved-quality and tracks what happened.

## Shared conventions

### Permission vocabulary (used by every role below)

| Permission | Meaning | Governance Level (see `docs/SECURITY_AND_GOVERNANCE.md`) |
|---|---|---|
| **Read** | Query existing tenant-scoped records (profile, campaign, prior deliverables, connected analytics/CRM data). Produces no artifact. | N/A |
| **Draft** | Produce a new internal deliverable/version. Runs automatically within usage limits; labeled AI-generated/draft; no external side effect. | Level 0 |
| **Propose** | Produce a deliverable/action request explicitly intended for an external or consequential action. Always enters `awaiting_approval`; the proposing agent can never approve its own proposal. | Level 1–2 |
| **Execute** | Call a connector's `execute_action()` — **only** after a valid, version-matched `Approval` exists, re-validated immediately before the call (same pattern as `execute_manual_handoff` in `app/services/external_action_service.py`). | Level 2 only. **No role is ever granted Level 3 execute** (spend changes, contracts, pricing, purchases, regulated claims) — those remain human-only per the non-negotiable governance rules, permanently, not just "until a future version." |

### Usage limits — defaults

Unless a role's section overrides it: **max 1 model call per task attempt,
1 bounded repair retry on invalid output** (matching
`AnthropicProvider`'s existing retry policy), **timeout 60s**, **budget
$1.00 per task** (matching `AI_WORKFLOW_BUDGET_USD`'s current default —
tune per role once real cost data exists). All usage is recorded as a
`UsageRecord` tied to the originating workflow run, exactly as the 5 pilot
stages do today. Per-role overrides below exist only where a role's work
is naturally multi-call (e.g. research across several sub-questions).

### Escalation — shared rules

Every role escalates to the **Marketing Manager** for anything about
*sequencing, priority, or resourcing* it cannot resolve itself, and to the
**CMO** (via the Marketing Manager) for anything that changes strategy,
budget envelope, or brand positioning. Every role escalates to a **human
approver** (not another agent) for anything at governance Level 2+, for
any request to bypass approval or conceal activity, for suspected
account/data compromise, for an unclear regulated/legal claim, or for an
ambiguous or contradictory client-approval-rule situation (e.g. PR
outreach rules that don't cover a specific request). No agent escalates by
simply producing a lower-quality answer — it returns a `needs_input` or
`blocked` state with a specific, named reason, the same pattern
`BusinessProfile.completeness_warnings()` already uses.

### Acceptance criteria — shared baseline

Every role's output must, at minimum: validate against its schema (no
schema violation ships), distinguish user-provided facts from assumptions
from the agent's own recommendations (the existing `assumptions`/
`sources` pattern in `app/ai/schemas.py`), stay within its usage limit,
and — for anything Level 1+ — be traceable to the exact campaign/version
that justified it. Role-specific criteria are listed per role below.

---

## 01. Chief Marketing Officer (CMO)

**Mission.** Own business-aligned marketing strategy: positioning, growth
priorities, cross-channel budget *envelope* recommendations (not line-item
spend — see role 5), and executive-level decision summaries. Coordinates
the department by setting direction the Marketing Manager executes
against, and is the escalation point for anything no specialist role can
resolve.

**Inputs.** Business profile (industry, audience, differentiators, goals),
campaign objective from the brief, prior campaign outcomes (via Reporting/
QA Analyst reports), market/competitive context (via Research Analyst).

**Outputs.** `StrategyBrief`: `strategic_direction` (string), `priorities`
(ranked list), `budget_envelope_recommendation` (string, explicitly
labeled "recommendation, not authorization"), `key_objectives` (list),
`assumptions` (list), `sources` (list), `escalation_notes` (list of
decisions requiring human sign-off). *(This is today's `strategy`
deliverable type, pilot-implemented as `CMOPlannerStage` — see "Pilot
implementation status.")*

**Tools.** Read: business profile, campaign brief, prior `WorkflowRun`
summaries/reports. Draft: `StrategyBrief`. No propose/execute — the CMO
never initiates an external action directly.

**Permissions.** Read, Draft only.

**Acceptance criteria.** Strategic direction is traceable to the business
profile's stated goal and differentiators (not generic boilerplate);
budget envelope is explicitly labeled a recommendation; every claim about
market conditions not from the business profile is in `sources` or
`assumptions`.

**Escalation rules.** Escalates to a human for: budget envelope exceeding
the organization's configured plan tier, any positioning claim touching a
regulated category (health, financial, safety), and any conflict between
the campaign brief's stated objective and the business profile's
constraints.

**Usage limits.** 1 call, default budget/timeout.

**Overlap boundary.** Does **not** write the campaign plan, task
breakdown, or creative content — that's roles 2 and 6. Does **not**
recommend tactical paid-channel bids — that's role 5's budget envelope is
*set by* the CMO, *spent within* by Performance Marketing.

---

## 02. Marketing Manager

**Mission.** Execution orchestrator. Converts the CMO's `StrategyBrief`
and the campaign brief into a structured campaign plan: workstreams,
tasks, dependencies, deadlines, and which specialist role each task is
assigned to. Monitors progress and is the single point of task routing —
no other role assigns work to another role.

**Inputs.** `StrategyBrief` (role 1), campaign brief fields (channels,
dates, success metrics), active `Task`/`WorkflowRun` state.

**Outputs.** `CampaignPlan`: `summary` (string), `channels` (list),
`timeline` (list of `{week, focus, owning_role}`), `success_metrics`
(list), `task_assignments` (list of `{role, task_type, depends_on}`),
`assumptions` (list). *(Today's `campaign_plan` deliverable type, pilot-
implemented as `MarketingManagerStage`.)*

**Tools.** Read: `StrategyBrief`, campaign, task/run state, all specialist
deliverables for the campaign (to check status, not to edit them). Draft:
`CampaignPlan`, task-assignment updates.

**Permissions.** Read, Draft. (Task assignment/sequencing is a Level 0
internal action — no approval needed to *plan* work; approval is needed
later, per-role, for anything that leaves the workspace.)

**Acceptance criteria.** Every task in the plan has a named owning role
from this 12-role list (no "someone will figure this out" tasks);
dependencies form a valid DAG (no cycles); the plan references the
`StrategyBrief`'s `key_objectives`, not an independently invented goal.

**Escalation rules.** Escalates to the CMO if the campaign brief's
objective doesn't fit any current strategic priority. Escalates to a human
if a deadline is infeasible given the monthly workflow/usage limit
(`check_monthly_workflow_limit`).

**Usage limits.** 1 call, default budget/timeout.

**Overlap boundary.** Does **not** set strategy (role 1) or produce
specialist content itself (roles 3, 4, 5, 6, 8, 9, 10). Does **not** push
approved output into CRM/fulfillment systems — that's role 11's job once
something is approved; the Marketing Manager's job ends at "this task is
assigned and sequenced."

---

## 03. Social Media & Community Manager

**Mission.** Own channel strategy, content calendars, publishing
schedules, community engagement/sentiment monitoring, and social
performance reporting — for social channels specifically. Adapts creative
assets from role 6 into platform-specific posts; does not originate core
creative assets itself.

**Inputs.** `CampaignPlan` (role 2), creative assets from the `ContentPack`
(role 6), prior social performance data (via role 12's reports), current
community sentiment signals (if a connected social listening source
exists — none is connected in the current build).

**Outputs.** `SocialCalendar`: `channel` (enum: instagram/linkedin/x/
tiktok/facebook/...), `calendar_entries` (list of `{date, asset_ref,
caption, hashtags, cta}`), `community_response_drafts` (list of `{thread_ref,
draft_reply, sentiment}`), `publish_requests` (list — each one an
*action request*, not a publish itself). *(Not yet pilot-implemented;
closest existing analog is the generic `variants` field inside today's
`content_pack` — a dedicated `SocialCalendar` schema is the concrete next
step per the roadmap's proposed rollout order.)*

**Tools.** Read: `CampaignPlan`, `ContentPack`, connected social-platform
read APIs (none connected today). Draft: calendar entries, community-reply
drafts. Propose: `publish_requests` (Level 2 — publishing is an external
communication action).

**Permissions.** Read, Draft, Propose. **Never Execute** directly — actual
posting requires an approved `Approval` + a connected publishing connector
(none exists in this build; see `docs/DECISIONS.md` D5), executed the same
re-validated way `execute_manual_handoff` works today.

**Acceptance criteria.** Every calendar entry references a real asset from
the `ContentPack` (no fabricated creative); every `publish_request`
carries the exact content version + destination + schedule, per the
approval-payload-hash pattern already enforced by `Approval`.

**Escalation rules.** Escalates to role 6 if no suitable creative asset
exists for a planned slot (does not invent one itself). Escalates to a
human for any community reply touching a complaint, legal threat, or
safety concern — never auto-replies to those categories even in draft
form without flagging it explicitly.

**Usage limits.** 1 call per calendar batch; community-reply drafting is
per-thread, budgeted separately and capped at a configurable max threads/
task (default 10) to bound cost on a busy day.

**Overlap boundary.** Does **not** produce the underlying creative asset
(role 6's job) and does **not** run paid social campaigns (role 5's job,
even though it's the same platform) — organic calendar/community work
only.

---

## 04. PR, Influencer & Events Manager

**Mission.** Identify media opportunities, research and shortlist
influencers, prepare outreach drafts, manage the collaboration pipeline,
and coordinate event logistics. All outreach and commitments follow
client-approved rules configured per organization — never improvised.

**Inputs.** `StrategyBrief` (role 1), business profile (audience,
differentiators), research notes (role 7), organization's configured
outreach rules/constraints (part of `business_profile.constraints`
today; a dedicated `outreach_policy` field is a reasonable future
addition).

**Outputs.** `OutreachPlan`: `media_targets` (list of `{name, relevance,
contact_status}`), `influencer_shortlist` (list of `{name/handle,
audience_fit, estimated_reach, assumptions}`), `outreach_drafts` (list of
`{target, channel, draft_message, requires_approval: true}`),
`event_plan` (optional, `{event, logistics_checklist, owner}`).

**Tools.** Read: business profile, research notes, outreach policy. Draft:
shortlists, event checklists. Propose: `outreach_drafts` (Level 2 —
external communication to a named third party).

**Permissions.** Read, Draft, Propose. No Execute — sending outreach is
always a human-confirmed action in this build (no email/CRM connector
exists yet).

**Acceptance criteria.** Every influencer/media target entry labels
estimated reach/relevance as an estimate, not a verified fact, unless a
real data source backs it (`sources` populated); no outreach draft is
generated for a target type excluded by the org's configured outreach
rules.

**Escalation rules.** Escalates to a human for: any outreach implying a
paid partnership or compensation (Level 3 — financial commitment), any
influencer with unverifiable or conflicting audience data, any event
requiring a venue/vendor contract.

**Usage limits.** 1 call for the shortlist/plan; outreach drafts capped at
a configurable max per batch (default 15) to avoid runaway draft
generation.

**Overlap boundary.** Does **not** manage paid social or paid media (role
5). Does **not** write general campaign creative (role 6) — its outreach
drafts are personalized correspondence, a distinct content type.

---

## 05. Performance Marketing Manager

**Mission.** Plan and optimize paid search, paid social, retargeting, and
full-funnel paid campaigns. Recommends bidding strategy, targeting, and
acquisition-cost targets, and may adjust spend **only within an
already-approved budget envelope and only up to configured limits** —
never authorizes new spend itself.

**Inputs.** `StrategyBrief`'s budget envelope recommendation (role 1,
*recommendation*, not authorization), `CampaignPlan` channels (role 2),
`ContentPack` ad-ready variants (role 6), connected ad-platform
performance data (none connected in this build).

**Outputs.** `PaidMediaPlan`: `channels` (list), `targeting` (object),
`bid_strategy_recommendation` (string), `budget_allocation_recommendation`
(list of `{channel, amount, rationale}` — explicitly a recommendation),
`acquisition_cost_targets` (object), `spend_change_requests` (list — each
one a Level 3 request, always routed to a human, never auto-applied).

**Tools.** Read: budget envelope, campaign plan, ad-ready creative,
connected ad-platform read-only reporting (none connected today). Draft:
plan and targeting recommendations. Propose: `spend_change_requests` —
explicitly Level 3, meaning propose is as far as this role (or any role)
ever goes; execution of an actual spend change requires a human acting
directly in the ad platform or through a future, separately designed and
reviewed high-friction spend-approval flow (not built, not planned as a
simple "add execute permission" change — see
`docs/SECURITY_AND_GOVERNANCE.md` Level 3 rules).

**Permissions.** Read, Draft, Propose. **Never Execute, ever, for spend
changes** — this is the one place in the whole operating model where
"propose" is a hard ceiling, not a stepping stone to a future "execute."

**Acceptance criteria.** Every budget number traces to the CMO's envelope
recommendation (never exceeds it without an explicit escalation); every
acquisition-cost target states its basis (historical data vs. estimate).

**Escalation rules.** Escalates to the CMO/human for: any recommendation
exceeding the budget envelope, any new channel not in the approved plan,
any bid strategy requiring platform-level account changes.

**Usage limits.** 1 call, default budget/timeout. Recommendation-only
scope keeps this cheap regardless of campaign size.

**Overlap boundary.** Does **not** touch organic social (role 3) or PR/
influencer spend (role 4 — sponsorship payment, if ever built, would still
route through this role's Level 3 ceiling, not role 4's). Budget
envelope-setting is role 1's; this role only recommends *within* it.

---

## 06. Brand, Creative & Content Studio

**Mission.** Produce brand-compliant creative: copy, graphics concepts,
campaign concepts, product imagery briefs, video briefs, landing-page
assets, and creative variations across channels. The single source of
creative assets other roles (3, 4, 5, 9) adapt but never originate.

**Inputs.** `CampaignPlan` (role 2), business profile's brand fields
(`tone_of_voice`, `preferred_phrases`, `prohibited_phrases`), channel list.

**Outputs.** `CampaignAsset` (the user's own example, adopted directly as
this role's canonical output shape): `channel` (string), `target_audience`
(string), `copy` (string), `creative_direction` (string), `cta` (string),
`supporting_claims` (list, each tagged `verified` | `assumption` |
`user_provided`), `validation_status` (enum: `draft` | `qa_passed` |
`qa_failed`, set by role 12, **not** by this role itself — see Overlap
boundary). A full creative deliverable is a `ContentPack`: `creative_brief`
(string) + `variants` (list of `CampaignAsset`) + `calendar_notes`
(string). *(Today's `content_pack` deliverable type, pilot-implemented as
`ContentCreatorStage` — extend its schema with the richer `CampaignAsset`
shape above as a concrete next step.)*

**Tools.** Read: campaign plan, brand profile. Draft: `ContentPack` /
`CampaignAsset` list.

**Permissions.** Read, Draft only. Creative drafting is always Level 0 —
no external effect until role 3/4/5/9 packages it into a `propose`-level
action and it's approved.

**Acceptance criteria.** No `prohibited_phrases` appear in any copy; every
`supporting_claims` entry is tagged; `validation_status` starts `draft`
and is never self-set to `qa_passed` (role 12 owns that transition, per
the Marketing Manager checking it against the brief, exactly as the task
brief's own example describes).

**Escalation rules.** Escalates to the Marketing Manager if the campaign
plan doesn't specify enough detail to produce a channel-appropriate asset
(a `needs_input` state, not an invented assumption about e.g. target
audience).

**Usage limits.** 1 call per asset batch; default budget/timeout.

**Overlap boundary.** Does **not** schedule, publish, or decide channel
mix (roles 3/5). Does **not** grade its own work — `validation_status` is
set by role 12 checking against the brief, exactly matching the brief's
own stated example.

---

## 07. Market Intelligence & Research Analyst

**Mission.** Research customers, competitors, pricing, category dynamics,
demand signals, and growth opportunities. Rigorously separates verified
facts from estimates — the one role whose entire output is organized
around that distinction.

**Inputs.** Business profile (industry, differentiators, geography),
campaign objective, any connected research/retrieval tool (none connected
in this build — see Overlap boundary).

**Outputs.** `ResearchNotes`: `audience_hypotheses` (list),
`competitor_notes` (list), `assumptions` (list), `sources` (list),
`scope_note` (string — states exactly what was and wasn't researched,
e.g. "based on user-provided context only; no external retrieval tool
connected"). *(Today's `research_notes` deliverable type, pilot-
implemented as `ResearchAnalystStage`.)*

**Tools.** Read: business profile, campaign, prior research for the
organization. Draft: `ResearchNotes`. A future external web-search/
retrieval tool would be added here as an explicit, allowlisted tool call —
never an open-ended browsing capability — per
`docs/SECURITY_AND_GOVERNANCE.md`'s prompt-injection rules (retrieved
content is data, never instructions).

**Permissions.** Read, Draft only.

**Acceptance criteria.** Every claim not directly from the business
profile is in `sources` (with a real citation, once a retrieval tool
exists) or `assumptions` (clearly labeled as such); `scope_note` never
implies research happened that didn't.

**Escalation rules.** Escalates (returns a clarification state) if the
campaign objective requires market data clearly outside what the business
profile + any connected tool can support — does not fabricate a citation
to fill the gap, per the spec's explicit "do not fabricate citations"
rule.

**Usage limits.** 1–3 calls (one per sub-question, e.g. audience +
competitor + pricing, if split that way in a future implementation);
default per-call budget/timeout.

**Overlap boundary.** Feeds the CMO (role 1) and PR/Influencer role (role
4) — does not itself write strategy or outreach drafts.

---

## 08. Customer Experience & Support Agent

**Mission.** Handle routine customer inquiries, knowledge-base responses,
lead qualification, and ticket classification across connected channels,
always routing anything outside its competence to a human.

**Inputs.** Incoming inquiry/ticket text (untrusted input — treated as
data per `docs/SECURITY_AND_GOVERNANCE.md`'s prompt-injection rules, never
as instructions), business profile (products/services, tone of voice),
organization's knowledge base (not modeled yet — see Overlap boundary).

**Outputs.** `SupportDraft`: `ticket_classification` (enum: `routine` |
`needs_human` | `escalation`), `suggested_response` (string, only
populated for `routine`), `lead_qualification` (optional object, if the
inquiry is sales-adjacent), `confidence` (float). *(Not pilot-implemented.
Per `docs/DECISIONS.md`'s Chatwoot evaluation: build this as one
`SupportDraft`-shaped table + a review screen, not a separate helpdesk
service, as the concrete next step.)*

**Tools.** Read: business profile, prior tickets for the same customer
(tenant-scoped). Draft: `SupportDraft`.

**Permissions.** Read, Draft only. A `routine`-classified draft is still a
draft — sending any reply to an actual customer is Level 2 (external
communication) and requires the same propose→approve→execute path as
everything else, even for a "routine" question, until false-positive rates
are measured in a real pilot.

**Acceptance criteria.** Every `needs_human`/`escalation` classification
includes a specific reason (not a bare label); `suggested_response` never
references account-specific data not present in the ticket + tenant-
scoped records (no cross-tenant leakage risk, same rule as everywhere
else in this codebase).

**Escalation rules.** Escalates to a human immediately for: anything
implying a refund/compensation (Level 3), legal/safety language, an angry
or threatening tone, or any request for data this org doesn't have
authorization to share.

**Usage limits.** 1 call per ticket, default budget/timeout — kept cheap
since volume could be high.

**Overlap boundary.** Does **not** own the knowledge base itself (a future
content-management concern, not this role's). Does **not** replace human
support — it drafts; a human (or, later, a narrowly-scoped auto-send rule
for a validated low-risk category) decides whether to send.

---

## 09. Website, SEO & E-commerce Manager

**Mission.** Own website content optimization, technical and on-page SEO,
product listing quality, conversion improvements, catalog quality, and
online-store performance recommendations.

**Inputs.** Business profile (website, products/services), `ContentPack`
assets adaptable for web/landing pages (role 6), connected site/analytics
data (none connected in this build), connected e-commerce catalog data
(none connected).

**Outputs.** `SiteOptimizationPlan`: `seo_findings` (list of `{page,
issue, recommendation, severity}`), `listing_quality_notes` (list, if
e-commerce catalog is connected), `conversion_recommendations` (list),
`assumptions` (list — e.g. "no analytics connector; recommendations based
on general best practice, not this site's actual traffic data").

**Tools.** Read: business profile, `ContentPack`, connected site/catalog
data (none today). Draft: `SiteOptimizationPlan`.

**Permissions.** Read, Draft only. Any actual website/listing change is
Level 1–2 depending on visibility (an internal draft recommendation is
Level 0; actually publishing a change to a live site or storefront is
Level 2, same pattern as role 3's publish requests) and would need a
dedicated connector not built in this session.

**Acceptance criteria.** Every recommendation states whether it's backed
by connected data or general best practice (the `assumptions` field is
not optional here — this role's single biggest honesty risk is implying
site-specific analysis without a connected analytics source).

**Escalation rules.** Escalates to role 6 if a recommendation requires new
creative assets it can't produce itself (e.g. a redesigned landing-page
hero) rather than attempting creative work outside its mission.

**Usage limits.** 1 call, default budget/timeout.

**Overlap boundary.** Does **not** produce the creative assets it
recommends (role 6's job) and does **not** run paid search (role 5's
job, even though SEO and SEM are adjacent disciplines) — organic/owned
website and catalog quality only.

---

## 10. Key Accounts & Partnerships Manager

**Mission.** Monitor account performance, retail/distribution
opportunities, trade promotions, partner pipelines, listings, and
account-level growth for named key accounts/partners (distinct from the
general-audience campaign work every other role does).

**Inputs.** Business profile, connected account/partner data (none
connected in this build), `CampaignPlan` (role 2) for any account-specific
campaign tie-ins.

**Outputs.** `AccountPlan`: `account` (string), `performance_summary`
(object, only populated if connected data exists), `opportunities` (list
of `{type, description, estimated_value, assumptions}`), `partner_
communications_drafts` (list, Level 2 — same propose pattern as role 4's
outreach).

**Tools.** Read: business profile, connected account/CRM data (none
connected today). Draft: account plans. Propose: partner communications.

**Permissions.** Read, Draft, Propose. No Execute — same reasoning as
roles 3 and 4: sending anything to a named external partner is always
human-confirmed in this build.

**Acceptance criteria.** `estimated_value` always labeled as an estimate
unless backed by connected account data; no partner communication draft
implies a commitment (pricing, exclusivity, terms) without flagging it as
Level 3 and routing to a human.

**Escalation rules.** Escalates to a human for anything implying a trade
term, discount, or contractual commitment to a partner (Level 3).

**Usage limits.** 1 call, default budget/timeout.

**Overlap boundary.** Account-specific work only — general-audience
campaign work stays with roles 2/3/5/6. Does **not** manage general PR/
influencer relationships (role 4) — those are media/creator relationships,
not retail/distribution partners.

---

## 11. Marketing Operations Manager

**Mission.** Coordinate *approved* campaign operations into business
systems: lead routing, CRM data updates, marketing-to-sales handoffs, and
e-commerce/fulfillment integration touchpoints. Owns the "plumbing" that
moves already-approved work forward — never originates campaign content
or decides what counts as quality (that's role 12).

**Inputs.** Approved `Deliverable`/`ExternalAction` records (only ever
acts on things already at `approved`/`succeeded` status), connected CRM/
fulfillment systems (none connected in this build).

**Outputs.** `OperationsLog`: `action` (enum: `lead_routed` |
`crm_updated` | `handoff_sent` | `fulfillment_synced`), `source_record`
(reference to the approved deliverable/action that triggered it),
`destination_system` (string), `status` (enum matching `ExternalAction`'s
own status vocabulary). This role's outputs are operational records, not
creative/strategic deliverables — they're closer in shape to `AuditEvent`
than to a `DeliverableVersion`.

**Tools.** Read: approved deliverables/actions. Draft: internal routing-
rule proposals. Execute: only for pre-approved, pre-configured, low-risk
internal operations (e.g. syncing an already-approved lead into the CRM)
— never for anything that itself requires a fresh approval; if the
operation is new or ambiguous, it's Level 2 and routes through the normal
approval path like everything else, not through this role's Execute
shortcut.

**Permissions.** Read, Draft, and a narrowly-scoped Execute limited to
already-approved, pre-configured internal-system syncs (Level 1 — "low-
impact internal changes" in `docs/SECURITY_AND_GOVERNANCE.md`'s risk
levels, explicitly *not* Level 2 external communication, which this role
never originates).

**Acceptance criteria.** Every `OperationsLog` entry references a real,
already-approved `source_record` — this role is **structurally incapable**
of acting on anything unapproved, since its only inputs are
already-approved records.

**Escalation rules.** Escalates to a human if a destination system
integration fails or returns an ambiguous result (the same
`verification_required` pattern `ExternalAction` already uses) — never
silently retries a non-idempotent sync.

**Usage limits.** Operational, not generative — no meaningful AI token
cost; rate-limited by the connected systems' own limits once they exist.

**Overlap boundary.** Does **not** decide what's approved (roles 1–10 +
human approvers do) and does **not** evaluate quality (role 12). Moves
already-decided things forward; makes no content or quality decisions
itself.

---

## 12. Reporting, Scheduling & Quality Analyst

**Mission.** The department's quality gate and record-keeper: schedules
recurring tasks, maintains reports and the audit trail, evaluates every
deliverable's quality against its originating brief (absorbing what the
pilot's `QualityReviewerStage` does today), checks KPI performance, and
identifies process improvements. The **only** role permitted to set a
`CampaignAsset`'s `validation_status`.

**Inputs.** Every deliverable produced by every other role for a campaign,
the originating `CampaignPlan`/brief, `AuditEvent` history, `UsageRecord`
history.

**Outputs.** `QAReport`: `passed` (bool), `issues` (list), `checked`
(list of what was verified — schema validity, completeness, brand-
constraint compliance, consistency with the brief, unsupported-claim
check), each entry in `issues` tagged with the specific deliverable/field
it refers to. Also: `ScheduleEntry` (recurring task definitions) and
`PerformanceReport` (KPI-vs-target summary, reusing the existing
`report_service.py` pattern — `cost_basis`/estimate labeling rules apply
here too). *(Today's `qa_report` deliverable type, pilot-implemented as
`QualityReviewerStage` — the scheduling and broader reporting surface is
new scope beyond the pilot stage's current reach.)*

**Tools.** Read: everything (this is the one role with cross-cutting read
access to all other roles' outputs for a campaign, by design — it's the
check on everyone else). Draft: `QAReport`, `ScheduleEntry`,
`PerformanceReport`.

**Permissions.** Read, Draft only. Quality evaluation and reporting are
inherently Level 0 — this role never takes an external action, only
produces the judgment that *gates* whether another role's proposed action
should proceed to approval.

**Acceptance criteria.** Every `issues` entry is specific enough to act on
(references a field, not "content could be better"); `passed: true` only
when every item in `checked` actually passed — this role's own output is
itself subject to the same "no fabricated success" rule as everything
else in this product's governance model.

**Escalation rules.** Escalates to the Marketing Manager when a
deliverable fails QA repeatedly (same task, bounded retry count
exceeded) rather than looping indefinitely. Escalates to a human for any
KPI miss severe enough to suggest the campaign strategy itself (role 1)
needs revisiting, not just a tactical fix.

**Usage limits.** 1 call per QA pass, default budget/timeout. Scheduling/
reporting functions are largely non-generative (querying persisted data),
so most of this role's work costs no AI tokens at all.

**Overlap boundary.** Does **not** fix the content it finds issues with —
it reports the issue; the originating role (or the Marketing Manager,
routing a revision task) fixes it. Does **not** move approved work into
business systems (role 11's job) — purely evaluative and record-keeping.

---

## Cross-agent handoff map

| Produces | Artifact | Consumed by |
|---|---|---|
| 01 CMO | `StrategyBrief` | 02 Marketing Manager |
| 02 Marketing Manager | `CampaignPlan` (+ task assignments) | 03, 04, 05, 06, 09, 10 |
| 06 Brand/Creative/Content Studio | `ContentPack` (`CampaignAsset` list) | 03, 04 (as needed), 05, 09 |
| 07 Research Analyst | `ResearchNotes` | 01, 04 |
| 03/04/05/08/10 | `*_request` / `*_drafts` (propose-level) | Human approver, then 11 (post-approval) |
| 11 Marketing Operations | `OperationsLog` | 12 (for reporting), human (for failures) |
| 12 Reporting/Scheduling/QA | `QAReport`, `PerformanceReport` | 02 (routes fixes), 01 (strategy-level misses), human |

No other handoff paths exist. If a future change seems to need one (e.g.
role 9 wanting to directly command role 6), route it through the Marketing
Manager (role 2) instead — that keeps task routing single-owner, per
design principle 1.

## Pilot implementation status

| Role | Status | Code |
|---|---|---|
| 01 CMO | Pilot-implemented (strategy only; budget-envelope field not yet in schema) | `app/agents/cmo_planner.py` |
| 02 Marketing Manager | Pilot-implemented | `app/agents/marketing_manager.py` |
| 03 Social Media & Community | Not implemented | — |
| 04 PR/Influencer/Events | Not implemented | — |
| 05 Performance Marketing | Not implemented | — |
| 06 Brand/Creative/Content Studio | Pilot-implemented (simpler schema than `CampaignAsset` above) | `app/agents/content_creator.py` |
| 07 Research Analyst | Pilot-implemented | `app/agents/research_analyst.py` |
| 08 Customer Experience & Support | Not implemented | — |
| 09 Website/SEO/E-commerce | Not implemented | — |
| 10 Key Accounts & Partnerships | Not implemented | — |
| 11 Marketing Operations | Not implemented (no connectors to operate exist yet) | — |
| 12 Reporting/Scheduling/QA | Partially implemented (QA only; scheduling/broader reporting not built) | `app/agents/quality_reviewer.py` |

Per `docs/12_AGENT_ROADMAP.md`'s proposed rollout order: role 07
gets a real retrieval tool next, then role 03 (closest to today's content
pipeline), then role 12 expands into real scheduling/reporting. Building a
new role means: one schema in `app/ai/schemas.py`, one `AgentStage`
subclass in `app/agents/`, one line in `campaign_workflow.py`'s `PIPELINE`
(or a second named pipeline, once workflows diverge — see roadmap item 1),
and tests following `tests/integration/test_workflow_success_path.py`'s
fake-provider pattern. Do not mark a role "implemented" without that test,
per `.claude/skills/release-checklist/SKILL.md`.
