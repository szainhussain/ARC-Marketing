"""Durable, dependency-aware execution engine for the 12-agent department.

How it works
------------
* `enqueue_campaign_run` (called by the API) only *records* work: one
  WorkflowRun, one Task per agent, and TaskDependency rows. It never calls
  a model, so the HTTP request returns immediately with 202.
* A separate worker process (`flask worker`, see app/cli.py) repeatedly
  calls `work_once`: recover expired leases, claim one ready task with a
  conditional UPDATE (so two workers can never claim the same task), run
  the agent, persist the result, and unblock dependents.
* Everything lives in the database, so a crash or restart loses nothing:
  a task whose worker died is recovered when its lease expires.

There is deliberately no Redis/Celery: one DB-backed queue is enough at
this scale and removes a moving part (see docs/DECISIONS.md D11).
"""

import json
import logging
import random
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import func, or_, update

from app.agents.base import StageContext
from app.agents.registry import AGENTS, get_agent
from app.ai.errors import (
    AIProviderError,
    AIRequestTimeout,
    BudgetExceeded,
    InvalidOutput,
    ProviderUnavailable,
    RateLimited,
)
from app.ai.provider_adapter import get_provider
from app.extensions import db
from app.models.agent_execution import (
    EXEC_FAILED,
    EXEC_RUNNING,
    EXEC_SUCCEEDED,
    AgentExecution,
    AgentSetting,
)
from app.models.base import utcnow
from app.models.campaign import Campaign
from app.models.deliverable import Deliverable
from app.models.organization import Organization
from app.models.task import (
    CLAIMABLE_TASK_STATUSES,
    STATUS_CANCELLED as TASK_CANCELLED,
    STATUS_FAILED as TASK_FAILED,
    STATUS_READY,
    STATUS_RETRYING,
    STATUS_RUNNING as TASK_RUNNING,
    STATUS_SUCCEEDED,
    STATUS_WAITING_FOR_DEPENDENCY,
    TERMINAL_TASK_STATUSES,
    TASK_TRANSITIONS,
    Task,
    TaskDependency,
)
from app.models.workflow_run import (
    RUN_TRANSITIONS,
    STATUS_CANCELLED as RUN_CANCELLED,
    STATUS_COMPLETED as RUN_COMPLETED,
    STATUS_FAILED as RUN_FAILED,
    STATUS_AWAITING_APPROVAL as RUN_AWAITING_APPROVAL,
    STATUS_NEEDS_INPUT,
    STATUS_PAUSED,
    STATUS_QUEUED,
    STATUS_RUNNING as RUN_RUNNING,
    WorkflowRun,
)
from app.services.audit_service import record_audit_event
from app.services.deliverable_service import create_deliverable_with_first_version
from app.services.errors import Conflict, NotFound
from app.services.platform_service import (
    approved_knowledge_for_agents,
    check_entitlement,
    entitlements,
    get_policy_mode,
    notify,
    propose_knowledge_from_record,
)
from app.services.usage_service import check_monthly_workflow_limit, record_usage
from app.services.webhook_service import emit
from app.workflows.evaluation import evaluate_output
from app.workflows.state_machine import apply_transition

log = logging.getLogger(__name__)

WORKFLOW_TYPE = "campaign_department_v2"
CLAIMABLE_RUN_STATUSES = (STATUS_QUEUED, RUN_RUNNING)

# A rate limit isn't the task's fault, so it doesn't use up an attempt;
# it has its own, larger cap instead.
MAX_CONSECUTIVE_RATE_LIMITS = 15

# When the provider says "slow down", this worker process stops claiming
# anything until the cooldown passes, instead of firing the next ready
# task straight into the same limit. Per-process by design: each worker
# learns the limit from its own calls.
_provider_cooldown_until: datetime | None = None


# --------------------------------------------------------------------------
# Enqueue
# --------------------------------------------------------------------------

