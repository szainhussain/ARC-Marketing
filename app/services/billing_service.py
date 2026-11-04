"""Subscription lifecycle driven only by verified payment events."""

import json
from datetime import timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.billing.providers import get_payment_provider
from app.extensions import db
from app.models.agent_execution import AgentExecution
from app.models.base import utcnow
from app.models.billing import BillingEvent
from app.models.organization import Organization
from app.models.platform import Notification, Plan
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, ValidationError
from app.services.platform_service import _month_start, get_subscription, notify, usage_against_entitlements


def start_checkout(organization_id: str, plan_code: str) -> dict:
    plan = Plan.query.filter_by(code=plan_code, is_public=True).first()
    if plan is None:
        raise ValidationError("Unknown plan.", details=[{"field": "plan_code", "issue": "Unknown"}])
    if plan.monthly_price_usd is None:
        raise ValidationError("Enterprise plans are arranged through sales. Use the contact form.")
    _check_downgrade_fits(organization_id, plan)
    origin = current_app.config["FRONTEND_ORIGIN"]
    provider = get_payment_provider(current_app.config)
    return provider.create_checkout(
        organization_id, plan.code, plan.stripe_price_ref,
        success_url=f"{origin}/app/billing?checkout=success", cancel_url=f"{origin}/app/billing?checkout=cancelled",
    )


def _check_downgrade_fits(organization_id: str, plan: Plan) -> None:
    usage = usage_against_entitlements(organization_id)
    problems = []
    for key in ("seats", "active_campaigns", "knowledge_entries"):
        limit = plan.entitlements.get(key)
        used = (usage.get(key) or {}).get("used") or 0
        if limit is not None and used > limit:
            problems.append(f"{key.replace('_', ' ')}: using {used}, {plan.name} allows {limit}")
    if problems:
        raise Conflict("This workspace uses more than the new plan allows. Reduce usage first: " + "; ".join(problems))


def handle_webhook(payload: bytes, signature_header: str | None) -> dict:
    provider = get_payment_provider(current_app.config)
    event = provider.parse_webhook(payload, signature_header)  # raises SignatureError
    return process_event(provider.name, event, is_test=not event.get("livemode", False))


def process_event(provider_name: str, event: dict, is_test: bool) -> dict:
    event_id, event_type = event.get("id"), event.get("type")
    if not event_id or not event_type:
        raise ValidationError("Malformed billing event.")
    if BillingEvent.query.filter_by(provider=provider_name, event_id=event_id).first():
        return {"status": "duplicate_ignored"}
    obj = (event.get("data") or {}).get("object") or {}
    meta = obj.get("metadata") or {}
    org_id = meta.get("organization_id") or obj.get("client_reference_id")
    org = db.session.get(Organization, org_id) if org_id else None

    outcome = "ignored_unhandled_type"
    amount = None
    if org is not None:
        sub = get_subscription(org.id)
        if event_type in ("checkout.session.completed", "customer.subscription.updated"):
            plan = Plan.query.filter_by(code=meta.get("plan_code")).first()
            if plan:
                sub.plan_id = plan.id
                sub.status = "active"
                sub.billing_provider_ref = obj.get("subscription") or obj.get("id")
                sub.current_period_start = utcnow()
                sub.current_period_end = utcnow() + timedelta(days=30)
                outcome = "subscription_activated"
                notify(org.id, "billing.activated", f"Subscription active: {plan.name}",
                       "Your plan limits have been updated.", link="/app/billing", severity="success")
        elif event_type == "invoice.paid":
            amount = (obj.get("amount_paid") or 0) / 100
            sub.status = "active"
            outcome = "invoice_recorded"
        elif event_type == "invoice.payment_failed":
            sub.status = "past_due"
            outcome = "marked_past_due"
            notify(org.id, "billing.payment_failed", "A subscription payment failed",
                   "Update your payment method to avoid interruption.", link="/app/billing", severity="error")
        elif event_type == "customer.subscription.deleted":
            sub.status = "cancelled"
            outcome = "subscription_cancelled"
        if outcome != "ignored_unhandled_type":
            record_audit_event(org.id, f"billing.{outcome}", target_type="subscription", target_id=sub.id,
                               metadata={"event": event_type, "test": is_test})
    else:
        outcome = "ignored_unknown_workspace"

    db.session.add(BillingEvent(provider=provider_name, event_id=event_id, event_type=event_type,
                                organization_id=org.id if org else None, amount_usd=amount, is_test=is_test,
                                payload_json=json.dumps(event)[:20000], outcome=outcome))
    try:
        db.session.commit()
    except IntegrityError:  # concurrent duplicate delivery
        db.session.rollback()
        return {"status": "duplicate_ignored"}
    return {"status": outcome}


def billing_history(organization_id: str) -> list[dict]:
    rows = (BillingEvent.query.filter_by(organization_id=organization_id)
            .order_by(BillingEvent.created_at.desc()).limit(50).all())
    return [r.to_dict() for r in rows]


def month_ai_cost(organization_id: str) -> float:
    from sqlalchemy import func

    return float(db.session.query(func.coalesce(func.sum(AgentExecution.estimated_cost_usd), 0.0))
                 .filter(AgentExecution.organization_id == organization_id,
                         AgentExecution.started_at >= _month_start()).scalar() or 0.0)


def check_budget_alerts(organization_id: str) -> None:
    """Notify once per month when estimated AI cost crosses 80% / 100% of
    the plan's monthly AI budget."""

    limit = get_subscription(organization_id).plan.entitlements.get("monthly_ai_budget_usd")
    if not limit:
        return
    spent = month_ai_cost(organization_id)
    for pct, severity in ((100, "error"), (80, "warning")):
        if spent >= limit * pct / 100:
            kind = f"budget.threshold_{pct}"
            already = Notification.query.filter(Notification.organization_id == organization_id,
                                                Notification.kind == kind,
                                                Notification.created_at >= _month_start()).first()
            if not already:
                notify(organization_id, kind, f"AI usage reached {pct}% of this month's budget",
                       f"Estimated ${spent:.2f} of ${limit:.2f}."
                       + (" New agent work is paused until next month or an upgrade." if pct == 100 else ""),
                       link="/app/settings/usage", severity=severity)
                from app.services.webhook_service import emit

                emit(organization_id, "budget.threshold", {"percent": pct, "spent_usd": round(spent, 4),
                                                           "limit_usd": limit})
            break
