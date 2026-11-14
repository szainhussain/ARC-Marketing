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
from app.models.platform import Notification
from app.services.platform_service import entitlements, notify

WARN_AT_PCT = 80


def cost_report(organization_id: str, days: int = 30) -> dict:
    now = utcnow()
    start = now - timedelta(days=max(1, min(days, 365)))
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    usage = UsageRecord.query.filter(UsageRecord.organization_id == organization_id,
                                     UsageRecord.created_at >= start).all()
    by_model = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for u in usage:
        m = by_model[(u.provider or "unknown", u.model or "unknown")]
        m["calls"] += 1
        m["input_tokens"] += u.input_tokens or 0
        m["cached_input_tokens"] += u.cached_input_tokens or 0
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
            "cached_input_tokens": sum(m["cached_input_tokens"] for m in by_model.values()),
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
        "cache_note": "Cached tokens are counted when the AI provider reports them; zero can mean the provider "
                      "did not cache or does not report it.",
    }


def _month_cost(organization_id: str, month_start) -> float:
    return sum(u.estimated_cost_usd or 0.0 for u in UsageRecord.query.filter(
        UsageRecord.organization_id == organization_id, UsageRecord.created_at >= month_start))


def notify_budget_if_crossed(organization_id: str) -> str | None:
    """One workspace notification the first time a month's AI spend passes 80%,
    and one when it reaches the plan's allowance. Returns the kind it raised."""

    allowance = entitlements(organization_id).get("monthly_ai_budget_usd")
    if not allowance:
        return None
    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used_pct = _month_cost(organization_id, month_start) / allowance * 100
    if used_pct >= 100:
        kind, title, severity = "ai_budget.reached", "This month's AI budget is used up", "error"
        body = "New runs stop until next month or a plan change."
    elif used_pct >= WARN_AT_PCT:
        kind, title, severity = "ai_budget.warning", f"{used_pct:.0f}% of this month's AI budget is used", "warning"
        body = "Runs continue until the budget is reached."
    else:
        return None
    already = Notification.query.filter(Notification.organization_id == organization_id, Notification.kind == kind,
                                        Notification.created_at >= month_start).first()
    if already:
        return None
    notify(organization_id, kind, title, body, link="/app/settings/usage", severity=severity)
    return kind


def platform_unit_economics() -> list[dict]:
    """For the platform owner only: what each workspace pays against what its AI
    work cost this month. Revenue counts only for active (paying) subscriptions."""

    from app.models.organization import Organization
    from app.services.platform_service import get_subscription

    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = []
    for org in Organization.query.order_by(Organization.created_at.desc()).limit(500):
        sub = get_subscription(org.id)
        price = sub.plan.monthly_price_usd if sub.plan else None
        revenue = price if sub.status == "active" and price else 0.0
        cost = round(_month_cost(org.id, month_start), 4)
        rows.append({
            "organization_id": org.id, "name": org.name, "plan": sub.plan.name if sub.plan else None,
            "status": sub.status, "list_price_usd": price, "revenue_usd": revenue, "ai_cost_usd": cost,
            "gross_margin_usd": round(revenue - cost, 2),
            "gross_margin_pct": round((revenue - cost) / revenue * 100, 1) if revenue else None,
        })
    return rows
