"""Record campaign results and derive the metrics clients care about.
Ratios are only computed when both sides exist, and never invented."""

from datetime import date, datetime

from app.extensions import db
from app.models.campaign import Campaign
from app.models.results import METRIC_FIELDS, CampaignResult
from app.services.audit_service import record_audit_event
from app.services.errors import NotFound, ValidationError


def _invalid(details):
    raise ValidationError("Please correct the highlighted fields.", details=details)


def _parse_date(v, field):
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        _invalid([{"field": field, "issue": "Use YYYY-MM-DD"}])


def _validate(organization_id: str, p: dict, partial: bool = False) -> dict:
    out, errors = {}, []
    if not partial or "campaign_id" in p:
        c = Campaign.query.filter_by(id=p.get("campaign_id"), organization_id=organization_id).first()
        if c is None:
            errors.append({"field": "campaign_id", "issue": "Choose a campaign in this workspace"})
        else:
            out["campaign_id"] = c.id
    if not partial or "channel" in p:
        channel = (p.get("channel") or "").strip()
        if not channel:
            errors.append({"field": "channel", "issue": "Required"})
        out["channel"] = channel[:64]
    for f in ("period_start", "period_end"):
        if not partial or f in p:
            out[f] = _parse_date(p.get(f), f)
    for f in METRIC_FIELDS:
        if f in p:
            v = p.get(f)
            if v in (None, ""):
                out[f] = None
                continue
            try:
                num = float(v)
            except (TypeError, ValueError):
                errors.append({"field": f, "issue": "Must be a number"})
                continue
            if num < 0:
                errors.append({"field": f, "issue": "Can't be negative"})
            out[f] = num
    if "notes" in p:
        out["notes"] = (p.get("notes") or "")[:2000] or None
    if errors:
        _invalid(errors)
    if out.get("period_start") and out.get("period_end") and out["period_end"] < out["period_start"]:
        _invalid([{"field": "period_end", "issue": "Must be on or after the start date"}])
    if not partial and not any(out.get(f) is not None for f in METRIC_FIELDS):
        _invalid([{"field": "spend", "issue": "Enter at least one number"}])
    return out


def create_result(organization_id: str, user_id: str, p: dict) -> CampaignResult:
    row = CampaignResult(organization_id=organization_id, entered_by_user_id=user_id, **_validate(organization_id, p))
    db.session.add(row)
    db.session.flush()
    record_audit_event(organization_id, "result.recorded", actor_user_id=user_id, target_type="campaign", target_id=row.campaign_id)
    db.session.commit()
    return row


def _get(organization_id: str, result_id: str) -> CampaignResult:
    row = CampaignResult.query.filter_by(id=result_id, organization_id=organization_id).first()
    if row is None:
        raise NotFound("Result not found.")
    return row


def update_result(organization_id: str, result_id: str, user_id: str, p: dict) -> CampaignResult:
    row = _get(organization_id, result_id)
    for k, v in _validate(organization_id, p, partial=True).items():
        setattr(row, k, v)
    if row.period_end < row.period_start:
        _invalid([{"field": "period_end", "issue": "Must be on or after the start date"}])
    record_audit_event(organization_id, "result.updated", actor_user_id=user_id, target_type="campaign", target_id=row.campaign_id)
    db.session.commit()
    return row


def delete_result(organization_id: str, result_id: str, user_id: str) -> None:
    row = _get(organization_id, result_id)
    db.session.delete(row)
    record_audit_event(organization_id, "result.deleted", actor_user_id=user_id, target_type="campaign", target_id=row.campaign_id)
    db.session.commit()


def _ratio(a, b, scale=1.0):
    return round(a / b * scale, 4) if a is not None and b else None


def derive(t: dict) -> dict:
    return {
        **t,
        "ctr_pct": _ratio(t.get("clicks"), t.get("impressions"), 100),
        "conversion_rate_pct": _ratio(t.get("conversions"), t.get("clicks"), 100),
        "cost_per_lead": _ratio(t.get("spend"), t.get("leads")),
        "cost_per_acquisition": _ratio(t.get("spend"), t.get("conversions")),
        "roas": _ratio(t.get("revenue"), t.get("spend")),
    }


def _sum(rows) -> dict:
    out = {}
    for f in METRIC_FIELDS:
        vals = [getattr(r, f) for r in rows if getattr(r, f) is not None]
        out[f] = round(sum(vals), 2) if vals else None
    return out


