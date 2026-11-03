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
`docs/12_AGENT_EXPANSION_ROADMAP.md`'s "AI provider adapter" row — this is
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
