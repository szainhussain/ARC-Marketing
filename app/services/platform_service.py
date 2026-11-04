"""Plans & entitlements, notifications, action policies, knowledge."""

import json
from datetime import datetime, timezone

from app.extensions import db
from app.models.base import utcnow
from app.models.campaign import Campaign
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.platform import (
    ACTION_POLICY_DEFAULTS,
    POLICY_MODES,
    ActionPolicy,
    Invitation,
    KnowledgeEntry,
    Notification,
    Plan,
    Subscription,
)
from app.services.errors import PermissionDenied, RateLimited, ValidationError

# Provisional: prices and limits are placeholders until commercial terms
# are approved (docs/BILLING_AND_PLANS.md). Editing these rows in the
# database changes plans without a deploy.
DEFAULT_PLANS = [
    {
        "code": "launch", "name": "Launch", "sort_order": 1, "monthly_price_usd": 149.0,
        "tagline": "Core autonomous marketing for small businesses.",
        "entitlements": {"monthly_workflow_runs": 10, "seats": 2, "active_campaigns": 3,
                         "knowledge_entries": 100, "max_run_budget_usd": 1.0, "agents": 12,
                         "monthly_ai_budget_usd": 10.0, "monthly_agent_executions": 300, "monthly_exports": 50},
        "features": ["All 12 agents", "Approval inbox", "Manual export to Meta, Google Ads, TikTok",
                     "Operations Center"],
        "overage_note": "Additional runs are not sold yet; the workspace pauses new runs at the limit.",
    },
    {
        "code": "growth", "name": "Growth", "sort_order": 2, "monthly_price_usd": 399.0,
        "tagline": "More campaigns, bigger budgets, deeper analytics.",
        "entitlements": {"monthly_workflow_runs": 40, "seats": 5, "active_campaigns": 10,
                         "knowledge_entries": 1000, "max_run_budget_usd": 3.0, "agents": 12,
                         "monthly_ai_budget_usd": 40.0, "monthly_agent_executions": 1500, "monthly_exports": 300},
        "features": ["Everything in Launch", "Content calendar", "Knowledge library",
                     "Per-agent budgets"],
        "overage_note": "Overage pricing to be confirmed.",
    },
    {
        "code": "scale", "name": "Scale", "sort_order": 3, "monthly_price_usd": 999.0,
        "tagline": "Advanced automation, team permissions, larger workloads.",
        "entitlements": {"monthly_workflow_runs": 150, "seats": 15, "active_campaigns": 50,
                         "knowledge_entries": 10000, "max_run_budget_usd": 10.0, "agents": 12,
                         "monthly_ai_budget_usd": 150.0, "monthly_agent_executions": 6000, "monthly_exports": 2000},
        "features": ["Everything in Growth", "Approver and Analyst roles", "Higher concurrency"],
        "overage_note": "Overage pricing to be confirmed.",
    },
    {
        "code": "enterprise", "name": "Enterprise", "sort_order": 4, "monthly_price_usd": None,
        "tagline": "Custom governance, deployment options and commercial terms.",
        "entitlements": {"monthly_workflow_runs": None, "seats": None, "active_campaigns": None,
                         "knowledge_entries": None, "max_run_budget_usd": None, "agents": 12,
                         "monthly_ai_budget_usd": None, "monthly_agent_executions": None, "monthly_exports": None},
        "features": ["Everything in Scale", "Custom limits", "Dedicated support (by agreement)"],
        "overage_note": "By agreement.",
    },
]
DEFAULT_PLAN_CODE = "launch"


def ensure_plans_seeded() -> None:
    if Plan.query.count():
        return
    for p in DEFAULT_PLANS:
        db.session.add(Plan(
            code=p["code"], name=p["name"], tagline=p["tagline"], sort_order=p["sort_order"],
            monthly_price_usd=p["monthly_price_usd"], price_is_provisional=True,
            entitlements_json=json.dumps(p["entitlements"]), features_json=json.dumps(p["features"]),
            overage_note=p["overage_note"],
        ))
    db.session.flush()


def public_plans() -> list[Plan]:
    ensure_plans_seeded()
    db.session.commit()
    return Plan.query.filter_by(is_public=True).order_by(Plan.sort_order).all()


def get_subscription(organization_id: str) -> Subscription:
    sub = Subscription.query.filter_by(organization_id=organization_id).first()
    if sub is None:
        ensure_plans_seeded()
        plan = Plan.query.filter_by(code=DEFAULT_PLAN_CODE).first()
        from datetime import timedelta

        from flask import current_app

        sub = Subscription(organization_id=organization_id, plan_id=plan.id, status="trialing",
                           current_period_start=utcnow(),
                           current_period_end=utcnow() + timedelta(days=current_app.config.get("TRIAL_DAYS", 14)))
        db.session.add(sub)
        db.session.flush()
    return sub


def entitlements(organization_id: str) -> dict:
    return get_subscription(organization_id).plan.entitlements