def enqueue_campaign_run(
    organization_id: str, campaign_id: str, user_id: str, idempotency_key: str
) -> WorkflowRun:
    existing = WorkflowRun.query.filter_by(
        organization_id=organization_id, idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing

    organization = db.session.get(Organization, organization_id)
    check_monthly_workflow_limit(organization)
    check_entitlement(organization_id, "monthly_workflow_runs")

    campaign = Campaign.query.filter_by(id=campaign_id, organization_id=organization_id).first()
    if campaign is None:
        raise NotFound("Campaign not found.")

    profile = organization.business_profile
    missing_fields = profile.completeness_warnings() if profile else ["business_profile"]

    run = WorkflowRun(
        organization_id=organization_id,
        campaign_id=campaign_id,
        started_by_user_id=user_id,
        idempotency_key=idempotency_key,
        workflow_type=WORKFLOW_TYPE,
        budget_usd=_run_budget(organization),
    )
    db.session.add(run)
    db.session.flush()

    tasks_by_agent: dict[str, Task] = {}
    for index, agent in enumerate(_topological_order()):
        task = Task(
            organization_id=organization_id,
            campaign_id=campaign_id,
            workflow_run_id=run.id,
            agent_id=agent.agent_id,
            stage=agent.agent_id,
            task_type=agent.task_type,
            title=f"{agent.name}: {', '.join(agent.outputs[:2])}",
            priority=agent.priority,
            sequence_index=index,
            max_attempts=agent.max_attempts,
            status=STATUS_READY if not agent.depends_on else STATUS_WAITING_FOR_DEPENDENCY,
        )
        db.session.add(task)
        tasks_by_agent[agent.agent_id] = task
    db.session.flush()

    for agent in AGENTS:
        for dep in agent.depends_on:
            db.session.add(
                TaskDependency(
                    task_id=tasks_by_agent[agent.agent_id].id,
                    depends_on_task_id=tasks_by_agent[dep].id,
                )
            )

    record_audit_event(
        organization_id, "workflow.started", actor_user_id=user_id,
        target_type="workflow_run", target_id=run.id,
    )

    if missing_fields:
        run.status = STATUS_NEEDS_INPUT
        run.error_summary = (
            "Business profile is missing required fields before a campaign "
            f"workflow can run: {', '.join(missing_fields)}."
        )
    elif get_policy_mode(organization_id, "agent_drafting") == "require_approval":
        run.status = RUN_AWAITING_APPROVAL
        notify(organization_id, "run.awaiting_start", "A campaign run is waiting for approval to start",
               f"{campaign.name}: an approver must start this run before agents begin work.",
               link=f"/app/campaigns/{campaign_id}", severity="warning")
    else:
        run.status = STATUS_QUEUED
    db.session.commit()
    return run


def _run_budget(organization: Organization) -> float:
    budget = organization.default_run_budget_usd or current_app.config.get("AI_WORKFLOW_BUDGET_USD", 1.0)
    plan_cap = entitlements(organization.id).get("max_run_budget_usd")
    return min(budget, plan_cap) if plan_cap is not None else budget


def approve_run_start(organization_id: str, run_id: str, user_id: str) -> WorkflowRun:
    run = get_run_or_404(organization_id, run_id)
    if run.status != RUN_AWAITING_APPROVAL:
        raise Conflict(f"This run is '{run.status}', not waiting to start.")
    apply_transition(run, STATUS_QUEUED, RUN_TRANSITIONS)
    record_audit_event(organization_id, "workflow.start_approved", actor_user_id=user_id,
                       target_type="workflow_run", target_id=run.id)
    db.session.commit()
    return run


def _topological_order():
    ordered, seen = [], set()

    def visit(agent):
        if agent.agent_id in seen:
            return
        for dep in agent.depends_on:
            visit(get_agent(dep))
        seen.add(agent.agent_id)
        ordered.append(agent)

    for agent in sorted(AGENTS, key=lambda a: a.priority):
        visit(agent)
    return ordered


# --------------------------------------------------------------------------
# Worker: claim / recover / execute
# --------------------------------------------------------------------------

def _lease_seconds() -> int:
    # The provider may make an initial + one repair call, each bounded by
    # the timeout; leave headroom so a slow-but-alive worker keeps its lease.
    return int(current_app.config.get("AI_TIMEOUT_SECONDS", 60)) * 3 + 30


def recover_expired_leases(now: datetime | None = None) -> int:
    """A task still 'running' past its lease belongs to a dead worker. Put
    it back in the queue (or fail it if it's out of attempts)."""

    now = now or utcnow()
    stale = Task.query.filter(
        Task.status == TASK_RUNNING, Task.lease_expires_at.isnot(None), Task.lease_expires_at < now
    ).all()
    for task in stale:
        _close_open_executions(task, "lease_expired", "Worker stopped before finishing this task.")
        task.lease_expires_at = None
        task.last_error_code = "lease_expired"
        if task.attempt_count >= task.max_attempts:
            task.status = TASK_FAILED
            task.error_summary = "Worker stopped repeatedly; attempts exhausted."
            task.completed_at = now
        else:
            task.status = STATUS_RETRYING
            task.next_attempt_at = None  # claimable immediately
            task.error_summary = "Recovered after worker interruption; will retry."
        record_audit_event(task.organization_id, "task.lease_recovered", target_type="task", target_id=task.id)
    if stale:
        db.session.commit()
        for task in stale:
            if task.status == TASK_FAILED:
                _refresh_run_status(task.workflow_run)
        db.session.commit()
    return len(stale)


def claim_next_task(now: datetime | None = None) -> Task | None:
    now = now or utcnow()
    paused_agents = (
        db.session.query(AgentSetting.id)
        .filter(
            AgentSetting.organization_id == Task.organization_id,
            AgentSetting.agent_id == Task.agent_id,
            AgentSetting.is_paused.is_(True),
        )
        .exists()
    )
    candidates = (
        Task.query.join(WorkflowRun, Task.workflow_run_id == WorkflowRun.id)
        .join(Organization, Task.organization_id == Organization.id)
        .filter(
            Task.status.in_(CLAIMABLE_TASK_STATUSES),
            or_(Task.next_attempt_at.is_(None), Task.next_attempt_at <= now),
            WorkflowRun.status.in_(CLAIMABLE_RUN_STATUSES),
            Organization.automation_paused.is_(False),
            ~paused_agents,
        )
        .order_by(Task.priority, Task.created_at)
        .limit(10)
        .all()
    )
    running_by_org: dict[str, int] = {}
    for candidate in candidates:
        org_id = candidate.organization_id
        if org_id not in running_by_org:
            running_by_org[org_id] = Task.query.filter_by(organization_id=org_id, status=TASK_RUNNING).count()
        limit = db.session.get(Organization, org_id).max_concurrent_tasks or 1
        if running_by_org[org_id] >= limit:
            continue  # workspace concurrency limit reached
        # Optimistic claim: only succeeds if nobody changed the row since we
        # read it. This is the single point that prevents double execution.
        result = db.session.execute(
            update(Task)
            .where(Task.id == candidate.id, Task.status == candidate.status)
            .values(
                status=TASK_RUNNING,
                attempt_count=Task.attempt_count + 1,
                lease_expires_at=now + timedelta(seconds=_lease_seconds()),
                started_at=now,
            )
        )
        if result.rowcount == 1:
            db.session.commit()
            task = db.session.get(Task, candidate.id)
            db.session.refresh(task)
            run = task.workflow_run
            if run.status == STATUS_QUEUED:
                run.status = RUN_RUNNING
                run.started_at = run.started_at or now
                db.session.commit()
            return task
        db.session.rollback()
    return None


def work_once() -> bool:
    """One worker iteration. Returns True if a task was processed."""

    recover_expired_leases()
    from app.services.webhook_service import deliver_due

    deliver_due()
    if _provider_cooldown_until and utcnow() < _provider_cooldown_until:
        return False
    task = claim_next_task()
    if task is None:
        return False
    execute_task(task)
    return True


def drain(max_iterations: int = 200) -> int:
    """Process until nothing is claimable right now (used by tests and the
    `flask worker --once` command)."""

    processed = 0
    while processed < max_iterations and work_once():
        processed += 1
    return processed


def execute_task(task: Task) -> None:
    agent = get_agent(task.agent_id)
    run = task.workflow_run
    org = db.session.get(Organization, task.organization_id)
    campaign = db.session.get(Campaign, task.campaign_id)
    profile = org.business_profile
    profile_dict = _compact(profile.to_dict() if profile else {})
    started = utcnow()

    execution = AgentExecution(
        organization_id=task.organization_id,
        task_id=task.id,
        workflow_run_id=run.id,
        agent_id=agent.agent_id,
        agent_version=agent.version,
        attempt_number=task.attempt_count,
        status=EXEC_RUNNING,
        correlation_id=run.id,
        started_at=started,
    )
    db.session.add(execution)
    db.session.commit()

    budget_error = _budget_error(run, agent.agent_id, task.organization_id)
    if budget_error:
        _fail(task, execution, "budget_exceeded", budget_error, retry=False)
        return

    ctx = StageContext(
        organization_id=task.organization_id,
        campaign=_compact(campaign.to_dict()),
        business_profile=profile_dict,
        upstream_outputs=_upstream_outputs(run, agent.reads),
        budget_usd=max(0.0, (run.budget_usd or 1.0) - (run.estimated_cost_usd or 0.0)),
        timeout_seconds=current_app.config.get("AI_TIMEOUT_SECONDS", 60),
        correlation_id=run.id,
        evaluation_flags=_evaluation_flags(run) if agent.agent_id == "marketing_ops" else [],
        knowledge=approved_knowledge_for_agents(task.organization_id)
        if agent.agent_id in ("cmo", "marketing_manager") else [],
    )

    provider = get_provider(current_app.config)
    try:
        result = agent.run(provider, ctx)
    except ProviderUnavailable as exc:
        _fail(task, execution, "capability_unavailable", f"capability_unavailable: {exc}", retry=False)
        return
    except RateLimited as exc:
        _handle_rate_limit(task, execution, exc)
        return
    except AIRequestTimeout as exc:
        _fail(task, execution, "timeout", f"AIRequestTimeout: {exc}", retry=True)
        return
    except InvalidOutput as exc:
        # Model output varies between calls, so a fresh attempt often passes.
        _fail(task, execution, "invalid_output", f"InvalidOutput: {exc}", retry=True)
        return
    except BudgetExceeded as exc:
        _fail(task, execution, "budget_exceeded", f"BudgetExceeded: {exc}", retry=False)
        return
    except AIProviderError as exc:
        _fail(task, execution, "provider_error", f"{type(exc).__name__}: {exc}", retry=True)
        return

    # The run or task may have been cancelled/paused while the model was
    # working. Re-read before writing anything.
    db.session.refresh(task)
    db.session.refresh(run)
    if task.status != TASK_RUNNING:
        execution.status = EXEC_FAILED
        execution.error_code = "discarded"
        execution.error_summary = f"Output discarded: task became '{task.status}' while running."
        execution.finished_at = utcnow()
        db.session.commit()
        return

    evaluation = evaluate_output(agent.evaluation_checks, result.data, profile_dict)

    deliverable = create_deliverable_with_first_version(
        organization_id=task.organization_id,
        campaign_id=task.campaign_id,
        workflow_run_id=run.id,
        deliverable_type=agent.task_type,
        content=result.data,
        created_by_run_id=run.id,
    )
    record_usage(
        organization_id=task.organization_id,
        workflow_run_id=run.id,
        provider=result.provider,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
    )
    run.estimated_cost_usd = (run.estimated_cost_usd or 0.0) + result.estimated_cost_usd
    emit(task.organization_id, "deliverable.created",
         {"deliverable_id": deliverable.id, "deliverable_type": agent.task_type, "campaign_id": task.campaign_id,
          "run_id": run.id, "agent_id": agent.agent_id})

    now = utcnow()
    execution.status = EXEC_SUCCEEDED
    execution.provider = result.provider
    execution.model = result.model
    execution.input_tokens = result.input_tokens
    execution.output_tokens = result.output_tokens
    execution.estimated_cost_usd = result.estimated_cost_usd
    execution.evaluation_json = json.dumps(evaluation)
    failed_checks = [e["check"] for e in evaluation if not e["passed"]]
    execution.summary = (
        f"Produced {agent.task_type} v1"
        + (f"; failed checks: {', '.join(failed_checks)}" if failed_checks else "")
    )
    execution.finished_at = now

    task.status = STATUS_SUCCEEDED
    task.deliverable_id = deliverable.id
    task.completed_at = now
    task.lease_expires_at = None
    task.error_summary = None
    task.last_error_code = None
    db.session.flush()

    if agent.agent_id == "record_keeper":
        count = propose_knowledge_from_record(task.organization_id, run.id, deliverable.id, result.data)
        if count:
            notify(task.organization_id, "knowledge.proposed",
                   f"{count} learning(s) proposed for the knowledge library",
                   "The Record Keeper extracted learnings from this run. Review them before agents use them.",
                   link="/app/knowledge")

    _unblock_dependents(task)
    _refresh_run_status(run)
    db.session.commit()
    from app.services.billing_service import check_budget_alerts

    check_budget_alerts(task.organization_id)
    db.session.commit()


# Provider error text can include account ids and raw JSON; users see these
# plain messages and the raw text goes to the server log only.
_SAFE_MESSAGES = {
    "rate_limited": "The AI provider's rate limit was reached; this task retries automatically.",
    "timeout": "The AI provider took too long to respond; this task retries automatically.",
    "provider_error": "The AI provider returned an error; this task retries automatically.",
}


def _fail(task, execution, code, summary, retry, retry_after=None):
    if code in _SAFE_MESSAGES:
        log.warning("Task %s (%s) %s: %s", task.id, task.agent_id, code, summary)
        summary = _SAFE_MESSAGES[code]
    now = utcnow()
    execution.status = EXEC_FAILED
    execution.error_code = code
    execution.error_summary = summary[:2000]
    execution.finished_at = now

    db.session.refresh(task)
    task.lease_expires_at = None
    task.last_error_code = code
    task.error_summary = summary[:2000]
    if task.status != TASK_RUNNING:
        db.session.commit()
        return
    if retry and task.attempt_count < task.max_attempts:
        task.status = STATUS_RETRYING
        task.next_attempt_at = now + timedelta(seconds=_backoff_seconds(task.attempt_count, retry_after))
    else:
        task.status = TASK_FAILED
        task.completed_at = now
        if retry:
            task.error_summary = f"Gave up after {task.attempt_count} attempts. Last error: {summary}"[:2000]
    db.session.flush()
    _refresh_run_status(task.workflow_run)
    db.session.commit()


def _handle_rate_limit(task: Task, execution: AgentExecution, exc: RateLimited) -> None:
    global _provider_cooldown_until

    previous = (
        AgentExecution.query.filter(AgentExecution.task_id == task.id, AgentExecution.id != execution.id)
        .order_by(AgentExecution.attempt_number.desc(), AgentExecution.started_at.desc())
        .all()
    )
    consecutive = 1
    for prior in previous:
        if prior.error_code != "rate_limited":
            break
        consecutive += 1

    summary = f"RateLimited: {exc}"
    if consecutive >= MAX_CONSECUTIVE_RATE_LIMITS:
        log.warning("Task %s rate-limited %s times in a row: %s", task.id, consecutive, summary)
        _fail(task, execution, "rate_limit_persistent",
              f"The AI provider's rate limit persisted across {consecutive} tries. "
              "Retry later, or use a provider plan with a higher limit.", retry=False)
        return

    delay = _backoff_seconds(consecutive, exc.retry_after_seconds)
    if exc.retry_after_seconds:
        _provider_cooldown_until = utcnow() + timedelta(seconds=exc.retry_after_seconds)
    # Refund the attempt: rate limits are capped separately above.
    db.session.refresh(task)
    if task.status == TASK_RUNNING:
        task.attempt_count = max(0, task.attempt_count - 1)
        db.session.flush()  # _fail re-reads the task; keep the refund
    _fail(task, execution, "rate_limited", summary, retry=True, retry_after=delay)


def _backoff_seconds(attempt: int, retry_after: float | None) -> float:
    base = float(current_app.config.get("WORKER_RETRY_BASE_SECONDS", 5))
    cap = float(current_app.config.get("WORKER_RETRY_MAX_SECONDS", 120))
    exponential = min(cap, base * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0, base / 2) if base else 0
    return max(exponential, retry_after or 0) + jitter


def _budget_error(run: WorkflowRun, agent_id: str, organization_id: str) -> str | None:
    from app.services.platform_service import usage_against_entitlements

    usage = usage_against_entitlements(organization_id)
    ai = usage.get("monthly_ai_budget_usd") or {}
    if ai.get("limit") is not None and ai["used"] >= ai["limit"]:
        return f"This month's plan AI budget (${ai['limit']:.2f} estimated) is used up."
    quota = usage.get("monthly_agent_executions") or {}
    # The execution row for this attempt already exists, hence ">".
    if quota.get("limit") is not None and quota["used"] > quota["limit"]:
        return f"This month's plan quota of {quota['limit']} agent executions is used up."
    if run.budget_usd is not None and (run.estimated_cost_usd or 0) >= run.budget_usd:
        return (
            f"Run budget of ${run.budget_usd:.2f} (estimated) is used up; "
            "raise the budget or approve a new run."
        )
    setting = AgentSetting.query.filter_by(organization_id=organization_id, agent_id=agent_id).first()
    if setting and setting.monthly_budget_usd is not None:
        month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = (
            db.session.query(func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0))
            .filter(
                AgentExecution.organization_id == organization_id,
                AgentExecution.agent_id == agent_id,
                AgentExecution.started_at >= month_start,
            )
            .scalar()
        )
        if spent >= setting.monthly_budget_usd:
            return f"Agent monthly budget of ${setting.monthly_budget_usd:.2f} (estimated) is used up."
    return None


