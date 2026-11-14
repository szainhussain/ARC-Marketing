# Architecture and Product Decisions

Material decisions made during this build, with rationale. Append new
entries rather than editing old ones, unless a decision is reversed (then
note the reversal and why).

## D1 — Modular Flask monolith, not microservices or an agent framework

**Decision:** One Flask app, domain logic in `app/services/`, AI stages as
plain classes in `app/agents/`, no LangChain/CrewAI/AutoGen-style agent
framework, no separate services.

**Why:** The spec explicitly asks for this ("avoid unnecessary agent
frameworks"; "do not add complex orchestration frameworks... merely because
they are fashionable"). The actual workflow is 5 sequential, bounded AI
calls with explicit input/output contracts — an agent framework would add
indirection without solving a problem this project has.

## D2 — SQLite for local dev/test, PostgreSQL via Docker/production

**Decision:** `requirements-dev.txt` excludes `psycopg2-binary`;
local dev and the test suite default to SQLite. `requirements.txt` (used by
the Dockerfile, pinned to `python:3.12-slim`) includes `psycopg2-binary` for
PostgreSQL.

**Why:** The host machine in this session runs Python 3.14.7, for which
`psycopg2-binary` 2.9.10 has no prebuilt wheel and fails to build from
source (`pg_config` not found). Rather than down-pin the host Python or
require PostgreSQL + build tools just to run `pytest`, SQLite is good
enough for local development per the spec's own allowance ("SQLite only
for local quick-start if needed"). Verified: the Docker image (Python 3.12)
installs `psycopg2-binary` cleanly from a prebuilt wheel — see
`docs/TEST_REPORT.md`.

## D3 — Session-cookie auth, not JWT

**Decision:** Flask-Login session cookies (`SameSite=Lax`, `HttpOnly`) +
Flask-WTF CSRF via a `/auth/csrf-token` endpoint and `X-CSRFToken` header,
not JWT access tokens.

**Why:** Single first-party SPA, no third-party API consumers yet, no SSO
requirement yet. Session cookies are simpler to get right (no token
refresh/rotation logic to build) and the spec allows it ("secure cookie
sessions for browser app where appropriate"). Revisit if/when a mobile app
or third-party API consumer appears.

**Consequence discovered during browser testing:** the frontend's
`VITE_API_BASE_URL` and the backend's `FRONTEND_ORIGIN` must share the same
hostname (`localhost` vs `127.0.0.1` count as different sites for
`SameSite` purposes, even on the same machine with CORS correctly
configured). Documented in `README.md` and `CLAUDE.md`; cost real debugging
time in this session (see `docs/TEST_REPORT.md`).

## D4 — Synchronous workflow execution, no queue yet

> **Superseded by D11 (2026-11-03).** Kept for history.

**Decision:** `start_campaign_workflow` runs all 5 pipeline stages inline
in the request/response cycle of `POST .../runs` (returns `202` once
started, but the work has actually already completed or failed by the time
the response is sent in this implementation — see note below).

**Why:** The spec explicitly allows this for the prototype ("begin
synchronous local workflow for prototype; move long runs to a queue before
pilot"). Adding Celery/RQ + Redis now would be infrastructure the single-
pipeline MVP doesn't need yet.

**Known gap:** because execution is synchronous, `POST .../runs` blocks
for the duration of all 5 AI calls (or fails fast if no provider is
configured). This is acceptable for one user testing one campaign at a
time; it will not scale to concurrent pilot users and must move to a
background queue before M12. The `202 Accepted` status code is technically
inaccurate for a synchronous implementation (chosen to keep the API
contract queue-ready without a breaking change later) — documented here so
nobody mistakes it for "already async."

## D5 — Manual handoff only; no live publishing connector

**Decision:** The only `Connector` implementation is
`ManualHandoffConnector`. `Integration` model and API exist and return an
honest "nothing connected" response.

**Why:** The spec requires selecting a pilot channel and verifying API
access, scopes, review requirements, and commercial terms *before*
building a live connector (M11). None of that discovery happened in this
session — building a connector now would mean guessing at an unverified
integration, which the spec explicitly forbids ("Do not implement a live
integration using a guessed endpoint").

## D6 — Full data model created now, only some of it wired to API routes

**Decision:** `Document`, `Integration`, and `UsageRecord` models/
migrations exist; `Document` has no upload endpoint, `Integration` has only
a read-only list endpoint.

**Why:** Creating the schema now avoids a disruptive migration later and
matches the spec's "design for the full architecture" instruction, while
*not* building unused routes avoids claiming capabilities that don't exist
("Do not build empty agent modules just to claim all 12 agents exist" — the
same principle applies to half-built API surfaces). `docs/IMPLEMENTATION_PLAN.md`
lists exactly what's wired versus schema-only.

## D7 — UI/UX Pro Max skill, Everything-Claude-Code repo, Paperclip: not adopted

**Decision:** None of the optional repositories/Skills listed in
`prompt.md` section 6 were installed or adopted in this session.

**Why:** Per the spec's own repository-adoption rule, each one requires
inspecting its current README/license/maintenance status before adoption,
and none of them solve a problem this build currently has (the Flask
workflow engine is sufficient for the 5-stage pipeline; no design-system
generation need yet; no multi-agent orchestration need yet). Revisit if a
concrete need appears — do not install speculatively.

## D8 — Added Groq as a second AI provider; disabled SDK-internal retries on both

**Decision:** `app/ai/provider_adapter.py` now has `GroqProvider` alongside
`AnthropicProvider`, both implementing the same `AIProvider` interface.
`get_provider()` branches on `AI_PROVIDER` (`anthropic` | `groq`). Both
provider clients are now constructed with `max_retries=0`.

**Why:** The user had a Groq API key (free-tier-friendly, no Anthropic key
available) and wanted real AI generation verified, not just the
`capability_unavailable` path. Groq serves open-weight models through an
OpenAI-compatible API — a different request/response shape from
Anthropic's SDK, but the same `generate_structured()` contract, which is
exactly what the provider-neutral design was for (see D1/D3 and
`docs/12_AGENT_ROADMAP.md`'s "AI provider adapter" row — this is
that design surviving contact with a real second provider, unmodified).

**What actually happened when tested against the real API** (see
`docs/TEST_REPORT.md` for the full log):
1. The model ID from Groq's own quickstart docs
   (`llama-3.3-70b-versatile`) no longer exists on the current API —
   confirmed via `client.models.list()` and switched to
   `openai/gpt-oss-120b`, which is live. **Docs can be stale; the live
   models endpoint is the source of truth.**
2. `marketing_manager`'s `success_metrics` (list of strings) and
   `timeline` (list of objects) fields initially failed schema validation
   — the open-weight model returned objects where strings were expected,
   and vice versa on the fix's first pass. Fixed by adding explicit
   per-field type hints to the prompt (`_describe_field()` in
   `provider_adapter.py`), generated from the Marshmallow schema itself
   rather than hand-written per field — so it stays correct if a schema
   changes. This is a genuine difference from Claude's instruction-
   following, not a bug in the schema or the pipeline.
3. Hit Groq's free-tier rate limit (8,000 tokens/minute) partway through
   a 5-stage run — handled correctly: `RateLimited` raised, task marked
   `failed` with the real error message, no fabricated output, no
   duplicate billing risk (nothing executes on a failed AI stage).
4. That same rate-limit response initially caused the whole request to
   hang for ~41 seconds before failing, because both the `anthropic` and
   `groq` SDKs retry 429/5xx responses internally by default, with their
   own sleep — layered on top of this app's own bounded-retry loop
   without either layer knowing about the other. Fixed by passing
   `max_retries=0` to both SDK clients, making this app's own retry/
   timeout/budget logic the only retry layer, exactly as the architecture
   doc already claimed it was before this was actually tested end-to-end
   against a rate-limited real provider.

**Consequence:** `.env`'s `AI_MODEL` default is now provider-dependent
(`app/config.py:_AI_MODEL_DEFAULTS`) rather than a single hardcoded
string, since Anthropic and Groq model IDs don't share a namespace.

## D9 — Platform-formatted manual export (Meta/Instagram, Google Ads, TikTok Ads), not live connectors

**Decision:** The user asked for Meta/Instagram, Google Ads, and TikTok
Ads "execution" (running ads, posting, scheduling). After explicitly
surfacing what that actually requires (a registered developer app, app
review, and for the ad platforms a linked ad account with API access —
all of which only the account owner can obtain, none of which existed
this session), the user chose the manual-export-formatting option rather
than scaffolding untestable OAuth connectors.

Built: `app/integrations/export_formats.py` — pure formatting functions
(no network calls, no API client, no OAuth) that take an already-approved
`content_pack` variant and reformat it to each platform's actual composer
constraints (character limits, field counts, asset specs), so pasting
into Meta Business Suite / Google Ads Editor / TikTok Ads Manager needs
less manual rework. Wired into the existing manual-handoff execute
endpoint via an optional `target_platform` parameter — this is the same
`ManualHandoffConnector` as before, with a formatting layer on top, not a
new connector and not a new permission level. No agent or code path in
this app can post, publish, or spend on any of these platforms; a human
still does that themselves, in the platform's own tool, after copying the
formatted output.

**Why this is consistent with the rest of the governance design:** Per
`docs/SECURITY_AND_GOVERNANCE.md` and the 12-agent operating model (roles
3 and 5 in `docs/AGENT_OPERATING_MODEL.md`), publishing/spend actions
require either a verified live connector + approval + re-validated
execution (Level 2) or remain permanently human-only (Level 3, ad spend).
Neither exists here — this feature only makes the existing, already-
governed manual handoff path more useful, it doesn't add a new execution
capability or widen any permission.

**Limits, stated plainly rather than glossed over:** Google Ads' RSA
character/count limits are sourced from Google's own help page and are
solid. Meta's ad-creative limits are sourced from Meta's own ad-spec
pages. Instagram's *organic* caption limit and TikTok's ad-text character
limit and CTA button list could not be found on any official page reached
in this session (tried multiple pages/angles for each, including the
Graph API field reference and TikTok's ad-creation help index) — these
are explicitly marked `limit_confirmed: false` in the API/UI rather than
filled in with the commonly-repeated-but-unofficial numbers (e.g. "2200
characters" for Instagram) that circulate in marketing blogs. If a real
official source for either surfaces later, update
`app/integrations/export_formats.py`'s docstrings and `FieldCheck` calls
with the citation — don't just add a number.

## D10 — Rebrand to ARC; dark, motion-driven redesign; timeline schema hardened

**Decision:** Renamed the product from "Marketing Department Harness" to
**ARC** across all user-facing surfaces (frontend nav/landing/page title,
`frontend/package.json`), and rebuilt the frontend's visual design:
dark theme (near-black `#020617` background, electric cyan/indigo accent
— the color choice ties directly to the name: an electric arc), animated
hero (ambient gradient drift, grid overlay, gradient-text headline),
scroll-reveal and 3D-tilt-on-hover components (`frontend/src/components/
motion/`, built on the `motion` package — Framer Motion's current name),
and animated KPI counters on the dashboard. Design direction (dark,
restrained motion over loud 3D) was chosen by the user from a set of
real reference sites (resend.com) after reviewing several; color palette
sourced from the `ui-ux-pro-max` skill's "API Developer Portal" dark-SaaS
catalog entry, with the accent swapped to cyan for the brand-name tie-in.
The original spec files
(`marketing_department_harness_complete_specification.md` and the
`marketing_department_harness_deliverables/` pack) were deliberately
**not** renamed — they're the historical source brief this build follows,
not branding.

**Real bug found and fixed during this work:** `CampaignPlanSchema.timeline`
was `fields.List(fields.Dict())` — no enforced inner shape. The frontend's
`DeliverableContent.tsx` always read `phase.activities`, but a real Groq
response used `key_activities` instead (different run, same schema gap),
so the rendered timeline silently showed phase titles with no activity
list — not a crash, just quietly incomplete output. Fixed by adding
`TimelinePhaseSchema` (`phase`, `activities`) and nesting it properly
(`fields.List(fields.Nested(TimelinePhaseSchema))`). This also sharpens
the AI prompt automatically — `_describe_field()` already turns a nested
schema into an exact "list of objects, each with keys: phase, activities"
hint instead of the generic "freeform key/value pairs" hint a bare
`Dict()` produces — so this fix addresses the prompt-precision root cause,
not just the symptom. **Lesson for future
schema fields holding structured list items: always use
`fields.Nested(...)`, never a bare `fields.Dict()`** — a bare `Dict()`
gives the model (and whoever reads the schema) no contract for what keys
should exist, which is exactly the kind of under-specification this
project's own governance principles argue against elsewhere.

## D11 — Durable DB-backed task queue + separate worker (supersedes D4)

**Decision:** A campaign run is now 12 `Task` rows linked by
`TaskDependency` rows. `POST .../runs` only *enqueues* them (so `202` is
true now) and a separate process, `flask worker` (`app/cli.py`), executes
them via `app/workflows/engine.py`. No Redis, Celery, or RQ.

**Why:** The synchronous pipeline could never finish a full run on the
Groq free tier (8,000 tokens/minute) — the request died on the first
429. A worker that persists state and retries with backoff fixes that
directly. The database is already the source of truth for runs, tasks,
deliverables and approvals; putting the queue there too means one store
to back up, one transaction boundary, and nothing new to deploy. At this
scale (tens of tasks per run, a few concurrent workspaces) a polled table
is well within what SQLite/Postgres handle.

**How it stays correct:**
- *No double execution:* a task is claimed with a conditional `UPDATE ...
  WHERE id = ? AND status = <the status we read>`; only one worker's update
  can match. Tested in `test_task_cannot_be_claimed_twice`.
- *Crash recovery:* a claimed task gets `lease_expires_at` (3 x AI timeout
  + 30s). Any worker that finds an expired lease puts the task back to
  `retrying` (or `failed` once attempts are exhausted).
- *Retries:* `RateLimited`, `AIRequestTimeout`, `InvalidOutput` and other
  provider errors retry with exponential backoff + jitter (base 5s, cap
  120s); a provider `retry-after` wins if longer. `ProviderUnavailable`
  and `BudgetExceeded` fail immediately — retrying a missing key is
  pointless (rule 5 in CLAUDE.md still holds: `capability_unavailable:`).
- *Cancellation while running:* the engine re-reads the task after the
  model returns and discards the output if the task is no longer
  `running`.
- *Independent branches continue:* one failed agent only blocks agents
  that depend on it; the run settles as `failed` once nothing else can
  progress, and a person's retry re-opens it.

**When to revisit:** if a single worker can't keep up (many workspaces
running at once) run several workers — the claim is already safe for
that. Move to a real broker only if polling load on the DB becomes a
measured problem, or if tasks need sub-second latency.

## D12 — The 12 agents as versioned specs, not classes

**Decision:** Each agent is an `AgentSpec` (`app/agents/base.py`) in
`app/agents/definitions.py`: id, number, version, role, instructions, one
output schema, `depends_on`, a `reads` allowlist, budget and retry policy,
external-action policy, honest integration status, and automated
evaluation checks. The five old per-stage classes were removed.

**Why:** the agents differ in *data*, not behavior — the same "build
input -> call provider -> validate schema" loop runs for all of them. A
spec makes every agent's permissions visible in one file and testable
(`tests/unit/test_agent_registry.py`), and the registry refuses to import
if a dependency is misspelled or cyclic.

**Notable choices:**
- The `reads` allowlist is enforced by the engine (`_upstream_outputs`),
  not by the prompt. An agent physically never receives output it isn't
  allowed to see. Input builders then pick specific fields so each call
  stays small — necessary on free-tier rate limits.
- Agent 11 (Marketing Ops/QA) keeps the existing `qa_report` type and
  receives code-level evaluation results (prohibited phrases, invented
  contact details) as confirmed issues — deterministic checks the model
  can't argue its way out of.
- Agent 5 (Paid Media) has `external_action_policy =
  never_executable_spend_is_human_only`; no code path lets an agent change
  spend.
- Prompts state the agent's role and that all input is untrusted data,
  never instructions (prompt-injection hygiene for business-profile text).
- `AgentExecution` records `agent_version` on every attempt, so changing
  an agent's instructions later never misattributes older output.

## D13 — Design system: CSS tokens + own components, not Tailwind/shadcn

**Decision:** Keep the existing token-based CSS (`index.css` `:root`,
`styles/components.css`) and a small typed component library
(`components/ui`), re-tokened to the brief's palette (#08090B, #111317,
#F5F5F0, #A1A4A5, ice-blue #9FD8FF) with Inter (UI), Instrument Serif
(display) and JetBrains Mono (metadata) — all SIL OFL.

**Why:** the brief says not to add libraries when existing ones solve the
problem. Migrating ~40 pages to Tailwind/shadcn would be a large rewrite
with no user-visible gain; the components needed (dialog, drawer, tabs,
toasts, table, KPI, timeline, command palette, confirm) are small and are
covered by tests. Resend was a benchmark only: no logo, copy, layout or
assets copied; ARC's mark is an original SVG.

## D14 — Knowledge: recent approved entries, no vector store

Agents 01 and 02 receive up to 8 most recent *approved* knowledge entries
(400 chars each) as untrusted data. No embeddings: the library is small
per workspace and there's no evidence yet that retrieval quality needs
it. Revisit when workspaces exceed ~200 entries.

## D15 — Billing via a provider adapter with a signed test mode

Plan state changes only from verified, idempotent payment events. Locally
the `test` provider completes checkout by sending a *signed* event through
the same webhook path, so the lifecycle is exercised end to end without
faking a real payment. The Stripe adapter is implemented but unexercised
(no keys). Production defaults to `none`.

## D16 — Deterministic fixture AI provider for E2E only

`AI_PROVIDER=fixture` works only with `ALLOW_FIXTURE_PROVIDER=true` and
never under `ProductionConfig`; its outputs are marked "[E2E fixture]".
This satisfies the brief's "deterministic fake providers for CI" without
weakening CLAUDE.md rule 5: an unconfigured provider still yields
`capability_unavailable`, never fabricated content.

## D17 — WordPress.com is the first live publishing connector

The user chose WordPress.com as the pilot channel (Phase 2) and chose
"verified by WordPress" for how publication is recorded. So:

- A workspace owner/admin connects a site with WordPress.com OAuth2. The
  state is signed (itsdangerous, 10-minute expiry), tied to the user and a
  single-use session nonce. The token is Fernet-encrypted at rest
  (`INTEGRATION_ENCRYPTION_KEY`, else derived from `SECRET_KEY`) and never
  returned by any endpoint.
- The SEO agent (v1.2.0) now writes one publish-ready blog article. An
  approver can publish it (or save it as a draft) only from an approved,
  current version. The request just queues an `ExternalAction`; the worker
  re-checks kill switch, approval decision and exact version immediately
  before posting (CLAUDE.md rule 3), posts once with a deterministic slug
  (retries look the slug up first, so they never duplicate), then reads
  the post back. Only that read-back sets `platform_verified_published`
  (CLAUDE.md rule 4, amended). Drafts are `draft_created`, never
  "published".
- Article markdown is converted to HTML after escaping everything, so model
  output cannot inject markup. A revoked token marks the connection
  `reauth_required` and fails the action with a reconnect message.
- New locked policy `live_publish` (require_approval). Spend stays blocked:
  ad launching (Phase 2, part 3) will add its own cap + kill-switch path
  and is built against a fake ad platform until the user has API access.

## D18 — Outreach email: client-owned sender, batch approval, lawful lists only

The user chose "each client connects their own" sender. A workspace admin
connects a Brevo or Resend API key (encrypted at rest, checked against the
provider) plus a verified from-address and a postal address. Emails go out
from the client's own domain and reputation.

- **Lists:** CSV upload only, with a lawful basis (consent / existing
  customer / legitimate interest), a source description and an attestation
  that contacts weren't scraped or bought. Invalid, duplicate and
  previously-unsubscribed addresses are skipped. No scraping exists.
- **Batch approval:** one template + one list + sender + daily limit,
  approved as a whole by an approver role. Approval freezes the recipient
  list and stores a SHA-256 of all of it. Editing the batch or changing the
  sender cancels the approval; the worker recomputes the hash before every
  email and pauses the batch on any drift.
- **Sending:** worker step, per-batch daily limit under a workspace cap
  (`OUTREACH_DAILY_CAP`, default 200), a few seconds between emails, kill
  switch checked each time. Resend sends carry an Idempotency-Key, so an
  interrupted attempt is retried; Brevo has none, so an interrupted Brevo
  send is marked failed rather than risking a duplicate email.
- **Compliance:** every email has the sender's postal address, why the
  person is receiving it, an unsubscribe link (a page that needs one click,
  so link scanners can't unsubscribe people) and RFC 8058
  `List-Unsubscribe` + `List-Unsubscribe-Post` headers pointing at a
  CSRF-exempt one-click endpoint. Unsubscribes go on a workspace-wide
  suppression list that the API never removes from.
- Locked policy `outreach_email` (require_approval).

## D19 — Ad launching: people launch, agents never spend, hard daily cap

The user chose "launch after approval + daily cap" and has no Meta/Google
API access yet, so the full flow runs against ARC's built-in **test ad
platform** (`app/integrations/ads_platforms.py`): no outside calls, no real
money, spend accrues on a clock so every guardrail can be exercised.

- `spend_change` stays **blocked** for agents (no code path). New locked
  policy `ad_launch` (require_approval) covers human launches.
- Launching is off until an owner/admin sets a workspace daily cap
  (`ADS_MAX_DAILY_CAP` bounds it, default 1000). Requests must fit under the
  cap minus every pending/approved/running budget.
- A launch comes from one ad in a paid-media plan whose *current* version is
  approved, with a daily budget and an end date (max 90 days). An approver
  must re-type the budget. The approval is a hash of exactly what launches.
- The worker (every iteration) re-checks hash, cap and plan approval before
  launching (idempotent create), then enforces on everything live: kill
  switch -> pause; end date -> stop; a person's pause/stop/Stop all; and if
  today's spend across the workspace exceeds the cap -> pause every ad.
- Meta Marketing API / Google Ads API connectors implement the same four
  methods (create, pause, resume, archive + status) once the user has access.

## D20 — Light theme, and accent colours a client can personalise

**Decision:** Every page supports a high-contrast light theme alongside the original dark
one. Each person chooses Light, Dark or "Match my device" (the default), saved in their
browser. Accent colour has two layers: workspace owners/admins pick a workspace default
(one of six presets, or "Brand colour" from the Brand Kit), and anyone can override it for
themselves with a preset.

**Why:** most business users run light mode during the day, and clients asked to see their
own brand in the workspace. Colours are tokens (D13), so the light theme is a second set of
token values (`:root[data-theme='light']` in `index.css`) rather than per-page styling;
tints, borders and glows use `color-mix()` on the tokens so they follow both theme and accent.

**Contrast is enforced, not hoped for:** the six presets have tuned dark and light values,
and `src/lib/theme.test.tsx` checks every one is at least 4.5:1 (WCAG AA) against the
background and card surfaces in both themes, and that button text on the accent is too.
A Brand Kit colour is lightened (dark theme) or darkened (light theme) until it reaches
4.5:1 on every surface, so a pale yellow or a dark navy brand can never make text
unreadable. Light-theme body text is 19:1, muted text 7:1.

**Details:** the workspace accent is `organizations.accent_color`, changed only through
the admin-only `PATCH /organizations/<id>` and validated against an allowlist; it's display
only and is not part of the business profile, so it never reaches agent prompts.
`index.html` applies the saved theme and accent before first paint, so there's no flash.
Charts read the same tokens via `var()` (`src/lib/chartTheme.ts`). Public pages always use
ARC Blue unless the visitor picked their own preset; a workspace's brand colour only
applies inside that workspace. The logo keeps ARC's own colours in every accent.

## D21 — Sell outcomes to UAE SMEs; run only the agents a campaign needs

**Decision (2026-11-14):** ARC's public and in-app copy leads with what a customer
receives each month (a plan, posts, ads, pages, emails, a report), aimed at growing
businesses in the UAE. It no longer counts or leads with "12 agents"; the agents remain
as internal machinery and are still described on `/agents`.

**Why:** an idea-scorecard review put ARC in the "validate" band. Evidence and path to
the buyer were the weak criteria, and both reviews found customers pay for outcomes, not
agent headcount. The same review found every run paid for specialists the campaign had
no use for.

**Details:**
- `app/agents/selection.py` picks agents from the campaign's `channels`. Six core agents
  always run (strategy, research, plan, creative, quality gate, record); the six channel
  specialists run only when a channel calls for them. Empty or unrecognised channels fall
  back to all twelve. The quality gate depends only on specialists that were queued.
- `AgentSpec.model_tier`: `record_keeper`, `customer_insights` and `key_accounts` are
  `light` and use `AI_MODEL_LIGHT` when it is set; otherwise nothing changes.
- Cost estimates use `AI_PRICE_INPUT_PER_MTOK` / `AI_PRICE_OUTPUT_PER_MTOK` (and the
  `LIGHT` pair). Unset, they stay on the old placeholder rate.
- `_build_prompt` puts the business/campaign context first, identical for every agent
  in a run, so a provider that caches a shared prompt prefix can reuse it. The saving
  is not measured yet; explicit Anthropic `cache_control` is not added.
- Password-reset links are emailed by `app/services/system_email.py` from a
  platform-level Resend or Brevo account (`SYSTEM_EMAIL_*`). Without it no email is
  sent, which is the state production was in before.
- `SENTRY_DSN` turns on error tracking (no request bodies or user details are sent).
- Frontend: a top-level `ErrorBoundary`, and `apiRequest` rejects a 200 that is not
  JSON. Before this, one malformed API response left the whole site blank.
- CI also applies migrations to PostgreSQL 16, which is what production runs.

## D22 — Profit maths, Growth Score and Growth Audit are calculations, not model output

**Decision (2026-11-14):** the features that tell a customer how their business is doing
are plain code over data ARC holds. No model call produces a score, a profit figure or an
audit finding.

**Why:** these numbers are what a customer acts on and what the free audit is judged by.
They must be repeatable, explainable and cheap. Anything ARC cannot work out is shown as
"not measured" or "not connected" (rule 5 applied to analytics, not only to agents).

**Details:**
- `unit_economics.py`: ROAS, break-even ROAS, profit after ad spend, cost per lead and per
  customer, lifetime value, payback. Gross margin, average sale value and repeat orders are
  entered by the customer on the business profile (five new columns, migration
  `da0bd4c6a403`). Every results summary carries an `economics` block.
- `growth_score.py`: six dimensions. Brand readiness, website conversion, lead generation
  and campaign performance are scored from the profile and recorded results on ARC's own
  disclosed scales. Retention and advocacy stay "not measured" until order and review data
  can be connected.
- `growth_audit.py`: the public free audit. Fifteen repeatable checks on one page's source
  through the existing SSRF-safe fetch; impact and effort are fixed labels per check. An
  email is optional and, when given, lands in the admin inbox as a `growth_audit` enquiry.
  The speed test calls Google PageSpeed Insights only when `PAGESPEED_API_KEY` is set (the
  keyless quota was exhausted when tried); otherwise it reports "not connected".
- `cost_service.py`: cost by model and campaign, failed and repeated calls, and the month's
  spend against the plan's AI budget with a warning from 80%. Cached tokens are not
  recorded yet. ARC's own revenue and margin per customer are not shown to customers and
  are not built for the platform admin yet.
- Agents: `app/agents/teams.py` groups the twelve specs into one orchestrator, six teams
  and on-demand skills. They stay separate small calls. The CMO (1.3.0) follows an
  evidence-first process and returns prioritised initiatives, risks and KPIs; it and the
  paid media agent (1.2.0) receive `performance_for_agents()`: what the business can
  afford from its margins, and recorded results per channel with a made/lost-money verdict.
  That is how results reach the next plan.
- Onboarding: a business-type picker for the five UAE segments pre-fills empty fields, most
  questions have one-tap answers, and a "Your numbers" step collects the commercial facts.
  The same segments supply campaign playbooks.
- Integrations: Search Console, Meta Ads read, TikTok, Shopify/WooCommerce, WhatsApp,
  scheduling tools and review platforms are listed as planned. None is built: each needs a
  developer app, platform approval and the customer's consent, which the user has not yet
  provided (see "What NOT to do without asking first" in CLAUDE.md).

## D23 — Research runs first; the strategy starts from verified context

**Decision (2026-11-14):** the research agent now runs before the CMO, and the CMO is given
everything verifiable that ARC can gather in code before the model is called.

**Why:** a strategy written before any research, with no view of the business's own
website or of how its last plan turned out, is a generic one. The dependency order was the
cause, not the prompt.

**Details:**
- `research_analyst` 1.3.0 has no dependencies and works from the brief. `cmo` 1.4.0 depends
  on and reads it. Everything else is unchanged, so runs take no extra calls.
- `strategy_context.py` adds three things to the CMO's input, each only when real:
  margins and recorded results (D22); the top gaps from the Growth Audit of the business's
  own website, fetched once in the worker (`STRATEGY_WEBSITE_AUDIT`, off in tests, and an
  unreachable site is simply left out); and the objectives and KPIs of the previous
  strategy. The CMO returns `previous_kpi_review` with a met / missed / not_measured status
  per KPI, judged from recorded results only.
- `marketing_manager` 1.3.0 returns `roadmap_90_day` (three 30-day periods with focus,
  activities, owner, budget share, forecast outcome and KPI) and `tracking_requirements`,
  inside the existing campaign plan rather than as a thirteenth agent.
- Cached input tokens are read from the provider's usage figures when present
  (`AIResult.cached_input_tokens`, stored on usage records and executions, migration
  `6f26a0de5734`) and shown in the cost view. Explicit Anthropic `cache_control` is still
  not added: production runs on Groq and it could not be tested live.
- `notify_budget_if_crossed()` raises one workspace notification at 80% of the month's AI
  budget and one at 100%.
- `/admin/unit-economics` (platform owner only): revenue, AI cost and gross margin per
  workspace. Trials count as zero revenue.
- Not done, on purpose: batch processing (provider batch APIs answer within hours, which
  does not fit a run a customer is waiting on) and a separate "skills" store (each agent
  already receives only its own instructions, so nothing unneeded is loaded).

## D24 — One type family, no em-dashes, an animated loop on the home page

**Decision (2026-11-14, at the user's request):** Plus Jakarta Sans replaces Inter (text)
and Instrument Serif (headlines); it is the "Friendly SaaS" pairing from the
`ui-ux-pro-max` typography data. Spaced em-dashes are removed from all user-facing text
and empty table cells show a hyphen. The home page's seven-box text loop is replaced by
`components/motion/FlowLoop.tsx`: six icon steps, a moving marker and one sentence at a
time.

**Details:** display headings are weight 800 with tighter tracking and a step smaller than
the serif was. `FlowLoop` pauses on hover and focus, has a pause button, and under
`prefers-reduced-motion` renders a static list instead. The model prompt in
`provider_adapter.py` was deliberately left untouched, so no agent version changes. The
text-based `LoopDiagram` remains on the How it works page.
