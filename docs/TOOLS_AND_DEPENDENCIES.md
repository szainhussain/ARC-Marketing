# Tools and Dependencies

## Adopted

| Tool/package | Why | Notes |
|---|---|---|
| Flask 3.1 + Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-CORS | Core web framework per spec | Pinned versions in `requirements.txt` |
| Marshmallow 3.23 | Request/response and AI-output schema validation | Chosen over Pydantic for simpler native Flask integration; spec allows either, says "choose one consistently" |
| SQLAlchemy 2.1 + Alembic | ORM + migrations | |
| `anthropic` 0.40 (Python SDK) | AI provider adapter | Only imported inside `app/ai/provider_adapter.py`, lazily, so the app still runs with the package absent/provider unconfigured |
| `groq` 1.7.0 (Python SDK) | Second AI provider (OpenAI-compatible, free-tier-friendly) | Same lazy-import pattern as `anthropic`. Verified against the real API this session — see `docs/DECISIONS.md` D8 and `docs/TEST_REPORT.md` for what broke and was fixed (stale model ID, schema-validation prompt gap, SDK-internal retry hang) |
| `psycopg2-binary` 2.9.10 | PostgreSQL driver | In `requirements.txt` (Docker/production) only — excluded from `requirements-dev.txt` because it has no prebuilt wheel for the host's Python 3.14 in this session; see `docs/DECISIONS.md` D2 |
| `gunicorn` 23.0 | Production WSGI server (Docker) | |
| `pytest`, `pytest-cov` | Test framework | 22 tests, see `docs/TEST_REPORT.md` |
| React 19 + TypeScript + Vite 6 | Frontend | Scaffolded via `npm create vite@6.3.1 -- --template react-ts` |
| `react-router-dom` 6.28 | Client-side routing | |
| `playwright` 1.49 (dev-only, not a project dependency) | Browser verification during this build session | Used from a throwaway script outside the repo (see `docs/TEST_REPORT.md`); not added to `package.json` since it's a one-off verification tool, not a runtime or CI dependency. Recommend adding `@playwright/test` properly if ongoing browser regression testing is wanted. |
| `ui-ux-pro-max` Skill (`.claude/skills/ui-ux-pro-max/`) | Read-only design-guidance catalog (accessibility, color, typography, layout, stack-specific UI rules), searchable via `scripts/search.py` | Installed and pruned this session — see full writeup below |

## External resources — actually inspected this session (README, license, maintenance, deps, security)

Every item below was fetched and evaluated in this session (not from memory). Full agent reports are in the session transcript; verdicts and reasoning are summarized here per the spec's repository-adoption rule.

### Adopted: `ui-ux-pro-max-skill` (nextlevelbuilder/ui-ux-pro-max-skill) — with pruning

**What it is:** A Claude Code Skill holding a searchable local catalog (colors, typography, fonts, UX rules, stack-specific guidance) for design decisions. MIT license, ~144.6k stars, 289 commits, Python stdlib only for the actual search logic, confirmed **no network calls** (`urllib.parse` is used for URL parsing only, not fetching).

**What actually happened on install:** The documented install path (`npx ui-ux-pro-max-cli@2.15.0 init --ai claude`) does **not** install just the one named skill — it writes 7 separate skill bundles into `.claude/skills/`: `ui-ux-pro-max` (the actual catalog/search skill), plus `banner-design`, `brand`, `design`, `design-system`, `slides`, and `ui-styling`. Several of these assume a Tailwind/shadcn stack (this project uses plain CSS) or cover work out of scope for this product entirely (slide-deck design, logo/icon design, banner design), and `brand/scripts/sync-brand-to-tokens.cjs` + `design-system/scripts/generate-tokens.cjs` can rewrite CSS design tokens — more invasive than the "design guidance" the repo's own description promises.

**Action taken:** Kept only `.claude/skills/ui-ux-pro-max/` (confirmed read-only, local-data-only, no network, no file-write scripts) and deleted the other 6 bundled directories — the spec's "choose the smallest useful integration" rule, applied after the fact once the installer's real scope became clear. This is itself a useful lesson: **a tool's own installer adopting more than its README implies is exactly the "don't import the entire repository" failure mode the spec warns about, even when you only asked for the one named thing.**

**Verdict: ADOPT (pruned).** Low risk, genuinely useful reference for the 10 UI/UX-spec screens not yet built (see `docs/IMPLEMENTATION_PLAN.md`). Re-run `npx ui-ux-pro-max-cli@2.15.0 update --ai claude` only if you want the catalog refreshed, and prune again afterward — the installer doesn't have a "just this skill" flag.

### Cherry-pick only, not adopted wholesale: "Everything Claude Code" (affaan-m — the actual repo is `affaan-m/ECC`, not `everything-claude-code`)

MIT license, ~296k stars, very large bundle: ~71 subagents, ~314 skills, ~98 command shims, hook scripts, installers for multiple AI coding tools. Contains individually interesting pieces (`skills/security-review/`, `skills/tdd-workflow/`, `agents/security-reviewer.md`) but the full installer writes to `~/.claude/settings.json`, auto-loads hooks, and runs fetched npm code via `npx ecc-universal@2.2.3` — exactly the "don't install unknown hooks that can execute arbitrary commands without review" case the spec warns against.