def summarize(organization_id: str, start: date | None = None, end: date | None = None,
              campaign_id: str | None = None) -> dict:
    q = CampaignResult.query.filter_by(organization_id=organization_id)
    if campaign_id:
        q = q.filter_by(campaign_id=campaign_id)
    if start:
        q = q.filter(CampaignResult.period_end >= start)
    if end:
        q = q.filter(CampaignResult.period_start <= end)
    rows = q.order_by(CampaignResult.period_start.desc()).all()
    names = {c.id: c.name for c in Campaign.query.filter_by(organization_id=organization_id)}

    def group(key):
        buckets = {}
        for r in rows:
            buckets.setdefault(key(r), []).append(r)
        return buckets

    by_channel = [{"channel": k, **derive(_sum(v))} for k, v in group(lambda r: r.channel).items()]
    by_campaign = [{"campaign_id": k, "campaign_name": names.get(k), **derive(_sum(v))}
                   for k, v in group(lambda r: r.campaign_id).items()]
    by_channel.sort(key=lambda x: -(x.get("revenue") or x.get("leads") or 0))
    return {
        "source": "manual",
        "totals": derive(_sum(rows)),
        "by_channel": by_channel,
        "by_campaign": by_campaign,
        "results": [{**r.to_dict(), "campaign_name": names.get(r.campaign_id)} for r in rows],
    }


def monthly_report(organization_id: str, month: str) -> dict:
    """A client-ready summary of one calendar month: results the team
    recorded, what the department produced, and what was learned."""

    import calendar
    from datetime import timezone

    from sqlalchemy import func

    from app.models.agent_execution import AgentExecution
    from app.models.approval import Approval
    from app.models.deliverable import Deliverable
    from app.models.external_action import ExternalAction
    from app.models.organization import Organization
    from app.models.platform import KnowledgeEntry
    from app.models.workflow_run import WorkflowRun

    try:
        year, mon = (int(x) for x in month.split("-"))
        first = date(year, mon, 1)
    except (ValueError, AttributeError):
        _invalid([{"field": "month", "issue": "Use YYYY-MM"}])
    last = date(year, mon, calendar.monthrange(year, mon)[1])
    t0 = datetime(year, mon, 1, tzinfo=timezone.utc)
    t1 = datetime(last.year, last.month, last.day, 23, 59, 59, tzinfo=timezone.utc)

    def between(model, col):
        return model.query.filter(model.organization_id == organization_id, col >= t0, col <= t1)

    results = summarize(organization_id, first, last)
    org = db.session.get(Organization, organization_id)
    cost = db.session.query(func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0)).filter(
        AgentExecution.organization_id == organization_id, AgentExecution.started_at >= t0,
        AgentExecution.started_at <= t1).scalar()
    ranked = [c for c in results["by_channel"] if c.get("cost_per_lead") is not None]
    ranked.sort(key=lambda c: c["cost_per_lead"])
    best_roas = sorted([c for c in results["by_channel"] if c.get("roas") is not None], key=lambda c: -c["roas"])
    highlights = []
    if best_roas:
        highlights.append(f"Best return on ad spend: {best_roas[0]['channel']} ({best_roas[0]['roas']:.2f}x).")
    if ranked:
        highlights.append(f"Lowest cost per lead: {ranked[0]['channel']} (${ranked[0]['cost_per_lead']:.2f}).")
        if len(ranked) > 1:
            highlights.append(f"Highest cost per lead: {ranked[-1]['channel']} (${ranked[-1]['cost_per_lead']:.2f}) — review targeting or creative.")
    return {
        "month": f"{year:04d}-{mon:02d}",
        "period": {"start": first.isoformat(), "end": last.isoformat()},
        "workspace_name": org.name if org else "",
        "results": results,
        "activity": {
            "runs_completed": between(WorkflowRun, WorkflowRun.completed_at).filter(WorkflowRun.status == "completed").count(),
            "deliverables_created": between(Deliverable, Deliverable.created_at).count(),
            "approvals_given": between(Approval, Approval.decided_at).filter(Approval.decision == "approved").count(),
            "exports": between(ExternalAction, ExternalAction.created_at).count(),
            "confirmed_published": between(ExternalAction, ExternalAction.publication_confirmed_at).count(),
            "ai_cost_usd": round(float(cost or 0), 4),
        },
        "learnings": [{"title": k.title, "kind": k.kind} for k in
                      between(KnowledgeEntry, KnowledgeEntry.created_at).filter(KnowledgeEntry.status == "approved")
                      .order_by(KnowledgeEntry.created_at.asc()).limit(20)],
        "highlights": highlights,
    }
