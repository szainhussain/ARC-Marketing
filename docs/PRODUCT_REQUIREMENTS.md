# Product Requirements — ARC (Marketing Department as a Service)

Sources: `marketing_department_harness_complete_specification.md` (primary)
and the MaaS master build brief (§1–25). This file maps each requirement to
its implementation status. "Built" means implemented **and** covered by an
automated test or the E2E journey (see `docs/TEST_REPORT.md`).

## Positioning

ARC is an AI-operated marketing department: 12 specialist agents
coordinated through one durable workflow, two control rooms (Business
Command Center, Marketing Operations Center), and version-bound human
approvals. It is not a content generator and makes no outcome guarantees.

## Requirement status

| Area (brief §) | Requirement | Status |
|---|---|---|
| Agents (§5, §13) | 12 distinct, versioned agents with own schema, `reads` allowlist, budgets, evaluation, approval policy | Built |
| Orchestration (§6) | Durable task graph, deps, retries w/ backoff+jitter, idempotency, leases/recovery, pause/resume/cancel, budgets, concurrency, approval checkpoint before start, correlation ids | Built |
| Orchestration (§6) | Recurring programs / scheduled runs | **Not built** (`scheduled` status reserved) |
| Orchestration (§6) | Agent-initiated mid-run approval checkpoints | **Not built**; approvals are run-start (policy) and per-deliverable |
| Human control (§7) | Action policies (workspace level), locked platform boundaries, approval record with agent/risk/outcome/expiry, approve/reject/request changes/revoke, edit-before-approve (new version invalidates) | Built |
| Human control (§7) | Campaign-/integration-level policy overrides | **Not built** (workspace level only) |
| Public site (§8) | 15 pages, interactive preview toggle, local workflow demo, agent detail dialogs, honest integration statuses, provisional pricing, contact form | Built |
| Command Center (§9) | Real KPIs w/ previous-period comparison, date-range + campaign filters, drill-down links, charts, campaign cards, attention/recommendations/upcoming/recent | Built |
| Command Center (§9) | Spend, conversions, CPA, revenue, ROAS | Shown as **Not connected** (no data source) |
| Operations Center (§10) | Agent cards, agent detail, live graph (zoom/pan/fit/list), task queue w/ retry/cancel, approval inbox, activity feed, global controls, budgets/concurrency | Built |
| Operations Center (§10) | Task reassignment to a different agent | **Not built** (each task type has exactly one owning agent by design) |
| App routes (§11) | All 29 routes | Built |
| Onboarding (§12) | Multi-step wizard with saved progress; knowledge library with provenance, versions, proposed→approved flow | Built |
| Onboarding (§12) | Vector retrieval | Not needed yet (recent approved entries only) — see D14 |
| AI layer (§13) | Provider-neutral adapter, Anthropic + Groq, schema validation, untrusted-data prompts, cost accounting, gated fixture provider for E2E | Built |
| AI layer (§13) | OpenAI adapter, per-agent model policy, evaluation datasets | **Not built** |
| Integrations (§14) | Catalog with honest statuses, enable/disable, outbound signed webhooks (SSRF-safe) | Built |
| Integrations (§14) | Live OAuth connectors (Meta, Google Ads, GA4…) | **Blocked** on your channel choice + credentials |
| Data model (§15) | See `docs/DATA_MODEL.md` | Built (feature flags, evaluation runs not built) |
| Security (§16) | Sessions w/ revocation, password reset, email verification, 7 roles, CSRF, secure headers, rate limits, upload validation, SSRF defense, data export/deletion, tenant tests, kill switch | Built |
| Security (§16) | MFA | **Designed, not built** |
| API (§17) | Versioned REST, OpenAPI from live routes, pagination on list endpoints, idempotency, X-Request-Id | Built |
| Billing (§18) | Plans/entitlements as data, trial, usage metering, quotas, budget alerts, upgrade/downgrade w/ fit check, history, signed idempotent webhooks, test-mode + Stripe adapter | Built (Stripe adapter **not exercised** without keys) |
| Design (§19) | Tokens, display font, component library, motion w/ reduced-motion, responsive tables/graph | Built (Tailwind/shadcn not adopted — D13) |
| Analytics (§20) | Platform vs business metrics separated, estimate labels, CSV export | Built |
| Testing (§21) | Backend unit/integration/security, frontend component tests, E2E journey | Built |
| Deployment (§22) | Docker Compose with worker, migrations, CI, runbook, release checklist | Built locally; **not deployed** |

## Non-goals (explicit)

ARC never posts, sends, or spends on a customer's behalf in this release.
Publication status changes only when a person confirms they published.