**Verdict: DEFER.** Not adopted this session — this project's own `.claude/skills/review-security/SKILL.md` already covers equivalent ground, tailored to this codebase's actual governance rules, which is more valuable than an unreviewed generic equivalent. If a specific file from ECC is wanted later, copy that one file by hand after reading its actual source (not done this session — only the path/title was visible, not verified content).

### Rejected: Paperclip (`paperclipai/paperclip`)

Very active (commits same-day, ~110.7k stars, ~2,700 merged PRs), MIT license — but it's a full Node.js + Postgres **control plane** for autonomous multi-agent teams (org charts, budgets, heartbeat-triggered agents, cron routines), not a library. Needs its own service, its own database, and broad provider credentials for agents that act without a human prompting each step.

**Verdict: REJECT for this project.** Confirms decision D7/D1: the current 5-stage sequential pipeline inside Flask does not need a separate autonomous-agent control plane. **Claude's alternative:** keep orchestration in `app/workflows/campaign_workflow.py` as a plain Python pipeline (what's already built) — revisit only if the 12-agent expansion (see `docs/12_AGENT_EXPANSION_ROADMAP.md`) genuinely needs cross-agent scheduling/budgeting infrastructure beyond what `Organization.monthly_workflow_limit` + per-call AI budgets already provide.

### Rejected: OpenWhispr (`OpenWhispr/openwhispr`)

MIT, ~10.6k stars, well-regarded — but it's a standalone **Electron desktop app** (global hotkey → paste transcribed text into whatever app has focus). No web-embeddable component or browser SDK.

**Verdict: REJECT — wrong form factor.** It cannot integrate into a web campaign-brief form. **Claude's alternative:** for voice input on the campaign-brief page, use the browser's native **Web Speech API** (`SpeechRecognition`) for a zero-dependency client-side dictation button, or a direct server-side call to a cloud STT API (e.g. via the same provider-neutral adapter pattern as `app/ai/provider_adapter.py`) if higher accuracy than the browser API is needed. Neither is built this session — not required for the MVP pilot.

### Deferred: Chatwoot (`chatwoot/chatwoot`)

Very actively maintained (daily commits, security fixes), but the core is MIT while the `enterprise/` directory is under a proprietary, seat-licensed "Chatwoot Enterprise License" (free for dev/testing only, forbidden to redistribute). Self-hosting means a separate Rails + Redis + DB service with its own auth system.

**Verdict: DEFER**, matching the spec's own instruction not to install it unless pilot requirements justify it. **Claude's alternative:** the "Customer Experience & Support Agent" role (see the 12-agent definitions below) only needs a draft-review queue today — one `SupportDraft`-style table plus a React review screen inside the existing app covers that without a second service, a second auth system, or a seat license. Revisit Chatwoot specifically if/when multi-channel (WhatsApp/Instagram/email) inbox management becomes a real, funded requirement.

### Adopt with caution, internal-only: AppFlowy (`AppFlowy-IO/AppFlowy`)

AGPL-3.0 (note: the network-use clause requires disclosing source of modifications if users interact with a modified version over a network — relevant if ever exposed customer-facing), ~78.1k stars, Flutter+Rust stack, self-hosted as a separate stateful service.

**Verdict: Fine as an internal team wiki/planning tool only; do not embed it in or expose it as part of the customer-facing product** (per the spec's own framing: "internal knowledge/workspace functionality... not a required customer-facing dependency"). Not installed this session — no internal-tooling need was in scope.

### Factual-only, no decision needed yet: Higgsfield (docs.higgsfield.ai)

Server-side REST API for image/video generation (e.g. SOUL V2 prompt-based generation, Genjutsu motion transfer), async job model (`POST` → poll `status_url` or webhook), official Python/TypeScript SDKs, key-pair auth (`Authorization: Key <id>:<secret>`), outputs retained ≥7 days. No public self-serve pricing found; enterprise tier adds SSO/retention controls/usage analytics, configured via Higgsfield support.

**Verdict: Fits the provider-adapter pattern well if/when image/video generation becomes a funded requirement** (role 6, Brand/Creative/Content Studio, in the 12-agent definitions below) — same shape as `app/ai/provider_adapter.py`: submit, store a reference, poll or webhook, validate output. Not built this session; no API key available, no confirmed pricing.

### Not evaluated — ambiguous names, not guessed (per the spec's own instruction)

**Open-SEO** and **CAP** (video tooling) — the spec itself flags these as names that "may refer to multiple projects or products" and explicitly says not to guess the repository. No credible single canonical repository was identified for either under these exact names. If these refer to specific tools, provide the exact GitHub URL and they'll be evaluated the same way as everything above.

## Known dependency risks

- `npm install` reported 15 vulnerabilities (12 moderate, 3 high) in the
  Vite scaffold's dev-dependency tree (eslint toolchain, typical for a
  fresh `create-vite` scaffold). Not run `npm audit fix --force` since
  that can introduce breaking changes to the build toolchain without
  review — flagging here for a deliberate follow-up rather than silently
  fixing or silently ignoring.
- `psycopg2-binary` is nearing end-of-life in favor of `psycopg` (v3);
  kept v2 to match the spec's own stack recommendation and existing
  Flask-SQLAlchemy ecosystem conventions. Revisit before a long-lived
  production deployment.
