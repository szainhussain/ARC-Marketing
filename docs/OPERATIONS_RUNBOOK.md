# Operations Runbook

How to run, watch, and stop ARC's agent department.

## Processes

| Process | Command | Notes |
|---|---|---|
| Web/API | `flask run` (dev) or gunicorn (prod) | Never calls a model; only enqueues |
| Worker | `flask --app wsgi.py worker` | Executes agent tasks. Required for any run to progress |
| Worker, one pass | `flask --app wsgi.py worker --once` | Processes what's claimable now, then exits (cron/debug) |

Docker Compose starts a `worker` service alongside `backend`. Several
workers can run at once; task claims are atomic (see `docs/DECISIONS.md` D11).

## Task lifecycle

```
waiting_for_dependency ─▶ ready ─▶ running ─▶ succeeded
                                     │
                                     ├─▶ retrying ─▶ running ...   (rate limit, timeout, invalid output)
                                     └─▶ failed                    (no provider, budget, attempts exhausted)
failed ─(person clicks Retry)─▶ ready
any non-terminal ─(cancel)─▶ cancelled
```

Run statuses: `queued` → `running` → `completed` | `failed`; also
`paused`, `needs_input` (business profile incomplete), `cancelled`.

## Controls (Operations Center, `/app/operations`)

| Control | Who | Effect |
|---|---|---|
| Pause all agents (`automation_paused`) | owner, admin | Worker claims nothing in this workspace; running tasks finish |
| Kill switch (`kill_switch_enabled`) | owner, admin | Blocks all exports/handoffs; agents may still draft |
| Pause agent | owner, admin, marketing lead | That agent's tasks are skipped until resumed |
| Pause/resume/cancel run | owner, admin, marketing lead | Run-level; cancel discards in-flight output |
| Retry failed task | owner, admin, marketing lead | Resets attempts; re-opens a failed run |

There is also a deployment-wide kill switch: `KILL_SWITCH_ENABLED=true`.

## Common situations

**Run stuck in "Queued".** The worker isn't running. Start it; the
campaign page shows a banner when no task has been attempted.

**Tasks keep "Retrying".** Usually provider rate limits (Groq free tier is
8,000 tokens/minute). The task row shows when the next try is. Nothing to
do unless attempts run out; then fix the cause and click Retry.

**`capability_unavailable` failure.** No provider key configured
(`AI_PROVIDER` + `ANTHROPIC_API_KEY` / `GROQ_API_KEY`). Set it, restart
the worker, then Retry the failed task.

**`budget_exceeded`.** The run's estimated cost reached
`AI_WORKFLOW_BUDGET_USD` (default $1.00) or an agent's monthly budget.
Raise the limit deliberately or start a new run.

**Worker crashed mid-task.** Nothing to do: when the task's lease expires
(3 × `AI_TIMEOUT_SECONDS` + 30s) any worker puts it back in the queue.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `AI_TIMEOUT_SECONDS` | 60 | Per model call; also sets lease length |
| `AI_WORKFLOW_BUDGET_USD` | 1.00 | Estimated cost cap per run |
| `WORKER_RETRY_BASE_SECONDS` | 5 | Backoff base (doubles per attempt) |
| `WORKER_RETRY_MAX_SECONDS` | 120 | Backoff cap (provider retry-after can exceed it) |