def _close_open_executions(task: Task, code: str, summary: str) -> None:
    for execution in AgentExecution.query.filter_by(task_id=task.id, status=EXEC_RUNNING).all():
        execution.status = EXEC_FAILED
        execution.error_code = code
        execution.error_summary = summary
        execution.finished_at = utcnow()


def _compact(data: dict) -> dict:
    return {k: v for k, v in data.items() if v not in (None, "", [], {})}


def _upstream_outputs(run: WorkflowRun, reads: tuple[str, ...]) -> dict[str, dict]:
    """Only agents in the allowlist — this is the enforcement point for
    each agent's `reads` permission."""

    outputs = {}
    for task in run.tasks:
        if task.agent_id in reads and task.status == STATUS_SUCCEEDED and task.deliverable_id:
            deliverable = db.session.get(Deliverable, task.deliverable_id)
            if deliverable and deliverable.current_version:
                outputs[task.agent_id] = json.loads(deliverable.current_version.content_json)
    return outputs


def _evaluation_flags(run: WorkflowRun) -> list[dict]:
    flags = []
    for execution in AgentExecution.query.filter_by(workflow_run_id=run.id, status=EXEC_SUCCEEDED):
        for item in json.loads(execution.evaluation_json or "[]"):
            if not item.get("passed"):
                flags.append({"agent_id": execution.agent_id, **item})
    return flags


