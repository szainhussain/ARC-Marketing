# Agent Workflows

The one workflow type today is `campaign_department_v2`: a single campaign
run through all 12 agents. Mechanics live in `app/workflows/engine.py`;
agent definitions in `app/agents/definitions.py`; see also
`docs/AGENT_SYSTEM.md` and `docs/OPERATIONS_RUNBOOK.md`.

## Lifecycle

1. **Enqueue** (`POST /campaigns/:id/runs`, Idempotency-Key required).
   Checks plan run quota and workspace limit, creates the run and 12 tasks
   with dependency rows. Run status:
   - `needs_input` if the business profile is missing required fields;
   - `awaiting_approval` if policy `agent_drafting = require_approval`
     (an Approver resumes it with `POST /runs/:id/approve-start` — the
     same run continues; nothing is duplicated);
   - otherwise `queued`.
2. **Claim** (worker). Skips paused workspaces/agents/runs and workspaces
   at their concurrency limit; atomic conditional UPDATE; sets a lease.
3. **Execute.** Budget checks (run budget, agent monthly cap, plan AI
   budget, plan execution quota) → agent builds a small input from its
   allowed upstream outputs + approved knowledge (CMO, Marketing Manager)
   → provider call → schema validation → code-level evaluation checks →
   deliverable v1 + usage record + AgentExecution.
4. **Unblock** dependents whose dependencies all succeeded.
5. **Settle.** Run `completed` when all 12 succeed; `failed` when nothing
   can progress (a person's retry re-opens it). Notifications and
   webhook events (`run.completed` / `run.failed`) are emitted.
6. **Learn.** Record Keeper's `knowledge_updates` become `proposed`
   knowledge entries (or `approved` if policy `knowledge_update = auto`).
   Only approved entries reach future runs.
7. **Review.** People request approval per deliverable; approval is bound
   to version + payload hash, expires (14 days), can be revoked; approved
   content can be exported (manual handoff) — never auto-published.

## Failure handling

| Error | Behaviour |
|---|---|
| Rate limited | Retry with backoff; doesn't consume an attempt; separate cap of 15 in a row; provider `retry-after` pauses the worker |
| Timeout / invalid output / provider error | Retry with exponential backoff + jitter, up to `max_attempts` (5) |
| Provider unavailable (no key) | Fail immediately, `capability_unavailable:` |
| Budget exceeded | Fail immediately, `budget_exceeded`, no model call |
| Worker died | Lease expires → task back to `retrying` |
| Cancelled while running | Output discarded, recorded on the execution |

## Bounded iteration

Each run creates exactly 12 tasks; agents cannot create tasks. Retries are
capped. QA (agent 11) reports issues but does not trigger re-drafting
loops; people decide whether to edit (new version) or re-run.

## Dependency graph

```
cmo → research_analyst → marketing_manager → creative_studio → social_media, paid_media
research_analyst → customer_insights
marketing_manager → seo_growth, pr_partnerships, key_accounts
{creative, social, paid, seo, pr, customer_insights, key_accounts} → marketing_ops → record_keeper
```
