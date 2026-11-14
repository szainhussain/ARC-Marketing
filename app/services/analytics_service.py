"""Analytics for the Business Command Center and Analytics page.

Two kinds of metric are kept apart (brief §20):
- Platform metrics: computed from this database (tasks, executions,
  approvals, runs). `basis` is "observed", except AI cost which is
  "estimate" (placeholder per-token prices).
- Business metrics (spend, leads, conversions, revenue, CPA, ROAS, traffic,
  engagement): need a connected source. None is connected yet, so each is
  returned with `available: false` and the source it would need, never a
  made-up number.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.agents.registry import AGENTS_BY_ID
from app.extensions import db
from app.models.agent_execution import AgentExecution
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.campaign import Campaign
from app.models.deliverable import Deliverable
from app.models.external_action import ExternalAction
from app.models.organization import Organization
from app.models.platform import CalendarEntry, KnowledgeEntry
from app.models.task import Task
from app.models.workflow_run import WorkflowRun

BUSINESS_METRICS = [
    ("marketing_spend", "Marketing spend", "Ad platform APIs (Google Ads, Meta Ads)"),
    ("leads", "Leads", "CRM or form integration"),
    ("conversions", "Conversions", "GA4 or ad platform conversion tracking"),
    ("conversion_rate", "Conversion rate", "GA4"),
    ("cpa", "Cost per acquisition", "Ad spend + conversion tracking"),
    ("revenue_attributed", "Revenue attributed", "E-commerce/CRM + attribution model"),
    ("roas", "Return on ad spend", "Ad spend + revenue attribution"),
    ("website_traffic", "Website traffic", "GA4"),
    ("engagement", "Social engagement", "Social platform analytics APIs"),
]


# Business metric key -> (field in the manual results summary, unit).
_MANUAL_METRIC = {"marketing_spend": ("spend", "usd"), "leads": ("leads", None), "conversions": ("conversions", None),
                  "conversion_rate": ("conversion_rate_pct", "%"), "cpa": ("cost_per_acquisition", "usd"),
                  "revenue_attributed": ("revenue", "usd"), "roas": ("roas", "x")}


def _business_metrics(organization_id, start, end, campaign_id):
    """Business numbers come only from results the team entered (labelled
    "manual") until a data source is connected, never estimated."""

    from app.services.results_service import summarize

    totals = summarize(organization_id, start.date(), end.date(), campaign_id)["totals"]
    out = []
    for k, label, source in BUSINESS_METRICS:
        field, unit = _MANUAL_METRIC.get(k, (None, None))
        value = totals.get(field) if field else None
        if value is not None:
            out.append({"key": k, "label": label, "available": True, "value": value, "unit": unit,
                        "status": "manual", "requires": source, "link": "/app/results"})
        else:
            out.append({"key": k, "label": label, "available": False, "value": None, "status": "not_connected",
                        "requires": source, "link": "/app/results" if field else "/app/integrations"})
    return out


def _window(days: int):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end, start - timedelta(days=days)


def _change(current, previous):
    if previous in (None, 0) or current is None:
        return None
    return round((current - previous) / previous * 100, 1)


def _count(model, org_id, start, end, *filters, date_col=None):
    col = date_col if date_col is not None else model.created_at
    return model.query.filter(model.organization_id == org_id, col >= start, col < end, *filters).count()


def dashboard(organization_id: str, days: int = 30, campaign_id: str | None = None) -> dict:
    start, end, prev_start = _window(days)

    def scoped(q, model):
        if campaign_id and hasattr(model, "campaign_id"):
            return q.filter(model.campaign_id == campaign_id)
        return q

    def count(model, s, e, *filters, date_col=None):
        col = date_col if date_col is not None else model.created_at
        q = model.query.filter(model.organization_id == organization_id, col >= s, col < e, *filters)
        return scoped(q, model).count()

    def cost(s, e):
        q = db.session.query(func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0)).filter(
            AgentExecution.organization_id == organization_id, AgentExecution.started_at >= s,
            AgentExecution.started_at < e)
        if campaign_id:
            q = q.join(Task, Task.id == AgentExecution.task_id).filter(Task.campaign_id == campaign_id)
        return round(float(q.scalar() or 0), 4)

    tasks_done = count(Task, start, end, Task.status == "succeeded", date_col=Task.completed_at)
    tasks_done_prev = count(Task, prev_start, start, Task.status == "succeeded", date_col=Task.completed_at)
    runs_completed = count(WorkflowRun, start, end, WorkflowRun.status == "completed")
    runs_failed = count(WorkflowRun, start, end, WorkflowRun.status == "failed")
    prev_completed = count(WorkflowRun, prev_start, start, WorkflowRun.status == "completed")
    prev_failed = count(WorkflowRun, prev_start, start, WorkflowRun.status == "failed")
    success = round(runs_completed / (runs_completed + runs_failed) * 100, 1) if runs_completed + runs_failed else None
    success_prev = round(prev_completed / (prev_completed + prev_failed) * 100, 1) if prev_completed + prev_failed else None
    exports = ExternalAction.query.filter(ExternalAction.organization_id == organization_id,
                                          ExternalAction.created_at >= start).count()
    exports_prev = ExternalAction.query.filter(ExternalAction.organization_id == organization_id,
                                               ExternalAction.created_at >= prev_start,
                                               ExternalAction.created_at < start).count()
    published_confirmed = ExternalAction.query.filter(
        ExternalAction.organization_id == organization_id,
        ExternalAction.publication_status == "manually_confirmed_published",
        ExternalAction.created_at >= start).count()

    camp_q = Campaign.query.filter_by(organization_id=organization_id)
    if campaign_id:
        camp_q = camp_q.filter_by(id=campaign_id)
    campaigns = camp_q.order_by(Campaign.updated_at.desc()).all()
    pending_approvals = Approval.query.filter_by(organization_id=organization_id, decision="pending").count()
    awaiting_review = scoped(Deliverable.query.filter_by(organization_id=organization_id, review_status="draft"),
                             Deliverable).count()
    c, cp = cost(start, end), cost(prev_start, start)

    kpis = [
        _kpi("active_campaigns", "Active campaigns", sum(1 for x in campaigns if x.status != "archived"), None,
             "Campaigns not archived.", "/app/campaigns"),
        _kpi("runs_completed", "Campaign runs completed", runs_completed, prev_completed,
             "Runs where every agent delivered its draft.", "/app/campaigns"),
        _kpi("tasks_completed", "Agent tasks completed", tasks_done, tasks_done_prev,
             "Succeeded agent tasks in the period.", "/app/tasks?status=succeeded"),
        _kpi("approvals_pending", "Awaiting your approval", pending_approvals, None,
             "Decisions waiting in the approval inbox.", "/app/approvals"),
        _kpi("content_awaiting_review", "Drafts awaiting review", awaiting_review, None,
             "Deliverables still in draft review status.", "/app/content"),
        _kpi("content_exported", "Content exported for publishing", exports, exports_prev,
             f"{published_confirmed} confirmed published by your team.", "/app/content"),
        _kpi("workflow_success_rate", "Workflow success rate", success, success_prev,
             "Completed ÷ (completed + failed) runs.", "/app/operations", unit="%"),
        _kpi("agent_cost", "Agent execution cost", c, cp, "Estimated from token usage; not an invoice.",
             "/app/settings/usage", unit="usd", basis="estimate"),
    ]
    business = _business_metrics(organization_id, start, end, campaign_id)

    return {
        "range": {"days": days, "start": start.isoformat(), "end": end.isoformat()},
        "kpis": kpis,
        "business_metrics": business,
        "series": _daily_series(organization_id, start, days, campaign_id),
        "cost_by_agent": _cost_by_agent(organization_id, start, campaign_id),
        "campaigns": [_campaign_card(x) for x in campaigns[:12]],
        "needs_attention": _needs_attention(organization_id),
        "upcoming": _upcoming(organization_id),
        "recent_deliverables": _recent_deliverables(organization_id, campaign_id),
        "recommendations": _recommendations(organization_id, campaigns),
    }


def _kpi(key, label, value, previous, explanation, link, unit=None, basis="observed"):
    return {"key": key, "label": label, "value": value, "previous": previous,
            "change_pct": _change(value, previous), "explanation": explanation, "link": link,
            "unit": unit, "basis": basis}


def _daily_series(org_id, start, days, campaign_id):
    buckets = defaultdict(lambda: {"tasks_succeeded": 0, "tasks_failed": 0, "cost_usd": 0.0, "retries": 0})
    q = AgentExecution.query.filter(AgentExecution.organization_id == org_id, AgentExecution.started_at >= start)
    if campaign_id:
        q = q.join(Task, Task.id == AgentExecution.task_id).filter(Task.campaign_id == campaign_id)
    for e in q.all():
        day = e.started_at.date().isoformat()
        b = buckets[day]
        b["cost_usd"] += e.estimated_cost_usd or 0
        if e.status == "succeeded":
            b["tasks_succeeded"] += 1
        elif e.status == "failed":
            b["tasks_failed"] += 1
            if e.error_code in ("rate_limited", "timeout", "invalid_output", "provider_error"):
                b["retries"] += 1
    out = []
    first = start.date()
    for i in range(days + 1):
        day = (first + timedelta(days=i)).isoformat()
        b = buckets.get(day, {"tasks_succeeded": 0, "tasks_failed": 0, "cost_usd": 0.0, "retries": 0})
        out.append({"date": day, **b, "cost_usd": round(b["cost_usd"], 4)})
    return out


def _cost_by_agent(org_id, start, campaign_id):
    q = db.session.query(AgentExecution.agent_id, func.count(AgentExecution.id),
                         func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0),
                         func.coalesce(func.sum(AgentExecution.input_tokens + AgentExecution.output_tokens), 0)
                         ).filter(AgentExecution.organization_id == org_id, AgentExecution.started_at >= start)
    if campaign_id:
        q = q.join(Task, Task.id == AgentExecution.task_id).filter(Task.campaign_id == campaign_id)
    rows = q.group_by(AgentExecution.agent_id).all()
    return sorted([{"agent_id": a, "agent_name": AGENTS_BY_ID[a].name if a in AGENTS_BY_ID else a,
                    "number": AGENTS_BY_ID[a].number if a in AGENTS_BY_ID else 0, "executions": n,
                    "cost_usd": round(float(cost), 4), "tokens": int(tokens)} for a, n, cost, tokens in rows],
                  key=lambda r: r["number"])


def _campaign_card(c: Campaign) -> dict:
    run = WorkflowRun.query.filter_by(campaign_id=c.id).order_by(WorkflowRun.created_at.desc()).first()
    tasks = run.tasks if run else []
    done = sum(1 for t in tasks if t.status == "succeeded")
    deliverables = Deliverable.query.filter_by(campaign_id=c.id).count()
    pending = (Approval.query.join(Deliverable, Deliverable.id == Approval.deliverable_id)
               .filter(Deliverable.campaign_id == c.id, Approval.decision == "pending").count())
    return {
        "id": c.id, "name": c.name, "objective": c.objective, "status": c.status,
        "start_date": c.start_date.isoformat() if getattr(c, "start_date", None) and hasattr(c.start_date, "isoformat") else c.start_date,
        "end_date": c.end_date.isoformat() if getattr(c, "end_date", None) and hasattr(c.end_date, "isoformat") else c.end_date,
        "budget_guidance": c.budget_guidance,
        "run_status": run.status if run else None,
        "progress_pct": round(done / len(tasks) * 100) if tasks else 0,
        "agents_done": done, "agents_total": len(tasks),
        "deliverables": deliverables, "pending_decisions": pending,
        "estimated_cost_usd": round(run.estimated_cost_usd or 0, 4) if run else 0,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _needs_attention(org_id):
    items = []
    org = db.session.get(Organization, org_id)
    if org.automation_paused:
        items.append({"severity": "warning", "title": "All agents are paused",
                      "detail": "No new agent work will start.", "link": "/app/operations"})
    if org.kill_switch_enabled:
        items.append({"severity": "warning", "title": "Kill switch is on",
                      "detail": "Exports and handoffs are blocked.", "link": "/app/operations"})
    profile = org.business_profile
    missing = profile.completeness_warnings() if profile else ["business_profile"]
    if missing:
        items.append({"severity": "warning", "title": "Brand profile incomplete",
                      "detail": f"Missing: {', '.join(m.replace('_', ' ') for m in missing)}.", "link": "/app/onboarding"})
    failed = Task.query.filter_by(organization_id=org_id, status="failed").count()
    if failed:
        items.append({"severity": "error", "title": f"{failed} agent task(s) failed",
                      "detail": "Retry them after fixing the cause.", "link": "/app/tasks?status=failed"})
    waiting = WorkflowRun.query.filter_by(organization_id=org_id, status="awaiting_approval").count()
    if waiting:
        items.append({"severity": "warning", "title": f"{waiting} run(s) waiting to start",
                      "detail": "Your policy requires approval before agents begin.", "link": "/app/campaigns"})
    pending = Approval.query.filter_by(organization_id=org_id, decision="pending").count()
    if pending:
        items.append({"severity": "info", "title": f"{pending} approval(s) waiting",
                      "detail": "Review exact versions before export.", "link": "/app/approvals"})
    proposed = KnowledgeEntry.query.filter_by(organization_id=org_id, status="proposed").count()
    if proposed:
        items.append({"severity": "info", "title": f"{proposed} proposed learning(s)",
                      "detail": "Approve them so agents can use them.", "link": "/app/knowledge?status=proposed"})
    return items


def _upcoming(org_id):
    today = datetime.now(timezone.utc).date()
    rows = (CalendarEntry.query.filter(CalendarEntry.organization_id == org_id,
                                       CalendarEntry.scheduled_date >= today,
                                       CalendarEntry.scheduled_date <= today + timedelta(days=14))
            .order_by(CalendarEntry.scheduled_date).limit(8).all())
    return [r.to_dict() for r in rows]


def _recent_deliverables(org_id, campaign_id):
    q = Deliverable.query.filter_by(organization_id=org_id)
    if campaign_id:
        q = q.filter_by(campaign_id=campaign_id)
    names = {c.id: c.name for c in Campaign.query.filter_by(organization_id=org_id)}
    return [{"id": d.id, "deliverable_type": d.deliverable_type, "review_status": d.review_status,
             "campaign_id": d.campaign_id, "campaign_name": names.get(d.campaign_id),
             "created_at": d.created_at.isoformat() if d.created_at else None}
            for d in q.order_by(Deliverable.created_at.desc()).limit(6).all()]


def _recommendations(org_id, campaigns):
    recs = []
    if not campaigns:
        recs.append({"title": "Create your first campaign", "detail": "Give your team a brief to work from.",
                     "link": "/app/campaigns/new", "action": "Create campaign"})
    for c in campaigns[:5]:
        run = WorkflowRun.query.filter_by(campaign_id=c.id).order_by(WorkflowRun.created_at.desc()).first()
        if run is None:
            recs.append({"title": f"Run the department on “{c.name}”", "detail": "No run yet for this campaign.",
                         "link": f"/app/campaigns/{c.id}", "action": "Open campaign"})
        elif run.status == "completed":
            social = Deliverable.query.filter_by(campaign_id=c.id, deliverable_type="social_calendar").first()
            if social and not CalendarEntry.query.filter_by(deliverable_id=social.id).first():
                recs.append({"title": f"Schedule “{c.name}” social posts",
                             "detail": "Add the Social Media agent's calendar to your content calendar.",
                             "link": f"/app/campaigns/{c.id}/deliverables", "action": "Review posts"})
    if not KnowledgeEntry.query.filter_by(organization_id=org_id).count():
        recs.append({"title": "Add brand knowledge", "detail": "FAQs and product facts make every agent sharper.",
                     "link": "/app/knowledge", "action": "Open knowledge"})
    return recs[:5]


def platform_analytics(organization_id: str, days: int = 30) -> dict:
    start, _end, _prev = _window(days)
    execs = AgentExecution.query.filter(AgentExecution.organization_id == organization_id,
                                        AgentExecution.started_at >= start).all()
    durations = [(e.finished_at - e.started_at).total_seconds() for e in execs if e.finished_at and e.started_at]
    succeeded = sum(1 for e in execs if e.status == "succeeded")
    failed = sum(1 for e in execs if e.status == "failed")
    decided = Approval.query.filter(Approval.organization_id == organization_id, Approval.decided_at.isnot(None),
                                    Approval.created_at >= start).all()
    turnaround = [(a.decided_at - a.created_at).total_seconds() / 3600 for a in decided if a.created_at]
    runs = WorkflowRun.query.filter(WorkflowRun.organization_id == organization_id, WorkflowRun.status == "completed",
                                    WorkflowRun.created_at >= start).all()
    completion = [(r.completed_at - r.started_at).total_seconds() / 60 for r in runs if r.completed_at and r.started_at]
    by_error = defaultdict(int)
    for e in execs:
        if e.status == "failed":
            by_error[e.error_code or "unknown"] += 1
    return {
        "range_days": days,
        "basis": "observed (costs are estimates)",
        "executions": len(execs),
        "success_rate_pct": round(succeeded / len(execs) * 100, 1) if execs else None,
        "retry_rate_pct": round(failed / len(execs) * 100, 1) if execs else None,
        "avg_execution_seconds": round(sum(durations) / len(durations), 1) if durations else None,
        "tokens": sum((e.input_tokens or 0) + (e.output_tokens or 0) for e in execs),
        "estimated_cost_usd": round(sum(e.estimated_cost_usd or 0 for e in execs), 4),
        "avg_approval_turnaround_hours": round(sum(turnaround) / len(turnaround), 2) if turnaround else None,
        "avg_run_completion_minutes": round(sum(completion) / len(completion), 1) if completion else None,
        "failures_by_reason": dict(by_error),
        "series": _daily_series(organization_id, start, days, None),
        "cost_by_agent": _cost_by_agent(organization_id, start, None),
        "audit_events": AuditEvent.query.filter(AuditEvent.organization_id == organization_id,
                                                AuditEvent.created_at >= start).count(),
    }