def _unblock_dependents(completed: Task) -> None:
    dependents = (
        Task.query.join(TaskDependency, TaskDependency.task_id == Task.id)
        .filter(TaskDependency.depends_on_task_id == completed.id)
        .all()
    )
    for task in dependents:
        if task.status == STATUS_WAITING_FOR_DEPENDENCY and all(
            dep.status == STATUS_SUCCEEDED for dep in task.dependencies
        ):
            task.status = STATUS_READY


def _refresh_run_status(run: WorkflowRun) -> None:
    if run.status in (RUN_CANCELLED, RUN_COMPLETED, STATUS_PAUSED, STATUS_NEEDS_INPUT):
        return
    tasks = run.tasks
    if tasks and all(t.status == STATUS_SUCCEEDED for t in tasks):
        run.status = RUN_COMPLETED
        run.completed_at = utcnow()
        run.error_summary = None
        record_audit_event(run.organization_id, "workflow.completed", target_type="workflow_run", target_id=run.id)
        notify(run.organization_id, "run.completed", "Your marketing team finished a campaign run",
               "All 12 agents delivered drafts. Review them and request approval for anything you want to use.",
               link=f"/app/campaigns/{run.campaign_id}", severity="success")
        emit(run.organization_id, "run.completed", {"run_id": run.id, "campaign_id": run.campaign_id,
                                                    "estimated_cost_usd": round(run.estimated_cost_usd or 0, 4)})
        return
    in_flight = any(t.status in (STATUS_READY, STATUS_RETRYING, TASK_RUNNING) for t in tasks)
    failed = [t for t in tasks if t.status in (TASK_FAILED, TASK_CANCELLED)]
    if failed and not in_flight:
        run.status = RUN_FAILED
        run.completed_at = utcnow()
        names = ", ".join(sorted(t.agent_id for t in failed))
        codes = {t.last_error_code for t in failed}
        prefix = "capability_unavailable: " if "capability_unavailable" in codes else ""
        run.error_summary = f"{prefix}Stopped: {names} failed; dependent agents are waiting."
        notify(run.organization_id, "run.failed", "A campaign run needs attention",
               run.error_summary, link=f"/app/campaigns/{run.campaign_id}", severity="error")
        emit(run.organization_id, "run.failed", {"run_id": run.id, "campaign_id": run.campaign_id,
                                                 "failed_agents": sorted(t.agent_id for t in failed)})
    elif run.status == RUN_FAILED and in_flight:
        run.status = RUN_RUNNING
        run.completed_at = None


