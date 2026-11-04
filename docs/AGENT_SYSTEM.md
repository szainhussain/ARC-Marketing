# Agent System

What is actually implemented for ARC's 12-agent marketing department.
Source of truth: `app/agents/definitions.py` (specs), `app/workflows/engine.py`
(execution), `app/workflows/evaluation.py` (automated checks).

## What every agent has

| Property | Where it lives | Enforced by |
|---|---|---|
| Stable id, number (1–12), version | `AgentSpec` | Registry validation at import |
| One task type → one output schema → one deliverable type | `task_type`, `app/ai/schemas.py` | Schema validation in the provider adapter |
| `depends_on` — agents that must succeed first | `AgentSpec.depends_on` | `TaskDependency` rows; task stays `waiting_for_dependency` |
| `reads` — whose output it may see | `AgentSpec.reads` | `engine._upstream_outputs` filters before the agent runs |
| Tools | `allowed_tools = ("ai.generate_structured",)` | No other tool exists in code |
| Budget | `max_cost_per_task_usd` (default $0.50 estimated) + run budget + optional per-agent monthly budget | `engine._budget_error`, provider budget check |
| Retries | `max_attempts` (default 5) | `engine._fail` |
| External actions | `external_action_policy` | No agent can call `external_action_service`; only a person can, after approval |
| Evaluation checks | `evaluation_checks` | `evaluation.evaluate_output`, stored on `AgentExecution.evaluation_json` |
| Integrations | `allowed_integrations` with honest status | Display only — `planned`, `manual_export_available`; none are live |

## The 12 agents

| # | id | Produces (`task_type`) | Waits for | May read |
|---|---|---|---|---|
| 01 | `cmo` | `strategy` | — | — |
| 02 | `marketing_manager` | `campaign_plan` | cmo, research_analyst | cmo, research_analyst |
| 03 | `social_media` | `social_calendar` | creative_studio | marketing_manager, creative_studio |
| 04 | `pr_partnerships` | `outreach_plan` | marketing_manager | marketing_manager, research_analyst |
| 05 | `paid_media` | `paid_media_plan` | creative_studio | marketing_manager, creative_studio |
| 06 | `creative_studio` | `content_pack` | marketing_manager | cmo, marketing_manager |
| 07 | `research_analyst` | `research_notes` | cmo | cmo |
| 08 | `customer_insights` | `customer_insights` | research_analyst | research_analyst |
| 09 | `seo_growth` | `site_optimization_plan` | marketing_manager | marketing_manager |
| 10 | `key_accounts` | `account_plan` | marketing_manager | marketing_manager |
| 11 | `marketing_ops` | `qa_report` | all specialists (03–10 except 07) and 06 | cmo, 03, 04, 05, 06, 09 (subset, for token limits) |
| 12 | `record_keeper` | `campaign_record` | marketing_ops | cmo, marketing_manager, marketing_ops |

Execution graph (each column runs once everything to its left that it
depends on has succeeded):

```
cmo ─▶ research_analyst ─▶ marketing_manager ─▶ creative_studio ─▶ social_media ─┐
                       │                     ├▶ seo_growth ───────────────────────┤
                       │                     ├▶ pr_partnerships ──────────────────┤
                       │                     └▶ key_accounts ─────────────────────┤
                       └▶ customer_insights ──────────────────────────────────────┤
                                               creative_studio ─▶ paid_media ─────┤
                                                                                  ▼
                                                               marketing_ops ─▶ record_keeper
```

## Honesty constraints built into the agents

- **Research (07)** has no web/search tool connected and is told so; it must
  set `scope_note` accordingly and never present invented sources as real.
- **Customer insights (08)** has no customer data connected; themes are
  labeled hypotheses, and refunds/complaints/legal/safety templates must
  set `escalate_to_human`.
- **PR (04)** describes target *profiles* only. The `no_contact_details`
  check flags any email address, phone number or @handle in its output.
- **Paid media (05)** expresses budget as percentages and cannot change
  spend — permanently human-only.
- **SEO (09)** must not claim search volumes (no analytics connected).
- **Every agent**: the prompt states the input is untrusted data and never
  instructions; prohibited brand phrases are checked in code after output.

## Execution records

Every attempt creates an `AgentExecution` row: agent id + version, attempt
number, provider, model, tokens, estimated cost, duration, error code, and
evaluation results. Costs are estimates from placeholder prices
(`provider_adapter.py`), always labeled as such in the UI.

## What is not built yet

- Agents cannot call tools other than structured generation (no web search,
  analytics, CRM, or publishing).
- No agent-initiated approval checkpoint (`waiting_for_approval` exists in
  the state machine but no agent requests one mid-run yet; approvals are
  requested by people on finished deliverables).
- Per-agent monthly budgets are enforced but have no UI to set them yet.
- No scheduled/recurring runs (`scheduled` status reserved).