def _month_start() -> datetime:
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_against_entitlements(organization_id: str) -> dict:
    from sqlalchemy import func

    from app.models.agent_execution import AgentExecution
    from app.models.external_action import ExternalAction
    from app.models.workflow_run import WorkflowRun

    limits = entitlements(organization_id)
    month = _month_start()
    used = {
        "monthly_workflow_runs": WorkflowRun.query.filter(
            WorkflowRun.organization_id == organization_id, WorkflowRun.created_at >= _month_start()
        ).count(),
        "seats": Membership.query.filter_by(organization_id=organization_id).count()
        + Invitation.query.filter(
            Invitation.organization_id == organization_id,
            Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None),
            Invitation.expires_at > utcnow(),
        ).count(),
        "active_campaigns": Campaign.query.filter(
            Campaign.organization_id == organization_id, Campaign.status != "archived"
        ).count(),
        "knowledge_entries": KnowledgeEntry.query.filter(
            KnowledgeEntry.organization_id == organization_id, KnowledgeEntry.status != "archived"
        ).count(),
        "monthly_ai_budget_usd": round(float(db.session.query(
            func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0)).filter(
            AgentExecution.organization_id == organization_id, AgentExecution.started_at >= month).scalar() or 0), 4),
        "monthly_agent_executions": AgentExecution.query.filter(
            AgentExecution.organization_id == organization_id, AgentExecution.started_at >= month).count(),
        "monthly_exports": ExternalAction.query.filter(
            ExternalAction.organization_id == organization_id, ExternalAction.created_at >= month).count(),
        "agents": 12,
    }
    return {k: {"used": used.get(k), "limit": limits.get(k)} for k in limits}


def check_entitlement(organization_id: str, key: str, adding: int = 1) -> None:
    usage = usage_against_entitlements(organization_id).get(key)
    if not usage or usage["limit"] is None:
        return
    if usage["used"] + adding > usage["limit"]:
        label = key.replace("_", " ")
        raise RateLimited(
            f"Your plan allows {usage['limit']} {label}; this workspace has used {usage['used']}. "
            "Upgrade the plan in Billing to continue."
        )


def change_plan(organization_id: str, plan_code: str) -> Subscription:
    plan = Plan.query.filter_by(code=plan_code, is_public=True).first()
    if plan is None:
        raise ValidationError("Unknown plan.", details=[{"field": "plan_code", "issue": "Unknown"}])
    if plan.monthly_price_usd is None:
        raise ValidationError("Enterprise plans are arranged through sales. Use the contact form.")
    sub = get_subscription(organization_id)
    sub.plan_id = plan.id
    db.session.flush()
    return sub


# ---- Notifications -------------------------------------------------------

def notify(organization_id: str, kind: str, title: str, body: str | None = None,
           link: str | None = None, severity: str = "info", user_id: str | None = None) -> Notification:
    n = Notification(organization_id=organization_id, kind=kind, title=title[:255], body=body,
                     link=link, severity=severity, user_id=user_id)
    db.session.add(n)
    return n


# ---- Action policies -----------------------------------------------------

def get_policy_mode(organization_id: str, action_type: str) -> str:
    default = ACTION_POLICY_DEFAULTS[action_type]
    if default["locked"]:
        return default["mode"]
    row = ActionPolicy.query.filter_by(organization_id=organization_id, action_type=action_type).first()
    return row.mode if row else default["mode"]


def list_policies(organization_id: str) -> list[dict]:
    return [
        {"action_type": key, "label": d["label"], "mode": get_policy_mode(organization_id, key),
         "default_mode": d["mode"], "locked": d["locked"], "enforced_by": d["enforced_by"]}
        for key, d in ACTION_POLICY_DEFAULTS.items()
    ]


def set_policy(organization_id: str, action_type: str, mode: str, user_id: str) -> None:
    if action_type not in ACTION_POLICY_DEFAULTS:
        raise ValidationError("Unknown action type.")
    if ACTION_POLICY_DEFAULTS[action_type]["locked"]:
        raise PermissionDenied("This policy is a platform safety boundary and cannot be changed.")
    if mode not in POLICY_MODES or mode == "blocked":
        raise ValidationError("Mode must be 'auto' or 'require_approval'.")
    row = ActionPolicy.query.filter_by(organization_id=organization_id, action_type=action_type).first()
    if row is None:
        row = ActionPolicy(organization_id=organization_id, action_type=action_type, mode=mode)
        db.session.add(row)
    row.mode = mode
    row.updated_by_user_id = user_id


# ---- Knowledge -----------------------------------------------------------

def approved_knowledge_for_agents(organization_id: str, limit: int = 8) -> list[dict]:
    """Small, recent, approved slice — never the whole library."""

    rows = (
        KnowledgeEntry.query.filter_by(organization_id=organization_id, status="approved")
        .order_by(KnowledgeEntry.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [{"title": r.title, "kind": r.kind, "note": r.body[:400]} for r in rows]


def propose_knowledge_from_record(organization_id: str, run_id: str, deliverable_id: str,
                                  record: dict) -> int:
    auto = get_policy_mode(organization_id, "knowledge_update") == "auto"
    created = 0
    for update in (record.get("knowledge_updates") or [])[:10]:
        if not isinstance(update, str) or not update.strip():
            continue
        db.session.add(KnowledgeEntry(
            organization_id=organization_id, kind="campaign_learning",
            title=update.strip()[:120], body=update.strip(),
            status="approved" if auto else "proposed",
            source_run_id=run_id, source_deliverable_id=deliverable_id,
        ))
        created += 1
    return created


def org_or_404(organization_id: str) -> Organization:
    return db.session.get(Organization, organization_id)