# --------------------------------------------------------------------------
# Human controls (called from the API; every caller has already passed
# get_membership_or_403 and any role check).
# --------------------------------------------------------------------------

def get_run_or_404(organization_id: str, run_id: str) -> WorkflowRun:
    run = WorkflowRun.query.filter_by(id=run_id, organization_id=organization_id).first()
    if run is None:
        raise NotFound("Workflow run not found.")
    return run


def get_task_or_404(organization_id: str, task_id: str) -> Task:
    task = Task.query.filter_by(id=task_id, organization_id=organization_id).first()
    if task is None:
        raise NotFound("Task not found.")
    return task


def pause_run(organization_id: str, run_id: str, user_id: str) -> WorkflowRun:
    run = get_run_or_404(organization_id, run_id)
    apply_transition(run, STATUS_PAUSED, RUN_TRANSITIONS)
    record_audit_event(organization_id, "workflow.paused", actor_user_id=user_id,
                       target_type="workflow_run", target_id=run.id)
    db.session.commit()
    return run


def resume_run(organization_id: str, run_id: str, user_id: str) -> WorkflowRun:
    run = get_run_or_404(organization_id, run_id)
    started = any(t.status != STATUS_READY and t.status != STATUS_WAITING_FOR_DEPENDENCY for t in run.tasks)
    apply_transition(run, RUN_RUNNING if started else STATUS_QUEUED, RUN_TRANSITIONS)
    record_audit_event(organization_id, "workflow.resumed", actor_user_id=user_id,
                       target_type="workflow_run", target_id=run.id)
    _refresh_run_status(run)
    db.session.commit()
    return run


