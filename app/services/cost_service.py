"""What a workspace's AI work costs, and how close it is to its plan's AI
budget (docs/DECISIONS.md D22). All amounts are estimates from token counts
and the configured prices; none is an invoice figure."""

from collections import defaultdict
from datetime import timedelta

from app.models.agent_execution import AgentExecution
from app.models.base import utcnow
from app.models.campaign import Campaign
from app.models.task import Task
from app.models.usage_record import UsageRecord
from app.services.platform_service import entitlements

WARN_AT_PCT = 80


def cost_report(organization_id: str, days: int = 30) -> dict:
    now = utcnow()
    start = now - timedelta(days=max(1, min(days, 365)))
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    usage = UsageRecord.query.filter(UsageRecord.organization_id == organization_id,
                                     UsageRecord.created_at >= start).all()
    by_model = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for u in usage:
        m = by_model[(u.provider or "unknown", u.model or "unknown")]
        m["calls"] += 1
        m["input_tokens"] += u.input_tokens or 0
        m["output_tokens"] += u.output_tokens or 0
        m["cost_usd"] += u.estimated_cost_usd or 0.0

    execs = AgentExecution.query.filter(AgentExecution.organization_id == organization_id,
                                        AgentExecution.started_at >= start).all()
    task_campaign = dict(Task.query.with_entities(Task.id, Task.campaign_id)
                         .filter(Task.organization_id == organization_id).all()) if execs else {}
    names = {c.id: c.name for c in Campaign.query.filter_by(organization_id=organization_id)}
    by_campaign = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0, "failed_calls": 0})
    for e in execs:
        c = by_campaign[task_campaign.get(e.task_id)]
        c["calls"] += 1
        c["cost_usd"] += e.estimated_cost_usd or 0.0
        c["failed_calls"] += 1 if e.status == "failed" else 0
    tasks_touched = {e.task_id for e in execs}
    failed = [e for e in execs if e.status == "failed"]
    errors = defaultdict(int)
    for e in failed:
        errors[e.error_code or "unknown"] += 1

    month_cost = sum(u.estimated_cost_usd or 0.0 for u in UsageRecord.query.filter(
        UsageRecord.organization_id == organization_id, UsageRecord.created_at >= month_start))
    allowance = entitlements(organization_id).get("monthly_ai_budget_usd")
    used_pct = round(month_cost / allowance * 100, 1) if allowance else None
    level = "none" if used_pct is None else "over" if used_pct >= 100 else "warning" if used_pct >= WARN_AT_PCT else "ok"

    total_cost = sum(m["cost_usd"] for m in by_model.values())
    return {
        "range_days": days,
        "basis": "Estimates from token counts and configured prices. Not an invoice.",
        "totals": {
            "calls": sum(m["calls"] for m in by_model.values()),
            "input_tokens": sum(m["input_tokens"] for m in by_model.values()),
            "output_tokens": sum(m["output_tokens"] for m in by_model.values()),
            "cost_usd": round(total_cost, 4),
        },
        "by_model": sorted(({"provider": p, "model": m, **v, "cost_usd": round(v["cost_usd"], 4)}
                            for (p, m), v in by_model.items()), key=lambda r: -r["cost_usd"]),
        "by_campaign": sorted(({"campaign_id": cid, "campaign_name": names.get(cid) or "Other work", **v,
                                "cost_usd": round(v["cost_usd"], 4)} for cid, v in by_campaign.items()),
                              key=lambda r: -r["cost_usd"]),
        "reliability": {
            "agent_calls": len(execs),
            "failed_calls": len(failed),
            "repeated_calls": sum(1 for e in execs if (e.attempt_number or 1) > 1),
            "calls_per_task": round(len(execs) / len(tasks_touched), 2) if tasks_touched else None,
            "failures_by_reason": dict(errors),
        },
        "budget": {
            "month_cost_usd": round(month_cost, 4),
            "monthly_allowance_usd": allowance,
            "used_pct": used_pct,
            "level": level,
            "message": {
                "over": "This month's AI budget is used up. New runs stop until next month or a plan change.",
                "warning": f"{used_pct}% of this month's AI budget is used.",
                "ok": f"{used_pct}% of this month's AI budget is used.",
                "none": "Your plan has no fixed monthly AI budget.",
            }[level],
        },
        "not_tracked": ["Cached versus uncached tokens (the provider figures are not recorded yet)."],
    }