def cancel_run(organization_id: str, run_id: str, user_id: str) -> WorkflowRun:
    run = get_run_or_404(organization_id, run_id)
    apply_transition(run, RUN_CANCELLED, RUN_TRANSITIONS)
    run.completed_at = utcnow()
    for task in run.tasks:
        if task.status not in TERMINAL_TASK_STATUSES:
            task.status = TASK_CANCELLED
            task.lease_expires_at = None
    record_audit_event(organization_id, "workflow.cancelled", actor_user_id=user_id,
                       target_type="workflow_run", target_id=run.id)
    db.session.commit()
    return run


def retry_task(organization_id: str, task_id: str, user_id: str) -> Task:
    task = get_task_or_404(organization_id, task_id)
    run = task.workflow_run
    if run.status == RUN_CANCELLED:
        raise Conflict("This run was cancelled; start a new run instead.")
    if task.status != TASK_FAILED:
        raise Conflict(f"Only failed tasks can be retried (this one is '{task.status}').")
    apply_transition(task, STATUS_READY, TASK_TRANSITIONS)
    task.attempt_count = 0
    task.next_attempt_at = None
    task.completed_at = None
    task.error_summary = None
    if run.status == RUN_FAILED:
        run.status = RUN_RUNNING
        run.completed_at = None
        run.error_summary = None
    record_audit_event(organization_id, "task.retried", actor_user_id=user_id,
                       target_type="task", target_id=task.id)
    db.session.commit()
    return task


def cancel_task(organization_id: str, task_id: str, user_id: str) -> Task:
    task = get_task_or_404(organization_id, task_id)
    apply_transition(task, TASK_CANCELLED, TASK_TRANSITIONS)
    task.completed_at = utcnow()
    task.lease_expires_at = None
    record_audit_event(organization_id, "task.cancelled", actor_user_id=user_id,
                       target_type="task", target_id=task.id)
    db.session.flush()
    _refresh_run_status(task.workflow_run)
    db.session.commit()
    return task


def set_agent_paused(organization_id: str, agent_id: str, paused: bool, user_id: str) -> AgentSetting:
    if get_agent(agent_id) is None:
        raise NotFound("Agent not found.")
    setting = AgentSetting.query.filter_by(organization_id=organization_id, agent_id=agent_id).first()
    if setting is None:
        setting = AgentSetting(organization_id=organization_id, agent_id=agent_id)
        db.session.add(setting)
    setting.is_paused = paused
    record_audit_event(organization_id, "agent.paused" if paused else "agent.resumed",
                       actor_user_id=user_id, target_type="agent", target_id=agent_id)
    db.session.commit()
    return setting
